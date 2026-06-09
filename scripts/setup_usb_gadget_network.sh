#!/usr/bin/env bash
# Assign a static IP to usb0 so Mac USB SSH works (192.168.7.2).
#
# Run once on the Pi while you have any SSH access (Wi-Fi or serial):
#   bash scripts/setup_usb_gadget_network.sh
#
# Prerequisites on the SD card (boot partition):
#   config.txt [all]:  dtoverlay=dwc2,dr_mode=peripheral
#   cmdline.txt:       modules-load=dwc2,g_ether
#   Do NOT use ip=...::usb0:off in cmdline — it runs before usb0 exists.
set -euo pipefail

PI_USB_IP="192.168.7.2/24"
MAC_USB_IP="192.168.7.1"

echo "==> Checking usb0..."
if ! ip link show usb0 &>/dev/null; then
  echo "usb0 not found. Plug the Pi USB port into your Mac and reboot, then re-run."
  exit 1
fi

configure_dhcpcd() {
  if grep -q "^interface usb0" /etc/dhcpcd.conf 2>/dev/null; then
    echo "usb0 already configured in /etc/dhcpcd.conf"
    return
  fi

  echo "==> Configuring usb0 via dhcpcd..."
  sudo tee -a /etc/dhcpcd.conf >/dev/null <<EOF

# USB gadget link to Mac (added by van-monitor setup_usb_gadget_network.sh)
interface usb0
static ip_address=${PI_USB_IP}
static routers=${MAC_USB_IP}
static domain_name_servers=${MAC_USB_IP}
EOF
  sudo systemctl restart dhcpcd
}

configure_networkmanager() {
  echo "==> Configuring usb0 via NetworkManager..."
  if nmcli -t -f NAME connection show | grep -qx "usb-gadget"; then
    sudo nmcli connection modify usb-gadget \
      ipv4.method manual \
      ipv4.addresses "${PI_USB_IP}" \
      ipv4.gateway "${MAC_USB_IP}" \
      connection.autoconnect yes
  else
    sudo nmcli connection add \
      con-name "usb-gadget" \
      ifname usb0 \
      type ethernet \
      ipv4.method manual \
      ipv4.addresses "${PI_USB_IP}" \
      ipv4.gateway "${MAC_USB_IP}" \
      connection.autoconnect yes
  fi
  sudo nmcli connection up usb-gadget || true
}

if systemctl is-active --quiet NetworkManager 2>/dev/null; then
  configure_networkmanager
elif systemctl is-active --quiet dhcpcd 2>/dev/null; then
  configure_dhcpcd
else
  echo "Neither NetworkManager nor dhcpcd is active."
  echo "Install/configure one of them, or add manually to /etc/network/interfaces."
  exit 1
fi

sleep 2
echo
echo "==> usb0 addresses:"
ip addr show usb0 | grep -E "inet |state" || true
echo
echo "On your Mac (RNDIS interface): manual IP ${MAC_USB_IP}, mask 255.255.255.0"
echo "Then:  ssh jamesli@192.168.7.2"
