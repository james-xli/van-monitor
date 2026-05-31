#!/usr/bin/env python3
"""Test the Victron MPPT BLE advertisement reader."""

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
from van_monitor.collectors.victron import read_victron_async
from van_monitor.dashboard import MetricsDashboard
from van_monitor.metrics import VanMetrics, print_metrics
from van_monitor.util import setup_logging


async def discover_victron(timeout: float) -> int:
    from victron_ble.scanner import DiscoveryScanner

    print(f"Listening for Victron advertisements for {timeout:.0f}s...")
    print("(Devices must have Instant Readout enabled in Victron Connect)")
    scanner = DiscoveryScanner()
    await scanner.start()
    try:
        await asyncio.sleep(timeout)
    finally:
        await scanner.stop()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Test Victron solar BLE readings")
    parser.add_argument("--address", help="Bluetooth MAC (overrides config.VICTRON_ADDRESS)")
    parser.add_argument("--key", help="Advertisement key (overrides config.VICTRON_KEY)")
    parser.add_argument(
        "--discover",
        action="store_true",
        help="Listen for Victron advertisements and print device IDs (no key needed)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=config.BLE_TIMEOUT_SECONDS,
        help="Seconds to wait for an advertisement",
    )
    parser.add_argument(
        "--display",
        action="store_true",
        help="Show this device's values on the e-paper display",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    setup_logging(args.verbose)

    if args.discover:
        return asyncio.run(discover_victron(args.timeout))

    metrics = VanMetrics(
        victron=asyncio.run(
            read_victron_async(args.address, args.key, timeout=args.timeout)
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

    return 0 if metrics.victron.connected else 1


if __name__ == "__main__":
    raise SystemExit(main())
