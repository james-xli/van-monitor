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

from van_monitor.util import setup_logging


async def scan(timeout: float) -> None:
    print(f"Scanning for {timeout:.0f}s...")
    devices = await BleakScanner.discover(timeout=timeout)
    devices = sorted(devices, key=lambda item: item.rssi or -999, reverse=True)

    if not devices:
        print("No devices found.")
        return

    print(f"{'ADDRESS':<20} {'RSSI':>5}  NAME")
    print("-" * 50)
    for device in devices:
        name = device.name or "(no name)"
        rssi = device.rssi if device.rssi is not None else "?"
        print(f"{device.address:<20} {rssi!s:>5}  {name}")


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
    asyncio.run(scan(args.timeout))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
