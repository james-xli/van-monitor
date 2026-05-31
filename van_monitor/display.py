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

    def reset_canvas(self) -> None:
        """Clear the in-memory canvas to white."""
        self._canvas = Image.new("1", (self.width, self.height), 255)
        self._draw = ImageDraw.Draw(self._canvas)

    def fill_rect(self, x0: int, y0: int, x1: int, y1: int, *, fill: int = 255) -> None:
        """Fill a rectangle on the canvas (255=white erases, 0=black)."""
        self._draw.rectangle((x0, y0, x1, y1), fill=fill)

    def draw_text(self, text: str, *, x: int = 10, y: int = 10, fill: int = 0) -> None:
        """Draw text onto the canvas without refreshing the panel."""
        self._draw.text((x, y), text, font=self._font, fill=fill)

    def refresh(self, *, partial: bool = False, region: tuple[int, int, int, int] | None = None) -> None:
        """
        Push the canvas to the panel.

        partial=False: full refresh (slower, no ghosting).
        partial=True:  partial refresh mode (faster). The Waveshare driver always
                       reads from the start of the full canvas buffer, so partial
                       updates still pass the full screen size — only draw the
                       changed areas on the canvas before calling this.
        """
        buffer = self._epd.getbuffer(self._canvas)
        if partial:
            # Waveshare demo uses full-screen coords; sub-regions need buffer cropping.
            x0, y0, x1, y1 = region or (0, 0, self.width, self.height)
            self._epd.display_Partial(buffer, x0, y0, x1, y1)
        else:
            self._epd.display(buffer)

    def show_text(
        self,
        text: str,
        *,
        x: int = 10,
        y: int = 10,
        partial: bool = False,
    ) -> None:
        """Draw text on a blank canvas and push it to the display."""
        self.reset_canvas()
        self.draw_text(text, x=x, y=y)
        self.refresh(partial=partial)

    def sleep(self) -> None:
        """Put the panel into low-power mode."""
        self._epd.sleep()
