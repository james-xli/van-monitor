#!/usr/bin/env python3
"""Test the Li-Time house battery BLE connection."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from van_monitor.collectors.litime import read_litime
from van_monitor.dashboard import MetricsDashboard
from van_monitor.metrics import VanMetrics, print_metrics
from van_monitor.util import setup_logging


def main() -> int:
    parser = argparse.ArgumentParser(description="Test Li-Time battery BLE readings")
    parser.add_argument(
        "--address",
        help="Bluetooth MAC (overrides config.LITIME_ADDRESS)",
    )
    parser.add_argument(
        "--display",
        action="store_true",
        help="Show this device's values on the e-paper display",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    setup_logging(args.verbose)
    metrics = VanMetrics(litime=read_litime(args.address))
    metrics.updated_at = datetime.now()
    print_metrics(metrics)

    if args.display:
        dashboard = MetricsDashboard()
        dashboard.init(partial=False)
        dashboard.clear()
        dashboard.show_metrics(metrics, partial=False)
        dashboard.sleep()

    return 0 if metrics.litime.connected else 1


if __name__ == "__main__":
    raise SystemExit(main())
