#!/usr/bin/env bash
# One-time Raspberry Pi setup: SPI, Bluetooth, system packages, Python venv.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV_DIR="$REPO_DIR/.venv"

echo "==> Checking SPI is enabled..."
if ! grep -q "^dtparam=spi=on" /boot/firmware/config.txt 2>/dev/null \
   && ! grep -q "^dtparam=spi=on" /boot/config.txt 2>/dev/null; then
  echo "SPI does not appear to be enabled."
  echo "Run: sudo raspi-config -> Interface Options -> SPI -> Enable"
  echo "Then reboot and run this script again."
  exit 1
fi

echo "==> Checking Python version (SolixBLE needs 3.11+)..."
PYTHON_VERSION="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
PYTHON_MINOR="$(python3 -c 'import sys; print(sys.version_info.minor)')"
if [ "$PYTHON_MINOR" -lt 11 ]; then
  echo "Warning: Python $PYTHON_VERSION found. SolixBLE requires Python 3.11+."
  echo "Upgrade Raspberry Pi OS or install a newer Python before using the Anker collector."
fi

echo "==> Installing system packages..."
sudo apt-get update
sudo apt-get install -y \
  python3-venv \
  python3-dev \
  python3-pil \
  python3-numpy \
  python3-gpiozero \
  python3-spidev \
  bluez \
  libbluetooth-dev \
  libffi-dev \
  libssl-dev

echo "==> Creating Python virtual environment..."
python3 -m venv --system-site-packages "$VENV_DIR"

echo "==> Installing pip packages (this may take several minutes on a Pi Zero)..."
"$VENV_DIR/bin/pip" install -r "$REPO_DIR/requirements-pi.txt"

echo ""
echo "Setup complete."
echo ""
echo "Next steps:"
echo "  1. Edit config.py with Bluetooth addresses and the Victron key"
echo "  2. Scan for devices:  .venv/bin/python3 scripts/ble_scan.py"
echo "  3. Test one device:   .venv/bin/python3 scripts/test_litime.py -v"
echo "  4. Run the dashboard: .venv/bin/python3 scripts/run_monitor.py --once"
