"""Read the Li-Time house battery over BLE."""

from __future__ import annotations

import asyncio
import logging

from bleak import BleakClient
from bleak_retry_connector import establish_connection
from litime_ble.client import CHAR_NOTIFY, CHAR_WRITE, REQUEST_STATS, parse_payload
from litime_ble.errors import BatteryConnectionError, BatteryTimeoutError

import config
from van_monitor.ble_util import find_device
from van_monitor.metrics import LitimeMetrics

logger = logging.getLogger(__name__)

_READ_TIMEOUT_SECONDS = 8.0
_CONNECT_ATTEMPTS = 3


async def read_litime_async(
    address: str | None = None,
    *,
    scan_timeout: float | None = None,
) -> LitimeMetrics:
    """Connect to the Li-Time battery, read once, and disconnect."""
    metrics = LitimeMetrics()
    addr = (address or config.LITIME_ADDRESS).strip()
    if not addr:
        metrics.error = "LITIME_ADDRESS not set in config.py"
        return metrics

    wait = scan_timeout or config.BLE_TIMEOUT_SECONDS
    device = await find_device(addr, timeout=wait)
    if device is None:
        metrics.error = f"Li-Time not seen during {wait:.0f}s scan ({addr})"
        return metrics

    client: BleakClient | None = None
    try:
        logger.info("Li-Time: connecting to %s (%s)...", device.name, device.address)
        client = await establish_connection(
            BleakClient,
            device,
            name=addr,
            max_attempts=_CONNECT_ATTEMPTS,
        )

        queue: asyncio.Queue[bytes] = asyncio.Queue()

        def _on_notify(_handle: int, data: bytearray) -> None:
            queue.put_nowait(bytes(data))

        await client.start_notify(CHAR_NOTIFY, _on_notify)
        await asyncio.sleep(0.2)
        await client.write_gatt_char(CHAR_WRITE, REQUEST_STATS, response=False)

        deadline = asyncio.get_running_loop().time() + _READ_TIMEOUT_SECONDS
        while asyncio.get_running_loop().time() < deadline:
            remaining = deadline - asyncio.get_running_loop().time()
            try:
                packet = await asyncio.wait_for(queue.get(), timeout=max(0.1, remaining))
            except asyncio.TimeoutError:
                break
            if len(packet) >= 66:
                status = parse_payload(packet)
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
                return metrics

        metrics.error = "No status packet from Li-Time after connect"
    except (BatteryConnectionError, BatteryTimeoutError, OSError, TimeoutError) as exc:
        metrics.error = str(exc) or "Li-Time BLE error"
        logger.warning("Li-Time: %s", metrics.error)
    except Exception as exc:
        metrics.error = str(exc) or type(exc).__name__
        logger.warning("Li-Time: %s", metrics.error)
    finally:
        if client is not None and client.is_connected:
            try:
                await client.disconnect()
            except Exception:
                pass

    return metrics


def read_litime(address: str | None = None, *, timeout: float | None = None) -> LitimeMetrics:
    """Synchronous wrapper around read_litime_async."""
    return asyncio.run(read_litime_async(address, scan_timeout=timeout))
