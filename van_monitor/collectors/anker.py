"""Read Anker Solix C1000 Gen 2 data over BLE."""

from __future__ import annotations

import asyncio
import logging
import time

from SolixBLE import C1000G2, discover_devices
from SolixBLE.const import DEFAULT_METADATA_INT

import config
from van_monitor.ble_util import find_device
from van_monitor.metrics import AnkerMetrics

logger = logging.getLogger(__name__)

# Gen 2 (A1763): realtime trigger then optional status request (anker-solix-api BLE map).
_RT_CMD = bytes.fromhex("0057")
_RT_PAYLOAD = bytes.fromhex("a10122a2020101a305033c000000")  # enable, 60s window
_STATUS_G2_CMD = bytes.fromhex("0040")
_STATUS_G2_PAYLOAD = bytes.fromhex("a10122")

# Gen 1 (A1761) fallback.
_STATUS_G1_CMD = bytes.fromhex("4040")
_STATUS_G1_PAYLOAD = bytes.fromhex("a10121")


def _valid_int(value: int) -> int | None:
    if value == DEFAULT_METADATA_INT:
        return None
    return value


async def _find_anker_device(address: str | None):
    addr = (address or config.ANKER_ADDRESS).strip() or None
    scan_timeout = config.BLE_TIMEOUT_SECONDS

    if addr:
        retries = config.ANKER_SCAN_RETRIES
        for attempt in range(1, retries + 1):
            logger.info(
                "Anker: scanning for %s (attempt %s/%s, %.0fs)...",
                addr,
                attempt,
                retries,
                scan_timeout,
            )
            device = await find_device(addr, timeout=scan_timeout)
            if device:
                return device
        return None

    logger.info("Anker: no address configured; scanning for Solix devices...")
    devices = await discover_devices(timeout=int(scan_timeout))
    if not devices:
        return None

    if len(devices) == 1:
        return devices[0]

    for device in devices:
        name = (device.name or "").upper()
        if "C1000" in name or "SOLIX" in name:
            return device

    return devices[0]


async def _wait_for_telemetry(anker: C1000G2, *, timeout: float) -> bool:
    """Wait until the notification handler assembles telemetry."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if anker.available:
            return True
        await asyncio.sleep(0.5)
    return False


async def _request_status_update(anker: C1000G2, *, packet_timeout: float) -> bool:
    """
    Ask the unit for a status snapshot.

    Gen 2 (A1763) uses 0057 realtime trigger or 0040 status request — not the
    Gen 1 4040/c840 pair. Replies arrive as c402/c405 via the notify handler.
    """
    triggers = (
        ("realtime trigger 0057", _RT_CMD, _RT_PAYLOAD),
        ("status request 0040", _STATUS_G2_CMD, _STATUS_G2_PAYLOAD),
        ("Gen1 status 4040", _STATUS_G1_CMD, _STATUS_G1_PAYLOAD),
    )
    for label, cmd, payload in triggers:
        logger.info("Anker: sending %s...", label)
        await anker._send_command(cmd, payload)
        if await _wait_for_telemetry(anker, timeout=packet_timeout):
            return True
    return anker.available


async def read_anker_async(
    address: str | None = None,
    *,
    telemetry_timeout: float | None = None,
) -> AnkerMetrics:
    """
    Connect to the Anker, wait for telemetry, read values, and disconnect.

    Power in is AC input plus solar/DC input when both are reported.
    """
    metrics = AnkerMetrics()
    wait_seconds = telemetry_timeout or config.ANKER_TELEMETRY_TIMEOUT_SECONDS
    poll_timeout = min(15.0, wait_seconds / 6)

    device = await _find_anker_device(address)
    if not device:
        metrics.error = (
            "Anker Solix device not found "
            "(wake unit: IoT LED blinking, close Anker app, retry ble_scan.py)"
        )
        return metrics

    anker = C1000G2(device)
    try:
        logger.info("Anker: connecting to %s (%s)...", device.name, device.address)
        if not await anker.connect():
            metrics.error = "Connection or negotiation failed"
            return metrics

        logger.info("Anker: connected; waiting for initial telemetry...")
        await asyncio.sleep(2)
        if not anker.available:
            logger.info("Anker: polling status (up to %.0fs)...", wait_seconds)
            deadline = time.time() + wait_seconds
            attempt = 0
            while time.time() < deadline:
                if anker.available:
                    break
                attempt += 1
                logger.info("Anker: status poll %s...", attempt)
                try:
                    if await _request_status_update(anker, packet_timeout=poll_timeout):
                        break
                except Exception as exc:
                    logger.warning(
                        "Anker: status request failed: %s",
                        exc or type(exc).__name__,
                    )
                await asyncio.sleep(2)

        if not anker.available:
            state = "negotiated" if anker.negotiated else "not negotiated"
            metrics.error = (
                f"No telemetry within {wait_seconds:.0f}s ({state}; "
                "wake the unit / blink IoT LED / close Anker app)"
            )
            return metrics

        ac_in = _valid_int(anker.ac_power_in)
        solar_in = _valid_int(anker.solar_power_in)
        power_in_parts = [value for value in (ac_in, solar_in) if value is not None]
        power_in = sum(power_in_parts) if power_in_parts else None

        metrics.connected = True
        metrics.soc_percent = _valid_int(anker.battery_percentage)
        metrics.power_in_w = power_in
        metrics.power_out_w = _valid_int(anker.power_out)
        logger.info(
            "Anker: %.0f%% in=%sW out=%sW",
            metrics.soc_percent or 0,
            metrics.power_in_w if metrics.power_in_w is not None else config.UNAVAILABLE_LABEL,
            metrics.power_out_w if metrics.power_out_w is not None else config.UNAVAILABLE_LABEL,
        )
    except Exception as exc:
        metrics.error = str(exc) or type(exc).__name__
        logger.warning("Anker: %s", metrics.error)
    finally:
        await anker.disconnect()

    return metrics


def read_anker(
    address: str | None = None,
    *,
    telemetry_timeout: float | None = None,
) -> AnkerMetrics:
    """Synchronous wrapper around read_anker_async."""
    return asyncio.run(
        read_anker_async(address, telemetry_timeout=telemetry_timeout)
    )
