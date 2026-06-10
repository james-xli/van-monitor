"""
Render P0 van metrics on the e-paper display.

Layout matches Figma "Main screen v4 w/o Anker" (node 21:30), strict B/W, no chart fills.

The house battery panel's black background is a 12h SOC area chart: the latest SOC
sits at the right edge, fill height at each column equals SOC% at that time, and thin
vertical lines mark each 1h increment counting back from now.
"""

from __future__ import annotations

import time
from collections.abc import Sequence
from typing import Protocol

from PIL import Image, ImageDraw, ImageFont

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


class _HistoryPoint(Protocol):
    t: float
    soc: float | None
    solar: float | None


class MetricsDashboard(EpaperDisplay):
    """Draw P0 metrics in fixed zones (Figma Main screen v4 w/o Anker)."""

    def __init__(self):
        super().__init__()
        self._font_label = load_bold_font(layout.FONT_LABEL)
        self._font_body = load_bold_font(layout.FONT_BODY)
        self._font_hero = load_bold_font(layout.FONT_HERO)
        self._font_caption = load_caption_font(layout.FONT_CAPTION)

    def render(
        self,
        metrics: VanMetrics,
        *,
        history: Sequence[_HistoryPoint] | None = None,
        now: float | None = None,
    ) -> None:
        """Redraw the full metrics screen."""
        if now is None:
            now = time.time()
        history = history or []
        self.reset_canvas()
        self._draw_zone(layout.SOLAR, layout.STYLE_SOLAR)
        self._draw_solar_chart(history, now)
        self._draw_house_battery_background(history, now)
        self._draw_flow_arrows()
        self._draw_solar(metrics)
        self._draw_house_battery(metrics)
        self._draw_updated_at(metrics)

    def _zone_bbox(self, zone: layout.Zone) -> tuple[int, int, int, int]:
        return (zone.x, zone.y, zone.x1 - 1, zone.y1 - 1)

    def _draw_zone(self, zone: layout.Zone, style: layout.PanelStyle) -> None:
        self._draw.rounded_rectangle(
            self._zone_bbox(zone),
            radius=layout.PANEL_CORNER_RADIUS,
            fill=style.fill,
            outline=style.border if style.border_width else style.fill,
            width=style.border_width,
        )

    def _clip_corners(self, zone: layout.Zone) -> None:
        """Whiten the four corner notches so chart content respects the radius."""
        bbox = self._zone_bbox(zone)
        notch = Image.new("1", (self.width, self.height), 0)
        nd = ImageDraw.Draw(notch)
        nd.rectangle(bbox, fill=1)
        nd.rounded_rectangle(bbox, radius=layout.PANEL_CORNER_RADIUS, fill=0)
        self._canvas.paste(layout.WHITE, mask=notch)

    def _draw_panel_border(self, zone: layout.Zone, style: layout.PanelStyle) -> None:
        self._draw.rounded_rectangle(
            self._zone_bbox(zone),
            radius=layout.PANEL_CORNER_RADIUS,
            outline=style.border,
            width=style.border_width,
        )

    # --- shared chart helpers ----------------------------------------------

    def _value_to_y(self, zone: layout.Zone, value: float, vmax: float, vmin: float = 0.0) -> int:
        """Absolute screen Y for a value mapped onto the zone (vmax = top)."""
        span = vmax - vmin
        frac = 0.0 if span <= 0 else (value - vmin) / span
        frac = max(0.0, min(1.0, frac))
        height = int(round(zone.height * frac))
        return zone.y + zone.height - height

    def _column_series(
        self,
        history: Sequence[_HistoryPoint],
        now: float,
        window: float,
        width: int,
        value_of,
    ) -> list[float | None]:
        """
        Map each pixel column to a value via sample-and-hold (last known value).

        Columns earlier than the first data point stay None (not drawn), which
        keeps the chart time-accurate after a fresh boot.
        """
        col_values: list[float | None] = [None] * width
        points = sorted(
            (
                (p.t, value_of(p))
                for p in history
                if value_of(p) is not None
            ),
            key=lambda item: item[0],
        )
        if not points or width <= 0:
            return col_values

        start = now - window
        idx = 0
        last = len(points) - 1
        for col in range(width):
            col_time = now if width == 1 else start + (col / (width - 1)) * window
            while idx < last and points[idx + 1][0] <= col_time:
                idx += 1
            if points[idx][0] <= col_time:
                col_values[col] = points[idx][1]
        return col_values

    def _hour_gridline_columns(self, window: float, width: int):
        """Yield interior column indices for each hour increment back from now."""
        grid = config.HISTORY_GRID_HOURS * 3600
        if grid <= 0 or width <= 1:
            return
        k = 1
        while k * grid < window:
            frac = 1.0 - (k * grid) / window
            col = int(round(frac * (width - 1)))
            k += 1
            if 0 < col < width:
                yield col

    # --- house battery SOC history chart ------------------------------------

    def _draw_house_battery_background(
        self,
        history: Sequence[_HistoryPoint],
        now: float,
    ) -> None:
        zone = layout.HOUSE_BATTERY
        window = config.HISTORY_WINDOW_HOURS * 3600

        self._draw.rectangle((zone.x, zone.y, zone.x1 - 1, zone.y1 - 1), fill=layout.WHITE)

        col_soc = self._column_series(history, now, window, zone.width, lambda p: p.soc)
        for col, soc in enumerate(col_soc):
            if soc is None:
                continue
            x = zone.x + col
            fill_top = self._value_to_y(zone, soc, 100.0)
            if fill_top <= zone.y1 - 1:
                self._draw.line((x, fill_top, x, zone.y1 - 1), fill=layout.BLACK)

        # Vertical hour gridlines, black, only in the white area above the fill.
        for col in self._hour_gridline_columns(window, zone.width):
            soc = col_soc[col]
            fill_top = self._value_to_y(zone, soc, 100.0) if soc is not None else zone.y1
            if fill_top - 1 >= zone.y:
                self._draw.line((zone.x + col, zone.y, zone.x + col, fill_top - 1), fill=layout.BLACK)

        # Clip the fill out of the rounded corners, then stroke the rounded frame.
        self._clip_corners(zone)
        self._draw_panel_border(zone, layout.STYLE_BATTERY)

    # --- solar power history line chart -------------------------------------

    def _draw_solar_chart(
        self,
        history: Sequence[_HistoryPoint],
        now: float,
    ) -> None:
        zone = layout.SOLAR
        window = config.HISTORY_WINDOW_HOURS * 3600

        # Stroke-only line of solar power (0..SOLAR_MAX_W), latest at the right edge.
        col_w = self._column_series(history, now, window, zone.width, lambda p: p.solar)
        vmax = float(config.SOLAR_MAX_W)

        # Hour gridlines, black, only in the area above the line (mirrors the battery panel).
        for col in self._hour_gridline_columns(window, zone.width):
            value = col_w[col]
            line_y = self._value_to_y(zone, value, vmax) if value is not None else zone.y1
            if line_y - 1 >= zone.y:
                self._draw.line((zone.x + col, zone.y, zone.x + col, line_y - 1), fill=layout.BLACK)

        # Keep the full stroke width inside the frame (0 W would otherwise spill
        # below the bottom border).
        half = layout.SOLAR_LINE_WIDTH // 2
        y_min = zone.y + half
        y_max = zone.y1 - 1 - half
        run: list[tuple[int, int]] = []
        for col, value in enumerate(col_w):
            if value is None:
                self._flush_line(run)
                run = []
                continue
            y = self._value_to_y(zone, value, vmax)
            y = max(y_min, min(y_max, y))
            run.append((zone.x + col, y))
        self._flush_line(run)

        # Clip the line/gridlines out of the rounded corners, then stroke the frame.
        self._clip_corners(zone)
        self._draw_panel_border(zone, layout.STYLE_SOLAR)

    def _flush_line(self, run: list[tuple[int, int]]) -> None:
        if len(run) >= 2:
            self._draw.line(run, fill=layout.BLACK, width=layout.SOLAR_LINE_WIDTH)
        elif len(run) == 1:
            self._draw.point(run[0], fill=layout.BLACK)

    # --- flow arrows --------------------------------------------------------

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

    # --- text helpers -------------------------------------------------------

    def _text(
        self,
        text: str,
        xy: tuple[int, int],
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        style: layout.PanelStyle,
        *,
        stroke_width: int | None = None,
    ) -> None:
        if stroke_width is None:
            stroke_width = layout.TEXT_STROKE_WIDTH
        self._draw.text(
            xy,
            text,
            font=font,
            fill=style.text_fill,
            stroke_width=stroke_width,
            stroke_fill=style.text_stroke,
        )

    def _draw_caption_right(
        self,
        text: str,
        zone: layout.Zone,
        y: int,
        style: layout.PanelStyle,
        *,
        stroke_width: int | None = None,
    ) -> None:
        """Right-aligned caption (Inter Medium Italic 14px)."""
        font = self._font_caption
        bbox = self._draw.textbbox((0, 0), text, font=font)
        width = bbox[2] - bbox[0]
        x = zone.x1 - width - layout.CAPTION_RIGHT_MARGIN
        self._text(text, (x, y), font, style, stroke_width=stroke_width)

    # --- panels -------------------------------------------------------------

    def _draw_solar(self, metrics: VanMetrics) -> None:
        # Black text with a white halo stays readable over the line chart + gridlines.
        style = layout.STYLE_SOLAR
        sw = layout.SOLAR_TEXT_STROKE_WIDTH
        self._text(layout.LABEL_SOLAR, layout.SOLAR_LABEL, self._font_label, style, stroke_width=sw)
        self._text(
            fmt(metrics.victron.solar_power_w, suffix=" W"),
            layout.SOLAR_VALUE,
            self._font_hero,
            style,
            stroke_width=sw,
        )
        self._text(
            fmt_yield_today(metrics.victron.yield_today_wh),
            layout.SOLAR_YIELD_TODAY,
            self._font_body,
            style,
            stroke_width=sw,
        )
        self._draw_caption_right(
            f"{config.SOLAR_MAX_W} W max",
            layout.SOLAR,
            layout.SOLAR_MAX_CAPTION_Y,
            style,
            stroke_width=sw,
        )
        if metrics.victron.error:
            self._text(
                metrics.victron.error[:28],
                (layout.SOLAR.x + 8, layout.SOLAR.y1 - 18),
                self._font_label,
                style,
                stroke_width=sw,
            )

    def _draw_house_battery(self, metrics: VanMetrics) -> None:
        # White text with a black halo stays readable over the variable SOC chart.
        style = layout.STYLE_BATTERY
        sw = layout.HOUSE_TEXT_STROKE_WIDTH
        self._text(layout.LABEL_HOUSE, layout.HOUSE_LABEL, self._font_label, style, stroke_width=sw)
        self._text(
            fmt(metrics.litime.soc_percent, suffix="%"),
            layout.HOUSE_SOC,
            self._font_hero,
            style,
            stroke_width=sw,
        )
        self._text(
            fmt_signed_watts(metrics.litime.power_w),
            layout.HOUSE_POWER,
            self._font_body,
            style,
            stroke_width=sw,
        )
        self._text(
            fmt(metrics.litime.voltage_v, decimals=1, suffix=" V"),
            layout.HOUSE_VOLTAGE,
            self._font_body,
            style,
            stroke_width=sw,
        )
        self._draw_caption_right(
            f"{config.HOUSE_BATTERY_CAPACITY_KWH} kWh capacity",
            layout.HOUSE_BATTERY,
            layout.HOUSE_CAPACITY_CAPTION_Y,
            style,
            stroke_width=sw,
        )
        if metrics.litime.error:
            self._text(
                metrics.litime.error[:28],
                (layout.HOUSE_BATTERY.x + 8, layout.HOUSE_BATTERY.y + 8),
                self._font_label,
                style,
                stroke_width=sw,
            )

    def _draw_updated_at(self, metrics: VanMetrics) -> None:
        stamp = fmt_updated_at(metrics.updated_at)
        if not stamp:
            return
        style = layout.STYLE_SOLAR
        self._text(stamp, layout.UPDATED_AT, self._font_label, style)

    # --- public API ---------------------------------------------------------

    def show_metrics(
        self,
        metrics: VanMetrics,
        *,
        history: Sequence[_HistoryPoint] | None = None,
        now: float | None = None,
        partial: bool = False,
    ) -> None:
        self.render(metrics, history=history, now=now)
        self.refresh(partial=partial)

    def show_status_message(self, message: str) -> None:
        self.reset_canvas()
        style = layout.STYLE_SOLAR
        self._text("van-monitor", (16, 16), self._font_label, style)
        self._text(message, (16, 40), self._font_body, style)
        self.refresh(partial=False)
