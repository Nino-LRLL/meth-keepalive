"""Tests du dispatcher de plateformes (src/backends.py).

Vérifie que l'API commune existe sur toutes les plateformes et que le
repli « autre » (macOS/BSD…) est HONNÊTE : jamais de keep-alive simulé.
"""
from __future__ import annotations

import os
import sys
import unittest

from src import backends as plat
from src.backends import (_OtherAutoStart, _OtherLid, _OtherPower,
                          _other_set_exec_state)


class TestApiCommune(unittest.TestCase):
    def test_expose_l_api_commune(self) -> None:
        for name in ("PLATFORM", "set_exec_state", "info", "Power", "Lid",
                     "AutoStart", "backend_info"):
            self.assertTrue(hasattr(plat, name), f"{name} manquant")

    def test_plateforme_est_connue(self) -> None:
        self.assertIn(plat.PLATFORM, ("windows", "linux", "other"))

    def test_info_retourne_un_dict_reel(self) -> None:
        info = plat.info()
        self.assertIsInstance(info, dict)
        self.assertTrue(info.get("os"))

    def test_info_et_backend_info_retournent_un_dict(self) -> None:
        self.assertIsInstance(plat.backend_info(), dict)


class TestRepliAutre(unittest.TestCase):
    """Le backend « autre » (macOS…) est honnête : jamais de faux support."""

    def test_keepalive_indisponible(self) -> None:
        self.assertEqual(_other_set_exec_state(0x80000001), 0)

    def test_power_toujours_inconnu(self) -> None:
        p = _OtherPower()
        self.assertEqual(p.status()["ac"], "INCONNU")

    def test_lid_toujours_inconnu(self) -> None:
        lid = _OtherLid()
        self.assertEqual(lid.state, "INCONNU")

    def test_autostart_noop_honnete(self) -> None:
        a = _OtherAutoStart()
        self.assertFalse(a.enabled())
        self.assertFalse(a.enable())


if __name__ == "__main__":
    unittest.main()
