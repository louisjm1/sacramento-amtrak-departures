"""Entry point: draw the Sacramento departures board on the Pi's LCD, on a loop.

    python3 board.py            # fullscreen on the DSI LCD, refresh every 2 min
    python3 board.py --once     # render a single frame and exit (saves PNG off-Pi)

The Hosyond 7" DSI panel is a normal fast LCD, so refreshes are instant; 2 min
keeps delays near-live while being gentle on the data feeds. ESC / Q quit.
"""

from __future__ import annotations

import argparse
import sys
import time

from amtrak_sac import get_board
from render_board import render
import display_screen

REFRESH_SECONDS = 120  # 2 minutes


def refresh_once() -> None:
    try:
        display_screen.show(render(get_board()))
    except Exception as e:  # noqa: BLE001 - never let a transient fetch error kill the loop
        print(f"refresh failed: {e}", file=sys.stderr)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="render one frame and exit")
    ap.add_argument("--interval", type=int, default=REFRESH_SECONDS)
    args = ap.parse_args()

    try:
        refresh_once()
        if args.once:
            return
        while True:
            # Wait out the interval while staying responsive to quit/touch events.
            waited = 0.0
            while waited < args.interval:
                if display_screen.should_quit():
                    return
                time.sleep(0.2)
                waited += 0.2
            refresh_once()
    finally:
        display_screen.teardown()


if __name__ == "__main__":
    main()
