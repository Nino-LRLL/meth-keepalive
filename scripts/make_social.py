"""Meth — GitHub social preview (1280×640), générée sans asset externe.

Même langage visuel que l'app : fond dégradé sombre, pastille ronde verte
avec « M », slogan. Usage : python scripts/make_social.py
"""
from __future__ import annotations

import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "assets", "social-preview.png")

W, H = 1280, 640
BG_TOP = (20, 20, 22)      # gris anthracite neutre (aucune teinte bleue)
BG_BOTTOM = (11, 11, 12)   # noir profond
GREEN = (48, 209, 88)      # vert Apple system — sobre
GREEN_DIM = (44, 158, 76)
TEXT = (245, 245, 247)
MUTED = (142, 142, 147)
FAINT = (90, 90, 94)
RING = (44, 44, 46)
METAL = (85, 85, 90)       # disque métal (dégradé radial clair)
METAL_DARK = (26, 26, 29)

FONT_BOLD = [
    "C:/Windows/Fonts/segoeuib.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]
FONT_REG = [
    "C:/Windows/Fonts/segoeui.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]


def _font(cands: list, size: int):
    for p in cands:
        if os.path.isfile(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _blend(c1, c2, t):
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def main() -> int:
    img = Image.new("RGB", (W, H), BG_BOTTOM)
    d = ImageDraw.Draw(img)
    # Dégradé vertical.
    for y in range(H):
        d.line((0, y, W, y), fill=_blend(BG_TOP, BG_BOTTOM, y / H))
    # Halo décoratif derrière la pastille (vert très doux, respiration).
    cx, cy = W // 2, H // 2 - 40
    for i, t in enumerate([0.0, 0.15, 0.3, 0.45, 0.6]):
        r = 240 - i * 38
        d.ellipse((cx - r, cy - r, cx + r, cy + r),
                  fill=_blend(BG_TOP, (20, 58, 34), t * 0.5))
    # Disque MÉTAL (identité épurée gris/noir) : dégradé radial + reflet +
    # anneau d'état vert fin (comme l'app : métal dominant, vert SOBRE).
    r = 96
    d.ellipse((cx - r - 7, cy - r - 7, cx + r + 7, cy + r + 7),
              outline=GREEN_DIM, width=2)
    d.ellipse((cx - r - 2, cy - r - 2, cx + r + 2, cy + r + 2),
              outline=RING, width=1)
    for i in range(r, 0, -2):
        d.ellipse((cx - i, cy - i, cx + i, cy + i),
                  fill=_blend(METAL, METAL_DARK, i / r))
    # Reflet supérieur (liseré de lumière, style Apple).
    d.ellipse((cx - r * 0.52, cy - r * 0.62, cx + r * 0.52, cy - r * 0.12),
              fill=(99, 99, 106))
    f_m = _font(FONT_BOLD, 110)
    d.text((cx, cy - 4), "M", font=f_m, fill=GREEN, anchor="mm")

    # Titre + slogan.
    f_title = _font(FONT_BOLD, 64)
    d.text((cx, cy + 150), "METH", font=f_title, fill=TEXT, anchor="mm")
    f_tag = _font(FONT_REG, 30)
    d.text((cx, cy + 215),
           "Your AI works. Meth keeps the PC awake.",
           font=f_tag, fill=MUTED, anchor="mm")

    # Pied : badges texte discrets.
    f_badge = _font(FONT_REG, 22)
    d.text((cx, H - 56), "Windows + Linux · 100% Rust · Local-first · No cloud",
           font=f_badge, fill=_blend(BG_TOP, MUTED, 0.6), anchor="mm")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    img.save(OUT, format="PNG")
    print(f"OK {OUT} ({W}x{H})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
