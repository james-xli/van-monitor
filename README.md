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
│   ├── dashboard.py       # Simple metrics layout for the display
│   ├── metrics.py         # Reading types and terminal output
│   └── collectors/        # Li-Time, Victron, Anker BLE readers
├── scripts/
│   ├── ble_scan.py        # Find nearby Bluetooth devices
│   ├── test_litime.py     # Test one device at a time
│   ├── test_victron.py
│   ├── test_anker.py
│   ├── run_monitor.py     # Poll all devices + show on display
│   ├── hello_display.py   # Display smoke test
│   ├── test_partial_refresh.py
│   ├── setup_pi.sh        # One-time Pi setup
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
bash scripts/setup_pi.sh          # first time only (slow on Pi Zero)
```

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

### 4. Anker Solix C1000 Gen 2

First connection can take up to 60 seconds (BLE negotiation).

```bash
# Find Anker devices:
.venv/bin/python3 scripts/test_anker.py --discover -v

# Read telemetry:
.venv/bin/python3 scripts/test_anker.py -v
```

Set `ANKER_ADDRESS` in `config.py`.

### 5. Run everything

```bash
# Single poll cycle (good for debugging):
.venv/bin/python3 scripts/run_monitor.py --once -v

# Continuous monitoring:
.venv/bin/python3 scripts/run_monitor.py -v
```

Terminal-only mode (no e-paper):

```bash
.venv/bin/python3 scripts/run_monitor.py --once --no-display -v
```

## Configuration

Edit `config.py`:

| Setting | Purpose |
| --- | --- |
| `POLL_INTERVAL_SECONDS` | Time between full poll cycles |
| `DISPLAY_REFRESH_INTERVAL_SECONDS` | Display update interval (used by partial refresh demo) |
| `UNAVAILABLE_LABEL` | Shown when a device is disconnected (default: `NA`) |
| `LITIME_ADDRESS` | Li-Time battery MAC (empty = auto-discover) |
| `VICTRON_ADDRESS` | Victron MPPT MAC |
| `VICTRON_KEY` | Victron Instant Readout advertisement key |
| `ANKER_ADDRESS` | Anker MAC (empty = auto-discover) |
| `BLE_TIMEOUT_SECONDS` | Scan / advertisement wait time |
| `ANKER_TELEMETRY_TIMEOUT_SECONDS` | Wait for Anker data after connecting |

## Hardware notes

- **Pi:** Raspberry Pi Zero W, always powered from the van
- **Display:** Waveshare 7.5" black/white V2 e-paper HAT over SPI
- SPI must be enabled: `sudo raspi-config` → Interface Options → SPI
- Python runs in a project venv (`.venv/`) to avoid Raspberry Pi OS pip restrictions
- **Anker collector** requires Python 3.11+ (check with `python3 --version`)
- **Bluetooth** must be enabled: `sudo raspi-config` → Interface Options → Bluetooth, or run `sudo systemctl start bluetooth && sudo bluetoothctl power on`

## Roadmap (P0)

| Device              | Metrics                          |
| ------------------- | -------------------------------- |
| Li Time house battery | SOC %, net power W, voltage V  |
| Victron MPPT 100/30 | Solar output W                   |
| Anker Solix C1000   | SOC %, power in W, power out W   |

## References

- [Li Time BLE](https://github.com/konnexio-inc/litime-ble)
- [SolixBLE](https://github.com/flip-dots/SolixBLE)
- [Victron BLE](https://github.com/keshavdv/victron-ble)
- [Waveshare e-Paper](https://github.com/waveshare/e-Paper)
