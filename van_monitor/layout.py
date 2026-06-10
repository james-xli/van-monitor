"""
Figma layout constants for the main screen (800×480).

Source: Van Systems Monitor — frame "Main screen v4 w/o Anker" (node 21:30).
Coordinates are absolute screen positions (panel origin + inner offset).

P1 chart fills are omitted; gray/black chart areas in Figma are placeholders.
"""

from __future__ import annotations

from dataclasses import dataclass

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 480

# Inter from Figma v4 (Bold 14/24/54, Medium Italic 14 captions)
FONT_LABEL = 14
FONT_BODY = 24
FONT_HERO = 54
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


# Solar panel (21:31): white fill, 2px black border
STYLE_SOLAR = PanelStyle(
    fill=WHITE,
    border=BLACK,
    text_fill=BLACK,
    text_stroke=WHITE,
    border_width=2,
)

# House battery panel (21:47): white SOC fill from bottom, black above the curve,
# border marks the 100% frame.
HOUSE_BATTERY_BORDER_WIDTH = 2
STYLE_BATTERY = PanelStyle(
    fill=WHITE,
    border=BLACK,
    text_fill=BLACK,
    text_stroke=WHITE,
    border_width=HOUSE_BATTERY_BORDER_WIDTH,
)

TEXT_STROKE_WIDTH = 1

# Panel text sits over a chart background, so it uses a thicker halo for contrast.
HOUSE_TEXT_STROKE_WIDTH = 5
SOLAR_TEXT_STROKE_WIDTH = 5

# Solar panel y-axis is 0..config.SOLAR_MAX_W; the history line is stroke-only (no fill).
SOLAR_LINE_WIDTH = 2

# Corner radius (px) for the solar and battery panel frames.
PANEL_CORNER_RADIUS = 8


def _abs(frame: Zone, left: int, top: int) -> tuple[int, int]:
    """Convert Figma position inside a panel to absolute screen coordinates."""
    return (frame.x + left, frame.y + top)


# Panels — node 21:31 Solar, node 21:47 House Battery
SOLAR = Zone(x=16, y=170, width=300, height=140)
HOUSE_BATTERY = Zone(x=344, y=69, width=440, height=341)

# Solar text (nodes 21:36–21:38, caption 21:33)
SOLAR_LABEL = _abs(SOLAR, 16, 15)
SOLAR_VALUE = _abs(SOLAR, 15, 32)
SOLAR_YIELD_TODAY = _abs(SOLAR, 16, 97)
SOLAR_MAX_CAPTION_Y = _abs(SOLAR, 0, 109)[1]

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
