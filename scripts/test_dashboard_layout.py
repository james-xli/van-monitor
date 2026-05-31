#!/usr/bin/env python3
"""
Preview the Figma Main screen v3 layout on the e-paper with sample P0 values.

Run on the Raspberry Pi:
    .venv/bin/python3 scripts/test_dashboard_layout.py
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from van_monitor.dashboard import MetricsDashboard
from van_monitor.metrics import AnkerMetrics, LitimeMetrics, VanMetrics, VictronMetrics

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def sample_metrics() -> VanMetrics:
    """Example readings matching the Figma mockup."""
    return VanMetrics(
        litime=LitimeMetrics(soc_percent=86, power_w=40, voltage_v=12.4, connected=True),
        victron=VictronMetrics(solar_power_w=202, yield_today_wh=645, connected=True),
        anker=AnkerMetrics(
            soc_percent=92,
            power_in_w=162,
            power_out_w=880,  # net displays as -718 W
            connected=True,
        ),
        updated_at=datetime.now(),
    )


def main() -> int:
    display = MetricsDashboard()
    logging.info("Drawing sample dashboard (full refresh)...")
    display.init(partial=False)
    display.clear()
    display.show_metrics(sample_metrics(), partial=False)
    logging.info("Done. Display will hold until powered off or overwritten.")
    display.sleep()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
