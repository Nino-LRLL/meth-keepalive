"""Meth — couche de plateformes / backends (Windows + Linux, pas macOS).

Nommé ``backends`` (et non ``platform``) pour ne pas écraser le module
stdlib ``platform`` — src/ est dans le path.

Sélectionne l'implémentation native selon ``sys.platform`` :
- ``windows`` → ``src.Windows``  (SetThreadExecutionState, registre, …) ;
- ``linux``   → ``src.Linux``    (systemd-inhibit, sysfs, autostart) ;
- autre (macOS, BSD, …) → repli HONNÊTE : l'app tourne, mais le keep-alive
  est indisponible (``set_exec_state`` → 0, Power/Lid → INCONNU). Meth ne
  prétend jamais maintenir le système éveillé quand il n'a pas de moyen.

Expose l'API commune consommée par ``App`` et ``run.py`` :
    PLATFORM, set_exec_state, info, Power, Lid, AutoStart
"""
from __future__ import annotations

import platform as _pyplatform
import sys
from typing import Callable, Optional

if sys.platform.startswith("win"):
    PLATFORM = "windows"
elif sys.platform.startswith("linux"):
    PLATFORM = "linux"
else:
    PLATFORM = "other"


def info() -> dict:
    """Version système + architecture réelles (jamais inventées)."""
    out = {}
    try:
        out["os"] = _pyplatform.system()
        out["version"] = _pyplatform.release()
        out["arch"] = _pyplatform.machine()
    except Exception:
        pass
    return out


# ---------------------------------------------------------------------------
# Windows — backend natif existant
# ---------------------------------------------------------------------------
if PLATFORM == "windows":
    from .Windows import System as _WinSystem
    from .Windows.Lid import Lid
    from .Windows.Power import Power
    from .Windows.System import AutoStart

    set_exec_state = _WinSystem.set_exec_state
    _sys_info = _WinSystem.info

    def _backend_info() -> dict:
        return _sys_info()


# ---------------------------------------------------------------------------
# Linux — backend natif (systemd / sysfs / proc)
# ---------------------------------------------------------------------------
elif PLATFORM == "linux":
    from .Linux import System as _LinSystem
    from .Linux.Lid import Lid
    from .Linux.Power import Power
    from .Linux.System import AutoStart

    set_exec_state = _LinSystem.set_exec_state
    _sys_info = _LinSystem.info

    def _backend_info() -> dict:
        return _sys_info()


# ---------------------------------------------------------------------------
# Autre (macOS, BSD…) — repli honnête : pas de keep-alive natif.
# Les classes sont nommées (testables) puis affectées dans le branchement.
# ---------------------------------------------------------------------------

class _OtherPower:  # noqa: D101 - même contrat, état toujours INCONNU
    def __init__(self, status_reader: Optional[Callable[[], dict]] = None,
                 interval_s: float = 2.0,
                 logger: Optional[Callable[[str, str], None]] = None) -> None:
        self._status = {"ac": "INCONNU", "battery_percent": None,
                        "available": False}

    def on_change(self, listener: Callable[[dict], None]) -> None:
        pass

    def status(self) -> dict:
        return dict(self._status)

    def refresh(self) -> dict:
        return self.status()

    def tick(self) -> None:
        pass

    def stop(self) -> None:
        pass


class _OtherLid:  # noqa: D101 - état toujours INCONNU (honnête)
    state = "INCONNU"

    def on_change(self, listener: Callable[[str], None]) -> None:
        pass

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass


class _OtherAutoStart:  # noqa: D101 - no-op honnête (pas de démarrage auto)
    def __init__(self, command: Optional[str] = None,
                 logger: Optional[Callable[[str, str], None]] = None) -> None:
        self._logger = logger

    def log(self, level: str, msg: str) -> None:
        if self._logger:
            try:
                self._logger(level, msg)
            except Exception:
                pass

    def enabled(self) -> bool:
        return False

    def enable(self) -> bool:
        self.log("warning", "autostart indisponible sur cette plateforme")
        return False

    def disable(self) -> bool:
        return True

    def set(self, on: bool) -> bool:
        return self.enable() if on else self.disable()


def _other_set_exec_state(flags: int) -> int:
    """Indisponible hors Windows/Linux. Refus honnête (0), jamais simulé."""
    return 0


def _other_backend_info() -> dict:
    return {"os": _pyplatform.system(), "unsupported": True}


if PLATFORM == "other":
    set_exec_state = _other_set_exec_state
    Power = _OtherPower
    Lid = _OtherLid
    AutoStart = _OtherAutoStart

    def _backend_info() -> dict:
        return _other_backend_info()


def backend_info() -> dict:
    """Infos réelles du backend actif (Windows/Linux) ou repli."""
    try:
        return _backend_info()
    except Exception:  # pragma: no cover
        return info()
