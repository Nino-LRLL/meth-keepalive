"""Tests du moteur KeepAlive (Core) — mocks, aucun Windows."""
from __future__ import annotations

import unittest

from helpers import FakeExecState, FakeLogger
from src.Core.KeepAlive import (ES_CONTINUOUS, ES_OFF, ES_SYSTEM_REQUIRED,
                                KeepAlive, Session)


class TestKeepAlive(unittest.TestCase):
    def setUp(self) -> None:
        self.exec = FakeExecState()
        self.logger = FakeLogger()
        self.ka = KeepAlive(set_exec_state=self.exec, logger=self.logger)

    def test_inactive_au_depart(self) -> None:
        self.assertFalse(self.ka.active)
        self.assertEqual(self.exec.calls, [])

    def test_activate_demande_es_system_required(self) -> None:
        ok = self.ka.activate()
        self.assertTrue(ok)
        self.assertTrue(self.ka.active)
        self.assertEqual(self.exec.calls, [ES_CONTINUOUS | ES_SYSTEM_REQUIRED])

    def test_activate_est_idempotent(self) -> None:
        self.ka.activate()
        self.ka.activate()  # second appel : aucun nouvel appel API
        self.assertEqual(len(self.exec.calls), 1)

    def test_deactivate_restaure_etat_normal(self) -> None:
        self.ka.activate()
        self.assertTrue(self.ka.deactivate())
        self.assertFalse(self.ka.active)
        self.assertEqual(self.exec.calls[-1], ES_OFF)

    def test_deactivate_quand_inactif_ne_casse_rien(self) -> None:
        self.assertTrue(self.ka.deactivate())
        self.assertEqual(self.exec.calls, [])

    def test_activate_echec_windows_refuse(self) -> None:
        self.exec.fail = True
        ok = self.ka.activate()
        self.assertFalse(ok)
        self.assertFalse(self.ka.active)

    def test_shutdown_restaure_toujours(self) -> None:
        self.ka.activate()
        self.ka.shutdown()
        self.assertFalse(self.ka.active)
        self.assertEqual(self.exec.calls[-1], ES_OFF)

    def test_shutdown_sans_activation_relache_quand_meme(self) -> None:
        # Fail-safe : le shutdown relâche TOUJOURS l'état (aucun risque
        # qu'un état actif persiste après la sortie de Meth).
        self.ka.shutdown()
        self.assertEqual(self.exec.calls, [ES_OFF])

    def test_restore_previous_rejoue_l_etat_memorise(self) -> None:
        # L'état précédent (avant activation) était ES_CONTINUOUS seul.
        self.ka.activate()
        prev = self.ka.restore_previous()
        self.assertIsNotNone(prev)


class TestSession(unittest.TestCase):
    def test_session_heartbeat_rafraichit(self) -> None:
        s = Session(owner="OpenCode", reason="compilation")
        before = s.heartbeat_at
        s.heartbeat()
        self.assertGreaterEqual(s.heartbeat_at, before)
        self.assertFalse(s.expired)

    def test_session_expire_apres_duree(self) -> None:
        s = Session(owner="test", duration_s=0.01)
        import time
        time.sleep(0.02)
        self.assertTrue(s.expired)


if __name__ == "__main__":
    unittest.main()
