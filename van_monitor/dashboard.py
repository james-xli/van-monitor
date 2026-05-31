"""
Render P0 van metrics on the e-paper display.

Layout matches Figma "Main screen v2" (node 4:2), light theme, no chart fills.
"""

from __future__ import annotations

from PIL import ImageFont

import config
from van_monitor.display import EpaperDisplay
from van_monitor import layout
from van_monitor.fonts import load_bold_font, load_caption_font
from van_monitor.metrics import (
    VanMetrics,
    fmt,
    fmt_anker_net,
    fmt_signed_watts,
    fmt_yield_today,
)


class MetricsDashboard(EpaperDisplay):
    """Draw P0 metrics in fixed zones (Figma Main screen v2)."""

    def __init__(self):
        super().__init__()
        self._font_label = load_bold_font(layout.FONT_LABEL)
        self._font_body = load_bold_font(layout.FONT_BODY)
        self._font_hero = load_bold_font(layout.FONT_HERO)
        self._font_caption = load_caption_font(layout.FONT_LABEL)

    def render(self, metrics: VanMetrics) -> None:
        """Redraw the full metrics screen (white background, black text)."""
        self.reset_canvas()
        self._draw_zone(layout.SOLAR)
        self._draw_zone(layout.HOUSE_BATTERY)
        self._draw_zone(layout.ANKER)
        self._draw_flow_arrows()
        self._draw_solar(metrics)
        self._draw_house_battery(metrics)
        self._draw_anker(metrics)

    def _draw_zone(self, zone: layout.Zone) -> None:
        self._draw.rectangle(
            (zone.x, zone.y, zone.x1 - 1, zone.y1 - 1),
            outline=0,
            width=1,
        )

    def _draw_flow_arrows(self) -> None:
        self._draw_arrow(*layout.ARROW_SOLAR_TO_HOUSE)
        self._draw_arrow(*layout.ARROW_HOUSE_TO_ANKER)

    def _draw_arrow(
        self,
        start: tuple[int, int],
        end: tuple[int, int],
    ) -> None:
        x0, y0 = start
        x1, y1 = end
        self._draw.line((x0, y0, x1, y1), fill=0, width=2)

        head = layout.ARROW_HEAD_SIZE
        if abs(x1 - x0) >= abs(y1 - y0):
            direction = 1 if x1 > x0 else -1
            base_x = x1 - direction * head
            self._draw.polygon(
                [(x1, y1), (base_x, y1 - 4), (base_x, y1 + 4)],
                fill=0,
            )
        else:
            direction = 1 if y1 > y0 else -1
            base_y = y1 - direction * head
            self._draw.polygon(
                [(x1, y1), (x1 - 4, base_y), (x1 + 4, base_y)],
                fill=0,
            )

    def _text(
        self,
        text: str,
        xy: tuple[int, int],
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    ) -> None:
        self._draw.text(xy, text, font=font, fill=0)

    def _draw_caption_right(self, text: str, zone: layout.Zone, y: int) -> None:
        """Right-aligned caption inside a panel (Figma Medium Italic 12px)."""
        font = self._font_caption
        bbox = self._draw.textbbox((0, 0), text, font=font)
        width = bbox[2] - bbox[0]
        x = zone.x1 - width - layout.CAPTION_RIGHT_MARGIN
        self._text(text, (x, y), font)

    def _draw_solar(self, metrics: VanMetrics) -> None:
        self._text(layout.LABEL_SOLAR, layout.SOLAR_LABEL, self._font_label)
        self._text(
            fmt(metrics.victron.solar_power_w, suffix=" W"),
            layout.SOLAR_VALUE,
            self._font_hero,
        )
        self._text(
            fmt_yield_today(metrics.victron.yield_today_wh),
            layout.SOLAR_YIELD_TODAY,
            self._font_body,
        )
        self._draw_caption_right(
            f"{config.SOLAR_MAX_W} W max",
            layout.SOLAR,
            layout.SOLAR_MAX_CAPTION_Y,
        )
        if metrics.victron.error:
            self._text(
                metrics.victron.error[:28],
                (layout.SOLAR.x + 8, layout.SOLAR.y1 - 18),
                self._font_label,
            )

    def _draw_house_battery(self, metrics: VanMetrics) -> None:
        self._text(layout.LABEL_HOUSE, layout.HOUSE_LABEL, self._font_label)
        self._text(
            fmt(metrics.litime.soc_percent, suffix="%"),
            layout.HOUSE_SOC,
            self._font_hero,
        )
        self._text(
            fmt_signed_watts(metrics.litime.power_w),
            layout.HOUSE_POWER,
            self._font_body,
        )
        self._text(
            fmt(metrics.litime.voltage_v, decimals=1, suffix=" V"),
            layout.HOUSE_VOLTAGE,
            self._font_body,
        )
        self._draw_caption_right(
            f"{config.HOUSE_BATTERY_CAPACITY_KWH} kWh capacity",
            layout.HOUSE_BATTERY,
            layout.HOUSE_CAPACITY_CAPTION_Y,
        )
        if metrics.litime.error:
            self._text(
                metrics.litime.error[:28],
                (layout.HOUSE_BATTERY.x + 8, layout.HOUSE_BATTERY.y + 8),
                self._font_label,
            )

    def _draw_anker(self, metrics: VanMetrics) -> None:
        self._text(layout.LABEL_ANKER, layout.ANKER_LABEL, self._font_label)
        self._text(
            fmt(metrics.anker.soc_percent, suffix="%"),
            layout.ANKER_SOC,
            self._font_hero,
        )
        self._text(
            fmt_anker_net(metrics.anker.power_in_w, metrics.anker.power_out_w),
            layout.ANKER_NET_POWER,
            self._font_body,
        )
        self._draw_caption_right(
            f"{config.ANKER_CAPACITY_KWH} kWh capacity",
            layout.ANKER,
            layout.ANKER_CAPACITY_CAPTION_Y,
        )
        if metrics.anker.error:
            self._text(
                metrics.anker.error[:28],
                (layout.ANKER.x + 8, layout.ANKER.y + 8),
                self._font_label,
            )

    def show_metrics(self, metrics: VanMetrics, *, partial: bool = False) -> None:
        self.render(metrics)
        self.refresh(partial=partial)

    def show_status_message(self, message: str) -> None:
        self.reset_canvas()
        self._text("van-monitor", (16, 16), self._font_label)
        self._text(message, (16, 40), self._font_body)
        self.refresh(partial=False)
