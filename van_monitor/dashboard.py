"""Render van metrics on the e-paper display."""

from __future__ import annotations

from van_monitor.display import EpaperDisplay
from van_monitor.metrics import VanMetrics, fmt


class MetricsDashboard(EpaperDisplay):
    """Draw P0 metrics as simple fixed text zones."""

    def render(self, metrics: VanMetrics) -> None:
        """Redraw the full metrics screen."""
        self.reset_canvas()

        y = 8
        y = self._line("van-monitor", y, size=1)
        y += 4
        y = self._line("Li-Time battery", y)
        y = self._line(f"  SOC  {fmt(metrics.litime.soc_percent, suffix='%')}", y)
        y = self._line(f"  Pwr  {fmt(metrics.litime.power_w, suffix=' W')}", y)
        y = self._line(f"  Volt {fmt(metrics.litime.voltage_v, decimals=1, suffix=' V')}", y)
        if metrics.litime.error:
            y = self._line(f"  ! {metrics.litime.error[:42]}", y)

        y += 4
        y = self._line("Victron solar", y)
        y = self._line(f"  Out  {fmt(metrics.victron.solar_power_w, suffix=' W')}", y)
        if metrics.victron.error:
            y = self._line(f"  ! {metrics.victron.error[:42]}", y)

        y += 4
        y = self._line("Anker", y)
        y = self._line(f"  SOC  {fmt(metrics.anker.soc_percent, suffix='%')}", y)
        y = self._line(f"  In   {fmt(metrics.anker.power_in_w, suffix=' W')}", y)
        y = self._line(f"  Out  {fmt(metrics.anker.power_out_w, suffix=' W')}", y)
        if metrics.anker.error:
            y = self._line(f"  ! {metrics.anker.error[:42]}", y)

        y += 4
        stamp = metrics.updated_at.strftime("%H:%M:%S") if metrics.updated_at else "--:--:--"
        self._line(f"Updated {stamp}", y)

    def _line(self, text: str, y: int, *, size: int = 0) -> int:
        self.draw_text(text, x=8, y=y)
        return y + 16 + (4 * size)

    def show_metrics(self, metrics: VanMetrics, *, partial: bool = False) -> None:
        """Render metrics and push them to the panel."""
        self.render(metrics)
        self.refresh(partial=partial)

    def show_status_message(self, message: str) -> None:
        """Show a single status line (useful while waiting for BLE)."""
        self.reset_canvas()
        self.draw_text("van-monitor", x=8, y=8)
        self.draw_text(message, x=8, y=32)
        self.refresh(partial=False)
