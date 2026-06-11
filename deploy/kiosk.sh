#!/usr/bin/env bash
# Launch Chromium fullscreen on the board. Run at login by the autostart entry
# that deploy/setup.sh creates. Waits for the data server, then never returns.
set -u

URL="http://localhost:8770"

# Wait for serve.py to be answering before opening the browser.
until curl -sf "$URL/data.json" >/dev/null 2>&1; do sleep 1; done

# Chromium is "chromium-browser" on Pi OS, "chromium" on some images.
CHROME="$(command -v chromium-browser || command -v chromium)"

# After a power cut Chromium otherwise shows a "restore pages?" bar — clear the
# unclean-exit flags so it boots straight to the board.
PREFS="$HOME/.config/chromium/Default/Preferences"
if [ -f "$PREFS" ]; then
  sed -i 's/"exit_type":"[^"]*"/"exit_type":"Normal"/; s/"exited_cleanly":false/"exited_cleanly":true/' "$PREFS" || true
fi

exec "$CHROME" \
  --kiosk "$URL" \
  --noerrdialogs \
  --disable-infobars \
  --disable-session-crashed-bubble \
  --disable-features=Translate \
  --check-for-update-interval=31536000 \
  --ozone-platform-hint=auto
