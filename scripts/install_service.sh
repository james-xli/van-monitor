#!/usr/bin/env bash
# Install (or remove) a systemd service to run run_monitor.py on boot.
#
# Run on the Raspberry Pi (via SSH), not on your Mac:
#   ssh jamesli@van-monitor.local
#   cd ~/van-monitor && bash scripts/install_service.sh
#
# Usage:
#   bash scripts/install_service.sh          # enable on boot + start now
#   bash scripts/install_service.sh --remove # disable and uninstall
set -euo pipefail

if [ "$(uname -s)" != "Linux" ] || ! command -v systemctl >/dev/null 2>&1; then
  echo "This script must be run on the Raspberry Pi (via SSH), not on your Mac." >&2
  echo "  ssh jamesli@van-monitor.local" >&2
  echo "  cd ~/van-monitor && bash scripts/install_service.sh" >&2
  exit 1
fi

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE_NAME="van-monitor"
SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}.service"

if [ "${1:-}" = "--remove" ] || [ "${1:-}" = "--disable" ]; then
  if [ "$(id -u)" -ne 0 ]; then
    exec sudo "$0" --remove
  fi
  systemctl disable --now "$SERVICE_NAME" 2>/dev/null || true
  rm -f "$SERVICE_PATH"
  systemctl daemon-reload
  echo "Removed ${SERVICE_NAME} service."
  exit 0
fi

if [ "$(id -u)" -ne 0 ]; then
  exec sudo "$0" "$@"
fi

RUN_USER="${SUDO_USER:-${USER}}"
if [ -z "$RUN_USER" ] || [ "$RUN_USER" = "root" ]; then
  echo "Run as: bash scripts/install_service.sh  (not sudo directly)" >&2
  exit 1
fi

if [ ! -x "${REPO_DIR}/.venv/bin/python3" ]; then
  echo "Missing ${REPO_DIR}/.venv — run bash scripts/setup_pi.sh first." >&2
  exit 1
fi

echo "==> Installing ${SERVICE_NAME}.service for user ${RUN_USER}"
echo "    Repo: ${REPO_DIR}"

tee "$SERVICE_PATH" >/dev/null <<EOF
[Unit]
Description=Van monitor BLE dashboard
After=bluetooth.service
Wants=bluetooth.service

[Service]
Type=simple
User=${RUN_USER}
WorkingDirectory=${REPO_DIR}
ExecStart=${REPO_DIR}/.venv/bin/python3 ${REPO_DIR}/scripts/run_monitor.py
Restart=on-failure
RestartSec=15
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"

echo ""
echo "Service enabled on boot."
echo "  status:  systemctl status ${SERVICE_NAME}"
echo "  logs:    journalctl -u ${SERVICE_NAME} -f"
echo "  stop:    sudo systemctl stop ${SERVICE_NAME}"
echo "  remove:  bash scripts/install_service.sh --remove"
