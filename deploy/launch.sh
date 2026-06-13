#!/usr/bin/env bash
# Click-to-launch the board: make sure the data server is up, then open it
# fullscreen in Chromium. Used by the desktop app icon (deploy/launch.sh).
set -u

REPO="$(cd "$(dirname "$0")/.." && pwd)"
URL="http://localhost:8770"
ready() { curl -sf -o /dev/null "$URL/"; }

# Start the data server if it isn't already answering.
if ! ready; then
  if systemctl --user cat sac-board.service >/dev/null 2>&1; then
    systemctl --user start sac-board || true          # installed service (even if disabled)
  else
    [ -f "$HOME/.config/sac-board/env" ] && { set -a; . "$HOME/.config/sac-board/env"; set +a; }
    nohup "$REPO/.venv/bin/python" "$REPO/serve.py" >/tmp/sac-board.log 2>&1 &
  fi
fi

# Give it up to ~30s to come up (the page itself also shows "CONNECTING…").
for _ in $(seq 1 30); do ready && break; sleep 1; done

CHROME="$(command -v chromium-browser || command -v chromium || true)"
if [ -z "$CHROME" ]; then
  echo "Chromium not found — install it: sudo apt install -y chromium-browser" >&2
  exit 1
fi

# --password-store=basic stops Chromium asking for the Pi login (keyring) password.
exec "$CHROME" \
  --kiosk "$URL" \
  --password-store=basic \
  --noerrdialogs \
  --disable-infobars \
  --disable-session-crashed-bubble \
  --disable-features=Translate \
  --check-for-update-interval=31536000 \
  --ozone-platform-hint=auto
