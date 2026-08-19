"""Tests de la couche Windows/Power — lecture mockée, notifications."""
from __future__ import annotations

import unittest

from helpers import FakeLogger
from src.Windows.Power import Power


class TestPower(unittest.TestCase):
    def test_statut_initial_inconnu_avant_lecture(self) -> None:
        p = Power(status_reader=lambda: {"ac": "INCONNU", "battery_percent": None,
                                         "available": False})
        self.assertEqual(p.status()["ac"], "INCONNU")

    def test_refresh_lit_l_etat_reel(self) -> None:
        p = Power(status_reader=lambda: {"ac": "SECTEUR", "battery_percent": 100,
                                         "available": True})
        st = p.refresh()
        self.assertEqual(st["ac"], "SECTEUR")
        self.assertEqual(st["battery_percent"], 100)

    def test_changement_notifie_les_abonnes(self) -> None:
        seen = []
        states = iter([
            {"ac": "BATTERIE", "battery_percent": 80, "available": True},
            {"ac": "SECTEUR", "battery_percent": 80, "available": True},
        ])
        p = Power(status_reader=lambda: next(states))
        p.on_change(lambda st: seen.append(st["ac"]))
        p.refresh()   # BATTERIE → notification
        p.refresh()   # SECTEUR → notification
        self.assertEqual(seen, ["BATTERIE", "SECTEUR"])

    def test_aucune_notification_sans_changement(self) -> None:
        seen = []
        p = Power(status_reader=lambda: {"ac": "SECTEUR", "battery_percent": 100,
                                         "available": True})
        p.on_change(lambda st: seen.append(st["ac"]))
        p.refresh()
        p.refresh()  # même état → aucune notification
        self.assertEqual(len(seen), 1)

    def test_tick_polling_leger_respecte_l_intervalle(self) -> None:
        calls = {"n": 0}
        def reader():
            calls["n"] += 1
            return {"ac": "SECTEUR", "battery_percent": 100, "available": True}
        p = Power(status_reader=reader, interval_s=3600.0)
        p.tick()  # première lecture
        p.tick()  # trop tôt → aucune relecture
        self.assertEqual(calls["n"], 1)

    def test_batterie_inconnue_expose_none(self) -> None:
        p = Power(status_reader=lambda: {"ac": "BATTERIE", "battery_percent": None,
                                         "available": True})
        self.assertIsNone(p.refresh()["battery_percent"])


if __name__ == "__main__":
    unittest.main()
