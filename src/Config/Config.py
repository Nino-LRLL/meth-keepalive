"""Meth Config — paramètres locaux.

Un seul fichier JSON dans le dossier de données de l'utilisateur
(``%APPDATA%/Meth/config.json``), surchargeable pour les tests via
``Config(path)``. Aucun cloud, aucun compte : tout est local.

Champs V0 :
- ``autostart``   : démarrer Meth avec Windows (booléen) ;
- ``show_tray``   : afficher dans le System Tray (booléen) ;
- ``ac_only``     : n'activer que sur secteur (booléen, préparé) ;
- ``last_state``  : état ON/OFF au dernier arrêt propre (rappels UI).

Chargement tolérant : fichier absent → défauts ; fichier corrompu →
défauts + avertissement (jamais de crash au démarrage).
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from typing import Any, Callable, Dict, Optional

DEFAULTS: Dict[str, Any] = {
    "autostart": False,
    "show_tray": True,
    "ac_only": False,
    "last_state": False,
}


def default_path() -> str:
    """Emplacement du fichier de config selon la plateforme :
    %APPDATA%/Meth sur Windows, $XDG_CONFIG_HOME/meth (ou ~/.config/meth)
    sur Linux — jamais dans le dossier de l'exe (Meth reste portable)."""
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA")
        if not base:
            base = os.path.join(tempfile.gettempdir(), "Meth")
        folder = os.path.join(base, "Meth")
    else:
        base = os.environ.get("XDG_CONFIG_HOME")
        folder = base if base else os.path.join(os.path.expanduser("~"), ".config")
        folder = os.path.join(folder, "meth")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "config.json")


class Config:
    """Paramètres persistés + listeners de changement (UI reactive)."""

    def __init__(self, path: Optional[str] = None,
                 logger: Optional[Callable[[str, str], None]] = None) -> None:
        self._logger = logger
        self._path = path or default_path()
        self._data: Dict[str, Any] = dict(DEFAULTS)
        self._listeners: list = []
        self._load()

    def log(self, level: str, msg: str) -> None:
        if self._logger:
            try:
                self._logger(level, msg)
            except Exception:
                pass

    # -- lecture / écriture ----------------------------------------------------
    @property
    def path(self) -> str:
        return self._path

    def _load(self) -> None:
        try:
            with open(self._path, "r", encoding="utf-8") as fh:
                saved = json.load(fh)
            if isinstance(saved, dict):
                for key, value in saved.items():
                    if key in DEFAULTS:
                        self._data[key] = value
            self.log("debug", f"config chargée: {self._path}")
        except FileNotFoundError:
            self.log("debug", "config absente → défauts")
        except (OSError, ValueError) as exc:
            self.log("warning", f"config illisible ({exc}) → défauts")

    def save(self) -> bool:
        try:
            os.makedirs(os.path.dirname(self._path), exist_ok=True)
            with open(self._path, "w", encoding="utf-8") as fh:
                json.dump(self._data, fh, indent=2, ensure_ascii=False)
            self.log("debug", f"config enregistrée: {self._path}")
            return True
        except OSError as exc:
            self.log("error", f"config: échec écriture: {exc}")
            return False

    # -- API ------------------------------------------------------------------
    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, DEFAULTS.get(key, default))

    def set(self, key: str, value: Any, persist: bool = True) -> None:
        if key not in DEFAULTS:
            self.log("warning", f"config: clé inconnue ignorée: {key}")
            return
        if self._data.get(key) == value:
            return
        self._data[key] = value
        if persist:
            self.save()
        for listener in list(self._listeners):
            try:
                listener(key, value)
            except Exception:
                pass

    def set_many(self, items: Dict[str, Any], persist: bool = True) -> None:
        changed = False
        for key, value in items.items():
            if key in DEFAULTS and self._data.get(key) != value:
                self._data[key] = value
                changed = True
        if changed and persist:
            self.save()
        if changed:
            for listener in list(self._listeners):
                try:
                    listener(None, None)
                except Exception:
                    pass

    def all(self) -> Dict[str, Any]:
        return dict(self._data)

    def on_change(self, listener) -> None:
        if listener not in self._listeners:
            self._listeners.append(listener)
