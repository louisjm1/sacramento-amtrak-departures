"""Generate deploy/icon.png — the desktop-app icon (amber train face on black).

    python3 deploy/make_icon.py
"""

import os
from PIL import Image, ImageDraw

S = 256
AMBER = (255, 200, 0, 255)
BLACK = (0, 0, 0, 255)

img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

# Rounded black tile (app-icon background).
d.rounded_rectangle([6, 6, S - 6, S - 6], radius=52, fill=BLACK)

# Train face (front view), amber.
d.rounded_rectangle([66, 46, 190, 206], radius=30, fill=AMBER)
# Windshield.
d.rounded_rectangle([84, 64, 172, 116], radius=16, fill=BLACK)
# Headlights.
d.ellipse([90, 150, 116, 176], fill=BLACK)
d.ellipse([140, 150, 166, 176], fill=BLACK)
# Front skirt / coupler bar.
d.rounded_rectangle([80, 186, 176, 202], radius=7, fill=BLACK)

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.png")
img.save(out)
print("wrote", out)
