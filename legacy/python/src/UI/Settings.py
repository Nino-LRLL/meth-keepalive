"""Meth UI — Paramètres.

Mini-fenêtre de paramètres (V0, volontairement réduite) — même langage
visuel épuré que la fenêtre principale (gris / noir métal, Apple) :
- ☑ Démarrer Meth avec Windows ;
- ☑ Afficher dans le System Tray ;
- ☐ Activer uniquement sur secteur (appliqué : refus honnête sur batterie) ;
- version.

Chaque case applique IMMÉDIATEMENT la modification via le contrôleur
(registre Run pour l'autostart, config pour le reste) — pas de bouton
« Enregistrer » superflu.

La palette vient de MainWindow (source unique, jamais de dérive de teinte).
"""
from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont
from typing import Callable, Optional

from .MainWindow import (ACCENT, BG_BOTTOM, BG_TOP, BORDER, FAINT, FONT,
                         MUTED, PANEL, TEXT, apply_dark_title_bar)


class SettingsWindow:
    """Fenêtre paramètres. ``controller`` expose :
    on_set(key, value)         : applique une modification (config + registre)
    config_get(key)            : état actuel
    on_settings_close()        : fermeture propre (n'affecte pas la fenêtre
                                 principale)
    """

    def __init__(self, controller=None,
                 logger: Optional[Callable[[str, str], None]] = None) -> None:
        self._controller = controller or _NullController()
        self._logger = logger
        self.root = tk.Toplevel()
        self.root.title("Paramètres — Meth")
        self.root.configure(bg=BG_BOTTOM)
        self.root.resizable(False, False)
        apply_dark_title_bar(self.root)
        self._build()
        # Centre la fenêtre sur l'écran (jamais hors champ).
        self.root.update_idletasks()
        w, h = self.root.winfo_reqwidth(), self.root.winfo_reqheight()
        x = (self.root.winfo_screenwidth() - w) // 2
        y = (self.root.winfo_screenheight() - h) // 2
        self.root.geometry(f"{w}x{h}+{max(x, 0)}+{max(y, 0)}")

    def log(self, level: str, msg: str) -> None:
        if self._logger:
            try:
                self._logger(level, msg)
            except Exception:
                pass

    def _build(self) -> None:
        f = tkfont.Font(family=FONT, size=12, weight="bold")
        fs = tkfont.Font(family=FONT, size=9)

        top = tk.Frame(self.root, bg=BG_TOP)
        top.pack(fill="x", padx=0, pady=(0, 0))
        tk.Label(top, text="PARAMÈTRES", bg=BG_TOP, fg=TEXT, font=f,
                 anchor="w").pack(side="left", padx=16, pady=12)

        self._vars = {}
        rows = [
            ("autostart", "Démarrer Meth au démarrage"),
            ("show_tray", "Afficher Meth dans le System Tray"),
            ("ac_only", "Activer uniquement sur secteur"),
        ]
        for i, (key, label) in enumerate(rows):
            var = tk.BooleanVar(value=bool(self._controller.config_get(key)))
            self._vars[key] = var
            cb = tk.Checkbutton(
                self.root, text=label, variable=var, bg=BG_BOTTOM, fg=TEXT,
                activebackground=BG_BOTTOM, activeforeground=TEXT,
                selectcolor=PANEL, font=fs, anchor="w", cursor="hand2",
                command=lambda k=key, v=var: self._controller.on_set(k, v.get()))
            cb.pack(fill="x", padx=18, pady=6)
            if i < len(rows) - 1:
                tk.Frame(self.root, bg=BORDER, height=1).pack(
                    fill="x", padx=18)

        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x", padx=16,
                                                      pady=10)
        try:
            from .. import __version__ as _meth_version
            _version_txt = f"Meth v{_meth_version} — local-first, sans compte."
        except Exception:
            _version_txt = "Meth — local-first, sans compte."
        tk.Label(self.root, text=_version_txt, bg=BG_BOTTOM, fg=FAINT,
                 font=fs).pack(padx=16, pady=(0, 12))

        self.root.protocol("WM_DELETE_WINDOW", self._close)
        # Dark title bar à CHAQUE affichage (DWM ignore les fenêtres
        # créées puis cachées avant le premier map).
        self.root.bind("<Map>", lambda _e: apply_dark_title_bar(self.root),
                       add="+")

    def _close(self) -> None:
        try:
            self._controller.on_settings_close()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass

    def close(self) -> None:
        self.destroy()

    def destroy(self) -> None:
        """Détruit la fenêtre paramètres (appelé par App.on_settings_close
        quand on veut la refermer proprement depuis le contrôleur)."""
        try:
            self.root.destroy()
        except Exception:
            pass


class _NullController:
    def config_get(self, key: str):
        return False
    def on_set(self, key: str, value: bool) -> None:
        pass
    def on_settings_close(self) -> None:
        pass
