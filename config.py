"""
Central configuration for van-monitor.

Edit these values in the field as needed. Keep settings simple and obvious.
"""

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

# Static captions shown on the dashboard (Main screen v2). Edit to match your gear.
SOLAR_MAX_W = 220
HOUSE_BATTERY_CAPACITY_KWH = 2
ANKER_CAPACITY_KWH = 1

# ---------------------------------------------------------------------------
# Bluetooth device addresses
#
# Run `scripts/ble_scan.py` on the Pi to find names and MAC addresses.
# Leave an address empty to auto-discover that device type (slower, less
# predictable — prefer filling in addresses once you know them).
# ---------------------------------------------------------------------------

# Li-Time 165 Ah house battery (Bluetooth MAC address).
LITIME_ADDRESS = ""

# Victron SmartSolar MPPT 100/30 with Instant Readout enabled.
# Get both values from Victron Connect app -> device settings -> Product Info
# -> Instant Readout via Bluetooth -> Show.
VICTRON_ADDRESS = ""
VICTRON_KEY = ""  # 32-character hex advertisement key

# Anker Solix C1000 Gen 2 portable power station.
ANKER_ADDRESS = ""

# Seconds to wait when scanning / connecting before giving up.
BLE_TIMEOUT_SECONDS = 15

# Seconds to wait for Anker telemetry after connecting (negotiation can be slow).
ANKER_TELEMETRY_TIMEOUT_SECONDS = 60
