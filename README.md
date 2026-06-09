# Sacramento Amtrak Departures Board

A small real-time **departures** board for **Sacramento Valley Station (SAC)**,
built for a Raspberry Pi + a 7" DSI touchscreen LCD (Hosyond 800x480). Shows the
next departures with delays marked. Departures only — trains terminating at
Sacramento are excluded.

Covers every route serving SAC: **Capitol Corridor, San Joaquins, California
Zephyr, Coast Starlight.**

## Data sources

The board blends a live feed with published timetables, because no single source
has everything:

- **[Amtraker v3](https://github.com/piemadd/amtrak)** (`api-v3.amtraker.com`) —
  community-decrypted Amtrak "Track a Train" data. Source of live positions and
  delays, and the only source for the long-distance trains (Zephyr, Starlight).
  No API key. But it only carries trains being *actively tracked*, so it can't
  show a full forward timetable.
- **511 GTFS** (`operator_id=AM`) — the full Capitol Corridor schedule. Needs a
  free [511.org](https://511.org/open-data) token.
- **[Gold Runner / SJJPA GTFS](https://goldrunner.com/developer-resources/)** —
  the full San Joaquins schedule (511 has no static feed for it). No token.

Capitol Corridor and San Joaquins come from their GTFS schedules (so the board
shows the complete forward timetable), with Amtraker's live delays overlaid by
train number. A Sacramento stop counts as a *departure* only when it isn't the
trip's final stop; Thruway connecting buses (`route_type != 2`) are filtered out.

## Configuration

The 511 token is read from the `TRANSIT_511_TOKEN` environment variable (it also
falls back to `~/dev/bay-area-transit-map/.env`). Get a free token at
<https://511.org/open-data/token>.

```sh
export TRANSIT_511_TOKEN=your-token-here
```

## Files

| File | Role |
|------|------|
| `amtrak_sac.py`  | Fetch Amtraker, merge GTFS schedule, compute delays, build the board |
| `gtfs_sched.py`  | Read the 511/Gold Runner GTFS feeds → scheduled SAC departures |
| `serve.py`        | **Animated** board: serves the canvas app + `/data.json` + font |
| `web/board.html`  | The `<canvas>` split-flap app (animation lives here) |
| `render_board.py` | Static PIL render of the board (amber-on-black) + `row_view` |
| `display_screen.py`| Static pygame fullscreen path (no-browser fallback) |
| `board.py`        | Entry point for the static pygame path (refresh every 2 min) |
| `amtrak_sac.py`   | Fetch Amtraker, merge GTFS schedule, compute delays, build the board |
| `gtfs_sched.py`   | Read the 511/Gold Runner GTFS feeds → scheduled SAC departures |
| `render_sample.py`| Dev tool: render the layout with any font (used for font selection) |
| `fonts/`          | Bundled **Chakra Petch Bold** (OFL) — the board font |

Styled as a classic split-flap departures board: ALL-CAPS Chakra Petch Bold,
**amber/yellow text on black** with delayed trains in orange-red. Times are
12-hour; delays compact (`+20 MIN`, `+1H35`). **Split-flap animation:** whenever
the data changes, each character spins *forward* through the alphabet to its
target, staggered left-to-right (a Solari-board cascade). This lives in the
canvas app (`web/board.html` via `serve.py`); the pygame path renders statically.

## Run / preview on any machine

```sh
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
export TRANSIT_511_TOKEN=your-token

./.venv/bin/python serve.py          # animated board at http://localhost:8770
./.venv/bin/python board.py --once   # static one-frame render to board.png
./.venv/bin/python amtrak_sac.py     # print the board as text
```

Open the URL to watch the split-flap animation; tap/click the board to replay it.

## Deploy on the Raspberry Pi (Hosyond 7" DSI LCD)

The Hosyond is a driver-free DSI panel: connect the ribbon to the Pi's
**DISPLAY/DSI** port (+ the USB-touch lead) and it works as the Pi's 800x480
screen — no driver install.

**Recommended — animated, via browser kiosk** (the animation runs in the browser):

1. Copy this repo to the Pi, `pip install -r requirements.txt`, `export TRANSIT_511_TOKEN=...`.
2. Run `python3 serve.py` (e.g. as a systemd service).
3. Launch the display: `chromium-browser --kiosk --app=http://localhost:8770`
   (add both to autostart). The touchscreen lets you tap to replay the flaps.

**Alternative — static, no browser:** `python3 board.py` draws the board
fullscreen via pygame (no animation). Autostart it the same way. If pygame won't
go fullscreen on Pi 5/Wayland, try `SDL_VIDEODRIVER=wayland`.

## Tuning

- **Resolution / colors** — `PANEL_SIZE` (800x480) and the `BLACK`/`YELLOW`/`RED`
  palette in `render_board.py`.
- **Time window** — `MAX_HOURS` in `amtrak_sac.py` (default 24).
- **Refresh rate** — `REFRESH_SECONDS` in `serve.py` (web) / `board.py` (pygame); default 120 = 2 min.
- **Flap speed / stagger** — `MS_PER_FLAP` and `STAGGER_MS_PER_PX` in `web/board.html`.
- **Rows shown** — `MAX_ROWS` in `render_board.py` (default 8).
- **Add a route** — one entry in `OPERATORS` in `gtfs_sched.py`.

## Data notes

GTFS feeds are cached in `gtfs_cache/` and refreshed about once a day. 511's
gateway is slow and rate-limited (60 req/hr), so fetches retry with backoff. If
the schedule feeds are unreachable, the board degrades to realtime-only.
