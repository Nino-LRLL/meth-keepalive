"""Meth Windows — System.

Infrastructure système honnête :
- ``set_exec_state(flags)`` : wrapper SetThreadExecutionState (kernel32),
  avec mémorisation de l'état précédent (restauration) ;
- ``AutoStart`` : démarrage de Meth avec Windows via la clé Run du registre
  (HKCU — aucun privilège administrateur requis) ;
- ``info()`` : version Windows réelle (jamais inventée).

Aucune simulation d'utilisateur (pas de faux clavier/souris) — uniquement
des mécanismes natifs documentés.
"""
from __future__ import annotations

import ctypes
import os
import sys
import winreg
from typing import Callable, Optional

ES_SYSTEM_REQUIRED = 0x00000001
ES_CONTINUOUS = 0x80000000
ES_OFF = ES_CONTINUOUS

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE = "Meth"


def set_exec_state(flags: int) -> int:
    """Appelle SetThreadExecutionState et retourne l'état PRÉCÉDENT (0 si échec).

    Ne lève pas : retourne 0 en cas d'erreur (le Core le traite comme échec).
    """
    try:
        kernel32 = ctypes.windll.kernel32
        kernel32.SetThreadExecutionState.argtypes = [ctypes.c_uint]
        kernel32.SetThreadExecutionState.restype = ctypes.c_uint
        return int(kernel32.SetThreadExecutionState(flags))
    except Exception:
        return 0


def info() -> dict:
    """Version Windows + architecture, réelles. Retourne des dicts vides si
    non disponible (jamais inventé)."""
    out = {}
    try:
        import platform
        out["os"] = platform.system()
        out["version"] = platform.release()
        out["build"] = platform.version()
        out["arch"] = platform.machine()
    except Exception:
        pass
    return out


def is_windows() -> bool:
    return sys.platform.startswith("win")


class AutoStart:
    """Démarrage de Meth avec Windows (clé Run de l'utilisateur, HKCU).

    ``command`` est le chemin de lancement : l'exe empaqueté (sys.executable)
    si PyInstaller, sinon ``pythonw.exe <script>``. Aucun admin requis.
    """

    def __init__(self, command: Optional[str] = None,
                 logger: Optional[Callable[[str, str], None]] = None) -> None:
        self._logger = logger
        self._command = command or _default_command()

    def log(self, level: str, msg: str) -> None:
        if self._logger:
            try:
                self._logger(level, msg)
            except Exception:
                pass

    def enabled(self) -> bool:
        """True si la clé Run contient Meth (état réel du registre)."""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                                winreg.KEY_READ) as key:
                value, _ = winreg.QueryValueEx(key, RUN_VALUE)
                return bool(value)
        except FileNotFoundError:
            return False
        except OSError:
            return False

    def enable(self) -> bool:
        """Active le démarrage avec Windows. Retourne True en cas de succès."""
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
                winreg.SetValueEx(key, RUN_VALUE, 0, winreg.REG_SZ,
                                  self._command)
            self.log("info", f"démarrage Windows activé: {self._command}")
            return True
        except OSError as exc:
            self.log("error", f"démarrage Windows: échec écriture registre: {exc}")
            return False

    def disable(self) -> bool:
        """Désactive le démarrage avec Windows (supprime la clé si présente)."""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                                winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, RUN_VALUE)
            self.log("info", "démarrage Windows désactivé")
            return True
        except FileNotFoundError:
            return True  # déjà absent : rien à faire
        except OSError as exc:
            self.log("error", f"démarrage Windows: échec suppression: {exc}")
            return False

    def set(self, on: bool) -> bool:
        return self.enable() if on else self.disable()


def _default_command() -> str:
    """Commande de lancement au démarrage : l'exe empaqueté si dispo, sinon
    pythonw + le script courant (aucun admin, aucune fenêtre console)."""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    # Mode source : pythonw.exe <chemin absolu de l'app> (fenêtre invisible).
    here = os.path.dirname(os.path.abspath(__file__))
    # remonte de src/Windows → racine Meth
    root = os.path.dirname(os.path.dirname(here))
    script = os.path.join(root, "run.py")
    if not os.path.isfile(script):
        script = os.path.abspath(sys.argv[0] if sys.argv else "meth.py")
    pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    launcher = pythonw if os.path.isfile(pythonw) else sys.executable
    return f'"{launcher}" "{script}"'
