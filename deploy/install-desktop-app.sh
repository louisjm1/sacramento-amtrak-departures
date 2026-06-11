#!/usr/bin/env bash
# Put a clickable "Sacramento Departures" app icon on the Pi desktop (and in the
# app menu). Run once on the Pi:  bash deploy/install-desktop-app.sh
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
chmod +x "$REPO/deploy/launch.sh"

DESKTOP_DIR="$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")"
APPS_DIR="$HOME/.local/share/applications"
mkdir -p "$DESKTOP_DIR" "$APPS_DIR"

entry() {
  cat <<EOF
[Desktop Entry]
Type=Application
Version=1.0
Name=Sacramento Departures
Comment=Live Amtrak departures board
Exec=$REPO/deploy/launch.sh
Icon=$REPO/deploy/icon.png
Terminal=false
Categories=Utility;Network;
EOF
}

DESKTOP_FILE="$DESKTOP_DIR/sacramento-departures.desktop"
entry > "$DESKTOP_FILE"
entry > "$APPS_DIR/sacramento-departures.desktop"
chmod +x "$DESKTOP_FILE"
# Mark trusted so it launches on double-click without an "untrusted" prompt
# (works on file managers that use GIO metadata; harmless elsewhere).
gio set "$DESKTOP_FILE" metadata::trusted true 2>/dev/null || true

echo "Installed. Look for the 'Sacramento Departures' icon on your desktop"
echo "(and in the app menu under Accessories/Internet)."
echo "First double-click may ask to 'Execute' — choose Execute."
