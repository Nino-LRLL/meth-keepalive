"""Meth Windows — Power.

Lit l'état d'alimentation RÉEL via GetSystemPowerStatus (kernel32) :
- alimentation : SECTEUR / BATTERIE / INCONNU (jamais inventé) ;
- niveau batterie 0-100 (ou INCONNU si Windows ne l'expose pas).

Le polling est événementiel et léger : un timer interne appelle
``refresh()``, et les abonnés (UI, tray) sont notifiés via ``listeners``
quand un état CHANGE réellement (pas à chaque tick).

Écran libre d'être éteint : Meth ne touche JAMAIS à ES_DISPLAY_REQUIRED.
"""
from __future__ import annotations

import ctypes
import time
from ctypes import wintypes
from typing import Callable, List, Optional

# États d'alimentation (valeurs documentées GetSystemPowerStatus).
AC_ONLINE = 1
AC_OFFLINE = 0
AC_UNKNOWN = 255
BATTERY_UNKNOWN_PERCENT = 255

# Structure SYSTEM_POWER_STATUS (winnt.h).
class SYSTEM_POWER_STATUS(ctypes.Structure):
    _fields_ = [
        ("ACLineStatus", ctypes.c_ubyte),
        ("BatteryFlag", ctypes.c_ubyte),
        ("BatteryLifePercent", ctypes.c_ubyte),
        ("SystemStatusFlag", ctypes.c_ubyte),
        ("BatteryLifeTime", wintypes.DWORD),
        ("BatteryFullLifeTime", wintypes.DWORD),
    ]


def _default_status_reader() -> dict:
    """Lit l'état réel via GetSystemPowerStatus. Ne lève jamais."""
    sps = SYSTEM_POWER_STATUS()
    try:
        ok = ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(sps))
    except Exception:
        ok = 0
    if not ok:
        return {"ac": "INCONNU", "battery_percent": None, "available": False}
    ac_map = {AC_ONLINE: "SECTEUR", AC_OFFLINE: "BATTERIE", AC_UNKNOWN: "INCONNU"}
    percent = sps.BatteryLifePercent
    return {
        "ac": ac_map.get(sps.ACLineStatus, "INCONNU"),
        "battery_percent": None if percent == BATTERY_UNKNOWN_PERCENT else int(percent),
        "available": True,
    }


class Power:
    """État d'alimentation réel + notifications de changement.

    ``status_reader`` est injectable (tests) ; par défaut GetSystemPowerStatus.
    ``interval_s`` : cadence de polling (défaut 2 s — léger, événementiel :
    aucun coût CPU entre deux lectures).
    """

    def __init__(self, status_reader: Optional[Callable[[], dict]] = None,
                 interval_s: float = 2.0,
                 logger: Optional[Callable[[str, str], None]] = None) -> None:
        self._reader = status_reader or _default_status_reader
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
