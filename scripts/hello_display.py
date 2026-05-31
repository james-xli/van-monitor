#!/usr/bin/env python3
"""
Hello-world test for the Waveshare 7.5" e-paper display.

Run on the Raspberry Pi (not on your Mac):
    .venv/bin/python3 scripts/hello_display.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Allow running as `python3 scripts/hello_display.py` from repo root.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from van_monitor.display import EpaperDisplay

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def main() -> int:
    display = EpaperDisplay()

    logging.info("Initializing display (full refresh)...")
    display.init(partial=False)
    display.clear()

    logging.info("Showing hello world...")
    display.show_text("Hello from van-monitor", partial=False)

    logging.info("Done. Putting display to sleep.")
    display.sleep()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
