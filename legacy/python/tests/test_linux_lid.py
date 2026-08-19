"""Tests de la couche Linux/Lid — fixtures /proc/acpi (aucun vrai matériel)."""
from __future__ import annotations

import os
import tempfile
import time
import unittest

from src.Linux.Lid import Lid, read_lid_state


def _make_lid_state(base: str, content: str) -> str:
    d = os.path.join(base, "proc", "acpi", "button", "lid", "LID0")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "state"), "w") as f:
        f.write(content)
    return base


class TestReadLidState(unittest.TestCase):
    def test_capot_ouvert(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _make_lid_state(tmp, "state:      open")
            self.assertEqual(read_lid_state(tmp), "OUVERT")

    def test_capot_ferme(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _make_lid_state(tmp, "state:      closed")
            self.assertEqual(read_lid_state(tmp), "FERMÉ")

    def test_abs_du_fichier_inconnu_honnete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(read_lid_state(tmp), "INCONNU")


class TestLidClass(unittest.TestCase):
    def test_etat_initial_inconnu(self) -> None:
        lid = Lid(reader=lambda: "INCONNU")
        self.assertEqual(lid.state, "INCONNU")

    def test_publish_change_l_etat_et_notifie(self) -> None:
        lid = Lid(reader=lambda: "INCONNU")
        seen: list = []
        lid.on_change(seen.append)
        lid._publish("OUVERT")
        self.assertEqual(lid.state, "OUVERT")
        self.assertEqual(seen, ["OUVERT"])

    def test_publish_deduplique_les_changements(self) -> None:
        lid = Lid(reader=lambda: "INCONNU")
        seen: list = []
        lid.on_change(seen.append)
        lid._publish("OUVERT")
        lid._publish("OUVERT")   # pas de changement → pas de notification
        self.assertEqual(seen, ["OUVERT"])
        lid._publish("FERMÉ")
        self.assertEqual(seen, ["OUVERT", "FERMÉ"])

    def test_publish_ignore_un_listener_qui_plante(self) -> None:
        lid = Lid(reader=lambda: "INCONNU")
        lid.on_change(lambda _st: (_ for _ in ()).throw(RuntimeError("boom")))
        lid._publish("FERMÉ")   # ne doit pas lever
        self.assertEqual(lid.state, "FERMÉ")

    def test_loop_public_l_etat_du_reader(self) -> None:
        lid = Lid(reader=lambda: "OUVERT", interval_s=0.05)
        lid.start()
        try:
            deadline = time.time() + 2.0
            while lid.state != "OUVERT" and time.time() < deadline:
                time.sleep(0.02)
            self.assertEqual(lid.state, "OUVERT")
        finally:
            lid.stop()

    def test_stop_arrete_le_thread(self) -> None:
        lid = Lid(reader=lambda: "OUVERT", interval_s=0.02)
        lid.start()
        thread = lid._thread
        lid.stop()
        self.assertFalse(thread.is_alive())


if __name__ == "__main__":
    unittest.main()
