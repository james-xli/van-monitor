"""
Central configuration for van-monitor.

Edit these values in the field as needed. Keep settings simple and obvious.
"""

# How often to poll Bluetooth devices for new readings (seconds).
POLL_INTERVAL_SECONDS = 5

# How often to refresh the e-paper display (seconds).
# Can differ from polling if you want to batch updates.
DISPLAY_REFRESH_INTERVAL_SECONDS = 5

# Shown when a device is disconnected or data is unavailable.
UNAVAILABLE_LABEL = "NA"
