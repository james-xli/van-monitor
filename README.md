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

### 4. Anker Solix C1000 Gen 2 (custom driver, not yet in main loop)

The C1000 Gen 2 is **not** supported by [SolixBLE](https://github.com/flip-dots/SolixBLE):
it connects and negotiates but never sends telemetry (`AVAILABLE: False`, see
[SolixBLE #22](https://github.com/flip-dots/SolixBLE/issues/22)). The Gen 2
firmware requires a live ECDH key exchange plus a one-time physical button press,
which the static SolixBLE handshake cannot do.

We replaced SolixBLE for the Gen 2 with our own port of the working community C++
protocol:

- `van_monitor/anker_g2_protocol.py` — pure-Python protocol/crypto (no Bluetooth).
- `van_monitor/collectors/anker_g2.py` — the bleak driver that runs it.

**First-time pairing requires pressing the button on the station.** After that,
a client id is saved (`config.ANKER_CLIENT_ID_FILE`) and reused, so reconnects
are automatic.

Validate it before relying on it:

```bash
# 0. Sanity-check the protocol/crypto with no hardware (works anywhere):
.venv/bin/python3 scripts/test_anker_protocol.py

# 1. Find the Anker's MAC address:
.venv/bin/python3 scripts/test_anker.py --discover -v

# 2. First-time pairing — watch for "PRESS THE BUTTON" and press the physical
#    button on the Anker within ~180s. You only do this once.
#    (-v prints each packet's hex; add --debug-ble for bleak internals.)
.venv/bin/python3 scripts/test_anker.py -v

# 3. Normal read (no button press needed once paired):
.venv/bin/python3 scripts/test_anker.py -v

# Re-pair from scratch (e.g. after a factory reset):
.venv/bin/python3 scripts/test_anker.py --reset-pairing -v
```

Set `ANKER_ADDRESS` in `config.py`. The driver needs the `cryptography` package
(already in `requirements-pi.txt`); SolixBLE is no longer required.

**`run_monitor.py` polls Anker** on a slower interval (`ANKER_POLL_INTERVAL_SECONDS`,
default 60s) because each read reconnects and re-handshakes over BLE. The display
uses the Figma **Main screen v8 w/ Anker** layout.

#### Assumptions & key decisions (Anker Gen 2)

- **Ported, not vendored.** The protocol is a hand port of the working C++
  (`SolixProtocol.cpp` / `BleController.cpp`) into `van_monitor/anker_g2_protocol.py`,
  using the `cryptography` package for AES-GCM and P-256 ECDH. The C++ targeted
  an ESP32 (NimBLE + mbedTLS); none of that is reusable on Linux, so the logic
  was rewritten in Python. The crypto constants (negotiation key/nonce/AAD) are
  firmware values copied verbatim.
- **One-time button press.** The Gen 2 authorizes a *client UUID*. The first
  connection triggers a "press the button" step; we then persist the UUID
  (`config.ANKER_CLIENT_ID_FILE`) and reuse it, so later connects are automatic.
  This mirrors how the Anker app pairs once. Delete that file (or use
  `--reset-pairing`) to start over.
- **Timestamps use real Unix time.** The C++ used a fake epoch + uptime; the
  station only needs a consistent, current-ish value, so we use `time.time()`.
- **Metric mapping:** `SOC = battery_percent` (param A5), `watts in = AC input +
  solar input` (A6/A8), `watts out = total power out` (A6). Same convention as
  the previous collector.
- **Disconnect after read**, like the Li-Time/Anker pattern already used here —
  the Pi Zero W radio is happier with one short connection per poll.
- **Validated offline** with `scripts/test_anker_protocol.py` (framing, TLV,
  ECDH agreement, AES-GCM, telemetry parsing). On-station behavior still needs
  your real-hardware check.

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
- is pruned to the last `HISTORY_RETENTION_HOURS` (default 24h),
- is excluded from `deploy.sh` (so deploys never overwrite Pi data) and from git.

Each panel shows the latest reading at the right edge with thin vertical lines
marking each hour counting back from now:

- **House battery** — `HOUSE_HISTORY_HOURS` (default 24h) of black area fill;
  height equals SOC% at that time. Stats sit in a solid-black strip below.
- **Solar** — `SOLAR_HISTORY_HOURS` (default 12h) as a stroke-only line (no
  fill); height maps 0..`SOLAR_MAX_W`.

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
| `SOLAR_HISTORY_HOURS` | Hours of solar history shown on the solar chart (default 12) |
| `HOUSE_HISTORY_HOURS` | Hours of SOC history shown on the house battery chart (default 24) |
| `HISTORY_RETENTION_HOURS` | Hours of history kept in memory/on disk (default 24) |
| `HISTORY_SAMPLE_INTERVAL_SECONDS` | Min seconds between logged points (default 60; decoupled from poll) |
| `HISTORY_GRID_HOURS` | Spacing of the battery chart's hour gridlines (default 1) |
| `HISTORY_FILE` | Where the time-series log is stored (default `data/history.jsonl`) |
| `LITIME_ADDRESS` | Li-Time battery MAC (empty = auto-discover) |
| `VICTRON_ADDRESS` | Victron MPPT MAC |
| `VICTRON_KEY` | Victron Instant Readout advertisement key |
| `ANKER_ADDRESS` | Anker MAC |
| `ANKER_CAPACITY_KWH` | Caption under the Anker panel (default 1) |
| `ANKER_POLL_INTERVAL_SECONDS` | How often to poll Anker in `run_monitor.py` (default 60s) |
| `ANKER_CLIENT_ID_FILE` | Saved Anker pairing id (delete to re-pair with button press) |
| `ANKER_BUTTON_WAIT_SECONDS` | How long to wait for the one-time button press (default 180s) |
| `BLE_TIMEOUT_SECONDS` | Active scan time before connect (default 25s) |
| `BLE_COOLDOWN_SECONDS` | Pause between BLE devices (default 2s) |
| `ANKER_TELEMETRY_TIMEOUT_SECONDS` | Wait for first Anker packet after negotiation (default 120s) |

## Hardware notes

- **Pi:** Raspberry Pi Zero W, always powered from the van
- **Display:** Waveshare 7.5" black/white V2 e-paper HAT over SPI
- SPI must be enabled: `sudo raspi-config` → Interface Options → SPI
- Python runs in a project venv (`.venv/`) to avoid Raspberry Pi OS pip restrictions
- **Anker C1000 Gen 2** uses a custom driver (`anker_g2_protocol.py`); first
  connection needs a one-time physical button press on the station to pair
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
| Anker Solix C1000 Gen 2 | SOC %, watts in, watts out (custom Gen 2 driver; one-time button-press pairing) |

## References

- [Li Time BLE](https://github.com/konnexio-inc/litime-ble)
- [SolixBLE](https://github.com/flip-dots/SolixBLE)
- [Victron BLE](https://github.com/keshavdv/victron-ble)
- [Waveshare e-Paper](https://github.com/waveshare/e-Paper)
