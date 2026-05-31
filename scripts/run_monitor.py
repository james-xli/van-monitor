#!/usr/bin/env python3
"""
Poll all BLE devices and show P0 metrics on the e-paper display.

Test each device individually first:
    scripts/test_litime.py
    scripts/test_victron.py
    scripts/test_anker.py
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config
from van_monitor.collectors import poll_all
from van_monitor.dashboard import MetricsDashboard
from van_monitor.metrics import print_metrics
from van_monitor.util import setup_logging

logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the van-monitor BLE dashboard")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Poll once and exit (good for debugging)",
    )
    parser.add_argument(
        "--no-display",
        action="store_true",
        help="Print to terminal only (skip e-paper)",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    setup_logging(args.verbose)

    dashboard = None
    partial_mode = False

    if not args.no_display:
        dashboard = MetricsDashboard()
        dashboard.init(partial=False)
        dashboard.clear()
        dashboard.show_status_message("Polling BLE devices...")

    while True:
        metrics = poll_all()
        print_metrics(metrics)

        if dashboard:
            if not partial_mode:
                dashboard.init(partial=False)
                dashboard.show_metrics(metrics, partial=False)
                dashboard.init(partial=True)
                partial_mode = True
            else:
                dashboard.show_metrics(metrics, partial=True)

        if args.once:
            break

        logger.info("Sleeping %ss...", config.POLL_INTERVAL_SECONDS)
        time.sleep(config.POLL_INTERVAL_SECONDS)

    if dashboard:
        dashboard.init(partial=False)
        dashboard.sleep()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
