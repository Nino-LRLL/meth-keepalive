"""Tests de la couche Linux/Power — fixtures sysfs (aucun vrai matériel).

Le lecteur par défaut accepte une racine ``base`` : les tests montent un
``/sys/class/power_supply`` factice dans un répertoire temporaire.
"""
from __future__ import annotations

import os
import tempfile
import unittest

from src.Linux.Power import Power, read_power_status


def _make_sysfs(base: str, mains_online=None, battery_capacity=None) -> str:
    """Monte un /sys/class/power_supply factice sous ``base``."""
    psu = os.path.join(base, "sys", "class", "power_supply")
    if mains_online is not None:
        d = os.path.join(psu, "AC0")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "type"), "w") as f:
            f.write("Mains\n")
        with open(os.path.join(d, "online"), "w") as f:
            f.write(f"{mains_online}\n")
    if battery_capacity is not None:
        d = os.path.join(psu, "BAT0")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "type"), "w") as f:
            f.write("Battery\n")
        with open(os.path.join(d, "capacity"), "w") as f:
            f.write(f"{battery_capacity}\n")
    return base


class TestReadPowerStatus(unittest.TestCase):
    def test_secteur_sans_batterie(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _make_sysfs(tmp, mains_online=1)
            st = read_power_status(tmp)
            self.assertEqual(st["ac"], "SECTEUR")
            self.assertIsNone(st["battery_percent"])
            self.assertTrue(st["available"])

    def test_batterie_sur_secteur_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _make_sysfs(tmp, mains_online=0)
            st = read_power_status(tmp)
            self.assertEqual(st["ac"], "BATTERIE")

    def test_batterie_avec_pourcentage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _make_sysfs(tmp, battery_capacity=73)
            st = read_power_status(tmp)
            self.assertEqual(st["battery_percent"], 73)
            # pas de Mains → INCONNU, mais la batterie rend l'état disponible
            self.assertEqual(st["ac"], "INCONNU")
            self.assertTrue(st["available"])

    def test_secteur_et_batterie_combines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _make_sysfs(tmp, mains_online=1, battery_capacity=100)
            st = read_power_status(tmp)
            self.assertEqual(st["ac"], "SECTEUR")
            self.assertEqual(st["battery_percent"], 100)

    def test_pourcentage_borne_0_100(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _make_sysfs(tmp, battery_capacity=999)
            self.assertEqual(read_power_status(tmp)["battery_percent"], 100)
            _make_sysfs(tmp, battery_capacity=-5)
            self.assertEqual(read_power_status(tmp)["battery_percent"], 0)

    def test_aucun_sysfs_inconnu_honnete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            st = read_power_status(tmp)
            self.assertEqual(st["ac"], "INCONNU")
            self.assertIsNone(st["battery_percent"])
            self.assertFalse(st["available"])

    def test_capacity_invalide_ignoree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _make_sysfs(tmp, battery_capacity="?")
            st = read_power_status(tmp)
            self.assertIsNone(st["battery_percent"])


class TestPowerClass(unittest.TestCase):
    def test_statut_initial_inconnu_avant_lecture(self) -> None:
        p = Power(status_reader=lambda: {"ac": "INCONNU", "battery_percent": None,
                                         "available": False})
        self.assertEqual(p.status()["ac"], "INCONNU")

    def test_refresh_notifie_les_abonnes_sur_changement(self) -> None:
        seen: list = []

        def reader():
            return {"ac": "SECTEUR", "battery_percent": 100, "available": True}

        p = Power(status_reader=reader)
        p.on_change(seen.append)
        p.refresh()
        self.assertEqual(seen, [{"ac": "SECTEUR", "battery_percent": 100,
                                 "available": True}])

    def test_tick_respecte_l_intervalle(self) -> None:
        import time
        calls = {"n": 0}

        def reader():
            calls["n"] += 1
            return {"ac": "INCONNU", "battery_percent": None, "available": False}

        p = Power(status_reader=reader, interval_s=60.0)
        p.tick()          # premier tick → lecture
        p.tick()          # délai non écoulé → aucune lecture
        self.assertEqual(calls["n"], 1)


if __name__ == "__main__":
    unittest.main()
