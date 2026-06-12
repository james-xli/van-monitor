"""
Bluetooth driver for the Anker Solix C1000 Gen 2, using our own protocol port.

This replaces the SolixBLE library for the Gen 2, which connects but never
delivers telemetry. See van_monitor/anker_g2_protocol.py for the protocol/crypto
details and why this is necessary.

Flow:
  1. Scan for / connect to the station with bleak.
  2. Subscribe to the telemetry characteristic (notifications).
  3. Send the negotiation init, then respond to each handshake step.
     - FIRST TIME ONLY: the station asks for a physical button press.
  4. Once negotiated, send the realtime trigger and wait for telemetry.
  5. Disconnect and return the reading.

The client UUID is persisted (config.ANKER_CLIENT_ID_FILE) so the button press
is only required the very first time you pair this Pi with the station.
"""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path

from bleak import BleakClient, BleakScanner

import config
from van_monitor.anker_g2_protocol import (
    UUID_COMMAND,
    UUID_IDENTIFIER,
    UUID_TELEMETRY,
    SolixProtocol,
)
from van_monitor.ble_util import find_device
from van_monitor.metrics import AnkerMetrics

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Persistent client id (so the button press is a one-time thing)
# ---------------------------------------------------------------------------


_DEFAULT_CLIENT_ID_FILE = Path(__file__).resolve().parents[2] / "data" / "anker_client_id.txt"


def _client_id_path() -> Path:
    configured = getattr(config, "ANKER_CLIENT_ID_FILE", "")
    return Path(configured) if configured else _DEFAULT_CLIENT_ID_FILE


def load_client_uuid() -> str | None:
    """Return the saved client UUID, or None if we have not paired yet."""
    path = _client_id_path()
    try:
        text = path.read_text().strip()
    except OSError:
        return None
    return text or None


def save_client_uuid(client_uuid: str) -> None:
    """Persist the client UUID so future connects skip the button press."""
    path = _client_id_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(client_uuid + "\n")
        logger.info("Anker: saved client id to %s", path)
    except OSError as exc:
        logger.warning("Anker: could not save client id (%s)", exc)


# ---------------------------------------------------------------------------
# Device discovery
# ---------------------------------------------------------------------------


async def _find_device(address: str | None):
    addr = (address or config.ANKER_ADDRESS).strip() or None
    timeout = config.BLE_TIMEOUT_SECONDS

    if addr:
        for attempt in range(1, config.ANKER_SCAN_RETRIES + 1):
            logger.info("Anker: scanning for %s (attempt %s/%s)...", addr, attempt, config.ANKER_SCAN_RETRIES)
            device = await find_device(addr, timeout=timeout)
            if device:
                return device
        return None

    logger.info("Anker: no address set; scanning for a Solix station...")
    device = await BleakScanner.find_device_by_filter(
        lambda d, adv: UUID_IDENTIFIER in (adv.service_uuids or [])
        or "C1000" in (d.name or "").upper()
        or "SOLIX" in (d.name or "").upper(),
        timeout=timeout,
    )
    return device


# ---------------------------------------------------------------------------
# Main read
# ---------------------------------------------------------------------------


async def read_anker_g2_async(
    address: str | None = None,
    *,
    telemetry_timeout: float | None = None,
    button_wait: float | None = None,
) -> AnkerMetrics:
    """Connect, run the handshake, read one telemetry snapshot, disconnect."""
    metrics = AnkerMetrics()
    telemetry_timeout = telemetry_timeout or config.ANKER_TELEMETRY_TIMEOUT_SECONDS
    button_wait = button_wait if button_wait is not None else getattr(config, "ANKER_BUTTON_WAIT_SECONDS", 180)

    device = await _find_device(address)
    if not device:
        metrics.error = (
            "Anker not found (wake the unit / close the Anker app, then retry)"
        )
        return metrics

    proto = SolixProtocol(client_uuid=load_client_uuid())
    # Persist the id immediately so it is reused even if pairing is interrupted.
    save_client_uuid(proto.client_uuid)

    loop = asyncio.get_running_loop()
    telemetry_event = asyncio.Event()
    outbound: asyncio.Queue[tuple[bytes, bool]] = asyncio.Queue()
    state = {"telemetry": None, "button_prompted": False, "command_no_response": False}

    def on_notify(_sender, data: bytearray) -> None:
        raw = bytes(data)
        logger.debug("Anker RX %s", raw.hex())
        result = proto.handle_notification(raw)
        if result.debug_message:
            logger.info("Anker: %s", result.debug_message)
        if result.waiting_for_button and not state["button_prompted"]:
            state["button_prompted"] = True
            _prompt_button(button_wait)
        if result.outbound_command:
            outbound.put_nowait((result.outbound_command, result.outbound_requires_response))
        if result.telemetry_updated and result.telemetry and result.telemetry.valid:
            state["telemetry"] = result.telemetry
            loop.call_soon_threadsafe(telemetry_event.set)

    client = BleakClient(device)
    try:
        logger.info("Anker: connecting to %s (%s)...", device.name, device.address)
        await client.connect()

        command_char = _find_char(client, UUID_COMMAND)
        telemetry_char = _find_char(client, UUID_TELEMETRY)
        if command_char is None or telemetry_char is None:
            metrics.error = "Anker GATT characteristics not found after connect"
            return metrics
        state["command_no_response"] = "write-without-response" in command_char.properties

        await client.start_notify(telemetry_char, on_notify)

        # Writer task: send outbound commands in order as the handshake demands.
        async def writer() -> None:
            while True:
                command, requires_response = await outbound.get()
                response = requires_response or not state["command_no_response"]
                try:
                    await client.write_gatt_char(command_char, command, response=response)
                    logger.debug("Anker TX %s (response=%s)", command.hex(), response)
                except Exception as exc:  # noqa: BLE001 - keep loop alive
                    logger.warning("Anker: write failed: %s", exc)

        writer_task = asyncio.create_task(writer())

        # Kick off the handshake.
        session_start = time.time()
        outbound.put_nowait((proto.build_negotiation_init(), True))

        # Wait for telemetry. Re-send the realtime trigger if it stalls, and
        # allow extra time while waiting for the physical button press.
        deadline = time.time() + telemetry_timeout
        last_trigger = 0.0
        while time.time() < deadline:
            try:
                await asyncio.wait_for(telemetry_event.wait(), timeout=2.0)
                break
            except asyncio.TimeoutError:
                pass

            if proto.is_waiting_for_button():
                # Extend the deadline so the user has time to press the button.
                deadline = max(deadline, time.time() + button_wait)
                continue

            if proto.is_negotiated() and (time.time() - last_trigger) > 8.0:
                # elapsed = seconds since the session timestamp was set, so the
                # request timestamp stays close to "now" (replay protection).
                elapsed = max(1, int(time.time() - session_start))
                trigger = proto.build_realtime_trigger(elapsed)
                if trigger:
                    outbound.put_nowait((trigger, False))
                last_trigger = time.time()

        writer_task.cancel()

        tel = state["telemetry"]
        if tel is None:
            phase = (
                "waiting for button press" if proto.is_waiting_for_button()
                else "negotiated" if proto.is_negotiated()
                else "negotiating"
            )
            metrics.error = f"No telemetry within {telemetry_timeout:.0f}s ({phase})"
            return metrics

        # Pairing succeeded: make sure the (now authorized) id is saved.
        save_client_uuid(proto.client_uuid)

        ac_in = tel.ac_power_in if tel.ac_power_in >= 0 else None
        solar_in = tel.solar_power_in if tel.solar_power_in >= 0 else None
        in_parts = [v for v in (ac_in, solar_in) if v is not None]

        metrics.connected = True
        metrics.soc_percent = tel.battery_percent if tel.battery_percent >= 0 else None
        metrics.power_in_w = sum(in_parts) if in_parts else None
        metrics.power_out_w = tel.total_power_out if tel.total_power_out >= 0 else None
        logger.info(
            "Anker: %s%% in=%sW out=%sW (sn=%s)",
            metrics.soc_percent if metrics.soc_percent is not None else config.UNAVAILABLE_LABEL,
            metrics.power_in_w if metrics.power_in_w is not None else config.UNAVAILABLE_LABEL,
            metrics.power_out_w if metrics.power_out_w is not None else config.UNAVAILABLE_LABEL,
            tel.serial_number or "?",
        )
    except Exception as exc:  # noqa: BLE001 - report instead of crashing the poll loop
        metrics.error = str(exc) or type(exc).__name__
        logger.warning("Anker: %s", metrics.error)
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass

    return metrics


def _find_char(client: BleakClient, uuid: str):
    for service in client.services:
        for char in service.characteristics:
            if char.uuid.lower() == uuid.lower():
                return char
    return None


def _prompt_button(button_wait: float) -> None:
    banner = (
        "\n"
        "============================================================\n"
        " ACTION NEEDED: press the physical power/IoT button on the\n"
        " Anker C1000 Gen 2 now to authorize this Raspberry Pi.\n"
        f" You have about {int(button_wait)} seconds. This is a ONE-TIME step;\n"
        " the pairing is remembered for future connections.\n"
        "============================================================\n"
    )
    logger.warning("Anker: PRESS THE BUTTON on the station to authorize (one-time).")
    print(banner, flush=True)
