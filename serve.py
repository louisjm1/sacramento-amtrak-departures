"""Web display of the board with a split-flap (Solari) animation.

Serves a <canvas> app that renders the amber-on-black board and animates each
character flipping forward to its target, staggered left-to-right, whenever the
data changes. Use it two ways:

  * Preview on a computer:  python3 serve.py  ->  http://localhost:8770
  * On the Pi (animated):   run this, then `chromium-browser --kiosk http://localhost:8770`

Endpoints:
  /            the canvas app (web/board.html)
  /data.json   current board rows (uses render_board.row_view — same strings
               as the PNG renderer) plus the refresh interval
  /font.ttf    the bundled Chakra Petch Bold, for @font-face
  /board.png   static PNG render (debug / pygame parity)
"""

from __future__ import annotations

import io
import json
import os
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from amtrak_sac import get_board, PACIFIC
from render_board import render, row_view, PANEL_SIZE, MAX_ROWS

PORT = 8770
REFRESH_SECONDS = 120  # how often the page polls /data.json (matches device)

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(HERE, "fonts", "ChakraPetch-Bold.ttf")
PAGE_PATH = os.path.join(HERE, "web", "board.html")


# Last successfully-fetched board, so a wifi/feed outage degrades gracefully:
# /data.json keeps serving the last good rows (with their age) instead of failing.
_LAST = {"rows": None, "at": None}
_LOCK = threading.Lock()


def board_json() -> dict:
    with _LOCK:
        try:
            fresh = [row_view(s) for s in get_board()[:MAX_ROWS]]
        except Exception:  # noqa: BLE001 - upstream/wifi down: fall back to cache
            fresh = None
        now = datetime.now(PACIFIC)
        if fresh is not None:
            _LAST["rows"], _LAST["at"] = fresh, now
        if _LAST["rows"] is None:
            raise RuntimeError("no board fetched yet")  # handler 502s; page retries
        return {
            "updated": _LAST["at"].strftime("updated %-I:%M %p"),
            "age_sec": max(0, int((now - _LAST["at"]).total_seconds())),
            "refresh": REFRESH_SECONDS,
            "panel": list(PANEL_SIZE),
            "rows": _LAST["rows"],
        }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):  # quiet
        pass

    def _send(self, data: bytes, ctype: str, cache: str = "no-store") -> None:
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", cache)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        try:
            if path in ("/", "/index.html"):
                with open(PAGE_PATH, "rb") as f:
                    self._send(f.read(), "text/html; charset=utf-8")
            elif path == "/data.json":
                self._send(json.dumps(board_json()).encode("utf-8"),
                           "application/json")
            elif path == "/font.ttf":
                with open(FONT_PATH, "rb") as f:
                    self._send(f.read(), "font/ttf", cache="max-age=86400")
            elif path == "/board.png":
                buf = io.BytesIO()
                render(get_board()).save(buf, format="PNG")
                self._send(buf.getvalue(), "image/png")
            else:
                self.send_error(404)
        except Exception as e:  # noqa: BLE001
            self.send_error(502, f"error: {e}")


if __name__ == "__main__":
    print(f"serving Sacramento board at http://localhost:{PORT}")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
