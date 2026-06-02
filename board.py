"""Entry point: refresh the Sacramento Amtrak e-ink board on an interval.

    python3 board.py            # loop forever, refresh every 90s
    python3 board.py --once     # render a single frame and exit

e-ink note: each refresh fully repaints the panel (a brief flash). 2 minutes is
a sane interval that's also polite to the free Amtraker service. The panel holds
the last image with zero power between refreshes.
"""

from __future__ import annotations

import argparse
import sys
import time

from amtrak_sac import get_board
from render_board import render
from display_eink import show

REFRESH_SECONDS = 120  # 2 minutes


def refresh_once() -> None:
    try:
        show(render(get_board()))
    except Exception as e:  # noqa: BLE001 - never let a transient fetch error kill the loop
        print(f"refresh failed: {e}", file=sys.stderr)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="render one frame and exit")
    ap.add_argument("--interval", type=int, default=REFRESH_SECONDS)
    args = ap.parse_args()

    if args.once:
        refresh_once()
        return

    while True:
        refresh_once()
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
