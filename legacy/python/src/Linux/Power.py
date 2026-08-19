"""Meth Linux — Power.

Lit l'état d'alimentation RÉEL depuis sysfs (``/sys/class/power_supply``) :
- alimentation : SECTEUR / BATTERIE / INCONNU (jamais inventé) ;
- niveau batterie 0-100 (ou INCONNU si le système ne l'expose pas).

Le polling est événementiel et léger : un timer interne appelle
``refresh()``, et les abonnés (UI, tray) sont notifiés via ``listeners``
quand un état CHANGE réellement (pas à chaque tick). Même contrat que
``src.Windows.Power``.
"""
from __future__ import annotations

import glob
import os
import time
from typing import Callable, List, Optional


def read_power_status(base: str = "/") -> dict:
    """Lit /sys/class/power_supply sous ``base`` (tests : base = tmp).

    Retourne ``{"ac": ..., "battery_percent": ..., "available": ...}``.
    Ne lève jamais : une panne d'accès → INCONNU honnête.
    """
    ac = "INCONNU"
    battery: Optional[int] = None
    try:
        pattern = os.path.join(base, "sys", "class", "power_supply", "*")
        for path in glob.glob(pattern):
            try:
                with open(os.path.join(path, "type")) as f:
                    kind = f.read().strip()
            except OSError:
                continue
            if kind == "Mains":
                try:
                    with open(os.path.join(path, "online")) as f:
                        online = f.read().strip()
                except OSError:
                    continue
                ac = "SECTEUR" if online == "1" else "BATTERIE"
            elif kind == "Battery":
                try:
                    with open(os.path.join(path, "capacity")) as f:
                        cap = f.read().strip()
                    battery = int(cap)
                    if battery < 0:
                        battery = 0
                    elif battery > 100:
                        battery = 100
                except (OSError, ValueError):
                    continue
    except Exception:  # pragma: no cover - défense contre les sysfs bizarres
        pass
    return {
        "ac": ac,
        "battery_percent": battery,
        "available": ac != "INCONNU" or battery is not None,
    }


class Power:
    """État d'alimentation réel + notifications de changement.

    ``status_reader`` est injectable (tests) ; par défaut
    ``read_power_status()``. ``interval_s`` : cadence de polling (défaut 2 s
    — léger, événementiel : aucun coût CPU entre deux lectures).
    """

    def __init__(self, status_reader: Optional[Callable[[], dict]] = None,
                 interval_s: float = 2.0,
                 logger: Optional[Callable[[str, str], None]] = None) -> None:
        self._reader = status_reader or read_power_status
        self._interval = interval_s
        self._logger = logger
        self._listeners: List[Callable[[dict], None]] = []
        self._status: dict = {"ac": "INCONNU", "battery_percent": None,
                              "available": False}
        self._last_check = 0.0
        self._stopped = False

    def log(self, level: str, msg: str) -> None:
        if self._logger:
            try:
                self._logger(level, msg)
            except Exception:
                pass

    def on_change(self, listener: Callable[[dict], None]) -> None:
        """Abonne un callable appelé quand l'état change réellement."""
        if listener not in self._listeners:
            self._listeners.append(listener)

    def status(self) -> dict:
        return dict(self._status)

    def refresh(self) -> dict:
        """Relit l'état système et notifie si changement. Idempotent."""
        raw = self._reader()
        changed = (raw.get("ac") != self._status.get("ac")
                   or raw.get("battery_percent") != self._status.get("battery_percent"))
        self._status = raw
        if changed:
            self.log("info", f"alimentation: {raw.get('ac')}"
                             f"{' (' + str(raw.get('battery_percent')) + '%)' if raw.get('battery_percent') is not None else ''}")
            for listener in list(self._listeners):
                try:
                    listener(dict(self._status))
                except Exception:
                    pass
        return self.status()

    def tick(self) -> None:
        """À appeler par la boucle UI (léger) : ne relit que si le délai est
        écoulé, jamais plus souvent que ``interval_s``."""
        now = time.time()
        if now - self._last_check >= self._interval:
            self._last_check = now
            self.refresh()

    def stop(self) -> None:
        self._stopped = True
