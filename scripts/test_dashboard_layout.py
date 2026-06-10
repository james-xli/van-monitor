#!/usr/bin/env python3
"""
Preview the Figma Main screen v4 layout on the e-paper with sample P0 values,
including a synthetic 12h battery SOC history chart.

Run on the Raspberry Pi:
    .venv/bin/python3 scripts/test_dashboard_layout.py
"""

from __future__ import annotations

import logging
import math
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config
from van_monitor.dashboard import MetricsDashboard
from van_monitor.history import HistoryPoint
from van_monitor.metrics import LitimeMetrics, VanMetrics, VictronMetrics

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

NOW = datetime(2026, 6, 10, 16, 30)


def sample_metrics() -> VanMetrics:
    """Example readings matching the Figma mockup (node 21:30)."""
    return VanMetrics(
        litime=LitimeMetrics(soc_percent=86, power_w=40, voltage_v=12.4, connected=True),
        victron=VictronMetrics(solar_power_w=202, yield_today_wh=1000, connected=True),
        updated_at=NOW,
    )


def sample_history(now: float) -> list[HistoryPoint]:
    """
    A 12h SOC curve: a low overnight floor, then a sunny recharge ending near 86%.

    The early (left) hours sit near empty on purpose so the panel text renders over
    the unfilled white area and its readability can be judged.
    """
    window = config.HISTORY_WINDOW_HOURS * 3600
    points: list[HistoryPoint] = []
    steps = 144  # every 5 minutes
    floor_frac = 0.4  # stay low through the first ~40% of the window
    for i in range(steps + 1):
        frac = i / steps
        t = now - window + frac * window
        ramp = max(0.0, (frac - floor_frac) / (1 - floor_frac))
        soc = 6 + 80 * ramp + 2 * math.sin(frac * math.pi * 4)
        soc = max(0.0, min(100.0, soc))
        # Daytime hump peaking mid-afternoon; right edge (~202 W) matches the metric.
        solar = max(0.0, 215.6 * math.sin(frac * math.pi * 0.55 + 0.2))
        points.append(HistoryPoint(t, soc, solar))
    return points


def main() -> int:
    now = NOW.timestamp()
    display = MetricsDashboard()
    logging.info("Drawing sample dashboard (full refresh)...")
    display.init(partial=False)
    display.clear()
    display.show_metrics(
        sample_metrics(),
        history=sample_history(now),
        now=now,
        partial=False,
    )
    logging.info("Done. Display will hold until powered off or overwritten.")
    display.sleep()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
