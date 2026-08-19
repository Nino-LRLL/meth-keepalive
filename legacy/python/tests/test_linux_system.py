"""Tests de la couche Linux/System.

- ``set_exec_state`` : systemd-inhibit mocké (aucun appel système réel) ;
- ``AutoStart`` : ~/.config/autostart factice dans un répertoire temporaire ;
- ``_default_command`` : contient run.py + --tray.
"""
from __future__ import annotations

import importlib
import os
import sys
import tempfile
import unittest
from unittest import mock

import src.Linux.System as System


class FakeProc:
    def __init__(self) -> None:
        self.killed = False
        self._poll = None

    def poll(self):
        return self._poll

    def terminate(self) -> None:
        self.killed = True
        self._poll = 15


def _reset_proc() -> None:
    System._proc = None


class TestSetExecState(unittest.TestCase):
    def tearDown(self) -> None:
        _reset_proc()

    def test_sans_systemd_inhibit_refus_honnete(self) -> None:
        with mock.patch.object(System.shutil, "which", return_value=None), \
                mock.patch.object(System.subprocess, "Popen") as popen:
            rc = System.set_exec_state(System.ES_CONTINUOUS | System.ES_SYSTEM_REQUIRED)
            self.assertEqual(rc, 0, "pas de systemd → refus, jamais de contournement")
            popen.assert_not_called()

    def test_activation_lance_systemd_inhibit(self) -> None:
        _reset_proc()
        proc = FakeProc()
        with mock.patch.object(System.shutil, "which",
                               return_value="/usr/bin/systemd-inhibit"), \
                mock.patch.object(System.subprocess, "Popen",
                                  return_value=proc) as popen:
            rc = System.set_exec_state(System.ES_CONTINUOUS | System.ES_SYSTEM_REQUIRED)
            self.assertEqual(rc, 1)
            args = popen.call_args[0][0]
            self.assertEqual(args[0], "systemd-inhibit")
            self.assertIn("--what=sleep:handle-lid-switch", args)
            self.assertIn("--mode=block", args)
            # `sleep infinity` : le processus doit rester vivant (fail-safe
            # natif : s'il meurt, systemd relâche l'inhibiteur).
            self.assertEqual(args[-2:], ["sleep", "infinity"])

    def test_activation_est_idempotente(self) -> None:
        _reset_proc()
        proc = FakeProc()
        with mock.patch.object(System.shutil, "which",
                               return_value="/usr/bin/systemd-inhibit"), \
                mock.patch.object(System.subprocess, "Popen",
                                  return_value=proc) as popen:
            System.set_exec_state(System.ES_CONTINUOUS | System.ES_SYSTEM_REQUIRED)
            System.set_exec_state(System.ES_CONTINUOUS | System.ES_SYSTEM_REQUIRED)
            self.assertEqual(popen.call_count, 1, "déjà actif → aucun nouveau process")

    def test_desactivation_termine_le_process(self) -> None:
        _reset_proc()
        proc = FakeProc()
        with mock.patch.object(System.shutil, "which",
                               return_value="/usr/bin/systemd-inhibit"), \
                mock.patch.object(System.subprocess, "Popen",
                                  return_value=proc):
            System.set_exec_state(System.ES_CONTINUOUS | System.ES_SYSTEM_REQUIRED)
            self.assertTrue(System._inhibit_alive())
            rc = System.set_exec_state(System.ES_OFF)
            self.assertEqual(rc, 1)
            self.assertTrue(proc.killed, "terminer le process relâche l'inhibiteur")
            self.assertFalse(System._inhibit_alive())

    def test_echou_lancement_retourne_zero(self) -> None:
        _reset_proc()
        with mock.patch.object(System.shutil, "which",
                               return_value="/usr/bin/systemd-inhibit"), \
                mock.patch.object(System.subprocess, "Popen",
                                   side_effect=OSError("no")):
            rc = System.set_exec_state(System.ES_CONTINUOUS | System.ES_SYSTEM_REQUIRED)
            self.assertEqual(rc, 0)


class TestAutoStart(unittest.TestCase):
    def test_enable_disable_dans_dossier_factice(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            System.AutoStart.AUTOSTART_DIR = os.path.join(tmp, "autostart")
            System.AutoStart.AUTOSTART_FILE = os.path.join(
                System.AutoStart.AUTOSTART_DIR, "meth.desktop")
            try:
                autostart = System.AutoStart(command="/usr/bin/meth")
                self.assertFalse(autostart.enabled())
                self.assertTrue(autostart.set(True))
                self.assertTrue(autostart.enabled())
                with open(System.AutoStart.AUTOSTART_FILE, encoding="utf-8") as f:
                    content = f.read()
                self.assertIn("[Desktop Entry]", content)
                self.assertIn("Exec=/usr/bin/meth", content)
                self.assertTrue(autostart.set(False))
                self.assertFalse(autostart.enabled())
            finally:
                System.AutoStart.AUTOSTART_DIR = os.path.join(
                    os.path.expanduser("~"), ".config", "autostart")
                System.AutoStart.AUTOSTART_FILE = os.path.join(
                    System.AutoStart.AUTOSTART_DIR, "meth.desktop")

    def test_default_command_contient_run_et_tray(self) -> None:
        cmd = System._default_command()
        self.assertIn("run.py", cmd)
        self.assertIn("--tray", cmd)


class TestInfo(unittest.TestCase):
    def test_info_contient_os_linux(self) -> None:
        info = System.info()
        self.assertEqual(info.get("os"), "Linux")
        self.assertTrue(info.get("version"))


if __name__ == "__main__":
    unittest.main()
