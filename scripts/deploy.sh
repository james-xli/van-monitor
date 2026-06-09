#!/usr/bin/env bash
# Sync project files from Mac to Raspberry Pi.
set -euo pipefail

PI_HOST="${PI_HOST:-jamesli@van-monitor.local}"
PI_DIR="${PI_DIR:-~/van-monitor}"

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> Syncing to $PI_HOST:$PI_DIR"
rsync -avz --delete \
  --exclude '.git/' \
  --exclude '.venv/' \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  --exclude 'data/' \
  "$REPO_DIR/" "$PI_HOST:$PI_DIR/"

echo ""
echo "Deployed. SSH in and run:"
echo "  ssh $PI_HOST"
echo "  cd van-monitor && bash scripts/setup_pi.sh   # first time only"
echo "  cd van-monitor && .venv/bin/python3 scripts/hello_display.py"
echo "  cd van-monitor && bash scripts/install_service.sh   # start on boot (on Pi)"
