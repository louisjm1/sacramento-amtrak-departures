"""The only hardware-specific file. Push a PIL image to the e-ink panel.

On a Mac (no panel) this falls back to saving board.png so the rest of the
pipeline is testable. On the Pi, install the Waveshare driver for your panel
and the `show()` below sends the image to it.

Waveshare 7.5" v2 example wiring uses their `waveshare_epd.epd7in5_V2` module
(clone https://github.com/waveshareteam/e-Paper into the project). For a
Pimoroni Inky panel, swap in `from inky.auto import auto` instead.
"""

from __future__ import annotations

from PIL import Image

try:
    from waveshare_epd import epd7in5_V2  # type: ignore
    _HAS_PANEL = True
except Exception:  # noqa: BLE001 - any import failure means "no panel here"
    _HAS_PANEL = False


def show(img: Image.Image) -> None:
    if not _HAS_PANEL:
        img.save("board.png")
        print("[no panel] wrote board.png")
        return

    epd = epd7in5_V2.EPD()
    epd.init()
    # Tri-color panels take a black buffer and a red buffer. The Waveshare 7.5"
    # v2 here is black/white; for a tri-color model, split the red pixels into a
    # second buffer and pass both to epd.display().
    epd.display(epd.getbuffer(img.convert("1")))
    epd.sleep()  # deep-sleep between refreshes — e-ink holds the image with no power


if __name__ == "__main__":
    from amtrak_sac import get_board
    from render_board import render
    show(render(get_board()))
