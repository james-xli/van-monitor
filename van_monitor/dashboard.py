"""
Render van metrics on the e-paper display.

Layout matches Figma "Main screen v8 w/ Anker" (node 42:116), strict B/W.

The house and Anker panels show SOC area charts in their top regions; the solar
panel shows a stroke-only power line. Stats sit on white below each divider.
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
    fmt_anker_power_lines,
    fmt_date_lines,
    fmt_signed_watts,
    fmt_yield_today,
)


class _HistoryPoint(Protocol):
    t: float
    soc: float | None
    solar: float | None
    anker_soc: float | None


class MetricsDashboard(EpaperDisplay):
    """Draw metrics in fixed zones (Figma Main screen v8 w/ Anker)."""

    def __init__(self):
        super().__init__()
        self._font_label = load_bold_font(layout.FONT_LABEL)
        self._font_stats = load_bold_font(layout.FONT_STATS)
        self._font_hero = load_bold_font(layout.FONT_HERO)
        self._font_solar_hero = load_bold_font(layout.FONT_SOLAR_HERO)
        self._font_solar_body = load_bold_font(layout.FONT_SOLAR_BODY)
        self._font_caption = load_caption_font(layout.FONT_CAPTION)
        self._font_date = load_bold_font(layout.FONT_DATE)

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
        self._draw_anker_background(history, now)
        self._draw_flow_arrows()
        self._draw_solar(metrics)
        self._draw_house_battery(metrics)
        self._draw_anker(metrics)
        self._draw_date(metrics)

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
        """Map each pixel column to a value via sample-and-hold."""
        col_values: list[float | None] = [None] * width
        points = sorted(
            ((p.t, value_of(p)) for p in history if value_of(p) is not None),
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

    def _draw_dotted_horizontal_above_fill(
        self,
        y: int,
        chart: layout.Zone,
        col_fill_top: Sequence[int],
    ) -> None:
        """Black dotted horizontal gridline only where y sits above the SOC fill."""
        period = layout.GRID_DASH_LEN + layout.GRID_DASH_GAP
        run_start: int | None = None
        for col in range(chart.width):
            x = chart.x + col
            above = chart.y <= y < col_fill_top[col]
            on_dash = (col % period) < layout.GRID_DASH_LEN
            if above and on_dash:
                if run_start is None:
                    run_start = x
            elif run_start is not None:
                self._draw.line((run_start, y, x - 1, y), fill=layout.BLACK)
                run_start = None
        if run_start is not None:
            self._draw.line((run_start, y, chart.x1 - 1, y), fill=layout.BLACK)

    def _draw_soc_area_chart(
        self,
        panel: layout.Zone,
        chart: layout.Zone,
        history: Sequence[_HistoryPoint],
        now: float,
        window: float,
        value_of,
    ) -> None:
        """Black SOC fill from the curve down to the divider; white above."""
        self._draw.rectangle((panel.x, panel.y, panel.x1 - 1, panel.y1 - 1), fill=layout.WHITE)

        col_soc = self._column_series(history, now, window, chart.width, value_of)
        for col, soc in enumerate(col_soc):
            if soc is None:
                continue
            x = chart.x + col
            fill_top = self._value_to_y(chart, soc, 100.0)
            if fill_top <= chart.y1 - 1:
                self._draw.line((x, fill_top, x, chart.y1 - 1), fill=layout.BLACK)

        col_fill_top = [
            self._value_to_y(chart, soc, 100.0) if soc is not None else chart.y1
            for soc in col_soc
        ]

        for col in self._hour_gridline_columns(window, chart.width):
            fill_top = col_fill_top[col]
            if fill_top - 1 >= chart.y:
                self._draw.line(
                    (chart.x + col, chart.y, chart.x + col, fill_top - 1),
                    fill=layout.BLACK,
                )

        for pct in range(layout.SOC_GRID_STEP, 100, layout.SOC_GRID_STEP):
            y = self._value_to_y(chart, float(pct), 100.0)
            self._draw_dotted_horizontal_above_fill(y, chart, col_fill_top)

        divider_y = chart.y + chart.height
        self._draw.line(
            (panel.x, divider_y, panel.x1 - 1, divider_y),
            fill=layout.BLACK,
            width=layout.SOLAR_DIVIDER_WIDTH,
        )

        self._clip_corners(panel)
        self._draw_panel_border(panel, layout.STYLE_BATTERY)

    # --- house battery SOC history chart ------------------------------------

    def _draw_house_battery_background(
        self,
        history: Sequence[_HistoryPoint],
        now: float,
    ) -> None:
        window = config.HOUSE_HISTORY_HOURS * 3600
        self._draw_soc_area_chart(
            layout.HOUSE_BATTERY,
            layout.HOUSE_CHART,
            history,
            now,
            window,
            lambda p: p.soc,
        )

    # --- anker SOC history chart --------------------------------------------

    def _draw_anker_background(
        self,
        history: Sequence[_HistoryPoint],
        now: float,
    ) -> None:
        window = config.HOUSE_HISTORY_HOURS * 3600
        self._draw_soc_area_chart(
            layout.ANKER,
            layout.ANKER_CHART,
            history,
            now,
            window,
            lambda p: p.anker_soc,
        )

    # --- solar power history line chart -------------------------------------

    def _draw_solar_chart(
        self,
        history: Sequence[_HistoryPoint],
        now: float,
    ) -> None:
        chart = layout.SOLAR_CHART
        panel = layout.SOLAR
        window = config.SOLAR_HISTORY_HOURS * 3600

        col_w = self._column_series(history, now, window, chart.width, lambda p: p.solar)
        vmax = float(config.SOLAR_MAX_W)

        col_line_y = [
            self._value_to_y(chart, value, vmax) if value is not None else chart.y1
            for value in col_w
        ]

        for col in self._hour_gridline_columns(window, chart.width):
            line_y = col_line_y[col]
            if line_y - 1 >= panel.y:
                self._draw.line((chart.x + col, panel.y, chart.x + col, line_y - 1), fill=layout.BLACK)

        for watts in range(layout.SOLAR_GRID_STEP, int(vmax), layout.SOLAR_GRID_STEP):
            y = self._value_to_y(chart, float(watts), vmax)
            self._draw_dotted_horizontal_above_fill(y, chart, col_line_y)

        half = layout.SOLAR_LINE_WIDTH // 2
        y_min = chart.y + half
        y_max = chart.y1
        run: list[tuple[int, int]] = []
        for col, value in enumerate(col_w):
            if value is None:
                self._flush_line(run)
                run = []
                continue
            y = self._value_to_y(chart, value, vmax)
            y = max(y_min, min(y_max, y))
            run.append((chart.x + col, y))
        self._flush_line(run)

        self._draw.line(
            (panel.x, layout.SOLAR_DIVIDER_Y, panel.x1 - 1, layout.SOLAR_DIVIDER_Y),
            fill=layout.BLACK,
            width=layout.SOLAR_DIVIDER_WIDTH,
        )

        self._clip_corners(panel)
        self._draw_panel_border(panel, layout.STYLE_SOLAR)

    def _flush_line(self, run: list[tuple[int, int]]) -> None:
        if len(run) >= 2:
            self._draw.line(run, fill=layout.BLACK, width=layout.SOLAR_LINE_WIDTH)
        elif len(run) == 1:
            self._draw.point(run[0], fill=layout.BLACK)

    # --- flow arrows --------------------------------------------------------

    def _draw_flow_arrows(self) -> None:
        self._draw_arrow(*layout.ARROW_SOLAR_TO_HOUSE, fill=layout.BLACK)
        self._draw_arrow(*layout.ARROW_HOUSE_TO_ANKER, fill=layout.BLACK)

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
    ) -> None:
        font = self._font_caption
        bbox = self._draw.textbbox((0, 0), text, font=font)
        width = bbox[2] - bbox[0]
        x = zone.x1 - width - layout.CAPTION_RIGHT_MARGIN
        self._text(text, (x, y), font, style)

    def _text_right(
        self,
        text: str,
        right_x: int,
        y: int,
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        style: layout.PanelStyle,
    ) -> None:
        bbox = self._draw.textbbox((0, 0), text, font=font)
        width = bbox[2] - bbox[0]
        self._text(text, (right_x - width, y), font, style)

    # --- panels -------------------------------------------------------------

    def _draw_solar(self, metrics: VanMetrics) -> None:
        style = layout.STYLE_SOLAR
        self._text(layout.LABEL_SOLAR, layout.SOLAR_LABEL, self._font_label, style)
        self._text(
            fmt(metrics.victron.solar_power_w, suffix=" W"),
            layout.SOLAR_VALUE,
            self._font_solar_hero,
            style,
        )
        self._text(
            fmt_yield_today(metrics.victron.yield_today_wh),
            layout.SOLAR_YIELD_TODAY,
            self._font_solar_body,
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
        style = layout.STYLE_BATTERY
        self._text(layout.LABEL_HOUSE, layout.HOUSE_LABEL, self._font_label, style)
        self._text(
            fmt(metrics.litime.soc_percent, suffix="%"),
            layout.HOUSE_SOC,
            self._font_hero,
            style,
        )
        self._text_right(
            fmt_signed_watts(metrics.litime.power_w),
            layout.HOUSE_STATS_RIGHT,
            layout.HOUSE_POWER_Y,
            self._font_stats,
            style,
        )
        self._text_right(
            fmt(metrics.litime.voltage_v, decimals=1, suffix=" V"),
            layout.HOUSE_STATS_RIGHT,
            layout.HOUSE_VOLTAGE_Y,
            self._font_stats,
            style,
        )
        self._draw_caption_right(
            f"{config.HOUSE_BATTERY_CAPACITY_KWH} kWh capacity",
            layout.HOUSE_BATTERY,
            layout.HOUSE_CAPACITY_CAPTION_Y,
            style,
        )
        if metrics.litime.error:
            self._text(
                metrics.litime.error[:28],
                (layout.HOUSE_BATTERY.x + 16, layout.HOUSE_DIVIDER_Y + 4),
                self._font_label,
                style,
            )

    def _draw_anker(self, metrics: VanMetrics) -> None:
        style = layout.STYLE_BATTERY
        self._text(layout.LABEL_ANKER, layout.ANKER_LABEL, self._font_label, style)
        self._text(
            fmt(metrics.anker.soc_percent, suffix="%"),
            layout.ANKER_SOC,
            self._font_hero,
            style,
        )
        power_in, power_out = fmt_anker_power_lines(
            metrics.anker.power_in_w,
            metrics.anker.power_out_w,
        )
        self._text_right(
            power_in,
            layout.ANKER_STATS_RIGHT,
            layout.ANKER_POWER_IN_Y,
            self._font_stats,
            style,
        )
        self._text_right(
            power_out,
            layout.ANKER_STATS_RIGHT,
            layout.ANKER_POWER_OUT_Y,
            self._font_stats,
            style,
        )
        self._draw_caption_right(
            f"{config.ANKER_CAPACITY_KWH} kWh capacity",
            layout.ANKER,
            layout.ANKER_CAPACITY_CAPTION_Y,
            style,
        )
        if metrics.anker.error:
            self._text(
                metrics.anker.error[:28],
                (layout.ANKER.x + 16, layout.ANKER_DIVIDER_Y + 4),
                self._font_label,
                style,
            )

    def _draw_date(self, metrics: VanMetrics) -> None:
        line1, line2 = fmt_date_lines(metrics.updated_at)
        if not line1 and not line2:
            return
        style = layout.STYLE_SOLAR
        x, y = layout.DATE_ORIGIN
        self._text(line1, (x, y), self._font_date, style)
        self._text(line2, (x, y + layout.DATE_LINE_HEIGHT), self._font_date, style)

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
        self._text(message, (16, 40), self._font_stats, style)
        self.refresh(partial=False)
