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
  echo "Upgrade Raspberry Pi OS or install a newer Python before using scripts/test_anker.py."
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
  bluez-tools \
  pi-bluetooth \
  libbluetooth-dev \
  libffi-dev \
  libssl-dev

echo "==> Enabling Bluetooth..."
if grep -q "^dtoverlay=disable-bt" /boot/firmware/config.txt 2>/dev/null \
   || grep -q "^dtoverlay=disable-bt" /boot/config.txt 2>/dev/null; then
  echo "Warning: dtoverlay=disable-bt is set — Bluetooth is disabled at boot."
  echo "Remove that line from config.txt and reboot."
else
  sudo systemctl enable hciuart bluetooth
  sudo systemctl start hciuart
  sudo systemctl start bluetooth
  sudo rfkill unblock bluetooth 2>/dev/null || true
  sleep 2
  sudo hciconfig hci0 up 2>/dev/null || true
  sudo bluetoothctl power on || true
fi

echo "==> Creating Python virtual environment..."
python3 -m venv --system-site-packages "$VENV_DIR"

# Pi Zero (armv6l) needs piwheels first; Trixie images may ship with PyPI-only config.
echo "==> Configuring piwheels as primary pip index..."
sudo tee /etc/pip.conf >/dev/null <<'EOF'
[global]
index-url = https://www.piwheels.org/simple
extra-index-url = https://pypi.org/simple
EOF

echo "==> Upgrading pip..."
"$VENV_DIR/bin/pip" install --upgrade pip wheel setuptools

_install_dbus_fast() {
  # piwheels dbus-fast wheels are manylinux armv7-tagged; pip on armv6l rejects them
  # and falls back to compiling Cython (~1–2 hours on Pi Zero). Install pure-Python
  # dbus-fast first so the later -r install reuses it.
  local py_tag
  py_tag="$("$VENV_DIR/bin/python" -c 'import sys; print(f"cp{sys.version_info.major}{sys.version_info.minor}")')"
  local wheel_url="https://www.piwheels.org/simple/dbus-fast/dbus_fast-5.0.22-${py_tag}-${py_tag}-manylinux_2_41_armv7l.whl"

  echo "==> Installing dbus-fast..."
  if "$VENV_DIR/bin/pip" install --no-deps "$wheel_url" 2>/dev/null; then
    echo "    Used piwheels binary wheel."
    return
  fi

  echo "    piwheels wheel not compatible with this CPU; using pure-Python build (SKIP_CYTHON=1)..."
  echo "    (downloads .tar.gz — expect ~1–3 min, not hours)"
  SKIP_CYTHON=1 "$VENV_DIR/bin/pip" install \
    --no-binary=dbus-fast \
    --no-build-isolation \
    'dbus-fast>=1.83.0'
}

_install_dbus_fast

echo "==> Installing remaining pip packages..."
"$VENV_DIR/bin/pip" install --prefer-binary -r "$REPO_DIR/requirements-pi.txt"

echo ""
echo "Setup complete."
echo ""
echo "Next steps:"
echo "  1. Edit config.py with Bluetooth addresses and the Victron key"
echo "  2. Scan for devices:  .venv/bin/python3 scripts/ble_scan.py"
echo "  3. Test one device:   .venv/bin/python3 scripts/test_litime.py -v"
echo "     Upgrade pip deps:  .venv/bin/pip install -U -r requirements-pi.txt"
echo "  4. Run the dashboard: .venv/bin/python3 scripts/run_monitor.py --once"
echo "  5. Start on boot:       bash scripts/install_service.sh"
