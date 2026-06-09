"""Render a representative SAC board with a given font, for font comparison.

    python3 render_sample.py <font_path> <out_png> [label]

Mirrors the real board layout (DEPART / ROUTE / TO / STATUS), 12-hour clock,
a smaller "updated" line, and one delayed row with the '->' mark — so we can
judge a candidate font on the actual content. Self-contained: no network.
"""

import sys
from PIL import Image, ImageDraw, ImageFont

PANEL = (800, 480)
BLACK, WHITE, RED = (0, 0, 0), (255, 255, 255), (220, 0, 0)
COL_TIME, COL_ROUTE, COL_TO = 16, 205, 435
DEJAVU = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"  # arrow fallback (Pi)
MAC_DEJAVU = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"

# (sched, revised-or-None, route, dest, status, is_late)
ROWS = [
    ("5:58p", None, "Capitol Corridor", "Oakland", "On time", False),
    ("6:06p", None, "San Joaquins", "Bakersfield", "On time", False),
    ("7:59p", None, "Capitol Corridor", "San Jose", "Scheduled", False),
    ("9:00p", "9:42p", "Coast Starlight", "Seattle", "+42 MIN LATE", True),
    ("9:30p", None, "California Zephyr", "Emeryville", "On time", False),
    ("1:25p", None, "Capitol Corridor", "Auburn", "On time", False),
    ("8:53a", None, "Capitol Corridor", "Oakland", "On time", False),
    ("10:53p", None, "Coast Starlight", "Los Angeles", "Scheduled", False),
]


def load(path, size):
    return ImageFont.truetype(path, size)


def arrow_font(size):
    for p in (DEJAVU, MAC_DEJAVU):
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return None


def main():
    font_path, out = sys.argv[1], sys.argv[2]
    label = sys.argv[3] if len(sys.argv) > 3 else font_path

    title_f = load(font_path, 36)
    upd_f = load(font_path, 13)   # smaller "updated"
    head_f = load(font_path, 20)
    row_f = load(font_path, 26)
    arr_f = arrow_font(26) or row_f

    w, h = PANEL
    img = Image.new("RGB", PANEL, WHITE)
    d = ImageDraw.Draw(img)

    d.rectangle([0, 0, w, 58], fill=BLACK)
    d.text((16, 10), "SACRAMENTO DEPARTURES", font=title_f, fill=WHITE)
    d.text((w - 16, 22), "updated 5:58 PM", font=upd_f, fill=WHITE, anchor="ra")

    y = 70
    d.text((COL_TIME, y), "DEPART", font=head_f, fill=BLACK)
    d.text((COL_ROUTE, y), "ROUTE", font=head_f, fill=BLACK)
    d.text((COL_TO, y), "TO", font=head_f, fill=BLACK)
    d.text((w - 16, y), "STATUS", font=head_f, fill=BLACK, anchor="ra")
    y += 30
    d.line([12, y, w - 12, y], fill=BLACK, width=2)
    y += 12

    row_h = (h - y - 12) // len(ROWS)
    for sched, revised, route, dest, status, late in ROWS:
        color = RED if late else BLACK
        if late and revised:
            d.text((COL_TIME, y), sched, font=row_f, fill=BLACK)
            x = COL_TIME + d.textlength(sched, font=row_f)
            d.text((x, y), " → ", font=arr_f, fill=BLACK)
            x += d.textlength(" → ", font=arr_f)
            d.text((x, y), revised, font=row_f, fill=RED)
        else:
            d.text((COL_TIME, y), sched, font=row_f, fill=color)
        d.text((COL_ROUTE, y), route[:18], font=row_f, fill=color)
        d.text((COL_TO, y), dest[:13], font=row_f, fill=color)
        d.text((w - 16, y), status, font=row_f, fill=color, anchor="ra")
        y += row_h

    img.save(out)
    print(f"wrote {out} with {label}")


if __name__ == "__main__":
    main()
