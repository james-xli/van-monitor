#!/usr/bin/env python3
"""Test the Anker Solix C1000 Gen 2 BLE connection."""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config
from van_monitor.collectors.anker import read_anker_async
from van_monitor.dashboard import MetricsDashboard
from van_monitor.metrics import VanMetrics, print_metrics
from SolixBLE import discover_devices
from van_monitor.util import setup_logging


async def discover_anker(timeout: float) -> int:
    print(f"Scanning for Anker Solix devices for {timeout:.0f}s...")
    devices = await discover_devices(timeout=int(timeout))
    if not devices:
        print("No Anker Solix devices found.")
        return 1

    print(f"{'ADDRESS':<20}  NAME")
    print("-" * 40)
    for device in devices:
        print(f"{device.address:<20}  {device.name or '(no name)'}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Test Anker Solix BLE readings")
    parser.add_argument("--address", help="Bluetooth MAC (overrides config.ANKER_ADDRESS)")
    parser.add_argument(
        "--discover",
        action="store_true",
        help="Scan for Anker Solix devices and print addresses",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=config.ANKER_TELEMETRY_TIMEOUT_SECONDS,
        help="Seconds to wait for telemetry after connecting",
    )
    parser.add_argument(
        "--display",
        action="store_true",
        help="Show the v4 dashboard on e-paper (Anker panel omitted from layout)",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument(
        "--debug-ble",
        action="store_true",
        help="Show bleak/SolixBLE debug (very noisy; use with -v)",
    )
    args = parser.parse_args()

    setup_logging(args.verbose, debug_ble=args.debug_ble)

    if args.discover:
        return asyncio.run(discover_anker(config.BLE_TIMEOUT_SECONDS))

    metrics = VanMetrics(
        anker=asyncio.run(
            read_anker_async(args.address, telemetry_timeout=args.timeout)
        )
    )
    metrics.updated_at = datetime.now()
    print_metrics(metrics)

    if args.display:
        dashboard = MetricsDashboard()
        dashboard.init(partial=False)
        dashboard.clear()
        dashboard.show_metrics(metrics, partial=False)
        dashboard.sleep()

    return 0 if metrics.anker.connected else 1


if __name__ == "__main__":
    raise SystemExit(main())
