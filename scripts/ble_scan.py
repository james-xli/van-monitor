#!/usr/bin/env python3
"""Scan for nearby Bluetooth devices (names and MAC addresses)."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bleak import BleakScanner
from bleak.exc import BleakBluetoothNotAvailableError

from van_monitor.util import setup_logging

_BLUETOOTH_HELP = """
Bluetooth is not available on this Pi.

Run the diagnostic script:
  bash scripts/check_bluetooth.sh

Common fixes:
  sudo apt install -y pi-bluetooth bluez
  sudo raspi-config  -> Interface Options -> Bluetooth -> Enable  (reboot)
  sudo rfkill unblock bluetooth
  sudo systemctl restart hciuart bluetooth
  sudo hciconfig hci0 up
  sudo bluetoothctl power on

Remove dtoverlay=disable-bt from /boot/firmware/config.txt if present.
"""


async def scan(timeout: float) -> None:
    print(f"Scanning for {timeout:.0f}s...")
    discovered = await BleakScanner.discover(timeout=timeout, return_adv=True)

    rows: list[tuple[int | None, str, str]] = []
    for device, advertisement in discovered.values():
        rows.append(
            (advertisement.rssi, device.address, device.name or "(no name)")
        )

    rows.sort(key=lambda row: row[0] if row[0] is not None else -999, reverse=True)

    if not rows:
        print("No devices found.")
        return

    print(f"{'ADDRESS':<20} {'RSSI':>5}  NAME")
    print("-" * 50)
    for rssi, address, name in rows:
        rssi_text = rssi if rssi is not None else "?"
        print(f"{address:<20} {rssi_text!s:>5}  {name}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan for nearby BLE devices")
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="Seconds to scan (default: 10)",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    setup_logging(args.verbose)
    try:
        asyncio.run(scan(args.timeout))
    except BleakBluetoothNotAvailableError as exc:
        print(f"Error: {exc}")
        print(_BLUETOOTH_HELP)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
