# van-monitor

Central systems monitor for a camper van. A Raspberry Pi Zero W reads metrics
from Bluetooth-enabled power equipment and shows them on a Waveshare 7.5"
e-paper display.

## Project layout

```
van-monitor/
├── config.py              # Intervals and settings (edit these in the field)
├── van_monitor/
│   ├── display.py         # E-paper wrapper
│   └── collectors/        # (future) Bluetooth device readers
├── scripts/
│   ├── hello_display.py   # Display smoke test
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

# 2. SSH in and run the hello-world display test
ssh jamesli@van-monitor.local
cd ~/van-monitor
bash scripts/setup_pi.sh          # first time only
.venv/bin/python3 scripts/hello_display.py
```

Override deploy target if needed:

```bash
PI_HOST=jamesli@192.168.0.95 ./scripts/deploy.sh
```

## Configuration

Edit `config.py`:

- `POLL_INTERVAL_SECONDS` — how often to read Bluetooth devices
- `DISPLAY_REFRESH_INTERVAL_SECONDS` — how often to update the screen
- `UNAVAILABLE_LABEL` — shown when a device is disconnected (default: `NA`)

## Hardware notes

- **Pi:** Raspberry Pi Zero W, always powered from the van
- **Display:** Waveshare 7.5" black/white V2 e-paper HAT over SPI
- SPI must be enabled: `sudo raspi-config` → Interface Options → SPI
- Python runs in a project venv (`.venv/`) to avoid Raspberry Pi OS pip restrictions

## Roadmap (P0)

| Device              | Metrics                          |
| ------------------- | -------------------------------- |
| Li Time house battery | SOC %, net power W, voltage V  |
| Victron MPPT 100/30 | Solar output W                   |
| Anker Solix C1000   | SOC %, power in W, power out W   |

## References

- [Li Time BLE](https://github.com/konnexio-inc/litime-ble)
- [Anker Solix API](https://github.com/thomluther/anker-solix-api) / [SolixBLE](https://github.com/flip-dots/SolixBLE)
- [Victron BLE](https://github.com/keshavdv/victron-ble)
- [Waveshare e-Paper](https://github.com/waveshare/e-Paper)
