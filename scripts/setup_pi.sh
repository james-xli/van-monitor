#!/usr/bin/env bash
# One-time Raspberry Pi setup: SPI, system packages, Python venv.
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

echo "==> Installing system packages..."
sudo apt-get update
sudo apt-get install -y \
  python3-venv \
  python3-pil \
  python3-numpy \
  python3-gpiozero \
  python3-spidev

echo "==> Creating Python virtual environment..."
python3 -m venv --system-site-packages "$VENV_DIR"

echo "==> Installing pip-only Python packages..."
if grep -qv '^\s*\(#\|$\)' "$REPO_DIR/requirements-pi.txt"; then
  "$VENV_DIR/bin/pip" install -r "$REPO_DIR/requirements-pi.txt"
else
  echo "(none yet — hardware libs come from apt)"
fi

echo ""
echo "Setup complete. Try:"
echo "  cd $REPO_DIR && .venv/bin/python3 scripts/hello_display.py"
