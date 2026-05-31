"""Reading types and formatting helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import config


@dataclass
class LitimeMetrics:
    soc_percent: float | None = None
    power_w: float | None = None
    voltage_v: float | None = None
    connected: bool = False
    error: str = ""


@dataclass
class VictronMetrics:
    solar_power_w: float | None = None
    yield_today_wh: float | None = None
    connected: bool = False
    error: str = ""


@dataclass
class AnkerMetrics:
    soc_percent: float | None = None
    power_in_w: float | None = None
    power_out_w: float | None = None
    connected: bool = False
    error: str = ""


@dataclass
class VanMetrics:
    litime: LitimeMetrics = field(default_factory=LitimeMetrics)
    victron: VictronMetrics = field(default_factory=VictronMetrics)
    anker: AnkerMetrics = field(default_factory=AnkerMetrics)
    updated_at: datetime | None = None


def fmt_yield_today(wh: float | None) -> str:
    """Format daily solar yield like Figma: '645 Wh today'."""
    if wh is None:
        return f"{config.UNAVAILABLE_LABEL} Wh today"
    return f"{int(round(wh))} Wh today"


def fmt(value: float | int | None, *, decimals: int = 0, suffix: str = "") -> str:
    """Format a numeric reading, or NA when missing."""
    if value is None:
        return config.UNAVAILABLE_LABEL
    if decimals == 0:
        text = str(int(round(value)))
    else:
        text = f"{value:.{decimals}f}"
    return f"{text}{suffix}"


def fmt_signed_watts(power_w: float | None) -> str:
    """Format signed watts like Figma v2: '+40 W' or '-718 W'."""
    if power_w is None:
        return config.UNAVAILABLE_LABEL
    watts = int(round(power_w))
    if watts > 0:
        return f"+{watts} W"
    return f"{watts} W"


def fmt_anker_net(power_in_w: float | None, power_out_w: float | None) -> str:
    """Anker net power (W in minus W out)."""
    if power_in_w is None or power_out_w is None:
        return config.UNAVAILABLE_LABEL
    return fmt_signed_watts(power_in_w - power_out_w)


def print_metrics(metrics: VanMetrics) -> None:
    """Print all metrics to the terminal for debugging."""
    updated = metrics.updated_at.strftime("%H:%M:%S") if metrics.updated_at else "?"

    print()
    print(f"=== van-monitor readings @ {updated} ===")

    print("Li-Time battery:")
    if metrics.litime.error:
        print(f"  error: {metrics.litime.error}")
    print(f"  SOC:     {fmt(metrics.litime.soc_percent, suffix='%')}")
    print(f"  Power:   {fmt(metrics.litime.power_w, suffix=' W')}")
    print(f"  Voltage: {fmt(metrics.litime.voltage_v, decimals=1, suffix=' V')}")

    print("Victron solar:")
    if metrics.victron.error:
        print(f"  error: {metrics.victron.error}")
    print(f"  Output:  {fmt(metrics.victron.solar_power_w, suffix=' W')}")
    print(f"  Today:   {fmt_yield_today(metrics.victron.yield_today_wh)}")

    print("Anker:")
    if metrics.anker.error:
        print(f"  error: {metrics.anker.error}")
    print(f"  SOC:     {fmt(metrics.anker.soc_percent, suffix='%')}")
    print(f"  Net:     {fmt_anker_net(metrics.anker.power_in_w, metrics.anker.power_out_w)}")
    print(f"    (in {fmt(metrics.anker.power_in_w, suffix=' W')}, out {fmt(metrics.anker.power_out_w, suffix=' W')})")
    print()
