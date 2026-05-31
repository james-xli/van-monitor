"""Read the Li-Time house battery over BLE."""

from __future__ import annotations

import logging

from litime_ble import BatteryClient, find_litime_batteries_sync

import config
from van_monitor.metrics import LitimeMetrics

logger = logging.getLogger(__name__)


def read_litime(address: str | None = None, *, timeout: float | None = None) -> LitimeMetrics:
    """
    Connect to the Li-Time battery, read once, and disconnect.

    If address is empty, scan briefly and use the first Li-Time battery found.
    """
    metrics = LitimeMetrics()
    addr = (address or config.LITIME_ADDRESS).strip()

    try:
        if not addr:
            logger.info("Li-Time: scanning for batteries...")
            batteries = find_litime_batteries_sync(timeout=timeout or config.BLE_TIMEOUT_SECONDS)
            if not batteries:
                metrics.error = "No Li-Time battery found during scan"
                return metrics
            addr = batteries[0]["address"]
            logger.info("Li-Time: found %s (%s)", batteries[0].get("name", "?"), addr)

        client = BatteryClient(address=addr)
        with client.sync() as connected:
            status = connected.read_once()

        metrics.connected = True
        metrics.soc_percent = status.soc_percent
        metrics.power_w = status.power_w
        metrics.voltage_v = status.voltage_v
        logger.info(
            "Li-Time: %.0f%% %.0fW %.1fV",
            metrics.soc_percent or 0,
            metrics.power_w or 0,
            metrics.voltage_v or 0,
        )
    except Exception as exc:
        metrics.error = str(exc)
        logger.warning("Li-Time: %s", exc)

    return metrics
