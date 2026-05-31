"""
Figma layout constants for the main screen (800×480).

Source: Van Systems Monitor — frame "Main screen v3" (node 10:55).
Coordinates are absolute screen positions (panel origin + inner offset).

P1 chart fills are omitted; gray areas in Figma are placeholders for time series.
"""

from __future__ import annotations

from dataclasses import dataclass

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 480

# Inter from Figma v3
FONT_LABEL = 14
FONT_BODY = 24
FONT_HERO = 54
FONT_CAPTION = 13

CAPTION_RIGHT_MARGIN = 13

# 1-bit canvas: 255=white, 0=black
WHITE = 255
BLACK = 0

LABEL_SOLAR = "SOLAR"
LABEL_HOUSE = "HOUSE  BATTERY"
LABEL_ANKER = "ANKER SOLIX"


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


# v3: solar = white panel / black type / white glyph outline
STYLE_SOLAR = PanelStyle(
    fill=WHITE,
    border=BLACK,
    text_fill=BLACK,
    text_stroke=WHITE,
)

# v3: battery panels = black fill / white type / black glyph outline
STYLE_BATTERY = PanelStyle(
    fill=WHITE,
    border=BLACK,
    text_fill=BLACK,
    text_stroke=WHITE,
)

TEXT_STROKE_WIDTH = 1
PANEL_BORDER_WIDTH = 2


def _abs(frame: Zone, left: int, top: int) -> tuple[int, int]:
    """Convert Figma position inside a panel to absolute screen coordinates."""
    return (frame.x + left, frame.y + top)


# Panels (Figma v3)
SOLAR = Zone(x=15, y=80, width=300, height=140)
HOUSE_BATTERY = Zone(x=350, y=10, width=440, height=280)
ANKER = Zone(x=350, y=330, width=440, height=140)

# Solar — Group offsets collapsed to inner text positions
SOLAR_LABEL = _abs(SOLAR, 16, 15)
SOLAR_VALUE = _abs(SOLAR, 15, 32)
SOLAR_YIELD_TODAY = _abs(SOLAR, 16, 97)
SOLAR_MAX_CAPTION_Y = _abs(SOLAR, 0, 111)[1]

# House battery — two body lines (+40 W, then 12.4 V)
HOUSE_LABEL = _abs(HOUSE_BATTERY, 16, 125)
HOUSE_SOC = _abs(HOUSE_BATTERY, 15, 142)
HOUSE_POWER = _abs(HOUSE_BATTERY, 16, 207)
HOUSE_VOLTAGE = _abs(HOUSE_BATTERY, 16, 231)
HOUSE_CAPACITY_CAPTION_Y = _abs(HOUSE_BATTERY, 0, 251)[1]

# Anker
ANKER_LABEL = _abs(ANKER, 16, 15)
ANKER_SOC = _abs(ANKER, 15, 32)
ANKER_NET_POWER = _abs(ANKER, 16, 97)
ANKER_CAPACITY_CAPTION_Y = _abs(ANKER, 0, 111)[1]

# Flow arrows
ARROW_SOLAR_TO_HOUSE = ((320, 150), (343, 150))
ARROW_HOUSE_TO_ANKER = ((570, 297), (570, 325))
ARROW_HEAD_SIZE = 10
