#!/usr/bin/env bash
# One-time fix for the "unlock keyring / enter password" prompt that pops up
# when Chromium launches. It moves any existing GNOME keyrings aside so nothing
# tries to unlock them; combined with Chromium's --password-store=basic (already
# in launch.sh/kiosk.sh), nothing re-creates them, so the prompt stops for good.
#
# Safe and recoverable: keyrings are RENAMED to *.bak, not deleted. (On a Pi,
# wifi passwords live in NetworkManager's system files, not this user keyring,
# so this won't affect your network.)
#
#   bash deploy/disable-keyring.sh
set -u

DIR="$HOME/.local/share/keyrings"
moved=0
if [ -d "$DIR" ]; then
  for f in "$DIR"/*.keyring; do
    [ -e "$f" ] || continue
    mv -f "$f" "$f.bak" && { echo "moved aside: $(basename "$f")"; moved=1; }
  done
fi

if [ "$moved" = 1 ]; then
  echo "Done. Relaunch the board — it shouldn't ask for your keyring/Pi password."
  echo "(Recover anytime by renaming the *.keyring.bak files back in $DIR.)"
else
  echo "No keyrings found in $DIR — nothing to move."
  echo "If you're still prompted, make sure you launch via the app icon (which"
  echo "uses --password-store=basic), not a plain 'chromium' command."
fi
