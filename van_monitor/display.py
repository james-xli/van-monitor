"""
Thin wrapper around the Waveshare 7.5" black/white V2 e-paper driver.

The low-level SPI code lives in vendor/waveshare_epd/ (from Waveshare's repo).
This module keeps our application code simple.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# Waveshare library expects to be importable as `waveshare_epd`.
VENDOR_DIR = Path(__file__).resolve().parents[1] / "vendor"
if str(VENDOR_DIR) not in sys.path:
    sys.path.insert(0, str(VENDOR_DIR))

from waveshare_epd import epd7in5_V2


class EpaperDisplay:
    """Manage the 7.5\" Waveshare black/white V2 e-paper HAT."""

    def __init__(self):
        self._epd = epd7in5_V2.EPD()
        self.width = self._epd.width
        self.height = self._epd.height
        self._canvas = Image.new("1", (self.width, self.height), 255)
        self._draw = ImageDraw.Draw(self._canvas)
        self._font = ImageFont.load_default()

    def init(self, *, partial: bool = False) -> None:
        """Power on and initialize the panel."""
        if partial:
            result = self._epd.init_part()
        else:
            result = self._epd.init()
        if result != 0:
            raise RuntimeError("Failed to initialize e-paper display")

    def clear(self) -> None:
        """Full white refresh."""
        self._epd.Clear()

    def show_text(
        self,
        text: str,
        *,
        x: int = 10,
        y: int = 10,
        partial: bool = False,
    ) -> None:
        """
        Draw text on a blank canvas and push it to the display.

        partial=False: full refresh (slower, no ghosting).
        partial=True:  partial refresh (faster, for frequent updates).
        """
        self._canvas = Image.new("1", (self.width, self.height), 255)
        self._draw = ImageDraw.Draw(self._canvas)
        self._draw.text((x, y), text, font=self._font, fill=0)

        if partial:
            self._epd.display_Partial(
                self._epd.getbuffer(self._canvas),
                0,
                0,
                self.width,
                self.height,
            )
        else:
            self._epd.display(self._epd.getbuffer(self._canvas))

    def sleep(self) -> None:
        """Put the panel into low-power mode."""
        self._epd.sleep()
