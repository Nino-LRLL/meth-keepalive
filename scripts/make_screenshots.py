"""Meth — screenshots OFF/ON (380x560, langage visuel métal mat v0.3 Rust).

Même rendu que l'app egui : fond dégradé anthracite→noir, disque métal mat
gris (dégradé radial doux), liseré de lumière supérieur, pastille d'état
8px (grise OFF / verte pulsante ON), sous-texte « · NORMAL · » / « · ACTIF · »,
version en pied. Usage : python scripts/make_screenshots.py
"""
from __future__ import annotations

import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "assets")

W, H = 380, 560
BG_TOP = (26, 26, 28)
BG_BOTTOM = (12, 12, 14)
GREEN = (52, 216, 104)
TEXT = (207, 207, 210)
MUTED = (119, 119, 125)
DISC_CENTER = (72, 72, 77)
DISC_EDGE = (21, 21, 23)
RING = (90, 90, 96)

FONT_BOLD = ["C:/Windows/Fonts/segoeuib.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
FONT_REG = ["C:/Windows/Fonts/segoeui.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]


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


def draw(on: bool) -> Image.Image:
    img = Image.new("RGB", (W, H), BG_BOTTOM)
    d = ImageDraw.Draw(img)
    for y in range(H):
        d.line((0, y, W, y), fill=_blend(BG_TOP, BG_BOTTOM, y / H))

    # Titre.
    f_title = _font(FONT_BOLD, 30)
    d.text((W // 2, 40), "Meth", font=f_title, fill=TEXT, anchor="ma")
    f_tag = _font(FONT_REG, 11)
    d.text((W // 2, 78), "Your AI works. The PC stays awake.", font=f_tag, fill=MUTED, anchor="ma")

    # Disque métal mat.
    cx, cy = W // 2, 300
    r = 105
    d.ellipse((cx - r - 3, cy - r - 3, cx + r + 3, cy + r + 3), outline=RING, width=1)
    for i in range(r, 0, -1):
        t = i / r
        d.ellipse((cx - i, cy - i, cx + i, cy + i), fill=_blend(DISC_EDGE, DISC_CENTER, t * t))
    # Liseré de lumière supérieur (2px) — seul reflet.
    d.ellipse((cx - r + 3, cy - r + 3, cx + r - 3, cy + r - 3), outline=(106, 106, 112), width=2)
    # Anneau d'état : vert fin en ON, gris en OFF.
    ring = GREEN if on else (51, 51, 55)
    d.ellipse((cx - r + 7, cy - r + 7, cx + r - 7, cy + r - 7), outline=ring, width=2 if on else 1)

    # Pastille d'état 8px + sous-texte.
    dot_y = cy - r + 24
    d.ellipse((cx - 4, dot_y - 4, cx + 4, dot_y + 4), fill=GREEN if on else (74, 74, 80))
    label = "· ACTIF ·" if on else "· NORMAL ·"
    d.text((cx, dot_y + 14), label, font=_font(FONT_REG, 12), fill=GREEN if on else MUTED, anchor="ma")

    # Pied : checkbox autostart + version.
    d.text((W // 2, cy + r + 50), "Démarrer Meth au démarrage", font=_font(FONT_REG, 11), fill=TEXT, anchor="ma")
    d.rectangle((W // 2 - 90, cy + r + 44, W // 2 - 66, cy + r + 60), outline=MUTED, width=1)
    if True:  # case cochée
        d.line((W // 2 - 86, cy + r + 52, W // 2 - 78, cy + r + 58), fill=GREEN, width=2)
        d.line((W // 2 - 78, cy + r + 58, W // 2 - 68, cy + r + 46), fill=GREEN, width=2)
    d.text((W // 2, cy + r + 78), "Meth v0.3.0 — windows", font=_font(FONT_REG, 9), fill=MUTED, anchor="ma")
    return img


def main() -> int:
    for on, name in ((False, "screenshot-off.png"), (True, "screenshot-on.png")):
        draw(on).save(os.path.join(OUT, name), format="PNG")
        print(f"OK {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
