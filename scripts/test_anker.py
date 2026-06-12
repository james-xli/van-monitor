#!/usr/bin/env python3
"""
Test the Anker Solix C1000 Gen 2 BLE connection (custom Gen 2 protocol).

Examples:
    # List nearby Solix stations and their MAC addresses
    python scripts/test_anker.py --discover

    # Connect to the address in config.py, show the handshake, read telemetry
    python scripts/test_anker.py -v

    # First-time pairing: watch for the "PRESS THE BUTTON" prompt, then press
    # the physical button on the Anker within ~180s. Done once, ever.
    # (-v already prints each packet's hex; add --debug-ble for bleak internals.)
    python scripts/test_anker.py -v

    # Force a brand-new pairing (you will have to press the button again)
    python scripts/test_anker.py --reset-pairing -v

The first successful run saves a client id (config.ANKER_CLIENT_ID_FILE); after
that, reconnects are automatic with no button press.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bleak import BleakScanner

import config
from van_monitor.anker_g2_protocol import UUID_IDENTIFIER
from van_monitor.collectors.anker import read_anker_async
from van_monitor.collectors.anker_g2 import load_client_uuid
from van_monitor.metrics import VanMetrics, print_metrics
from van_monitor.util import setup_logging


def _looks_like_solix(device, adv) -> bool:
    if UUID_IDENTIFIER in (adv.service_uuids or []):
        return True
    name = (device.name or adv.local_name or "").upper()
    return "C1000" in name or "SOLIX" in name


async def discover_anker(timeout: float) -> int:
    print(f"Scanning for Anker Solix devices for {timeout:.0f}s...")
    found = await BleakScanner.discover(timeout=timeout, return_adv=True)

    rows = []
    for device, adv in found.values():
        if _looks_like_solix(device, adv):
            rows.append((device.address, device.name or adv.local_name or "(no name)", adv.rssi))

    if not rows:
        print("No Anker Solix devices found. Wake the unit and close the Anker app.")
        return 1

    print(f"\n{'ADDRESS':<20}  {'RSSI':>5}  NAME")
    print("-" * 48)
    for address, name, rssi in sorted(rows, key=lambda r: r[2] or -999, reverse=True):
        print(f"{address:<20}  {rssi if rssi is not None else '?':>5}  {name}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Test Anker Solix C1000 Gen 2 BLE readings")
    parser.add_argument("--address", help="Bluetooth MAC (overrides config.ANKER_ADDRESS)")
    parser.add_argument(
        "--discover",
        action="store_true",
        help="Scan for Anker Solix devices and print addresses",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=config.ANKER_TELEMETRY_TIMEOUT_SECONDS,
        help="Seconds to wait for telemetry after connecting",
    )
    parser.add_argument(
        "--reset-pairing",
        action="store_true",
        help="Delete the saved client id and pair fresh (button press required)",
    )
    parser.add_argument(
        "--display",
        action="store_true",
        help="Show the v4 dashboard on e-paper (Anker panel omitted from layout)",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument(
        "--debug-ble",
        action="store_true",
        help="Also show bleak's internal BLE logs (very noisy; -v already shows packet hex)",
    )
    args = parser.parse_args()

    setup_logging(args.verbose, debug_ble=args.debug_ble)

    if args.reset_pairing:
        path = Path(config.ANKER_CLIENT_ID_FILE)
        if path.exists():
            path.unlink()
            print(f"Removed saved pairing: {path}")
        else:
            print("No saved pairing to remove.")

    if args.discover:
        return asyncio.run(discover_anker(config.BLE_TIMEOUT_SECONDS))

    saved = load_client_uuid()
    if saved:
        print(f"Using saved pairing (client id {saved[:8]}...). No button press expected.")
    else:
        print(
            "No saved pairing yet — FIRST-TIME setup.\n"
            "Watch for a 'PRESS THE BUTTON' prompt and press the physical button\n"
            "on the Anker C1000 Gen 2 when asked."
        )

    metrics = VanMetrics(
        anker=asyncio.run(read_anker_async(args.address, telemetry_timeout=args.timeout))
    )
    metrics.updated_at = datetime.now()
    print_metrics(metrics)

    if args.display:
        # Imported lazily: this pulls in the e-paper driver, which claims GPIO
        # pins on import. Only do that when the display is actually requested
        # (and not while the monitor service is holding the display).
        from van_monitor.dashboard import MetricsDashboard

        dashboard = MetricsDashboard()
        dashboard.init(partial=False)
        dashboard.clear()
        dashboard.show_metrics(metrics, partial=False)
        dashboard.sleep()

    return 0 if metrics.anker.connected else 1


if __name__ == "__main__":
    raise SystemExit(main())
