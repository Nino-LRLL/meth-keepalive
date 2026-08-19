"""Helpers de test Meth — ajout du path src + petits faux (logger, API)."""
from __future__ import annotations

import os
import sys

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)


class FakeLogger:
    """Enregistre les messages (level, msg) — aucun affichage."""

    def __init__(self) -> None:
        self.entries: list = []

    def __call__(self, level: str, msg: str) -> None:
        self.entries.append((level, msg))


class FakeExecState:
    """Faux SetThreadExecutionState : enregistre les flags et renvoie un état
    précédent plausible (0x80000000 = ES_CONTINUOUS seul)."""

    def __init__(self, initial: int = 0x80000000) -> None:
        self.calls: list = []
        self.current = initial
        self.fail = False

    def __call__(self, flags: int) -> int:
        if self.fail:
            return 0
        self.calls.append(flags)
        previous = self.current
        self.current = flags
        return previous
