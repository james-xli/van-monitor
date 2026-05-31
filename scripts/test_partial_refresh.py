#!/usr/bin/env python3
"""
Test partial refresh on the e-paper display.

Draws static text once (full refresh), then updates a clock every few seconds
using partial refresh. Press Ctrl+C to stop early.

Run on the Raspberry Pi:
    .venv/bin/python3 scripts/test_partial_refresh.py
"""

from __future__ import annotations

import logging
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config
from van_monitor.display import EpaperDisplay

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# How many partial updates to run before exiting (Ctrl+C also works).
UPDATE_COUNT = 12

# Canvas area we redraw each tick (erase + draw). Not passed to the driver —
# partial refresh still sends the full canvas; see van_monitor/display.py.
CLOCK_X = 10
CLOCK_Y = 120
CLOCK_ERASE_WIDTH = 200
CLOCK_ERASE_HEIGHT = 40


def main() -> int:
    display = EpaperDisplay()
    interval = config.DISPLAY_REFRESH_INTERVAL_SECONDS

    logging.info("Full refresh: drawing static header...")
    display.init(partial=False)
    display.clear()
    display.reset_canvas()
    display.draw_text("van-monitor", x=10, y=10)
    display.draw_text("Partial refresh test", x=10, y=30)
    display.draw_text("Static text stays put.", x=10, y=60)
    display.draw_text("Clock updates below:", x=10, y=90)
    display.draw_text(datetime.now().strftime("%H:%M:%S"), x=CLOCK_X, y=CLOCK_Y)
    display.refresh(partial=False)

    logging.info("Switching to partial refresh mode...")
    display.init(partial=True)

    for i in range(UPDATE_COUNT):
        now = datetime.now().strftime("%H:%M:%S")

        # Erase the old clock text, then draw the new time on the full canvas.
        display.fill_rect(
            CLOCK_X,
            CLOCK_Y,
            CLOCK_X + CLOCK_ERASE_WIDTH,
            CLOCK_Y + CLOCK_ERASE_HEIGHT,
            fill=255,
        )
        display.draw_text(now, x=CLOCK_X, y=CLOCK_Y)
        display.refresh(partial=True)

        logging.info("Partial update %s/%s: %s", i + 1, UPDATE_COUNT, now)
        if i + 1 < UPDATE_COUNT:
            time.sleep(interval)

    logging.info("Done. Putting display to sleep.")
    display.init(partial=False)
    display.sleep()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
