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
FONT_TIMESTAMP = 14

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


# Panels — node 38:36 Solar, node 38:44 House Battery
SOLAR = Zone(x=16, y=124, width=300, height=213)
HOUSE_BATTERY = Zone(x=344, y=69, width=440, height=341)

# Solar chart area (node 38:37): the top region of the panel, above the divider
# line (node 38:57). The text lives below this, so the chart no longer overlaps it.
SOLAR_CHART = Zone(x=SOLAR.x, y=SOLAR.y + 8, width=300, height=108)
SOLAR_DIVIDER_Y = SOLAR.y + 116

# Solar text below the divider (nodes 38:41–38:43, caption 38:38)
SOLAR_LABEL = _abs(SOLAR, 11, 125)
SOLAR_VALUE = _abs(SOLAR, 9, 138)
SOLAR_YIELD_TODAY = _abs(SOLAR, 9, 182)
SOLAR_MAX_CAPTION_Y = _abs(SOLAR, 0, 187)[1]

# House battery text (nodes 21:51–21:53, caption 21:49)
HOUSE_LABEL = _abs(HOUSE_BATTERY, 16, 186)
HOUSE_SOC = _abs(HOUSE_BATTERY, 15, 203)
HOUSE_POWER = _abs(HOUSE_BATTERY, 16, 268)
HOUSE_VOLTAGE = _abs(HOUSE_BATTERY, 16, 292)
HOUSE_CAPACITY_CAPTION_Y = _abs(HOUSE_BATTERY, 0, 310)[1]

# Last-updated stamp (node 25:32)
UPDATED_AT = (14, 451)

# Flow arrow solar → house (node 21:55)
ARROW_SOLAR_TO_HOUSE = ((321, 240), (339, 240))
ARROW_HEAD_SIZE = 10
