"""
Figma layout constants for the main screen (800×480).

Source: Van Systems Monitor — frame "Main screen v5 w/o Anker" (node 38:35).
Coordinates are absolute screen positions (panel origin + inner offset).

P1 chart fills are omitted; gray/black chart areas in Figma are placeholders.
"""

from __future__ import annotations

from dataclasses import dataclass

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 480

# Inter from Figma (Bold labels/values, Medium Italic 14 captions).
# House battery uses the large 54/24 pair; the v5 Solar panel uses a smaller 40/20.
FONT_LABEL = 14
FONT_BODY = 24
FONT_HERO = 54
FONT_SOLAR_HERO = 40
FONT_SOLAR_BODY = 20
FONT_CAPTION = 14
# v7 shows a large two-line date (node 40:97) instead of a small timestamp.
FONT_DATE = 36

CAPTION_RIGHT_MARGIN = 14

# 1-bit canvas: 255=white, 0=black
WHITE = 255
BLACK = 0

LABEL_SOLAR = "SOLAR"
LABEL_HOUSE = "HOUSE  BATTERY"


@dataclass(frozen=True)
class Zone:
    """A bordered panel on the main screen."""

    x: int
    y: int
    width: int
    height: int

    @property
    def x1(self) -> int:
        return self.x + self.width

    @property
    def y1(self) -> int:
        return self.y + self.height


@dataclass(frozen=True)
class PanelStyle:
    """Fill, border, and outlined text colors for a panel."""

    fill: int
    border: int
    text_fill: int
    text_stroke: int
    border_width: int = 2


# Solar panel (38:36): white fill, 3px black border (matches the house battery)
STYLE_SOLAR = PanelStyle(
    fill=WHITE,
    border=BLACK,
    text_fill=BLACK,
    text_stroke=WHITE,
    border_width=2,
)

# House battery panel (38:44): black SOC fill from bottom, 3px border marks 100% frame
HOUSE_BATTERY_BORDER_WIDTH = 2
STYLE_BATTERY = PanelStyle(
    fill=BLACK,
    border=BLACK,
    text_fill=WHITE,
    text_stroke=BLACK,
    border_width=HOUSE_BATTERY_BORDER_WIDTH,
)

TEXT_STROKE_WIDTH = 1

# The house battery text sits over its chart background, so it uses a thicker halo.
# (v5 moved the solar text below its chart, so solar text needs no halo.)
HOUSE_TEXT_STROKE_WIDTH = 5

# Solar panel y-axis is 0..config.SOLAR_MAX_W; the history line is stroke-only (no fill).
SOLAR_LINE_WIDTH = 2

# Thickness (px) of the divider between the solar chart and its text (node 38:57).
SOLAR_DIVIDER_WIDTH = 2

# Corner radius (px) for the solar and battery panel frames.
PANEL_CORNER_RADIUS = 10


def _abs(frame: Zone, left: int, top: int) -> tuple[int, int]:
    """Convert Figma position inside a panel to absolute screen coordinates."""
    return (frame.x + left, frame.y + top)


# Panels — node 40:80 Solar (half width), node 40:89 House Battery
SOLAR = Zone(x=20, y=150, width=240, height=200)
HOUSE_BATTERY = Zone(x=300, y=86, width=480, height=340)

# Solar chart area (node 40:81): top region above the divider (node 40:88).
SOLAR_CHART = Zone(x=SOLAR.x, y=SOLAR.y + 8, width=SOLAR.width, height=97)
SOLAR_DIVIDER_Y = SOLAR.y + 105

# Solar text below the divider (nodes 40:85–40:87, caption 40:82 right-aligned)
SOLAR_LABEL = _abs(SOLAR, 12, 113)
SOLAR_VALUE = _abs(SOLAR, 10, 127)
SOLAR_YIELD_TODAY = _abs(SOLAR, 10, 171)
SOLAR_MAX_CAPTION_Y = _abs(SOLAR, 0, 113)[1]

# House battery chart area (node 40:90) above its stats divider (node 40:110).
# The stats strip below the divider is filled solid black with white text.
HOUSE_CHART = Zone(x=HOUSE_BATTERY.x, y=HOUSE_BATTERY.y, width=HOUSE_BATTERY.width, height=245)
HOUSE_DIVIDER_Y = HOUSE_BATTERY.y + 245

# House battery stats (nodes 40:93–40:95, caption 40:91). The SOC % and label are
# left-aligned; power/voltage and the capacity caption are right-aligned.
HOUSE_LABEL = _abs(HOUSE_BATTERY, 16, 255)
HOUSE_SOC = _abs(HOUSE_BATTERY, 15, 272)
HOUSE_STATS_RIGHT = HOUSE_BATTERY.x1 - 15
HOUSE_POWER_Y = HOUSE_BATTERY.y + 279
HOUSE_VOLTAGE_Y = HOUSE_BATTERY.y + 303
HOUSE_CAPACITY_CAPTION_Y = _abs(HOUSE_BATTERY, 0, 255)[1]

# Large two-line date, top-left (node 40:97). Time is no longer shown.
DATE_ORIGIN = (20, 20)
DATE_LINE_HEIGHT = 36

# Flow arrow solar → house (node 40:96)
ARROW_SOLAR_TO_HOUSE = ((271, 256), (289, 256))
ARROW_HEAD_SIZE = 10
