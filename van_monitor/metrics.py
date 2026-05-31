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


def fmt(value: float | int | None, *, decimals: int = 0, suffix: str = "") -> str:
    """Format a numeric reading, or NA when missing."""
    if value is None:
        return config.UNAVAILABLE_LABEL
    if decimals == 0:
        text = str(int(round(value)))
    else:
        text = f"{value:.{decimals}f}"
    return f"{text}{suffix}"


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

    print("Anker:")
    if metrics.anker.error:
        print(f"  error: {metrics.anker.error}")
    print(f"  SOC:     {fmt(metrics.anker.soc_percent, suffix='%')}")
    print(f"  Power in:  {fmt(metrics.anker.power_in_w, suffix=' W')}")
    print(f"  Power out: {fmt(metrics.anker.power_out_w, suffix=' W')}")
    print()
