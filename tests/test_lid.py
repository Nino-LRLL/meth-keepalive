"""Tests de la couche Windows/Lid (logique pure — l'API native est
enveloppée par ``_message_loop``, testée sur du vrai matériel).

Les imports Windows (WINFUNCTYPE…) n'existent que sur Windows : sur
Linux, tout le module est skippé (le backend Linux a ses propres tests).
"""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from helpers import SRC  # noqa: F401  (assure src/ dans le path)

try:
    from src.Windows import Lid
    from src.Windows.Lid import (LID_CLOSED, LID_OPEN,
                                 PBT_POWERSETTINGCHANGE,
                                 POWERBROADCAST_SETTING, WM_POWERBROADCAST)
    _WINDOWS_LID = True
except (AttributeError, ImportError):
    Lid = None
    _WINDOWS_LID = False


class FakeLogger:
    def __init__(self) -> None:
        self.entries: list = []
    def __call__(self, level: str, msg: str) -> None:
        self.entries.append((level, msg))


@unittest.skipUnless(_WINDOWS_LID and sys.platform.startswith("win"),
                      "backend Windows uniquement")
class TestLidState(unittest.TestCase):
    def test_etat_initial_inconnu(self) -> None:
        lid = Lid.Lid()
        self.assertEqual(lid.state, "INCONNU")

    def test_publish_change_l_etat_et_notifie(self) -> None:
        lid = Lid.Lid()
        seen: list = []
        lid.on_change(seen.append)
        lid._publish("OUVERT")
        self.assertEqual(lid.state, "OUVERT")
        self.assertEqual(seen, ["OUVERT"])

    def test_publish_deduplique_les_changements(self) -> None:
        lid = Lid.Lid()
        seen: list = []
        lid.on_change(seen.append)
        lid._publish("OUVERT")
        lid._publish("OUVERT")   # pas de changement → pas de notification
        self.assertEqual(seen, ["OUVERT"])
        lid._publish("FERMÉ")
        self.assertEqual(seen, ["OUVERT", "FERMÉ"])

    def test_publish_ignore_un_listener_qui_plante(self) -> None:
        lid = Lid.Lid()
        lid.on_change(lambda _st: (_ for _ in ()).throw(RuntimeError("boom")))
        lid._publish("FERMÉ")   # ne doit pas lever
        self.assertEqual(lid.state, "FERMÉ")

    def test_guid_lidswitch_a_la_bonne_taille(self) -> None:
        self.assertEqual(len(Lid.GUID_LIDSWITCH_STATE_CHANGE), 16)


@unittest.skipUnless(_WINDOWS_LID and sys.platform.startswith("win"),
                      "backend Windows uniquement")
class TestLidWndProc(unittest.TestCase):
    """Le WndProc : le message WM_POWERBROADCAST/PBT_POWERSETTINGCHANGE doit
    être traduit en état capot (0 = fermé, sinon ouvert)."""

    def _wnd_proc_fake(self, state: int):
        lid = Lid.Lid()
        # On mocke uniquement la publication pour isoler le parsing.
        lid._publish = lambda st: lid._set_state(st) if hasattr(lid, "_set_state") else None
        return lid

    def _simulate(self, lid: Lid.Lid, lid_state: int) -> str:
        """Construit un LPARAM valide (structure POWERBROADCAST_SETTING) et
        invoque _wnd_proc comme Windows le ferait."""
        import ctypes
        setting = POWERBROADCAST_SETTING()
        setting.PowerSetting = (ctypes.c_byte * 16)(*Lid.GUID_LIDSWITCH_STATE_CHANGE)
        setting.DataLength = 4
        setting.Data = lid_state
        lparam = ctypes.cast(ctypes.pointer(setting), ctypes.c_void_p).value
        lid._wnd_proc(0, WM_POWERBROADCAST, PBT_POWERSETTINGCHANGE, lparam)
        return lid.state

    def test_capot_ferme(self) -> None:
        lid = Lid.Lid()
        self.assertEqual(self._simulate(lid, LID_CLOSED), "FERMÉ")

    def test_capot_ouvert(self) -> None:
        lid = Lid.Lid()
        self.assertEqual(self._simulate(lid, LID_OPEN), "OUVERT")

    def test_message_sans_rapport_ignore(self) -> None:
        lid = Lid.Lid()
        # Un message quelconque ne doit rien changer.
        lid._wnd_proc(0, 0x000F, 0, 0)  # WM_PAINT
        self.assertEqual(lid.state, "INCONNU")


if __name__ == "__main__":
    unittest.main()
