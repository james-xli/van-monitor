"""Shared helpers for van-monitor."""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


_BLE_QUIET_LOGGERS = (
    "bleak",
    "dbus_fast",
)


def setup_logging(verbose: bool = False, *, debug_ble: bool = False) -> None:
    """Configure logging to the terminal."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
    )
    if verbose and not debug_ble:
        for name in _BLE_QUIET_LOGGERS:
            logging.getLogger(name).setLevel(logging.WARNING)


def run_async(coro):
    """Run an async function from synchronous code."""
    return asyncio.run(coro)
