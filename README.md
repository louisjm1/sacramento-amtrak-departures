# Sacramento Amtrak Departures Board

A small real-time **departures** board for **Sacramento Valley Station (SAC)**,
built for a Raspberry Pi + e-ink panel. Shows the next departures with delays
marked in red. Departures only — trains terminating at Sacramento are excluded.

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
| `render_board.py`| Draw the board to a PIL image (amber-on-black, panel-sized) |
| `display_eink.py`| The one hardware-specific file — push the image to the panel |
| `board.py`       | Entry point: refresh on an interval (default 15 min) |
| `serve.py`       | Optional local web preview of the panel image |
| `render_sample.py`| Dev tool: render the layout with any font (used for font selection) |
| `fonts/`         | Bundled **Chakra Petch Bold** (OFL) — the split-flap-style board font |

Styled as a classic split-flap departures board: ALL-CAPS Chakra Petch Bold,
**amber/yellow text on black** with delayed trains in orange-red (for a colour
e-ink panel). Times are 12-hour; delays compact (`+20 MIN`, `+1H35`).

## Run / preview on any machine

```sh
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
export TRANSIT_511_TOKEN=your-token

./.venv/bin/python board.py --once   # render one frame to board.png (no panel)
./.venv/bin/python serve.py          # live web preview at http://localhost:8770
./.venv/bin/python amtrak_sac.py     # print the board as text
```

## Deploy on the Raspberry Pi

1. Copy this repo to the Pi, create the venv, `pip install -r requirements.txt`,
   and set `TRANSIT_511_TOKEN`.
2. Install your colour panel's driver and confirm the import in `display_eink.py`
   matches it (Pimoroni Inky Impression and Waveshare 7.3" 7-colour `epd7in3f`
   are both handled). Set `PANEL_SIZE` in `render_board.py` to your panel's pixels.
3. Run `python3 board.py` (under systemd or a cron `@reboot` to start on boot).

## Tuning

- **Panel size / colors** — `PANEL_SIZE` and the `BLACK`/`YELLOW`/`RED` palette
  in `render_board.py`. Colours are chosen to map onto common colour e-ink
  palettes (4-colour B/W/R/Y and 7-colour ACeP/Inky Impression).
- **Time window** — `MAX_HOURS` in `amtrak_sac.py` (default 24).
- **Refresh rate** — `--interval` seconds, or `REFRESH_SECONDS` (default 900 = 15 min).
- **Rows shown** — `MAX_ROWS` in `render_board.py` (default 8).
- **Add a route** — one entry in `OPERATORS` in `gtfs_sched.py`.

## Data notes

GTFS feeds are cached in `gtfs_cache/` and refreshed about once a day. 511's
gateway is slow and rate-limited (60 req/hr), so fetches retry with backoff. If
the schedule feeds are unreachable, the board degrades to realtime-only.
