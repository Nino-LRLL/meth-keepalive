"""Meth — App (composition root).

Relie les briques :
    UI (MainWindow + Settings + Tray)
        ↓
    App (contrôleur : traduit clics → actions)
        ↓
    Core (KeepAlive)
        ↓
    Windows (Power, Lid, System)

L'App possède :
- l'état ON/OFF (KeepAlive) ;
- les abonnements power/lid → mise à jour UI + tray ;
- le fail-safe : restauration au shutdown et à la fermeture ;
- la boucle UI légère (Power.tick pour rafraîchir le polling).

Fermer la fenêtre ≠ quitter : la fenêtre se cache, Meth continue en tray.
« Quitter » depuis le tray arrête réellement Meth (restauration incluse).
"""
from __future__ import annotations

import os
import sys
import time
from typing import Callable, Optional

from .Config.Config import Config
from .Core.KeepAlive import KeepAlive
from .backends import AutoStart, Lid, Power, set_exec_state

try:
    from .UI import MainWindow as MainWindowModule
    from .UI import Settings as SettingsModule
    from .UI import Tray as TrayModule
    _HAS_UI = True
except Exception:
    _HAS_UI = False


def _default_logger(level: str, msg: str) -> None:
    try:
        print(f"[meth:{level}] {msg}", file=sys.stderr)
    except Exception:
        pass


class MethApp:
    """Contrôleur global de Meth. Testable sans Windows ni Tkinter :
    chaque brique est injectable (kwargs) avec des faux dans les tests.
    """

    def __init__(self, *, config: Optional[Config] = None,
                 power=None, lid: Optional[Lid] = None,
                 keepalive: Optional[KeepAlive] = None,
                 autostart: Optional[SystemModule.AutoStart] = None,
                 logger: Optional[Callable[[str, str], None]] = None,
                 window=None, tray=None, settings=None) -> None:
        self.logger = logger or _default_logger
        self.config = config or Config(logger=self.logger)
        self.power = power or Power(logger=self.logger)
        self.lid = lid or Lid(logger=self.logger)
        self.keepalive = keepalive or KeepAlive(
            set_exec_state=set_exec_state, logger=self.logger)
        self.autostart = autostart or AutoStart(logger=self.logger)

        self.window = window
        self.tray = tray
        self.settings = settings

        self._last_ui_state: Optional[dict] = None
        self._quitting = False
        self._notice: Optional[str] = None

    # -- démarrage -------------------------------------------------------------
    def start(self) -> None:
        self.power.refresh()
        # Abonnements : tout changement power/lid → rafraîchir l'UI.
        self.power.on_change(lambda _st: self.refresh_ui())
        if self.lid is not None:
            self.lid.on_change(lambda _st: self.refresh_ui())
            try:
                self.lid.start()
            except Exception as exc:
                self.log("warning", f"lid: démarrage échoué: {exc}")

        if self.window is not None:
            self.window.render(self.state())
        if self.tray is not None:
            self.tray.set_state(self.keepalive.active)

        # Restaure l'état précédent si « last_state » était ON (fail-safe
        # volontaire : l'utilisateur retrouve Meth actif après un redémarrage).
        if self.config.get("last_state"):
            self.set_on(True)

        # Boucle UI : polling power léger (événementiel, 2 s).
        if self.window is not None and hasattr(self.window, "root"):
            self.window.root.after(500, self._ui_tick)

    def _ui_tick(self) -> None:
        if self._quitting or self.window is None:
            return
        try:
            self.power.tick()
            self.refresh_ui()
        except Exception:
            pass
        try:
            if hasattr(self.window, "root"):
                self.window.root.after(500, self._ui_tick)
        except Exception:
            pass

    # -- état ------------------------------------------------------------------
    def state(self) -> dict:
        power = self.power.status()
        return {
            "on": bool(self.keepalive.active),
            "lid": (self.lid.state if self.lid is not None else "INCONNU"),
            "power": power.get("ac", "INCONNU"),
            "battery": power.get("battery_percent"),
            # « PC » reflète la demande de Meth, pas un mensonge : ACTIF quand
            # Meth maintient Windows éveillé, NORMAL sinon (jamais « VEILLE »
            # — le PC n'est pas nécessairement en veille).
            "pc": "ACTIF" if bool(self.keepalive.active) else "NORMAL",
            # Notice optionnelle à afficher par l'UI (ex. refus ac_only).
            "notice": self._notice,
        }

    def refresh_ui(self) -> None:
        st = self.state()
        if st == self._last_ui_state:
            return
        self._last_ui_state = st
        if self.window is not None:
            try:
                self.window.render(st)
            except Exception:
                pass
        if self.tray is not None:
            try:
                self.tray.set_state(st["on"])
            except Exception:
                pass

    # -- actions ---------------------------------------------------------------
    def set_on(self, on: bool) -> bool:
        # « Activer uniquement sur secteur » : refus honnête sur batterie.
        if on and self.config.get("ac_only"):
            power = self.power.status()
            if power.get("ac") == "BATTERIE":
                self._notice = ("Refusé : « secteur uniquement » est coché "
                                "et Meth est sur batterie.")
                self.logger("warning", "activation refusée (ac_only, batterie)")
                self.refresh_ui()
                return False
            self._notice = None
        if on:
            self._notice = None

        ok = self.keepalive.activate() if on else self.keepalive.deactivate()
        if ok:
            self.config.set("last_state", bool(on))
            if not on:
                self._notice = None
        self.refresh_ui()
        return ok

    def on_toggle(self) -> bool:
        return self.set_on(not self.keepalive.active)

    def on_open(self) -> None:
        if self.window is not None:
            self.window.show()

    def on_close(self) -> None:
        # Fermer la fenêtre principale ≠ arrêter Meth : Meth continue.
        # Si le tray est actif → on cache (Meth vit dans le tray).
        # Si le tray est désactivé → on MINIMISE (Meth reste accessible
        # dans la barre des tâches — jamais perdu invisible).
        if self.window is None:
            return
        tray_on = bool(self.config.get("show_tray"))
        if tray_on and self.tray is not None and self.tray.available:
            self.window.hide()
        else:
            self.window.minimize()

    def on_settings_close(self) -> None:
        """Fermeture de la fenêtre paramètres : NE TOUCHE PAS à la fenêtre
        principale (bug corrigé : avant, fermer ⚙ cachait Meth)."""
        if self.settings is not None:
            try:
                self.settings.destroy()
            except Exception:
                pass

    def on_settings(self) -> None:
        if self.settings is None:
            return
        try:
            self.settings.root.deiconify()
            self.settings.root.lift()
        except Exception:
            # Fenêtre détruite (déjà fermée) → la reconstruire proprement.
            try:
                from src.UI.Settings import SettingsWindow
                self.settings = SettingsWindow(controller=self,
                                               logger=self.logger)
                self.settings.root.withdraw()
                self.settings.root.deiconify()
                self.settings.root.lift()
            except Exception:
                pass

    def on_about(self) -> None:
        if self.window is not None:
            self.window.show()

    def on_set(self, key: str, value) -> None:
        self.config.set(key, bool(value))
        if key == "autostart":
            self.autostart.set(bool(value))
        elif key == "show_tray" and self.tray is not None:
            if value:
                self.tray.start()
            else:
                self.tray.stop()

    def config_get(self, key: str):
        return self.config.get(key)

    def on_quit(self) -> None:
        self._quitting = True
        # Fail-safe : restaure le comportement Windows normal AVANT de partir.
        try:
            self.keepalive.shutdown()
        except Exception:
            pass
        if self.lid is not None:
            try:
                self.lid.stop()
            except Exception:
                pass
        if self.window is not None:
            try:
                self.window.destroy()
            except Exception:
                pass
        if self.settings is not None:
            try:
                self.settings.close()
            except Exception:
                pass
        if self.tray is not None:
            try:
                self.tray.stop()
            except Exception:
                pass
        # Force la fin du process (les threads daemon se terminent).
        os._exit(0)
