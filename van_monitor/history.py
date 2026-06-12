"""
Persistent time-series log of battery SOC and solar power.

Points are kept in memory for fast chart rendering and appended to a JSONL file
(one JSON object per line) so the history survives reboots. The log is pruned to
a rolling retention window (default 24h); the charts display a shorter window.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path

import config

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class HistoryPoint:
    """A single logged reading."""

    t: float  # epoch seconds
    soc: float | None  # Li-Time house battery SOC, %
    solar: float | None  # solar power, W
    anker_soc: float | None = None  # Anker SOC, %


def _coerce_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


class MetricsHistory:
    """Append-only SOC/solar log, pruned to a rolling time window."""

    def __init__(
        self,
        path: Path | str | None = None,
        *,
        window_seconds: float | None = None,
        min_interval_seconds: float | None = None,
        prune_interval_seconds: float = 3600.0,
    ) -> None:
        self.path = Path(path) if path is not None else Path(config.HISTORY_FILE)
        self.window_seconds = (
            window_seconds
            if window_seconds is not None
            else config.HISTORY_RETENTION_HOURS * 3600
        )
        self._min_interval = (
            min_interval_seconds
            if min_interval_seconds is not None
            else config.HISTORY_SAMPLE_INTERVAL_SECONDS
        )
        self._prune_interval = prune_interval_seconds
        self._points: list[HistoryPoint] = []
        self._last_recorded_t: float | None = None
        self._last_prune = time.monotonic()
        self._load()

    def record(
        self,
        soc: float | None,
        solar: float | None,
        *,
        anker_soc: float | None = None,
        now: float | None = None,
    ) -> bool:
        """
        Append a reading to memory and disk, then prune old data.

        Skips (returns False) if the last point is newer than the sampling
        interval, so logging cadence stays independent of the display poll.
        """
        now = now if now is not None else time.time()
        if (
            self._min_interval > 0
            and self._last_recorded_t is not None
            and (now - self._last_recorded_t) < self._min_interval
        ):
            return False

        point = HistoryPoint(now, soc, solar, anker_soc)
        self._points.append(point)
        self._last_recorded_t = now
        self._append_line(point)
        self._trim_memory(now)
        if time.monotonic() - self._last_prune >= self._prune_interval:
            self._prune_file(now)
        return True

    def points(self) -> list[HistoryPoint]:
        """Return a copy of the in-window points, oldest first."""
        return list(self._points)

    def _load(self) -> None:
        if not self.path.is_file():
            return
        cutoff = time.time() - self.window_seconds
        points: list[HistoryPoint] = []
        try:
            with self.path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    t = _coerce_float(obj.get("t"))
                    if t is None or t < cutoff:
                        continue
                    points.append(
                        HistoryPoint(
                            t,
                            _coerce_float(obj.get("soc")),
                            _coerce_float(obj.get("solar")),
                            _coerce_float(obj.get("anker_soc")),
                        )
                    )
        except OSError as exc:
            logger.warning("History: could not read %s: %s", self.path, exc)
            return
        points.sort(key=lambda p: p.t)
        self._points = points
        if points:
            self._last_recorded_t = points[-1].t
        logger.info("History: loaded %d points from %s", len(points), self.path)

    def _trim_memory(self, now: float) -> None:
        cutoff = now - self.window_seconds
        if self._points and self._points[0].t < cutoff:
            self._points = [p for p in self._points if p.t >= cutoff]

    def _serialize(self, point: HistoryPoint) -> str:
        payload = {
            "t": round(point.t, 1),
            "soc": point.soc,
            "solar": point.solar,
        }
        if point.anker_soc is not None:
            payload["anker_soc"] = point.anker_soc
        return json.dumps(payload)

    def _append_line(self, point: HistoryPoint) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(self._serialize(point) + "\n")
        except OSError as exc:
            logger.warning("History: could not append to %s: %s", self.path, exc)

    def _prune_file(self, now: float) -> None:
        self._last_prune = time.monotonic()
        cutoff = now - self.window_seconds
        kept = [p for p in self._points if p.t >= cutoff]
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with tmp.open("w", encoding="utf-8") as fh:
                for point in kept:
                    fh.write(self._serialize(point) + "\n")
            os.replace(tmp, self.path)
            logger.info("History: pruned log to %d points", len(kept))
        except OSError as exc:
            logger.warning("History: could not prune %s: %s", self.path, exc)
