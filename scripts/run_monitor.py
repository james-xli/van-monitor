#!/usr/bin/env python3
"""
Poll all BLE devices and show P0 metrics on the e-paper display.

Test each device individually first:
    scripts/test_litime.py
    scripts/test_victron.py

Anker is not polled here (SolixBLE lacks C1000 Gen 2 telemetry). Use
scripts/test_anker.py to experiment with that collector in isolation.
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
from van_monitor.history import MetricsHistory
from van_monitor.metrics import print_metrics
from van_monitor.util import setup_logging

logger = logging.getLogger(__name__)


def _should_full_refresh(last_full_refresh: float) -> bool:
    interval = config.FULL_REFRESH_INTERVAL_SECONDS
    if interval <= 0:
        return False
    return (time.monotonic() - last_full_refresh) >= interval


def _update_dashboard(
    dashboard: MetricsDashboard,
    metrics,
    *,
    history,
    now: float,
    partial_mode: bool,
    force_full: bool,
    last_full_refresh: float,
) -> tuple[bool, float]:
    """
    Push metrics to the display.

    Returns (partial_mode, last_full_refresh monotonic time).
    """
    if force_full or not partial_mode:
        if force_full:
            logger.info(
                "Full display refresh (every %ss)",
                config.FULL_REFRESH_INTERVAL_SECONDS,
            )
        dashboard.init(partial=False)
        dashboard.show_metrics(metrics, history=history, now=now, partial=False)
        dashboard.init(partial=True)
        return True, time.monotonic()

    dashboard.show_metrics(metrics, history=history, now=now, partial=True)
    return partial_mode, last_full_refresh


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
    parser.add_argument(
        "--debug-ble",
        action="store_true",
        help="Show bleak/SolixBLE debug (very noisy; use with -v)",
    )
    args = parser.parse_args()

    setup_logging(args.verbose, debug_ble=args.debug_ble)

    dashboard = None
    partial_mode = False
    last_full_refresh = time.monotonic()
    history = MetricsHistory()

    if not args.no_display:
        dashboard = MetricsDashboard()
        dashboard.init(partial=False)
        dashboard.clear()
        dashboard.show_status_message("Polling BLE devices...")

    while True:
        now = time.time()
        metrics = poll_all()
        print_metrics(metrics)

        history.record(
            metrics.litime.soc_percent,
            metrics.victron.solar_power_w,
            now=now,
        )

        if dashboard:
            force_full = _should_full_refresh(last_full_refresh)
            partial_mode, last_full_refresh = _update_dashboard(
                dashboard,
                metrics,
                history=history.points(),
                now=now,
                partial_mode=partial_mode,
                force_full=force_full,
                last_full_refresh=last_full_refresh,
            )

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
