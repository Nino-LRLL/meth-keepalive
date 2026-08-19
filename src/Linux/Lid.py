"""Meth Linux — Lid (détection du capot).

Lit l'état RÉEL du capot depuis ACPI (``/proc/acpi/button/lid/*/state``) :
- « state: open »   → OUVERT
- « state: closed » → FERMÉ

Pas de fichier (poste fixe, VM, noyau sans module ACPI) → INCONNU (honnête,
jamais inventé). Windows utilise un abonnement événementiel
(RegisterPowerSettingNotification) ; Linux expose l'état par requête →
polling léger (2 s) sur un thread daemon, même contrat que
``src.Windows.Lid`` (state, on_change, start, stop).
"""
from __future__ import annotations

import glob
import os
import threading
import time
from typing import Callable, List, Optional


def read_lid_state(base: str = "/") -> str:
    """Lit /proc/acpi/button/lid/*/state sous ``base`` (tests : base = tmp)."""
    try:
        pattern = os.path.join(base, "proc", "acpi", "button", "lid", "*", "state")
        for path in glob.glob(pattern):
            try:
                with open(path) as f:
                    txt = f.read().strip().lower()
            except OSError:
                continue
            if "closed" in txt:
                return "FERMÉ"
            if "open" in txt:
                return "OUVERT"
    except Exception:  # pragma: no cover - défense /proc inhabituel
        pass
    return "INCONNU"


class Lid:
    """État du capot (best-effort, honnête).

    ``listener(state)`` reçoit "OUVERT" / "FERMÉ" / "INCONNU" à chaque
    changement. ``start()`` lance le thread de polling ; ``stop()`` arrête
    proprement. ``state`` reflète le dernier état connu.
    """

    def __init__(self, reader: Optional[Callable[[], str]] = None,
                 interval_s: float = 2.0,
                 logger: Optional[Callable[[str, str], None]] = None) -> None:
        self._reader = reader or read_lid_state
        self._interval = interval_s
        self._logger = logger
        self._listeners: List[Callable[[str], None]] = []
        self._state: str = "INCONNU"
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def log(self, level: str, msg: str) -> None:
        if self._logger:
            try:
                self._logger(level, msg)
            except Exception:
                pass

    @property
    def state(self) -> str:
        return self._state

    def on_change(self, listener: Callable[[str], None]) -> None:
        if listener not in self._listeners:
            self._listeners.append(listener)

    def _publish(self, state: str) -> None:
        if state == self._state:
            return
        self._state = state
        self.log("info", f"capot: {state}")
        for listener in list(self._listeners):
            try:
                listener(state)
            except Exception:
                pass

    # -- cycle de vie ----------------------------------------------------------
    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._loop, name="MethLid", daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        # Lecture initiale immédiate, puis polling léger.
        while not self._stop_event.is_set():
            try:
                self._publish(self._reader())
            except Exception:  # pragma: no cover - ne lève jamais dans un thread
                self._publish("INCONNU")
            self._stop_event.wait(self._interval)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            try:
                self._thread.join(timeout=1.5)
            except Exception:
                pass
        self._thread = None
