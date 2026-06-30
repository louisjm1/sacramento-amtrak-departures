#!/usr/bin/env bash
# One-time setup to make the board a permanent, boot-on kiosk on Raspberry Pi OS.
# Run ON THE PI, from anywhere:  bash deploy/setup.sh
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"
echo "Project: $REPO"

# 1) Python venv + dependencies (Pillow, pygame) — ARM wheels via piwheels.
echo "==> Creating venv and installing dependencies"
python3 -m venv .venv
./.venv/bin/pip install --quiet --upgrade pip
./.venv/bin/pip install --quiet -r requirements.txt

# 2) 511 API token (stored outside the repo, read by the service).
mkdir -p "$HOME/.config/sac-board"
ENVFILE="$HOME/.config/sac-board/env"
if ! grep -q '^TRANSIT_511_TOKEN=' "$ENVFILE" 2>/dev/null; then
  read -rp "Enter your 511.org API token: " TOK
  echo "TRANSIT_511_TOKEN=$TOK" > "$ENVFILE"
  chmod 600 "$ENVFILE"
fi

# 3) Data server as a systemd *user* service (starts on boot, auto-restarts).
echo "==> Installing the data-server service"
mkdir -p "$HOME/.config/systemd/user"
sed -e "s#%REPO%#$REPO#g" -e "s#%ENVFILE%#$ENVFILE#g" \
  deploy/sac-board.service > "$HOME/.config/systemd/user/sac-board.service"
systemctl --user daemon-reload
systemctl --user enable --now sac-board.service
# Let the user service run at boot before/without an interactive login.
sudo loginctl enable-linger "$USER" || true

# 4) Chromium kiosk at login (XDG autostart works on Pi OS desktop, X or Wayland).
echo "==> Installing the kiosk autostart entry"
chmod +x deploy/kiosk.sh
mkdir -p "$HOME/.config/autostart"
cat > "$HOME/.config/autostart/sac-board-kiosk.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Sacramento Departures Kiosk
Exec=$REPO/deploy/kiosk.sh
X-GNOME-Autostart-enabled=true
EOF

# 5) Never blank the screen.
echo "==> Disabling screen blanking"
sudo raspi-config nonint do_blanking 1 || true

echo "==> Stopping the Chromium keyring/password prompt"
bash "$REPO/deploy/disable-keyring.sh" || true

echo
echo "Done. Reboot to launch the board:  sudo reboot"
echo "  - Server status:   systemctl --user status sac-board"
echo "  - Server logs:     journalctl --user -u sac-board -f"
echo "  - To stop kiosk:   rm ~/.config/autostart/sac-board-kiosk.desktop"
