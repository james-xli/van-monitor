"""
Central configuration for van-monitor.

Edit these values in the field as needed. Keep settings simple and obvious.
"""

import os

# How often to poll Bluetooth devices for new readings (seconds).
POLL_INTERVAL_SECONDS = 5

# How often to refresh the e-paper display (seconds).
# Used by scripts/test_partial_refresh.py; run_monitor updates each poll cycle.
DISPLAY_REFRESH_INTERVAL_SECONDS = 5

# Full e-paper refresh interval when using partial updates (seconds).
# Partial refresh is fast but ghosts over time; a full refresh clears it.
# Set to 0 to disable periodic full refresh (initial full refresh still runs).
FULL_REFRESH_INTERVAL_SECONDS = 3600

# Shown when a device is disconnected or data is unavailable.
UNAVAILABLE_LABEL = "NA"

# Static captions shown on the dashboard (Main screen v4 w/o Anker).
SOLAR_MAX_W = 220
HOUSE_BATTERY_CAPACITY_KWH = 2

# ---------------------------------------------------------------------------
# Battery / solar history (logged every poll, persisted across reboots)
# ---------------------------------------------------------------------------

# Hours of history shown on each chart (right edge = "now"). The solar chart shows
# a shorter window than the house battery.
SOLAR_HISTORY_HOURS = 12
HOUSE_HISTORY_HOURS = 24

# Hours of history retained in memory and on disk; older data is discarded.
# Must be >= the largest charted window above.
HISTORY_RETENTION_HOURS = 24

# Minimum seconds between logged history points. Decoupled from the (faster)
# display poll: 5s resolution can't be shown on a ~98s-per-pixel chart and just
# wears the SD card. 60s keeps ~720 points over 12h (still finer than the chart).
HISTORY_SAMPLE_INTERVAL_SECONDS = 60

# Spacing of the vertical hour gridlines on the battery chart (hours).
HISTORY_GRID_HOURS = 1

# Time-series log file. Stored in the repo's data/ folder so it survives reboots;
# deploy.sh excludes data/ so deploys do not overwrite it.
HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "history.jsonl")

# ---------------------------------------------------------------------------
# Bluetooth device addresses
#
# Run `scripts/ble_scan.py` on the Pi to find names and MAC addresses.
# Leave an address empty to auto-discover that device type (slower, less
# predictable — prefer filling in addresses once you know them).
# ---------------------------------------------------------------------------

# Li-Time 165 Ah house battery (Bluetooth MAC address).
LITIME_ADDRESS = "C8:47:80:3F:8B:64"

# Victron SmartSolar MPPT 100/30 with Instant Readout enabled.
# Get both values from Victron Connect app -> device settings -> Product Info
# -> Instant Readout via Bluetooth -> Show.
VICTRON_ADDRESS = "F6:76:F4:A0:59:A7"
VICTRON_KEY = "5396e672b53fa0194d9b5730508bb1aa"  # 32-character hex advertisement key

# Anker Solix C1000 Gen 2 (used by scripts/test_anker.py only — not polled by run_monitor).
ANKER_ADDRESS = "7C:E9:13:31:84:52"

# Seconds to wait when scanning before connect (Pi Zero W: allow 20–30).
BLE_TIMEOUT_SECONDS = 25

# Extra Anker discovery attempts when the unit advertises intermittently.
ANKER_SCAN_RETRIES = 2

# Pause between BLE connect cycles so the radio can settle.
BLE_COOLDOWN_SECONDS = 2

# Seconds to wait for Anker telemetry after negotiation (first packet can be slow).
ANKER_TELEMETRY_TIMEOUT_SECONDS = 120
