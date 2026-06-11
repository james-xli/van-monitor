#!/usr/bin/env python3
"""
Preview the Figma Main screen v4 layout with sample P0 values, including a
synthetic 12h battery SOC + solar history chart.

Run on the Raspberry Pi (draws to the e-paper):
    .venv/bin/python3 scripts/test_dashboard_layout.py

Render to a PNG on any machine (no e-paper hardware required):
    python3 scripts/test_dashboard_layout.py --png preview.png
"""

from __future__ import annotations

import argparse
import logging
import math
import sys
import types
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config
from van_monitor import layout
from van_monitor.history import HistoryPoint
from van_monitor.metrics import LitimeMetrics, VanMetrics, VictronMetrics

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

NOW = datetime(2026, 6, 10, 16, 30)


# Ending SOC per scenario; the metric tile is drawn with the same value.
SCENARIO_END_SOC = {"low": 86, "high": 96}


def sample_metrics(end_soc: int = 86) -> VanMetrics:
    """Example readings matching the Figma mockup (node 21:30)."""
    return VanMetrics(
        litime=LitimeMetrics(soc_percent=end_soc, power_w=40, voltage_v=12.4, connected=True),
        victron=VictronMetrics(solar_power_w=202, yield_today_wh=1000, connected=True),
        updated_at=NOW,
    )


def sample_history(now: float, scenario: str = "low") -> list[HistoryPoint]:
    """
    A 12h SOC + solar curve for previewing the chart.

    scenario="low":  a low overnight floor then a sunny recharge ending near 86%.
                     The early (left) hours sit near empty so panel text renders
                     over the unfilled white area and its readability can be judged.
    scenario="high": SOC stays high all window (~62% -> ~96%), so most of the panel
                     is filled and the in-fill white gridlines are visible.
    """
    window = config.HISTORY_WINDOW_HOURS * 3600
    points: list[HistoryPoint] = []
    steps = 144  # every 5 minutes
    floor_frac = 0.4  # stay low through the first ~40% of the window
    for i in range(steps + 1):
        frac = i / steps
        t = now - window + frac * window
        if scenario == "high":
            soc = 62 + 34 * frac + 2 * math.sin(frac * math.pi * 4)
        else:
            ramp = max(0.0, (frac - floor_frac) / (1 - floor_frac))
            soc = 6 + 80 * ramp + 2 * math.sin(frac * math.pi * 4)
        soc = max(0.0, min(100.0, soc))
        # Daytime hump peaking mid-afternoon; right edge (~202 W) matches the metric.
        solar = max(0.0, 215.6 * math.sin(frac * math.pi * 0.55 + 0.2))
        points.append(HistoryPoint(t, soc, solar))
    return points


def _install_fake_epd() -> None:
    """Stub the Waveshare HAT so the dashboard imports/renders off-Pi."""
    epd_mod = types.ModuleType("waveshare_epd.epd7in5_V2")

    class _EPD:
        width = layout.SCREEN_WIDTH
        height = layout.SCREEN_HEIGHT

    epd_mod.EPD = _EPD
    pkg = types.ModuleType("waveshare_epd")
    pkg.epd7in5_V2 = epd_mod
    sys.modules["waveshare_epd"] = pkg
    sys.modules["waveshare_epd.epd7in5_V2"] = epd_mod


def _render_png(path: str, metrics: VanMetrics, history: list[HistoryPoint], now: float) -> None:
    _install_fake_epd()
    from PIL import Image, ImageDraw

    from van_monitor.dashboard import MetricsDashboard
    from van_monitor.fonts import load_bold_font, load_caption_font

    class _PreviewDashboard(MetricsDashboard):
        """Renders to an in-memory canvas only; no hardware calls."""

        def __init__(self) -> None:
            self.width = layout.SCREEN_WIDTH
            self.height = layout.SCREEN_HEIGHT
            self._canvas = Image.new("1", (self.width, self.height), layout.WHITE)
            self._draw = ImageDraw.Draw(self._canvas)
            self._font_label = load_bold_font(layout.FONT_LABEL)
            self._font_body = load_bold_font(layout.FONT_BODY)
            self._font_hero = load_bold_font(layout.FONT_HERO)
            self._font_solar_hero = load_bold_font(layout.FONT_SOLAR_HERO)
            self._font_solar_body = load_bold_font(layout.FONT_SOLAR_BODY)
            self._font_caption = load_caption_font(layout.FONT_CAPTION)

    dash = _PreviewDashboard()
    dash.render(metrics, history=history, now=now)
    dash._canvas.convert("L").save(path)
    logging.info("Saved preview to %s", path)


def _scenario_inputs(scenario: str, now: float) -> tuple[VanMetrics, list[HistoryPoint]]:
    end_soc = SCENARIO_END_SOC[scenario]
    return sample_metrics(end_soc), sample_history(now, scenario)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--png",
        metavar="PATH",
        help="Render to a PNG file instead of the e-paper (works on any machine).",
    )
    parser.add_argument(
        "--scenario",
        choices=("low", "high", "both"),
        default="low",
        help="SOC profile to preview (default: low). 'both' writes a _low/_high pair (PNG only).",
    )
    args = parser.parse_args(argv)

    now = NOW.timestamp()

    if args.png:
        if args.scenario == "both":
            base = Path(args.png)
            for scenario in ("low", "high"):
                metrics, history = _scenario_inputs(scenario, now)
                out = base.with_name(f"{base.stem}_{scenario}{base.suffix}")
                _render_png(str(out), metrics, history, now)
        else:
            metrics, history = _scenario_inputs(args.scenario, now)
            _render_png(args.png, metrics, history, now)
        return 0

    if args.scenario == "both":
        parser.error("--scenario both is only supported with --png")

    metrics, history = _scenario_inputs(args.scenario, now)

    from van_monitor.dashboard import MetricsDashboard

    display = MetricsDashboard()
    logging.info("Drawing sample dashboard (full refresh)...")
    display.init(partial=False)
    display.clear()
    display.show_metrics(metrics, history=history, now=now, partial=False)
    logging.info("Done. Display will hold until powered off or overwritten.")
    display.sleep()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
