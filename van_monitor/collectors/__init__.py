"""Poll all configured devices."""

from __future__ import annotations

import logging
import time
from datetime import datetime

import config
from van_monitor.collectors.litime import read_litime
from van_monitor.collectors.victron import read_victron
from van_monitor.metrics import VanMetrics

logger = logging.getLogger(__name__)


def _cooldown() -> None:
    if config.BLE_COOLDOWN_SECONDS > 0:
        time.sleep(config.BLE_COOLDOWN_SECONDS)


def poll_all() -> VanMetrics:
    """
    Read each device one at a time.

    Devices are polled sequentially because the Pi Zero W BLE radio handles
    one connection at a time more reliably than overlapping operations.
    Victron is passive (advertisements only) and runs between connect cycles.

    Anker is intentionally omitted from the main loop for now. The Gen 2 driver
    (van_monitor/collectors/anker_g2.py) works, but it needs a one-time button
    press to pair and the current v4 display layout has no Anker panel. Validate
    with scripts/test_anker.py first, then add it here once it's on the display.
    """
    metrics = VanMetrics()

    logger.info("Polling Li-Time...")
    metrics.litime = read_litime()
    _cooldown()

    logger.info("Polling Victron...")
    metrics.victron = read_victron()

    metrics.updated_at = datetime.now()
    return metrics
