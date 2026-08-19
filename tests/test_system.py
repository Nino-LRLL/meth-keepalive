"""Tests de la couche Windows/System.

- ``set_exec_state`` est testé RÉELLEMENT (API native Windows, sans danger :
  on demande ES_SYSTEM_REQUIRED puis on relâche immédiatement) ;
- AutoStart : testé avec un registre simulé (aucune écriture réelle) ;
- info() : réel (Windows présent ici).

``winreg`` n'existe que sur Windows : sur Linux, tout le module est
skippé (le backend Linux a ses propres tests).
"""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from helpers import SRC  # noqa: F401  (assure src/ dans le path)

try:
    from src.Windows import System
    _WINDOWS_SYSTEM = True
except (ImportError, AttributeError):
    System = None
    _WINDOWS_SYSTEM = False


@unittest.skipUnless(_WINDOWS_SYSTEM and sys.platform.startswith("win"),
                     "backend Windows uniquement")
class TestSetExecStateWindows(unittest.TestCase):
    def test_demande_et_relache_sans_erreur(self) -> None:
        # ES_CONTINUOUS | ES_SYSTEM_REQUIRED puis ES_CONTINUOUS (relâche).
        prev = System.set_exec_state(System.ES_CONTINUOUS | System.ES_SYSTEM_REQUIRED)
        self.assertNotEqual(prev, 0, "SetThreadExecutionState doit réussir")
        System.set_exec_state(System.ES_OFF)  # restaure proprement
        prev2 = System.set_exec_state(System.ES_OFF)
        self.assertNotEqual(prev2, 0)

    def test_infos_windows_reelles(self) -> None:
        info = System.info()
        self.assertEqual(info.get("os"), "Windows")
        self.assertTrue(info.get("version"))


@unittest.skipUnless(_WINDOWS_SYSTEM and sys.platform.startswith("win"),
                      "backend Windows uniquement")
class TestAutoStart(unittest.TestCase):
    """AutoStart avec registre simulé (aucune écriture réelle)."""

    def _fake_winreg(self):
        import types
        store = {}

        class FakeKey:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def Close(self): pass

        class FakeHKEYType:
            pass

        def OpenKey(root, sub, res=0, access=0):
            if sub not in store:
                raise FileNotFoundError(sub)
            return FakeKey()

        def QueryValueEx(key, name):
            if name not in store:
                raise FileNotFoundError(name)
            return store[name], 1

        def CreateKey(root, sub):
            store.setdefault(sub, {})
            return FakeKey()

        def SetValueEx(key, name, res, typ, value):
            store.setdefault(name, {})
            store[name] = value
            return None

        def DeleteValue(key, name):
            store.pop(name, None)
            return None

        mod = types.SimpleNamespace(
            HKEY_CURRENT_USER="HKCU", KEY_READ=1, KEY_SET_VALUE=2,
            REG_SZ=1, OpenKey=OpenKey, QueryValueEx=QueryValueEx,
            CreateKey=CreateKey, SetValueEx=SetValueEx, DeleteValue=DeleteValue)
        return mod

    def test_commande_par_defaut_contient_un_lanceur(self) -> None:
        cmd = System._default_command()
        self.assertIn(".exe", cmd.lower() or "pythonw") or self.assertTrue(
            cmd.endswith(".py") or ".exe" in cmd.lower())

    def test_enable_disable_dans_registre_simule(self) -> None:
        import sys as _sys
        saved = _sys.modules.get("winreg")
        _sys.modules["winreg"] = self._fake_winreg()
        try:
            from src.Windows.System import AutoStart
            import winreg  # noqa: F401 (le module simulé)
            # Recharge la référence du module (il importe winreg à l'import).
            import importlib
            import src.Windows.System as syst
            importlib.reload(syst)
            AutoStart = syst.AutoStart
            autostart = AutoStart(command="C:/Meth/Meth.exe")
            self.assertFalse(autostart.enabled())
            self.assertTrue(autostart.set(True))
            self.assertTrue(autostart.enabled())
            self.assertTrue(autostart.set(False))
            self.assertFalse(autostart.enabled())
        finally:
            if saved is None:
                _sys.modules.pop("winreg", None)
            else:
                _sys.modules["winreg"] = saved


if __name__ == "__main__":
    unittest.main()
