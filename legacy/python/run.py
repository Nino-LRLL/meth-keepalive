#!/usr/bin/env python3
"""Meth — point d'entrée (fenêtre + tray).

Usage :
    python run.py            # lance Meth (fenêtre + tray)
    python run.py --tray     # démarre directement dans le tray (silencieux)

Singleton multi-plateforme : un mutex Windows (MethSingleInstance) ou un
lockfile flock Linux (/tmp/meth-singleton.lock) empêche deux instances de
Meth de tourner en même temps — deux processus se battraient sur le
keep-alive. Une seconde instance s'arrête proprement.
"""
from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes

MUTEX_NAME = "MethSingleInstance"
ERROR_ALREADY_EXISTS = 183
_MUTEX_HANDLE = None

_LOCK_FILE = "/tmp/meth-singleton.lock"
_LOCK_HANDLE = None


def _acquire_singleton() -> bool:
    """Instance unique selon la plateforme. False si Meth tourne déjà."""
    if sys.platform.startswith("win"):
        return _acquire_windows_mutex()
    if sys.platform.startswith("linux"):
        return _acquire_linux_lock()
    # Autre plateforme : pas de mutex natif — repli permissif (honnête).
    return True


def _acquire_windows_mutex() -> bool:
    """Crée/ouvre le mutex d'instance unique. False si Meth tourne déjà."""
    global _MUTEX_HANDLE
    try:
        kernel32 = ctypes.windll.kernel32
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL,
                                          wintypes.LPCWSTR]
        handle = kernel32.CreateMutexW(None, False, MUTEX_NAME)
        _MUTEX_HANDLE = handle
        err = kernel32.GetLastError()
        if handle and err == ERROR_ALREADY_EXISTS:
            return False
        return bool(handle)
    except Exception:
        # Sur un système sans kernel32 (ex. tests hors Windows), on laisse
        # passer — le mutex est une garantie Windows uniquement.
        return True


def _acquire_linux_lock() -> bool:
    """Verrou flock non-bloquant sur /tmp. False si Meth tourne déjà.

    Le descripteur est conservé pour la vie du processus : la fermeture
    (ou la mort du process) libère le verrou automatiquement.
    """
    global _LOCK_HANDLE
    try:
        import fcntl
        f = open(_LOCK_FILE, "a+")
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            f.close()
            return False
        _LOCK_HANDLE = f
        return True
    except Exception:
        # Pas de fcntl (rare) : repli permissif — jamais de faux refus.
        return True


def main() -> int:
    # Ajoute src/ au path (indépendant de l'installation).
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(here, "src")
    if src not in sys.path:
        sys.path.insert(0, src)

    # Instance unique : Meth tourne déjà → on ne duplique pas le processus.
    if not _acquire_singleton():
        print("Meth tourne déjà (instance unique).")
        return 0

    from src.App import MethApp
    from src.Config.Config import Config
    from src.UI.MainWindow import MainWindow
    from src.UI.Settings import SettingsWindow
    from src.UI.Tray import Tray

    start_hidden = "--tray" in sys.argv

    app = MethApp(config=Config())
    window = MainWindow(controller=app)
    settings = SettingsWindow(controller=app)
    tray = Tray(controller=app)

    app.window = window
    app.settings = settings
    app.tray = tray

    # La fenêtre paramètres reste fermée au départ.
    settings.root.withdraw()

    app.start()
    tray.start()

    if start_hidden:
        window.hide()
    else:
        window.show()

    try:
        window.root.mainloop()
    except KeyboardInterrupt:
        app.on_quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
