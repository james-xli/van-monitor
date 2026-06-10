# van-monitor

Central systems monitor for a camper van. A Raspberry Pi Zero W reads metrics
from Bluetooth-enabled power equipment and shows them on a Waveshare 7.5"
e-paper display.

## Project layout

```
van-monitor/
├── config.py              # Intervals, device addresses, Victron key
├── van_monitor/
│   ├── display.py         # E-paper wrapper
│   ├── dashboard.py       # Figma Main screen v4 layout (P0, B/W panels)
│   ├── layout.py          # Zone positions from Figma
│   ├── metrics.py         # Reading types and terminal output
│   └── collectors/        # Li-Time, Victron, and Anker BLE readers
├── scripts/
│   ├── ble_scan.py        # Find nearby Bluetooth devices
│   ├── test_litime.py     # Test one device at a time
│   ├── test_victron.py
│   ├── test_anker.py      # Anker only (not used by run_monitor)
│   ├── run_monitor.py     # Poll all devices + show on display
│   ├── hello_display.py   # Display smoke test
│   ├── test_partial_refresh.py
│   ├── test_dashboard_layout.py  # Sample P0 layout on e-paper
│   ├── setup_pi.sh        # One-time Pi setup
│   ├── install_service.sh # Run monitor on boot (systemd)
│   └── deploy.sh          # Sync code from Mac to Pi
├── vendor/waveshare_epd/  # Waveshare SPI driver (vendored)
└── requirements-pi.txt    # Python deps for the Pi
```

## Development workflow

Develop on your Mac. Run hardware code on the Pi.

```bash
# 1. Deploy to the Pi
./scripts/deploy.sh

# 2. SSH in
ssh jamesli@van-monitor.local
cd ~/van-monitor
bash scripts/setup_pi.sh          # first time only
```

**Pi Zero pip note:** `bleak` needs `dbus-fast`. piwheels has wheels but pip on
armv6l (Pi Zero) cannot use their armv7/manylinux tags, so pip would compile the
Cython extension for 1–2 hours. `setup_pi.sh` sets `SKIP_CYTHON=1` for a fast
pure-Python install instead.

Override deploy target if needed:

```bash
PI_HOST=jamesli@192.168.0.95 ./scripts/deploy.sh
```

## Offline BLE setup (recommended order)

Work through devices **one at a time**. Each test script prints readings to
the terminal and shows errors clearly. Add `--display` to also push results
to the e-paper.

### 1. Scan for device addresses

```bash
.venv/bin/python3 scripts/ble_scan.py
```

Copy MAC addresses into `config.py`.

### 2. Li-Time house battery

```bash
.venv/bin/python3 scripts/test_litime.py -v
# or with a known address:
.venv/bin/python3 scripts/test_litime.py --address AA:BB:CC:DD:EE:FF -v
```

Set `LITIME_ADDRESS` in `config.py` once it works.

### 3. Victron MPPT

Get the **MAC address** and **advertisement key** from Victron Connect on your
phone: device settings → Product Info → Instant Readout via Bluetooth → Show.

```bash
# See which Victron devices are advertising (no key needed):
.venv/bin/python3 scripts/test_victron.py --discover -v

# Read solar output (needs address + key in config.py or on command line):
.venv/bin/python3 scripts/test_victron.py -v
.venv/bin/python3 scripts/test_victron.py --address AA:BB:CC:DD:EE:FF --key YOUR32CHARHEXKEY -v
```

Set `VICTRON_ADDRESS` and `VICTRON_KEY` in `config.py`.

**Tip:** Close Victron Connect on your phone while testing — it can interfere
with advertisements.

### 4. Anker Solix C1000 Gen 2 (optional, not in main loop)

The Anker collector and `scripts/test_anker.py` are kept for future use, but
**`run_monitor.py` does not poll Anker**. [SolixBLE](https://github.com/flip-dots/SolixBLE)
connects and negotiates with the C1000 Gen 2, yet telemetry stays unavailable
(`AVAILABLE: False`) — see [SolixBLE #22](https://github.com/flip-dots/SolixBLE/issues/22).
Skipping Anker in the main loop avoids a ~2 minute timeout on every poll cycle.

To experiment with the collector in isolation:

```bash
# Find Anker devices:
.venv/bin/python3 scripts/test_anker.py --discover -v

# Attempt telemetry (terminal output only for now):
.venv/bin/python3 scripts/test_anker.py -v
```

Set `ANKER_ADDRESS` in `config.py`. Requires Python 3.11+ for SolixBLE.

### 5. Run everything

```bash
# Single poll cycle (good for debugging):
.venv/bin/python3 scripts/run_monitor.py --once -v

# Continuous monitoring:
.venv/bin/python3 scripts/run_monitor.py -v
```

### 6. Start on boot

After `run_monitor.py` works manually, install a systemd service **on the Pi**
(not on your Mac — the sudo prompt is for the Pi user password):

```bash
ssh jamesli@van-monitor.local
cd ~/van-monitor
bash scripts/install_service.sh
```

This enables `van-monitor.service` on boot and starts it immediately. Logs:

```bash
journalctl -u van-monitor -f
```

To stop or uninstall:

```bash
sudo systemctl stop van-monitor
bash scripts/install_service.sh --remove
```

After deploying code updates, restart the service:

```bash
sudo systemctl restart van-monitor
```

Terminal-only mode (no e-paper):

```bash
.venv/bin/python3 scripts/run_monitor.py --once --no-display -v
```

## Battery / solar history

`run_monitor.py` logs battery SOC % and solar power to `data/history.jsonl`
(one JSON object per line). The log:

- samples at most every `HISTORY_SAMPLE_INTERVAL_SECONDS` (default 60s),
  independent of the faster display poll — 5s resolution can't be shown on a
  chart with ~98s per pixel and only wears the SD card,
- persists across reboots (the service reloads it on start),
- is pruned to the last `HISTORY_WINDOW_HOURS` (default 12h),
- is excluded from `deploy.sh` (so deploys never overwrite Pi data) and from git.

Both panels show a 12h chart with the latest reading at the right edge and thin
vertical lines marking each hour counting back from now:

- **House battery** — black area fill; height equals SOC% at that time.
- **Solar** — a stroke-only line (no fill); height maps 0..`SOLAR_MAX_W`.

## Configuration

Edit `config.py`:

| Setting | Purpose |
| --- | --- |
| `POLL_INTERVAL_SECONDS` | Time between full poll cycles |
| `DISPLAY_REFRESH_INTERVAL_SECONDS` | Display update interval (used by partial refresh demo) |
| `FULL_REFRESH_INTERVAL_SECONDS` | Full e-paper refresh while in partial mode (default 3600; `0` = off) |
| `UNAVAILABLE_LABEL` | Shown when a device is disconnected (default: `NA`) |
| `SOLAR_MAX_W` | Solar panel caption, e.g. `220 W max` |
| `HOUSE_BATTERY_CAPACITY_KWH` | House battery caption, e.g. `2 kWh capacity` |
| `HISTORY_WINDOW_HOURS` | Hours of SOC/solar history to keep and chart (default 12) |
| `HISTORY_SAMPLE_INTERVAL_SECONDS` | Min seconds between logged points (default 60; decoupled from poll) |
| `HISTORY_GRID_HOURS` | Spacing of the battery chart's hour gridlines (default 1) |
| `HISTORY_FILE` | Where the time-series log is stored (default `data/history.jsonl`) |
| `LITIME_ADDRESS` | Li-Time battery MAC (empty = auto-discover) |
| `VICTRON_ADDRESS` | Victron MPPT MAC |
| `VICTRON_KEY` | Victron Instant Readout advertisement key |
| `ANKER_ADDRESS` | Anker MAC (for `test_anker.py` only) |
| `BLE_TIMEOUT_SECONDS` | Active scan time before connect (default 25s) |
| `BLE_COOLDOWN_SECONDS` | Pause between BLE devices (default 2s) |
| `ANKER_TELEMETRY_TIMEOUT_SECONDS` | Wait for first Anker packet after negotiation (default 120s) |

## Hardware notes

- **Pi:** Raspberry Pi Zero W, always powered from the van
- **Display:** Waveshare 7.5" black/white V2 e-paper HAT over SPI
- SPI must be enabled: `sudo raspi-config` → Interface Options → SPI
- Python runs in a project venv (`.venv/`) to avoid Raspberry Pi OS pip restrictions
- **Anker test script** (`test_anker.py`) requires Python 3.11+ for SolixBLE
- **Bluetooth** must be enabled: `sudo raspi-config` → Interface Options → Bluetooth, or run `sudo systemctl start bluetooth && sudo bluetoothctl power on`

## USB SSH (Pi Zero W ↔ Mac)

Use when Wi‑Fi is unavailable. SD card boot settings:

**`config.txt`** under `[all]`:

```
dtoverlay=dwc2,dr_mode=peripheral
enable_uart=1
```

**`cmdline.txt`** — include `modules-load=dwc2,g_ether` after `rootwait`.

Do **not** add `ip=...::usb0:off` to cmdline — it runs before `usb0` exists and can
break USB enumeration.

After the gadget shows up on the Mac once, assign the Pi USB IP (one-time, any SSH):

```bash
ssh jamesli@van-monitor.local   # use Wi‑Fi for this one step if needed
cd ~/van-monitor
bash scripts/setup_usb_gadget_network.sh
sudo reboot
```

Mac: System Settings → RNDIS/Ethernet Gadget → manual **192.168.7.1**, mask **255.255.255.0**.

```bash
ssh jamesli@192.168.7.2
PI_HOST=jamesli@192.168.7.2 ./scripts/deploy.sh
```

`van-monitor.local` over mDNS uses Wi‑Fi, not USB — use **192.168.7.2** for USB SSH.


| Device              | Metrics                          |
| ------------------- | -------------------------------- |
| Li Time house battery | SOC %, net power W, voltage V  |
| Victron MPPT 100/30 | Solar output W, daily yield Wh   |
| Anker Solix C1000 Gen 2 | Collector present; not polled (SolixBLE telemetry gap) |

## References

- [Li Time BLE](https://github.com/konnexio-inc/litime-ble)
- [SolixBLE](https://github.com/flip-dots/SolixBLE)
- [Victron BLE](https://github.com/keshavdv/victron-ble)
- [Waveshare e-Paper](https://github.com/waveshare/e-Paper)
