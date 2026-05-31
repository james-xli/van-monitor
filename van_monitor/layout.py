"""
Figma layout constants for the main screen (800×480, light theme).

Source: Van Systems Monitor — frame "Main screen v2" (node 4:2).
Coordinates are absolute screen positions (frame origin + Figma left/top).

P1 chart fills are omitted; gray areas are placeholders for historical series.
"""

from __future__ import annotations

from dataclasses import dataclass

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 480

FONT_LABEL = 12
FONT_BODY = 20
FONT_HERO = 48

CAPTION_RIGHT_MARGIN = 8

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


def _abs(frame: Zone, left: int, top: int) -> tuple[int, int]:
    """Convert Figma position inside a panel to absolute screen coordinates."""
    return (frame.x + left, frame.y + top)


# Panels
SOLAR = Zone(x=16, y=80, width=299, height=140)
HOUSE_BATTERY = Zone(x=349, y=13, width=440, height=280)
ANKER = Zone(x=349, y=328, width=440, height=140)

# Solar (frame 4:3) — text at left 18–19px, top 31/46/103px
SOLAR_LABEL = _abs(SOLAR, 19, 31)
SOLAR_VALUE = _abs(SOLAR, 18, 46)
SOLAR_YIELD_TODAY = _abs(SOLAR, 18, 103)
SOLAR_MAX_CAPTION_Y = _abs(SOLAR, 0, 119)[1]  # right-aligned; y from Figma node 4:26

# House battery (frame 4:15) — two lines: "+40 W" then "12.4 V" at top 219px
HOUSE_LABEL = _abs(HOUSE_BATTERY, 19, 150)
HOUSE_SOC = _abs(HOUSE_BATTERY, 18, 162)
HOUSE_POWER = _abs(HOUSE_BATTERY, 18, 219)
HOUSE_VOLTAGE = _abs(HOUSE_BATTERY, 18, 239)  # second line in 20px stack
HOUSE_CAPACITY_CAPTION_Y = _abs(HOUSE_BATTERY, 0, 259)[1]

# Anker (frame 4:9) — net W at top 103px
ANKER_LABEL = _abs(ANKER, 19, 31)
ANKER_SOC = _abs(ANKER, 18, 46)
ANKER_NET_POWER = _abs(ANKER, 18, 103)
ANKER_CAPACITY_CAPTION_Y = _abs(ANKER, 0, 116)[1]

# Flow arrows (nodes 4:22, 4:21)
ARROW_SOLAR_TO_HOUSE = ((316, 153), (348, 153))
ARROW_HOUSE_TO_ANKER = ((569, 294), (569, 327))
ARROW_HEAD_SIZE = 6
