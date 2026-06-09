"""Small BLE helpers for reliable discovery on the Pi."""

from __future__ import annotations

from bleak import BleakScanner
from bleak.backends.device import BLEDevice


async def find_device(
    address: str,
    *,
    timeout: float,
    retries: int = 1,
) -> BLEDevice | None:
    """
    Find a device by MAC using an active scan.

    On Raspberry Pi / BlueZ this is more reliable than connecting to a stale
    address without a fresh scan.
    """
    target = address.lower()
    for _ in range(max(1, retries)):
        device = await BleakScanner.find_device_by_address(target, timeout=timeout)
        if device:
            return device

        discovered = await BleakScanner.discover(timeout=timeout)
        for candidate in discovered:
            if candidate.address.lower() == target:
                return candidate
    return None
