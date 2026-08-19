"""Meth Linux — System.

Infrastructure système honnête :
- ``set_exec_state(flags)`` : keep-alive via **systemd-inhibit** (session,
  sans root) — bloque la veille (``sleep``) ET l'action fermeture du capot
  (``handle-lid-switch``) : capot fermé → l'écran s'éteint normalement mais
  le PC reste éveillé. L'écran n'est JAMAIS maintenu allumé (pas de
  ``ES_DISPLAY_REQUIRED``-like) : Meth ne garde que le système actif.
  Le processus enfant meurt avec Meth → systemd relâche l'inhibiteur
  automatiquement (fail-safe natif, comme Windows). Sans systemd →
  refus honnête (0), jamais de contournement.
- ``AutoStart`` : ~/.config/autostart/meth.desktop (démarrage avec la
  session, sans admin).
- ``info()`` : distribution + noyau réels (jamais inventés).

Aucune simulation d'utilisateur (pas de faux clavier/souris) — uniquement
des mécanismes natifs documentés.
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from typing import Callable, Optional

# Mêmes constantes que src.Windows.System — le contrat Core est partagé.
ES_SYSTEM_REQUIRED = 0x00000001
ES_CONTINUOUS = 0x80000000
ES_OFF = ES_CONTINUOUS

INHIBIT_WHATS = "sleep:handle-lid-switch"
INHIBIT_MODE = "block"
INHIBIT_WHY = "Meth — l'IA qui ne dort pas (travail en cours)"

# Processus systemd-inhibit en cours (None = aucune demande active).
_proc: Optional[subprocess.Popen] = None


def set_exec_state(flags: int) -> int:
    """Demande/relâche le keep-alive Linux.

    Même contrat que Windows : retourne l'état PRÉCÉDENT sous forme non
    nulle (le Core traite 0 comme un échec). ``flags & ES_SYSTEM_REQUIRED``
    → active l'inhibiteur ; sinon (ES_OFF) → le relâche.
    """
    global _proc
    if flags & ES_SYSTEM_REQUIRED:
        if _proc is not None and _proc.poll() is None:
            return 1  # déjà actif, idempotent
        if shutil.which("systemd-inhibit") is None:
            return 0  # pas de systemd : refus honnête, jamais de contournement
        try:
            _proc = subprocess.Popen(
                ["systemd-inhibit", "--what=" + INHIBIT_WHATS,
                 "--mode=" + INHIBIT_MODE, "--why=" + INHIBIT_WHY,
                 "sleep", "infinity"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return 1
        except Exception:
            _proc = None
            return 0
    # relâche (ES_OFF) : tuer le process libère l'inhibiteur chez systemd.
    if _proc is not None:
        try:
            _proc.terminate()
            try:
                _proc.wait(timeout=2)
            except Exception:
                pass
        except Exception:
            pass
        _proc = None
    return 1


def _inhibit_alive() -> bool:
    """True si l'inhibiteur systemd est réellement actif (process vivant)."""
    global _proc
    return _proc is not None and _proc.poll() is None


def info() -> dict:
    """Distribution + noyau réels (jamais inventés)."""
    out = {"os": "Linux"}
    try:
        out["version"] = platform.release()
        out["arch"] = platform.machine()
    except Exception:
        pass
    # Nom de la distribution depuis /etc/os-release (fiable, standard).
    try:
        with open("/etc/os-release") as f:
            for line in f:
                if line.startswith("PRETTY_NAME="):
                    out["distro"] = line.split("=", 1)[1].strip().strip('"')
                    break
    except OSError:
        pass
    return out


def is_windows() -> bool:
    return False


class AutoStart:
    """Démarrage de Meth avec la session (fichier ~/.config/autostart).

    ``command`` est le chemin de lancement : l'exe empaqueté (sys.executable)
    si PyInstaller, sinon ``python3 <script> --tray``. Aucun admin requis.
    """

    AUTOSTART_DIR = os.path.join(os.path.expanduser("~"), ".config", "autostart")
    AUTOSTART_FILE = os.path.join(AUTOSTART_DIR, "meth.desktop")

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
        """True si meth.desktop existe (état réel du dossier autostart)."""
        return os.path.isfile(self.AUTOSTART_FILE)

    def enable(self) -> bool:
        """Active le démarrage avec la session. Retourne True en cas de succès."""
        try:
            os.makedirs(self.AUTOSTART_DIR, exist_ok=True)
            content = (
                "[Desktop Entry]\n"
                "Type=Application\n"
                "Name=Meth\n"
                "Comment=Meth — l'IA qui ne dort pas (keep-alive)\n"
                "Exec=%s\n"
                "Terminal=false\n"
                "X-GNOME-Autostart-enabled=true\n" % self._command
            )
            with open(self.AUTOSTART_FILE, "w", encoding="utf-8") as f:
                f.write(content)
            self.log("info", f"autostart activé: {self.AUTOSTART_FILE}")
            return True
        except OSError as exc:
            self.log("error", f"autostart: échec écriture: {exc}")
            return False

    def disable(self) -> bool:
        """Désactive le démarrage (supprime meth.desktop si présent)."""
        try:
            if os.path.isfile(self.AUTOSTART_FILE):
                os.remove(self.AUTOSTART_FILE)
                self.log("info", "autostart désactivé")
            return True
        except OSError as exc:
            self.log("error", f"autostart: échec suppression: {exc}")
            return False

    def set(self, on: bool) -> bool:
        return self.enable() if on else self.disable()


def _default_command() -> str:
    """Commande de lancement au démarrage : l'exe empaqueté si dispo, sinon
    python3 + le script courant (--tray : démarre silencieux)."""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(os.path.dirname(here))
    script = os.path.join(root, "run.py")
    if not os.path.isfile(script):
        script = os.path.abspath(sys.argv[0] if sys.argv else "meth.py")
    return f'"{sys.executable}" "{script}" --tray'
