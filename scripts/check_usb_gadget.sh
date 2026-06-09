#!/usr/bin/env bash
# Check USB Ethernet gadget (g_ether) setup for SSH over a direct USB cable.
set -euo pipefail

echo "=== USB gadget diagnostics ==="
echo

echo "-- boot config --"
for cfg in /boot/firmware/config.txt /boot/config.txt; do
  if [ -f "$cfg" ]; then
    echo "[$cfg]"
    grep -iE "^(dtoverlay=dwc2|dtoverlay=.*g_ether|enable_uart)" "$cfg" || echo "  dtoverlay=dwc2 NOT FOUND"
  fi
done
echo

echo "-- cmdline (modules-load) --"
for cmdline in /boot/firmware/cmdline.txt /boot/cmdline.txt; do
  if [ -f "$cmdline" ]; then
    if grep -q "modules-load=dwc2,g_ether" "$cmdline"; then
      echo "OK: modules-load=dwc2,g_ether found in $cmdline"
    else
      echo "MISSING: modules-load=dwc2,g_ether not in $cmdline"
    fi
    if grep -q "ip=.*usb0" "$cmdline"; then
      echo "WARNING: ip=...usb0 in cmdline can prevent USB gadget — remove it"
    fi
  fi
done
echo

echo "-- kernel modules --"
if lsmod | grep -q g_ether; then
  lsmod | grep -E "g_ether|dwc2|libcomposite"
else
  echo "g_ether module NOT loaded"
fi
echo

echo "-- usb0 interface --"
if ip link show usb0 &>/dev/null; then
  ip addr show usb0
else
  echo "usb0 does NOT exist (Pi is not presenting USB Ethernet to the host)"
  echo "Plug the data cable into the Pi USB port (not PWR IN) and re-run this script."
fi
echo

echo "-- recent kernel messages --"
dmesg 2>/dev/null | grep -iE "g_ether|usb0|dwc2|gadget|configfs" | tail -15 || \
  echo "  (run with sudo for dmesg: sudo bash scripts/check_usb_gadget.sh)"
echo

echo "=== Mac-side checklist ==="
echo "1. Data cable: Pi USB port -> Mac (try WITHOUT the USB hub/dock first)"
echo "2. Power: separate cable to Pi PWR IN (power bank is fine)"
echo "3. Mac Network: look for 'RNDIS/Ethernet Gadget' interface"
echo "4. Set Mac to manual IP 192.168.7.1, subnet 255.255.255.0"
echo "5. ssh jamesli@192.168.7.2"
echo
echo "If usb0 is missing after a direct cable, fix boot config and reboot."
