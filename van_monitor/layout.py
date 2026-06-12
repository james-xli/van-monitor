"""
Figma layout constants for the main screen (800×480).

Source: Van Systems Monitor — frame "Main screen v8 w/ Anker" (node 42:116).
Coordinates are absolute screen positions (panel origin + inner offset).

Chart line widths, grid dash settings, and corner radii follow the values
established in v5–v7 (not re-derived from Figma placeholders).
"""

from __future__ import annotations

from dataclasses import dataclass

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 480

# Inter from Figma v8 (Bold labels/values, Medium Italic 14 captions).
FONT_LABEL = 14
FONT_STATS = 18
FONT_SOLAR_HERO = 32
FONT_SOLAR_BODY = 18
FONT_HERO = 40
FONT_CAPTION = 14
FONT_DATE = 40

CAPTION_RIGHT_MARGIN = 14

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
    border_width: int = 2


# Solar panel (42:117): white fill, black border
STYLE_SOLAR = PanelStyle(
    fill=WHITE,
    border=BLACK,
    text_fill=BLACK,
    text_stroke=WHITE,
    border_width=2,
)

# House + Anker panels (42:125, 43:137): white fill, black border, black text
STYLE_BATTERY = PanelStyle(
    fill=WHITE,
    border=BLACK,
    text_fill=BLACK,
    text_stroke=WHITE,
    border_width=2,
)

TEXT_STROKE_WIDTH = 1

# Solar panel y-axis is 0..config.SOLAR_MAX_W; the history line is stroke-only (no fill).
SOLAR_LINE_WIDTH = 2

# Thickness (px) of the divider between chart and stats text.
SOLAR_DIVIDER_WIDTH = 2

# Corner radius (px) for panel frames.
PANEL_CORNER_RADIUS = 10

# Dotted horizontal grid: dash/gap in pixels (shared by battery + solar charts).
GRID_DASH_LEN = 1
GRID_DASH_GAP = 3

# House battery chart: horizontal lines every N% SOC.
SOC_GRID_STEP = 10

# Solar chart: horizontal lines every N watts (0..SOLAR_MAX_W).
SOLAR_GRID_STEP = 100


def _abs(frame: Zone, left: int, top: int) -> tuple[int, int]:
    """Convert Figma position inside a panel to absolute screen coordinates."""
    return (frame.x + left, frame.y + top)


# Panels — Solar (42:117), House (42:125), Anker (43:137)
SOLAR = Zone(x=20, y=52, width=240, height=185)
HOUSE_BATTERY = Zone(x=300, y=20, width=480, height=250)
ANKER = Zone(x=300, y=300, width=480, height=160)

# Solar chart (42:118): top 100px, divider at y=100 (42:124)
SOLAR_CHART = Zone(x=SOLAR.x, y=SOLAR.y, width=SOLAR.width, height=100)
SOLAR_DIVIDER_Y = SOLAR.y + 100

# Solar text below divider (42:119–42:123)
SOLAR_LABEL = _abs(SOLAR, 12, 106)
SOLAR_VALUE = _abs(SOLAR, 10, 121)
SOLAR_YIELD_TODAY = _abs(SOLAR, 10, 157)
SOLAR_MAX_CAPTION_Y = _abs(SOLAR, 0, 106)[1]

# House chart (42:126): top 180px, divider implied at y=180
HOUSE_CHART = Zone(x=HOUSE_BATTERY.x, y=HOUSE_BATTERY.y, width=HOUSE_BATTERY.width, height=180)
HOUSE_DIVIDER_Y = HOUSE_BATTERY.y + 180

# House stats (42:127–42:132) on white below the chart
HOUSE_LABEL = _abs(HOUSE_BATTERY, 16, 186)
HOUSE_SOC = _abs(HOUSE_BATTERY, 15, 200)
HOUSE_STATS_RIGHT = HOUSE_BATTERY.x1 - 15
HOUSE_POWER_Y = HOUSE_BATTERY.y + 205
HOUSE_VOLTAGE_Y = HOUSE_BATTERY.y + 223
HOUSE_CAPACITY_CAPTION_Y = _abs(HOUSE_BATTERY, 0, 186)[1]

# Anker chart (43:138): top 90px
ANKER_CHART = Zone(x=ANKER.x, y=ANKER.y, width=ANKER.width, height=90)
ANKER_DIVIDER_Y = ANKER.y + 90

# Anker stats (43:145–43:150)
ANKER_LABEL = _abs(ANKER, 16, 95)
ANKER_SOC = _abs(ANKER, 15, 109)
ANKER_STATS_RIGHT = ANKER.x1 - 15
ANKER_POWER_IN_Y = ANKER.y + 114
ANKER_POWER_OUT_Y = ANKER.y + 132
ANKER_CAPACITY_CAPTION_Y = _abs(ANKER, 0, 95)[1]

# Two-line date, bottom-left (42:135)
DATE_ORIGIN = (20, 360)
DATE_LINE_HEIGHT = 40

# Flow arrows (42:134 solar→house, 43:152 house→anker)
ARROW_SOLAR_TO_HOUSE = ((271, 152), (289, 152))
ARROW_HOUSE_TO_ANKER = ((540, 276), (540, 294))
ARROW_HEAD_SIZE = 10
