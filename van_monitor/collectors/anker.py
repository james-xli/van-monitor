"""Read Anker Solix C1000 Gen 2 data over BLE."""

from __future__ import annotations

import asyncio
import logging
import time

from bleak import BleakScanner
from SolixBLE import C1000G2, discover_devices
from SolixBLE.const import DEFAULT_METADATA_INT

import config
from van_monitor.metrics import AnkerMetrics

logger = logging.getLogger(__name__)


def _valid_int(value: int) -> int | None:
    if value == DEFAULT_METADATA_INT:
        return None
    return value


async def _find_anker_device(address: str | None):
    if address:
        logger.info("Anker: looking for %s...", address)
        device = await BleakScanner.find_device_by_address(
            address, timeout=config.BLE_TIMEOUT_SECONDS
        )
        if device:
            return device
        return None

    logger.info("Anker: scanning for Solix devices...")
    devices = await discover_devices(timeout=config.BLE_TIMEOUT_SECONDS)
    return devices[0] if devices else None


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
    addr = (address or config.ANKER_ADDRESS).strip() or None
    wait_seconds = telemetry_timeout or config.ANKER_TELEMETRY_TIMEOUT_SECONDS

    device = await _find_anker_device(addr)
    if not device:
        metrics.error = "Anker Solix device not found"
        return metrics

    anker = C1000G2(device)
    try:
        logger.info("Anker: connecting to %s (%s)...", device.name, device.address)
        if not await anker.connect():
            metrics.error = "Connection or negotiation failed"
            return metrics

        deadline = time.time() + wait_seconds
        while time.time() < deadline:
            if anker.available:
                break
            await asyncio.sleep(0.5)

        if not anker.available:
            metrics.error = f"Connected but no telemetry within {wait_seconds:.0f}s"
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
        metrics.error = str(exc)
        logger.warning("Anker: %s", exc)
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
