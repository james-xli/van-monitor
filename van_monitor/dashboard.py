"""
Render P0 van metrics on the e-paper display.

Layout matches Figma "Main screen v4 w/o Anker" (node 21:30), strict B/W, no chart fills.
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
    fmt_signed_watts,
    fmt_updated_at,
    fmt_yield_today,
)


class MetricsDashboard(EpaperDisplay):
    """Draw P0 metrics in fixed zones (Figma Main screen v4 w/o Anker)."""

    def __init__(self):
        super().__init__()
        self._font_label = load_bold_font(layout.FONT_LABEL)
        self._font_body = load_bold_font(layout.FONT_BODY)
        self._font_hero = load_bold_font(layout.FONT_HERO)
        self._font_caption = load_caption_font(layout.FONT_CAPTION)

    def render(self, metrics: VanMetrics) -> None:
        """Redraw the full metrics screen."""
        self.reset_canvas()
        self._draw_zone(layout.SOLAR, layout.STYLE_SOLAR)
        self._draw_house_battery_background(metrics.litime.soc_percent)
        self._draw_flow_arrows()
        self._draw_solar(metrics)
        self._draw_house_battery(metrics)
        self._draw_updated_at(metrics)

    def _draw_zone(self, zone: layout.Zone, style: layout.PanelStyle) -> None:
        self._draw.rectangle(
            (zone.x, zone.y, zone.x1 - 1, zone.y1 - 1),
            fill=style.fill,
            outline=style.border if style.border_width else style.fill,
            width=style.border_width,
        )

    def _draw_flow_arrows(self) -> None:
        self._draw_arrow(*layout.ARROW_SOLAR_TO_HOUSE, fill=layout.BLACK)

    def _draw_arrow(
        self,
        start: tuple[int, int],
        end: tuple[int, int],
        *,
        fill: int,
    ) -> None:
        x0, y0 = start
        x1, y1 = end
        self._draw.line((x0, y0, x1, y1), fill=fill, width=2)

        head = layout.ARROW_HEAD_SIZE
        if abs(x1 - x0) >= abs(y1 - y0):
            direction = 1 if x1 > x0 else -1
            base_x = x1 - direction * head
            self._draw.polygon(
                [(x1, y1), (base_x, y1 - 4), (base_x, y1 + 4)],
                fill=fill,
            )
        else:
            direction = 1 if y1 > y0 else -1
            base_y = y1 - direction * head
            self._draw.polygon(
                [(x1, y1), (x1 - 4, base_y), (x1 + 4, base_y)],
                fill=fill,
            )

    def _text(
        self,
        text: str,
        xy: tuple[int, int],
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        style: layout.PanelStyle,
    ) -> None:
        self._draw.text(
            xy,
            text,
            font=font,
            fill=style.text_fill,
            stroke_width=layout.TEXT_STROKE_WIDTH,
            stroke_fill=style.text_stroke,
        )

    def _draw_caption_right(
        self,
        text: str,
        zone: layout.Zone,
        y: int,
        style: layout.PanelStyle,
    ) -> None:
        """Right-aligned caption (Inter Medium Italic 14px)."""
        font = self._font_caption
        bbox = self._draw.textbbox((0, 0), text, font=font)
        width = bbox[2] - bbox[0]
        x = zone.x1 - width - layout.CAPTION_RIGHT_MARGIN
        self._text(text, (x, y), font, style)

    def _house_battery_fill_top(self, soc_percent: float | None) -> int:
        """Absolute screen Y where the black SOC fill begins (fills up from bottom)."""
        zone = layout.HOUSE_BATTERY
        if soc_percent is None:
            return zone.y1
        soc = max(0.0, min(100.0, soc_percent))
        fill_height = int(round(zone.height * soc / 100.0))
        return zone.y + zone.height - fill_height

    def _draw_house_battery_background(self, soc_percent: float | None) -> None:
        """White panel with black fill height proportional to SOC (100% = full black)."""
        zone = layout.HOUSE_BATTERY
        self._draw.rectangle(
            (zone.x, zone.y, zone.x1 - 1, zone.y1 - 1),
            fill=layout.WHITE,
        )
        fill_top = self._house_battery_fill_top(soc_percent)
        if fill_top < zone.y1:
            self._draw.rectangle(
                (zone.x, fill_top, zone.x1 - 1, zone.y1 - 1),
                fill=layout.BLACK,
            )
        self._draw.rectangle(
            (zone.x, zone.y, zone.x1 - 1, zone.y1 - 1),
            outline=layout.BLACK,
            width=layout.HOUSE_BATTERY_BORDER_WIDTH,
        )

    def _house_text_style(self, y: int, fill_top: int) -> layout.PanelStyle:
        """White text on the black fill; black text on the unfilled area above."""
        return layout.STYLE_BATTERY if y >= fill_top else layout.STYLE_SOLAR

    def _draw_solar(self, metrics: VanMetrics) -> None:
        style = layout.STYLE_SOLAR
        self._text(layout.LABEL_SOLAR, layout.SOLAR_LABEL, self._font_label, style)
        self._text(
            fmt(metrics.victron.solar_power_w, suffix=" W"),
            layout.SOLAR_VALUE,
            self._font_hero,
            style,
        )
        self._text(
            fmt_yield_today(metrics.victron.yield_today_wh),
            layout.SOLAR_YIELD_TODAY,
            self._font_body,
            style,
        )
        self._draw_caption_right(
            f"{config.SOLAR_MAX_W} W max",
            layout.SOLAR,
            layout.SOLAR_MAX_CAPTION_Y,
            style,
        )
        if metrics.victron.error:
            self._text(
                metrics.victron.error[:28],
                (layout.SOLAR.x + 8, layout.SOLAR.y1 - 18),
                self._font_label,
                style,
            )

    def _draw_house_battery(self, metrics: VanMetrics) -> None:
        fill_top = self._house_battery_fill_top(metrics.litime.soc_percent)

        self._text(
            layout.LABEL_HOUSE,
            layout.HOUSE_LABEL,
            self._font_label,
            self._house_text_style(layout.HOUSE_LABEL[1], fill_top),
        )
        self._text(
            fmt(metrics.litime.soc_percent, suffix="%"),
            layout.HOUSE_SOC,
            self._font_hero,
            self._house_text_style(layout.HOUSE_SOC[1], fill_top),
        )
        self._text(
            fmt_signed_watts(metrics.litime.power_w),
            layout.HOUSE_POWER,
            self._font_body,
            self._house_text_style(layout.HOUSE_POWER[1], fill_top),
        )
        self._text(
            fmt(metrics.litime.voltage_v, decimals=1, suffix=" V"),
            layout.HOUSE_VOLTAGE,
            self._font_body,
            self._house_text_style(layout.HOUSE_VOLTAGE[1], fill_top),
        )
        self._draw_caption_right(
            f"{config.HOUSE_BATTERY_CAPACITY_KWH} kWh capacity",
            layout.HOUSE_BATTERY,
            layout.HOUSE_CAPACITY_CAPTION_Y,
            self._house_text_style(layout.HOUSE_CAPACITY_CAPTION_Y, fill_top),
        )
        if metrics.litime.error:
            self._text(
                metrics.litime.error[:28],
                (layout.HOUSE_BATTERY.x + 8, layout.HOUSE_BATTERY.y + 8),
                self._font_label,
                layout.STYLE_SOLAR,
            )

    def _draw_updated_at(self, metrics: VanMetrics) -> None:
        stamp = fmt_updated_at(metrics.updated_at)
        if not stamp:
            return
        style = layout.STYLE_SOLAR
        self._text(stamp, layout.UPDATED_AT, self._font_label, style)

    def show_metrics(self, metrics: VanMetrics, *, partial: bool = False) -> None:
        self.render(metrics)
        self.refresh(partial=partial)

    def show_status_message(self, message: str) -> None:
        self.reset_canvas()
        style = layout.STYLE_SOLAR
        self._text("van-monitor", (16, 16), self._font_label, style)
        self._text(message, (16, 40), self._font_body, style)
        self.refresh(partial=False)
