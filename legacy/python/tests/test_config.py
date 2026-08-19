"""Tests de la Config — fichier temporaire, aucune persistance réelle."""
from __future__ import annotations

import json
import os
import tempfile
import unittest

from helpers import FakeLogger
from src.Config.Config import Config


class TestConfig(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp(prefix="meth-config-test-")
        self.path = os.path.join(self.tmpdir, "config.json")

    def tearDown(self) -> None:
        if os.path.isdir(self.tmpdir):
            import shutil
            shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_defauts_sans_fichier(self) -> None:
        c = Config(path=self.path)
        self.assertFalse(c.get("autostart"))
        self.assertTrue(c.get("show_tray"))
        self.assertFalse(c.get("ac_only"))

    def test_set_persiste_et_recharge(self) -> None:
        c = Config(path=self.path)
        c.set("autostart", True)
        c2 = Config(path=self.path)  # recharge depuis le disque
        self.assertTrue(c2.get("autostart"))

    def test_fichier_corrompu_retombe_sur_les_defauts(self) -> None:
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.write("{pas du json")
        c = Config(path=self.path, logger=FakeLogger())
        self.assertFalse(c.get("autostart"))  # défauts, pas de crash

    def test_cle_inconnue_ignoree(self) -> None:
        c = Config(path=self.path)
        c.set("does_not_exist", True)
        self.assertIsNone(c.get("does_not_exist", None))

    def test_listener_notifie_le_changement(self) -> None:
        c = Config(path=self.path)
        seen = []
        c.on_change(lambda key, val: seen.append((key, val)))
        c.set("ac_only", True)
        self.assertEqual(seen, [("ac_only", True)])

    def test_set_meme_valeur_ne_notifie_pas(self) -> None:
        c = Config(path=self.path)
        seen = []
        c.on_change(lambda key, val: seen.append((key, val)))
        c.set("ac_only", False)  # déjà la valeur par défaut
        self.assertEqual(seen, [])


if __name__ == "__main__":
    unittest.main()
