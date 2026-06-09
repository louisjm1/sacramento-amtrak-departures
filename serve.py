"""Tiny web preview of the e-ink board for desktop development.

Serves an HTML page that shows the rendered panel at its true pixel size and
auto-refreshes, plus the live PNG at /board.png (regenerated on each request).
This is ONLY for previewing on a computer; the Pi uses board.py + the panel.

    python3 serve.py            # http://localhost:8765
"""

from __future__ import annotations

import io
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from amtrak_sac import get_board
from render_board import render, PANEL_SIZE

PORT = 8770
REFRESH_SECONDS = 900  # 15 minutes — browser-side auto-reload (matches device)

PAGE = """<!doctype html>
<html><head><meta charset="utf-8">
<title>Sacramento Amtrak Board — preview</title>
<meta http-equiv="refresh" content="{refresh}">
<style>
  html,body {{ margin:0; height:100%; background:#222;
    display:flex; align-items:center; justify-content:center;
    font-family:-apple-system,system-ui,sans-serif; }}
  .frame {{ background:#000; padding:14px; border-radius:10px;
    box-shadow:0 10px 40px rgba(0,0,0,.6); }}
  img {{ width:{w}px; height:{h}px; display:block; image-rendering:pixelated; }}
  .cap {{ color:#888; font-size:12px; text-align:center; margin-top:8px; }}
</style></head>
<body><div class="frame">
  <img src="/board.png?t={refresh}" width="{w}" height="{h}" alt="board">
  <div class="cap">{w}×{h} e-ink preview · auto-refreshes every {refresh}s</div>
</div></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):  # quiet, but keep errors visible via exceptions
        pass

    def do_GET(self):
        if self.path.startswith("/board.png"):
            try:
                buf = io.BytesIO()
                render(get_board()).save(buf, format="PNG")
                data = buf.getvalue()
            except Exception as e:  # noqa: BLE001
                self.send_error(502, f"render failed: {e}")
                return
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        w, h = PANEL_SIZE
        body = PAGE.format(w=w, h=h, refresh=REFRESH_SECONDS).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    print(f"serving Sacramento board preview at http://localhost:{PORT}")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
