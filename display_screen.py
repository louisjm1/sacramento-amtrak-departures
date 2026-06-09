"""Show the board fullscreen on the Pi's DSI LCD (Hosyond 7", 800x480) via pygame.

The Hosyond panel is driver-free and acts as the Pi's normal display, so we just
draw the rendered image to it fullscreen. ESC / Q / window-close quit. On a
machine without pygame (e.g. your Mac) show() falls back to saving board.png, so
the pipeline stays testable — use serve.py to preview there.
"""

from __future__ import annotations

from PIL import Image

try:
    import pygame
    _HAS_PYGAME = True
except Exception:  # noqa: BLE001 - pygame is a Pi-only dependency
    _HAS_PYGAME = False

_screen = None


def _ensure(size):
    global _screen
    if _screen is None:
        pygame.init()
        pygame.mouse.set_visible(False)
        # DOUBLEBUF + a full-screen blit each refresh = the new frame replaces the
        # old one in a single buffer swap, so the panel never flashes/blanks.
        _screen = pygame.display.set_mode(size, pygame.FULLSCREEN | pygame.DOUBLEBUF)
        pygame.display.set_caption("Sacramento Departures")
    return _screen


def show(img: Image.Image) -> None:
    img = img.convert("RGB")
    if not _HAS_PYGAME:
        img.save("board.png")
        print("[no pygame] wrote board.png")
        return
    screen = _ensure(img.size)
    to_surface = getattr(pygame.image, "frombytes", pygame.image.fromstring)
    screen.blit(to_surface(img.tobytes(), img.size, "RGB"), (0, 0))
    pygame.display.flip()


def should_quit() -> bool:
    """Pump pygame events; return True if the user asked to exit (ESC/Q/close)."""
    if not _HAS_PYGAME or _screen is None:
        return False
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            return True
        if e.type == pygame.KEYDOWN and e.key in (pygame.K_ESCAPE, pygame.K_q):
            return True
    return False


def teardown() -> None:
    global _screen
    if _HAS_PYGAME and _screen is not None:
        pygame.quit()
        _screen = None


if __name__ == "__main__":
    from amtrak_sac import get_board
    from render_board import render
    show(render(get_board()))
