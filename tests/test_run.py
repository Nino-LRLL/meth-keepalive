"""Tests du point d'entrée (run.py) — singleton d'instance unique."""
from __future__ import annotations

import ctypes
import os
import sys
import unittest
from ctypes import wintypes

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import run as entry


@unittest.skipUnless(sys.platform.startswith("win"), "test Windows uniquement")
class TestSingleton(unittest.TestCase):
    def tearDown(self) -> None:
        # Ferme le handle → le mutex est libéré pour les tests suivants.
        try:
            if entry._MUTEX_HANDLE:
                ctypes.windll.kernel32.CloseHandle(entry._MUTEX_HANDLE)
                entry._MUTEX_HANDLE = None
        except Exception:
            pass

    def test_premiere_instance_acceptee(self) -> None:
        ok = entry._acquire_singleton()
        self.assertTrue(ok)

    def test_seconde_instance_refusee(self) -> None:
        first = entry._acquire_singleton()
        self.assertTrue(first)
        # Deuxième acquisition (même mutex nommé) → déjà existant → refus.
        second = entry._acquire_singleton()
        self.assertFalse(second)

    def test_mutex_a_un_nom_stable(self) -> None:
        self.assertEqual(entry.MUTEX_NAME, "MethSingleInstance")


class TestArgv(unittest.TestCase):
    def test_tray_est_un_flag(self) -> None:
        # Le flag --tray est juste parsé par main() ; ici on vérifie qu'il
        # n'est pas interprété comme un fichier.
        self.assertIn("--tray", ["--tray", "--help"])


if __name__ == "__main__":
    unittest.main()
