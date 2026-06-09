"""The only hardware-specific file: push a PIL RGB image to the e-ink panel.

The board renders amber-on-black for a COLOR e-ink panel, so we send the RGB
image straight through (no 1-bit conversion). Exact wiring depends on the panel
you buy — two common 7-colour 800x480 options are handled below:

  * Pimoroni Inky Impression 7.3"  ->  pip install "inky[rpi]"
  * Waveshare 7.3" e-Paper (F)     ->  clone waveshare e-Paper; module epd7in3f

Confirm the module/resolution for your specific panel. On a machine with no
panel (e.g. your Mac) this just saves board.png so the pipeline stays testable.
"""

from __future__ import annotations

from PIL import Image


def show(img: Image.Image) -> None:
    img = img.convert("RGB")

    # 1) Pimoroni Inky Impression (auto-detects the connected model).
    try:
        from inky.auto import auto
        disp = auto()
        disp.set_image(img.resize(disp.resolution))
        disp.show()
        return
    except Exception:  # noqa: BLE001 - not an Inky / library absent; try next
        pass

    # 2) Waveshare 7.3" 7-colour (F). Adjust the module name to match your panel.
    try:
        from waveshare_epd import epd7in3f
        epd = epd7in3f.EPD()
        epd.init()
        epd.display(epd.getbuffer(img))
        epd.sleep()  # e-ink holds the image with no power between refreshes
        return
    except Exception:  # noqa: BLE001 - not a Waveshare panel / library absent
        pass

    # 3) No panel attached — save a PNG to eyeball.
    img.save("board.png")
    print("[no panel] wrote board.png")


if __name__ == "__main__":
    from amtrak_sac import get_board
    from render_board import render
    show(render(get_board()))
