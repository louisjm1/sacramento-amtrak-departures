# Permanent kiosk setup (Raspberry Pi)

Turns the board into an appliance: power on → it boots straight to the fullscreen
departures board and stays there, auto-refreshing and re-animating. No app to
open; survives reboots and power cuts.

## One-time install (on the Pi)

```sh
git clone https://github.com/louisjm1/sacramento-amtrak-departures.git ~/sacramento-amtrak-departures
cd ~/sacramento-amtrak-departures
bash deploy/setup.sh        # asks for your 511 token, then wires everything up
sudo reboot
```

`setup.sh` does all of it:
- creates the Python venv and installs deps,
- saves your 511 token to `~/.config/sac-board/env`,
- installs **`sac-board`** (a systemd *user* service) so `serve.py` starts on
  boot and auto-restarts,
- adds a **Chromium kiosk** autostart entry that opens the board fullscreen,
- disables screen blanking.

## What runs

| Piece | Role |
|-------|------|
| `sac-board.service` | runs `serve.py` in the background (boot + auto-restart) |
| `kiosk.sh`          | waits for the server, then launches Chromium `--kiosk` |
| autostart `.desktop`| starts `kiosk.sh` at desktop login (auto-login is on by default) |

## Desktop app icon (click to launch)

Prefer launching it yourself instead of (or alongside) auto-boot? Install a
clickable desktop icon:

```sh
bash deploy/install-desktop-app.sh
```

A **Sacramento Departures** icon appears on the desktop and in the app menu.
Double-click it to open the board fullscreen — `deploy/launch.sh` starts the
data server if it isn't already running, then opens Chromium in kiosk mode.
(The first double-click may ask to "Execute" — choose Execute.)

This pairs well with turning auto-boot off (see below): the board is there when
you click it, not forced on every boot.

## Handy commands

```sh
systemctl --user status sac-board       # is the server up?
journalctl --user -u sac-board -f       # live server logs
systemctl --user restart sac-board      # restart after a code change
rm ~/.config/autostart/sac-board-kiosk.desktop   # disable the kiosk
```

To exit the kiosk on-screen: plug in a keyboard and press **Alt+F4** (or Ctrl+W).

## If the kiosk doesn't auto-start

XDG autostart (`~/.config/autostart/`) works on the standard Pi OS desktop on
both X and Wayland. If your image uses a compositor that ignores it:

- **Wayfire** (some Bookworm builds): add to `~/.config/wayfire.ini`
  ```ini
  [autostart]
  sacboard = /home/<user>/sacramento-amtrak-departures/deploy/kiosk.sh
  ```
- **labwc**: add the same `kiosk.sh` line to `~/.config/labwc/autostart`.

The data-server service is independent of the display, so
`systemctl --user status sac-board` should be green regardless.

## Notes

- `serve.py` binds `127.0.0.1` (local only). To also view the board from your
  phone on the same network, change the bind in `serve.py` to `0.0.0.0` and open
  `http://<pi-ip>:8770`.
- Static, no-browser alternative: skip the kiosk and autostart `python3 board.py`
  (pygame fullscreen) instead — but that path has no flap animation.
