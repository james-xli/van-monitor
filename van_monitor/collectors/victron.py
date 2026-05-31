"""Read Victron solar charger data from BLE advertisements."""

from __future__ import annotations

import asyncio
import logging

from victron_ble.devices import detect_device_type
from victron_ble.exceptions import UnknownDeviceError
from victron_ble.scanner import BaseScanner

import config
from van_monitor.metrics import VictronMetrics

logger = logging.getLogger(__name__)


class _VictronReader(BaseScanner):
    """Listen for one advertisement from a configured Victron device."""

    def __init__(self, address: str, key: str):
        super().__init__()
        self._address = address.lower()
        self._key = key
        self.result: VictronMetrics | None = None
        self.done = asyncio.Event()

    def callback(self, ble_device, raw_data, advertisement):
        if ble_device.address.lower() != self._address:
            return

        try:
            device_class = detect_device_type(raw_data)
            if not device_class:
                raise UnknownDeviceError(f"Unknown Victron device at {ble_device.address}")

            device = device_class(self._key)
            parsed = device.parse(raw_data)
            solar_power = parsed.get_solar_power() if hasattr(parsed, "get_solar_power") else None
            yield_today = (
                parsed.get_yield_today() if hasattr(parsed, "get_yield_today") else None
            )

            metrics = VictronMetrics(
                connected=True,
                solar_power_w=solar_power,
                yield_today_wh=yield_today,
            )
            self.result = metrics
            self.done.set()
            logger.info(
                "Victron: %.0fW, %.0f Wh today (RSSI %s)",
                solar_power or 0,
                yield_today or 0,
                advertisement.rssi,
            )
        except Exception as exc:
            self.result = VictronMetrics(error=str(exc))
            self.done.set()
            logger.warning("Victron: %s", exc)


async def read_victron_async(
    address: str | None = None,
    key: str | None = None,
    *,
    timeout: float | None = None,
) -> VictronMetrics:
    """
    Wait for a Victron Instant Readout advertisement and parse solar power.

    Requires VICTRON_ADDRESS and VICTRON_KEY in config.py (or pass them in).
    """
    addr = (address or config.VICTRON_ADDRESS).strip()
    adv_key = (key or config.VICTRON_KEY).strip()
    wait_seconds = timeout or config.BLE_TIMEOUT_SECONDS

    if not addr or not adv_key:
        return VictronMetrics(
            error="Set VICTRON_ADDRESS and VICTRON_KEY in config.py "
            "(Victron Connect -> Product Info -> Instant Readout -> Show)"
        )

    logger.info("Victron: listening for advertisements from %s...", addr)
    reader = _VictronReader(addr, adv_key)
    await reader.start()
    try:
        await asyncio.wait_for(reader.done.wait(), timeout=wait_seconds)
    except asyncio.TimeoutError:
        return VictronMetrics(
            error=f"No advertisement from {addr} in {wait_seconds:.0f}s "
            "(check key, range, and that Instant Readout is enabled)"
        )
    finally:
        await reader.stop()

    return reader.result or VictronMetrics(error="No data received")


def read_victron(
    address: str | None = None,
    key: str | None = None,
    *,
    timeout: float | None = None,
) -> VictronMetrics:
    """Synchronous wrapper around read_victron_async."""
    return asyncio.run(read_victron_async(address, key, timeout=timeout))
