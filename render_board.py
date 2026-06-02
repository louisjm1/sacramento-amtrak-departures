"""Render the SAC board to a PIL image sized for an e-ink panel.

Palette is black / white / red — the three colors a tri-color Waveshare/Inky
panel supports. On the Pi this image goes straight to the panel; on a Mac it
saves as a PNG you can eyeball. Layout is resolution-driven, so changing
PANEL_SIZE to match your panel is the only edit needed.
"""

from __future__ import annotations

from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

from amtrak_sac import Stop

# Waveshare 7.5" v2 is 800x480. Change this to match your panel.
PANEL_SIZE = (800, 480)

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (220, 0, 0)

MAX_ROWS = 8  # rows that fit comfortably at this size

# Font candidates: macOS (for local testing) then Raspberry Pi OS.
_FONT_PATHS = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in _FONT_PATHS:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _clock(dt) -> str:
    """Local time like '3:05p' (no leading zero, compact am/pm)."""
    return dt.astimezone().strftime("%-I:%M%p").lower()[:-1]


# Column x-positions (px). Time column is wide enough for 'sched -> revised'
# (~174px); route ends by ~417, "To" by ~588, before the right-aligned status.
COL_TIME, COL_ROUTE, COL_TO = 16, 205, 435


def render(board: list[Stop], now: datetime | None = None) -> Image.Image:
    now = now or datetime.now().astimezone()
    w, h = PANEL_SIZE
    img = Image.new("RGB", PANEL_SIZE, WHITE)
    d = ImageDraw.Draw(img)

    title_f = _font(36)
    sub_f = _font(18)
    row_f = _font(26)
    small_f = _font(20)

    # Header bar.
    d.rectangle([0, 0, w, 58], fill=BLACK)
    d.text((16, 10), "SACRAMENTO DEPARTURES", font=title_f, fill=WHITE)
    d.text((w - 16, 20), now.strftime("updated %-I:%M %p"),
           font=sub_f, fill=WHITE, anchor="ra")

    # Column header.
    y = 70
    d.text((COL_TIME, y), "DEPART", font=small_f, fill=BLACK)
    d.text((COL_ROUTE, y), "ROUTE", font=small_f, fill=BLACK)
    d.text((COL_TO, y), "TO", font=small_f, fill=BLACK)
    d.text((w - 16, y), "STATUS", font=small_f, fill=BLACK, anchor="ra")
    y += 30
    d.line([12, y, w - 12, y], fill=BLACK, width=2)
    y += 12

    if not board:
        d.text((w // 2, h // 2), "No upcoming trains", font=row_f,
               fill=BLACK, anchor="mm")
        return img

    row_h = (h - y - 12) // MAX_ROWS
    for stop in board[:MAX_ROWS]:
        late = stop.is_late
        color = RED if late else BLACK

        # Departure time: scheduled in black; when late, '-> revised' in red.
        if late and stop.est is not None:
            sched = _clock(stop.sch)
            x = COL_TIME
            d.text((x, y), sched, font=row_f, fill=BLACK)
            x += d.textlength(sched, font=row_f)
            d.text((x, y), " → ", font=row_f, fill=BLACK)
            x += d.textlength(" → ", font=row_f)
            d.text((x, y), _clock(stop.est), font=row_f, fill=RED)
        else:
            d.text((COL_TIME, y), _clock(stop.sch), font=row_f, fill=color)

        d.text((COL_ROUTE, y), stop.route[:18], font=row_f, fill=color)
        d.text((COL_TO, y), stop.dest[:13], font=row_f, fill=color)

        if late:
            status = f"+{stop.delay_min} MIN LATE"
        elif stop.delay_min is not None:
            status = "On time"
        else:
            status = stop.status or "Scheduled"
        d.text((w - 16, y), status, font=row_f, fill=color, anchor="ra")
        y += row_h

    return img


if __name__ == "__main__":
    from amtrak_sac import get_board
    out = "board.png"
    render(get_board()).save(out)
    print(f"wrote {out}")
