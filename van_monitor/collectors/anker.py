"""
Read Anker Solix C1000 Gen 2 data over BLE.

The C1000 Gen 2 is not supported by the SolixBLE library (it connects but never
sends telemetry). We use our own protocol port instead — see
van_monitor/collectors/anker_g2.py and van_monitor/anker_g2_protocol.py.

This module keeps the original read_anker / read_anker_async API so the rest of
the app does not need to change.
"""

from __future__ import annotations

import asyncio

from van_monitor.collectors.anker_g2 import read_anker_g2_async
from van_monitor.metrics import AnkerMetrics


async def read_anker_async(
    address: str | None = None,
    *,
    telemetry_timeout: float | None = None,
    button_wait: float | None = None,
) -> AnkerMetrics:
    """Connect to the Anker, wait for telemetry, read values, and disconnect."""
    return await read_anker_g2_async(
        address,
        telemetry_timeout=telemetry_timeout,
        button_wait=button_wait,
    )


def read_anker(
    address: str | None = None,
    *,
    telemetry_timeout: float | None = None,
) -> AnkerMetrics:
    """Synchronous wrapper around read_anker_async."""
    return asyncio.run(read_anker_async(address, telemetry_timeout=telemetry_timeout))
