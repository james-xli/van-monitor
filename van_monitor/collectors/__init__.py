"""Poll all configured devices."""

from __future__ import annotations

import logging
import time
from datetime import datetime

import config
from van_monitor.collectors.anker import read_anker
from van_monitor.collectors.litime import read_litime
from van_monitor.collectors.victron import read_victron
from van_monitor.metrics import AnkerMetrics, VanMetrics

logger = logging.getLogger(__name__)

_last_anker_poll: float = 0.0
_cached_anker: AnkerMetrics = AnkerMetrics()


def _cooldown() -> None:
    if config.BLE_COOLDOWN_SECONDS > 0:
        time.sleep(config.BLE_COOLDOWN_SECONDS)


def _poll_anker_if_due() -> AnkerMetrics:
    """
    Read the Anker on a slower cadence than Li-Time/Victron.

    Each Anker read reconnects and runs the full BLE handshake (~15–30s), so
    polling it every display cycle would dominate the loop.
    """
    global _last_anker_poll, _cached_anker

    now = time.time()
    if now - _last_anker_poll < config.ANKER_POLL_INTERVAL_SECONDS:
        return _cached_anker

    logger.info("Polling Anker...")
    _cached_anker = read_anker()
    _last_anker_poll = now
    _cooldown()
    return _cached_anker


def poll_all() -> VanMetrics:
    """
    Read each device one at a time.

    Devices are polled sequentially because the Pi Zero W BLE radio handles
    one connection at a time more reliably than overlapping operations.
    Victron is passive (advertisements only) and runs between connect cycles.
    Anker is polled less often (see ANKER_POLL_INTERVAL_SECONDS).
    """
    metrics = VanMetrics()

    logger.info("Polling Li-Time...")
    metrics.litime = read_litime()
    _cooldown()

    logger.info("Polling Victron...")
    metrics.victron = read_victron()
    _cooldown()

    metrics.anker = _poll_anker_if_due()

    metrics.updated_at = datetime.now()
    return metrics
