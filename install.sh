#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# install.sh — Controller Dashboard fast setup (skips already-installed items)
# ─────────────────────────────────────────────────────────────────────────────
set -e

RED='\033[0;31m'; RESET='\033[0m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'
info()  { echo -e "${RED}[*]${RESET} $*"; }
ok()    { echo -e "${GREEN}[✓]${RESET} $*"; }
skip()  { echo -e "${YELLOW}[-]${RESET} $* (already installed, skipped)"; }

info "Controller Dashboard — Fast Installer"
echo ""

# ── Helper: check if apt package is installed ─────────────────────────────────
apt_installed() { dpkg -s "$1" &>/dev/null; }

# ── Helper: check if pip package is importable ───────────────────────────────
pip_installed() { python3 -c "import $1" &>/dev/null; }

# 1. System packages — only install what's missing
MISSING_APT=()
for pkg in python3-pip python3-pygame libhidapi-hidraw0 libhidapi-dev python3-evdev joystick; do
    apt_installed "$pkg" || MISSING_APT+=("$pkg")
done

if [ ${#MISSING_APT[@]} -eq 0 ]; then
    skip "All system packages"
else
    info "Installing missing system packages: ${MISSING_APT[*]}"
    sudo apt-get update -qq
    sudo apt-get install -y --no-install-recommends "${MISSING_APT[@]}"
    ok "System packages done"
fi

# 2. pip packages — only install what's missing
MISSING_PIP=()
pip_installed dearpygui || MISSING_PIP+=("dearpygui")
pip_installed hid        || MISSING_PIP+=("hid")

if [ ${#MISSING_PIP[@]} -eq 0 ]; then
    skip "All pip packages (dearpygui, hid)"
else
    info "Installing missing pip packages: ${MISSING_PIP[*]}"
    pip3 install "${MISSING_PIP[@]}" --break-system-packages 2>/dev/null || \
    pip3 install "${MISSING_PIP[@]}" --user
    ok "pip packages done"
fi

# 3. udev rules — only write if not already present
UDEV_RULE="/etc/udev/rules.d/70-ps4-controller.rules"
if [ -f "$UDEV_RULE" ]; then
    skip "udev rules ($UDEV_RULE)"
else
    info "Installing udev rules..."
    cat <<'EOF' | sudo tee "$UDEV_RULE" > /dev/null
# DualShock 4 v1 (USB)
KERNEL=="hidraw*", ATTRS{idVendor}=="054c", ATTRS{idProduct}=="05c4", MODE="0666", GROUP="input", TAG+="uaccess"
SUBSYSTEM=="usb",  ATTRS{idVendor}=="054c", ATTRS{idProduct}=="05c4", MODE="0666"
# DualShock 4 v2 (USB + BT)
KERNEL=="hidraw*", ATTRS{idVendor}=="054c", ATTRS{idProduct}=="09cc", MODE="0666", GROUP="input", TAG+="uaccess"
SUBSYSTEM=="usb",  ATTRS{idVendor}=="054c", ATTRS{idProduct}=="09cc", MODE="0666"
# Generic gamepad joystick access
KERNEL=="js*",    MODE="0666"
KERNEL=="event*", SUBSYSTEM=="input", MODE="0666"
EOF
    sudo udevadm control --reload-rules && sudo udevadm trigger
    ok "udev rules installed"
fi

# 4. input group — only add if not already a member
if id -nG "$USER" | grep -qw input; then
    skip "User '$USER' already in 'input' group"
else
    info "Adding $USER to 'input' group..."
    sudo usermod -aG input "$USER"
    ok "Added to input group (re-login or run: newgrp input)"
fi

# 5. Make scripts executable
chmod +x "$(dirname "$0")/start.sh"

echo ""
ok "Done!  Run: ${RED}./start.sh${RESET}"
echo ""
