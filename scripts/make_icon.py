"""Meth — génération de l'icône (ICO + PNG) sans aucun asset externe.

Design : pastille ronde sombre avec anneau + lettre « M », pastille centrale
verte (ON). Aucune image tierce — tout est dessiné avec Pillow.

Usage :
    python scripts/make_icon.py
    → assets/icon.ico  (256, 128, 64, 48, 32, 16)
    → assets/icon.png  (256, pour la social preview / README)
"""
from __future__ import annotations

import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ASSETS = os.path.join(ROOT, "assets")

BG = (13, 17, 23, 255)
GREEN = (61, 220, 104, 255)
GREEN_DIM = (31, 122, 65, 255)
TEXT = (232, 238, 245, 255)
RING = (44, 58, 82, 255)

FONT_CANDIDATES = [
    "C:/Windows/Fonts/segoeuib.ttf",       # Segoe UI Bold
    "C:/Windows/Fonts/segoeui.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]


def _font(size: int):
    for path in FONT_CANDIDATES:
        if os.path.isfile(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def draw(size: int, on: bool = True) -> Image.Image:
    """Dessine l'icône Meth à la taille demandée (pastille ronde + M)."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Fond : pastille ronde sombre.
    m = max(1, int(size * 0.04))
    d.ellipse((m, m, size - m, size - m), fill=BG, outline=RING, width=max(1, int(size * 0.035)))
    # Pastille centrale : verte (ON).
    c = int(size * 0.30)
    d.ellipse((size / 2 - c / 2, size / 2 - c / 2, size / 2 + c / 2, size / 2 + c / 2),
              fill=GREEN, outline=GREEN_DIM, width=max(1, int(size * 0.02)))
    # Lettre M.
    try:
        f = _font(int(size * 0.42))
        bbox = d.textbbox((0, 0), "M", font=f)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        d.text((size / 2 - w / 2 - bbox[0], size / 2 - h / 2 - bbox[1]),
               "M", font=f, fill=TEXT)
    except Exception:
        pass
    return img


def main() -> int:
    os.makedirs(ASSETS, exist_ok=True)
    sizes = [256, 128, 64, 48, 32, 16]
    frames = [draw(s) for s in sizes]
    ico_path = os.path.join(ASSETS, "icon.ico")
    frames[0].save(ico_path, format="ICO", sizes=[(s, s) for s in sizes])
    png_path = os.path.join(ASSETS, "icon.png")
    draw(512).save(png_path, format="PNG")
    print(f"ICON  {ico_path}  ({', '.join(str(s) for s in sizes)} px)")
    print(f"PNG   {png_path}  (512 px)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
