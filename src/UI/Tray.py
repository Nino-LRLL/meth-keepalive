"""Meth UI — System Tray (pystray).

Meth vit dans la zone de notification :
- icône ⚪ (OFF) / 🟢 (ON), générée localement (Pillow) — aucun asset externe ;
- menu : Ouvrir Meth / Activer-Désactiver / Paramètres / À propos / Quitter ;
- « Quitter » est le SEUL moyen d'arrêter Meth (fermer la fenêtre ≠ quitter).

L'icône reflète l'état RÉEL (toggle label + couleur), jamais inventé.
"""
from __future__ import annotations

from typing import Callable, Optional

try:
    import pystray
    from PIL import Image, ImageDraw
    _HAS_TRAY = True
except ImportError:
    pystray = None
    Image = ImageDraw = None
    _HAS_TRAY = False

ON_COLOR = (63, 185, 80, 255)      # vert
OFF_COLOR = (139, 152, 168, 255)   # gris clair
BG_COLOR = (13, 17, 23, 255)


def _make_icon(on: bool) -> "Image":
    """Icône 64×64 : pastille ronde ON/OFF + lettre M (aucun asset)."""
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((4, 4, 60, 60), fill=BG_COLOR, outline=on and ON_COLOR or OFF_COLOR, width=3)
    draw.ellipse((20, 20, 44, 44), fill=on and ON_COLOR or OFF_COLOR)
    # Lettre M (petite police système, repli sans police).
    try:
        from PIL import ImageFont
        for cand in ("C:/Windows/Fonts/segoeui.ttf",
                     "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
            import os
            if os.path.isfile(cand):
                f = ImageFont.truetype(cand, 22)
                draw.text((32, 30), "M", font=f,
                          fill=on and BG_COLOR or ON_COLOR, anchor="mm")
                break
    except Exception:
        pass
    return img


class Tray:
    """Wrapper pystray : état + menu, appels vers le contrôleur.

    ``controller`` expose : on_toggle(), on_open(), on_settings(),
    on_about(), on_quit(). ``on_state`` → callable() pour ré-afficher.
    """

    def __init__(self, controller=None,
                 logger: Optional[Callable[[str, str], None]] = None) -> None:
        self._controller = controller or _NullController()
        self._logger = logger
        self._icon = None
        self._on = False

    def log(self, level: str, msg: str) -> None:
        if self._logger:
            try:
                self._logger(level, msg)
            except Exception:
                pass

    @property
    def available(self) -> bool:
        return _HAS_TRAY

    def _menu(self):
        toggle_fn = self._controller.on_toggle
        return pystray.Menu(
            # Le texte est un CALLABLE : pystray l'évalue à chaque
            # update_menu() → le label « Activer/Désactiver » reste à jour
            # quand l'état change (API pystray documentée pour menus
            # dynamiques).
            pystray.MenuItem("Meth", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                lambda _i: "🟢 Désactiver Meth" if self._on else "⚪ Activer Meth",
                lambda _i, _e: toggle_fn()),
            pystray.MenuItem("Ouvrir Meth", lambda _i, _e: self._controller.on_open()),
            pystray.MenuItem("Paramètres", lambda _i, _e: self._controller.on_settings()),
            pystray.MenuItem("À propos", lambda _i, _e: self._controller.on_about()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quitter", lambda _i, _e: self._controller.on_quit()),
        )

    def start(self) -> None:
        if not _HAS_TRAY:
            self.log("warning", "tray indisponible (pystray/Pillow manquants)")
            return
        try:
            self._icon = pystray.Icon(
                "Meth", _make_icon(self._on), "Meth", self._menu())
            self._icon.run_detached()
            self.log("info", "tray démarré")
        except Exception as exc:
            self.log("error", f"tray: échec démarrage: {exc}")
            self._icon = None

    def set_state(self, on: bool) -> None:
        """Met à jour l'icône + le menu (label « Activer/Désactiver »)."""
        self._on = bool(on)
        if self._icon is not None:
            try:
                self._icon.icon = _make_icon(self._on)
                self._icon.update_menu()
            except Exception:
                pass

    def stop(self) -> None:
        if self._icon is not None:
            try:
                self._icon.stop()
            except Exception:
                pass
            self._icon = None


class _NullController:
    def on_toggle(self) -> bool:
        return False
    def on_open(self) -> None:
        pass
    def on_settings(self) -> None:
        pass
    def on_about(self) -> None:
        pass
    def on_quit(self) -> None:
        pass
