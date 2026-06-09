"""Render the SAC board to a PIL image sized for an e-ink panel.

Styled as a classic split-flap departures board: amber/yellow text on black,
with delayed trains in orange-red. These colors are in the palette of common
color e-ink panels (4-colour B/W/R/Y and 7-colour ACeP/Inky Impression). On
the Pi this image goes straight to the panel; on a Mac it saves a PNG. Layout
is resolution-driven, so changing PANEL_SIZE to match your panel is the only
required edit.
"""

from __future__ import annotations

import os
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

from amtrak_sac import Stop

# Waveshare 7.5" v2 is 800x480. Change this to match your panel.
PANEL_SIZE = (800, 480)

BLACK = (0, 0, 0)        # background
YELLOW = (255, 200, 0)   # amber board text
RED = (255, 75, 35)      # delayed trains (orange-red, pops on black)

MAX_ROWS = 8  # rows that fit comfortably at this size

# Departure-board font (Chakra Petch Bold), bundled in fonts/ so it works
# identically on the Mac and the Pi. System fonts are emergency fallbacks.
_BUNDLED_FONT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "fonts", "ChakraPetch-Bold.ttf")
_FONT_PATHS = [
    _BUNDLED_FONT,
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in _FONT_PATHS:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _clock(dt) -> str:
    """12-hour local time like '3:05P' (no leading zero, compact upper am/pm)."""
    return dt.astimezone().strftime("%-I:%M%p").upper()[:-1]


# Column x-positions (px), tuned for ALL-CAPS Chakra Petch Bold at row size 24:
# late time ends ~176, route ends ~433, "TO" ends ~612, before status (~622+).
COL_TIME, COL_ROUTE, COL_TO = 16, 190, 448


def render(board: list[Stop], now: datetime | None = None) -> Image.Image:
    now = now or datetime.now().astimezone()
    w, h = PANEL_SIZE
    img = Image.new("RGB", PANEL_SIZE, BLACK)
    d = ImageDraw.Draw(img)

    title_f = _font(36)
    sub_f = _font(13)   # smaller "updated …" line
    row_f = _font(24)
    small_f = _font(20)

    # Title + updated time (amber on black, split-flap style — no header bar).
    d.text((16, 10), "SACRAMENTO DEPARTURES", font=title_f, fill=YELLOW)
    d.text((w - 16, 20), now.strftime("updated %-I:%M %p"),
           font=sub_f, fill=YELLOW, anchor="ra")

    # Column header.
    y = 70
    d.text((COL_TIME, y), "DEPART", font=small_f, fill=YELLOW)
    d.text((COL_ROUTE, y), "ROUTE", font=small_f, fill=YELLOW)
    d.text((COL_TO, y), "TO", font=small_f, fill=YELLOW)
    d.text((w - 16, y), "STATUS", font=small_f, fill=YELLOW, anchor="ra")
    y += 30
    d.line([12, y, w - 12, y], fill=YELLOW, width=2)
    y += 12

    if not board:
        d.text((w // 2, h // 2), "NO UPCOMING TRAINS", font=row_f,
               fill=YELLOW, anchor="mm")
        return img

    row_h = (h - y - 12) // MAX_ROWS
    for stop in board[:MAX_ROWS]:
        late = stop.is_late
        color = RED if late else YELLOW

        # Departure time: scheduled in amber; when late, '-> revised' in red.
        if late and stop.est is not None:
            sched = _clock(stop.sch)
            x = COL_TIME
            d.text((x, y), sched, font=row_f, fill=YELLOW)
            x += d.textlength(sched, font=row_f)
            d.text((x, y), " → ", font=row_f, fill=YELLOW)
            x += d.textlength(" → ", font=row_f)
            d.text((x, y), _clock(stop.est), font=row_f, fill=RED)
        else:
            d.text((COL_TIME, y), _clock(stop.sch), font=row_f, fill=color)

        d.text((COL_ROUTE, y), stop.route.upper()[:18], font=row_f, fill=color)
        d.text((COL_TO, y), stop.dest.upper()[:13], font=row_f, fill=color)

        if late:
            m = stop.delay_min
            status = f"+{m} MIN" if m < 60 else f"+{m // 60}H{m % 60:02d}"
        elif stop.delay_min is not None:
            status = "ON TIME"
        else:
            status = (stop.status or "SCHEDULED").upper()
        d.text((w - 16, y), status, font=row_f, fill=color, anchor="ra")
        y += row_h

    return img


if __name__ == "__main__":
    from amtrak_sac import get_board
    out = "board.png"
    render(get_board()).save(out)
    print(f"wrote {out}")
