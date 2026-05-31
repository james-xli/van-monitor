#!/usr/bin/env bash
# Check why Bluetooth may not be working on the Pi.
set -euo pipefail

echo "=== Bluetooth diagnostics ==="
echo

echo "-- rfkill --"
if command -v rfkill >/dev/null; then
  rfkill list || true
else
  echo "rfkill not installed"
fi
echo

echo "-- hci0 adapter --"
if command -v hciconfig >/dev/null; then
  hciconfig -a 2>&1 || echo "hciconfig: no adapter"
else
  echo "hciconfig not installed (try: sudo apt install bluez)"
fi
echo

echo "-- systemd services --"
for unit in hciuart.service bluetooth.service bthelper@hci0.service; do
  if systemctl list-unit-files "$unit" &>/dev/null; then
    printf "%-28s %s\n" "$unit" "$(systemctl is-active "$unit" 2>/dev/null || echo inactive)"
  fi
done
echo

echo "-- boot config (bt-related lines) --"
for cfg in /boot/firmware/config.txt /boot/config.txt; do
  if [ -f "$cfg" ]; then
    echo "[$cfg]"
    grep -iE "^(dtparam=.*bt|dtoverlay=.*bt|enable_uart|disable-bt)" "$cfg" || echo "  (no bt-related lines)"
  fi
done
echo

echo "-- recent kernel messages --"
if dmesg 2>/dev/null | grep -iE "bluetooth|hci|bcm434" | tail -10 | grep -q .; then
  dmesg 2>/dev/null | grep -iE "bluetooth|hci|bcm434" | tail -10
else
  echo "  (no bluetooth messages — try: sudo dmesg | grep -i bluetooth)"
fi
echo

echo "-- packages --"
for pkg in bluez pi-bluetooth; do
  if dpkg -s "$pkg" &>/dev/null; then
    echo "  $pkg: installed"
  else
    echo "  $pkg: NOT installed"
  fi
done
echo

echo "=== Suggested fixes (try in order) ==="
echo "1. sudo apt install -y pi-bluetooth bluez bluez-tools"
echo "2. Remove dtoverlay=disable-bt from config.txt if present, then reboot"
echo "3. sudo raspi-config  -> Interface Options -> Bluetooth -> Enable, then reboot"
echo "4. sudo rfkill unblock bluetooth"
echo "5. sudo systemctl enable hciuart bluetooth"
echo "6. sudo systemctl restart hciuart bluetooth"
echo "7. sudo hciconfig hci0 up"
echo "8. sudo bluetoothctl power on"
echo
echo "If hci0 never appears in hciconfig, Bluetooth is not initialized at the"
echo "hardware/driver level — fix boot config and pi-bluetooth first, then reboot."
