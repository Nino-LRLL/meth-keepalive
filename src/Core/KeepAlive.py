"""Meth Core — KeepAlive.

Le moteur qui « empêche Windows de dormir » pendant que l'IA travaille.

Mécanisme natif :
    SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)

- ``ES_SYSTEM_REQUIRED`` empêche la veille SYSTÈME (le PC reste actif).
- ``ES_DISPLAY_REQUIRED`` n'est PAS utilisé : l'écran peut (et doit)
  s'éteindre — Meth ne garde pas l'écran allumé (capot fermé → écran off).
- Windows réinitialise automatiquement l'état d'exécution à la mort du
  processus (crash, arrêt, redémarrage) : le FAIL-SAFE est natif, aucun
  état dangereux ne peut persister. Meth restaure en plus explicitement
  l'état normal à la désactivation et au shutdown propre.

Ce module est volontairement indépendant de l'API Windows : l'exécution
réelle est injectée (``set_exec_state``) pour être testable sans Windows.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Optional

# États d'exécution Windows (constantes documentées par Microsoft).
ES_SYSTEM_REQUIRED = 0x00000001
ES_CONTINUOUS = 0x80000000
ES_OFF = ES_CONTINUOUS  # relâche les demandes (état normal)

# Type du setter injecté : reçoit les flags, retourne les flags précédents.
ExecStateFn = Callable[[int], int]


@dataclass
class KeepAlive:
    """Moteur ON/OFF de Meth.

    ``set_exec_state`` : fonction qui appelle SetThreadExecutionState (ou un
    mock dans les tests). ``logger`` : callable(level, message) optionnel.

    Comportement :
      - ``activate()``  → demande ES_SYSTEM_REQUIRED (Windows reste actif,
        écran libre de s'éteindre). Mémorise l'état précédent.
      - ``deactivate()`` → restaure l'état précédent (ES_CONTINUOUS seul).
      - idempotent : activer deux fois ne casse rien, désactiver deux fois
        non plus. ``state`` reflète l'état RÉEL demandé à Windows.
    """

    set_exec_state: ExecStateFn
    logger: Optional[Callable[[str, str], None]] = None

    _active: bool = False
    _last_flags: Optional[int] = None

    def log(self, level: str, msg: str) -> None:
        if self.logger:
            try:
                self.logger(level, msg)
            except Exception:
                pass

    @property
    def active(self) -> bool:
        return self._active

    def activate(self) -> bool:
        """Active Meth : demande à Windows de rester actif. Idempotent."""
        if self._active:
            self.log("debug", "activate(): déjà actif, rien à faire")
            return True
        try:
            previous = self.set_exec_state(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
        except Exception as exc:  # pragma: no cover - dépend de la plateforme
            self.log("error", f"activate(): échec SetThreadExecutionState: {exc}")
            return False
        if not previous:
            self.log("error", "activate(): Windows a refusé la demande (0)")
            return False
        self._active = True
        self._last_flags = previous
        self.log("info", "METH ON — Windows reste actif (ES_SYSTEM_REQUIRED)")
        return True

    def deactivate(self) -> bool:
        """Désactive Meth : restaure le comportement normal de Windows."""
        if not self._active:
            self.log("debug", "deactivate(): déjà inactif, rien à faire")
            return True
        try:
            # ES_CONTINUOUS seul = relâche toutes les demandes d'exécution.
            self.set_exec_state(ES_OFF)
        except Exception as exc:  # pragma: no cover
            self.log("error", f"deactivate(): échec SetThreadExecutionState: {exc}")
            return False
        self._active = False
        self._last_flags = None
        self.log("info", "METH OFF — Windows reprend son comportement normal")
        return True

    def shutdown(self) -> None:
        """Arrêt propre : restaure TOUJOURS l'état normal (fail-safe)."""
        self.log("debug", "shutdown(): restauration fail-safe")
        try:
            self.set_exec_state(ES_OFF)
        except Exception:
            pass
        self._active = False
        self._last_flags = None

    def restore_previous(self) -> Optional[int]:
        """Fail-safe explicite : restaure l'état précédent si mémorisé."""
        if self._last_flags is not None and self._last_flags != ES_OFF:
            try:
                self.set_exec_state(self._last_flags)
            except Exception:
                return None
        return self._last_flags


@dataclass
class Session:
    """Session de travail (préparée pour V0.2, déjà structurée).

    Une future IA pourra déclarer : « je travaille encore » (heartbeat).
    La V0 reste sur un simple ON/OFF, mais l'objet existe et est testé.
    """

    owner: str
    reason: str = ""
    priority: str = "normal"  # low | normal | high
    started_at: float = field(default_factory=time.time)
    heartbeat_at: float = field(default_factory=time.time)
    duration_s: Optional[float] = None  # None = illimité (V0)

    def heartbeat(self) -> None:
        self.heartbeat_at = time.time()

    @property
    def expired(self) -> bool:
        if self.duration_s is None:
            return False
        return time.time() - self.started_at > self.duration_s

    @property
    def idle_since(self) -> float:
        return time.time() - self.heartbeat_at
