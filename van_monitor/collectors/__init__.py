"""Poll all configured devices."""

from __future__ import annotations

import logging
from datetime import datetime

from van_monitor.collectors.anker import read_anker
from van_monitor.collectors.litime import read_litime
from van_monitor.collectors.victron import read_victron
from van_monitor.metrics import VanMetrics

logger = logging.getLogger(__name__)


def poll_all() -> VanMetrics:
    """
    Read each device one at a time.

    Devices are polled sequentially because the Pi Zero W BLE radio handles
    one connection at a time more reliably than overlapping operations.
    """
    metrics = VanMetrics()

    logger.info("Polling Li-Time...")
    metrics.litime = read_litime()

    logger.info("Polling Victron...")
    metrics.victron = read_victron()

    logger.info("Polling Anker...")
    metrics.anker = read_anker()

    metrics.updated_at = datetime.now()
    return metrics
