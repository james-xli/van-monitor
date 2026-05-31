"""Shared helpers for van-monitor."""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def setup_logging(verbose: bool = False) -> None:
    """Configure logging to the terminal."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
    )


def run_async(coro):
    """Run an async function from synchronous code."""
    return asyncio.run(coro)
