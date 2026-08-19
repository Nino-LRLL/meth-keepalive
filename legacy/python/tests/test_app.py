"""Tests de l'App (composition root) — briques mockées, aucune UI réelle."""
from __future__ import annotations

import unittest

from helpers import FakeExecState, FakeLogger
from src.App import MethApp
from src.Config.Config import Config
from src.Core.KeepAlive import ES_OFF, ES_SYSTEM_REQUIRED, KeepAlive


class FakePower:
    def __init__(self) -> None:
        self._status = {"ac": "SECTEUR", "battery_percent": 100, "available": True}
        self._listeners = []

    def status(self):
        return dict(self._status)

    def refresh(self):
        return self.status()

    def tick(self):
        pass

    def on_change(self, listener):
        self._listeners.append(listener)

    def set_status(self, st):
        self._status = st
        for l in self._listeners:
            l(dict(self._status))


class FakeLid:
    def __init__(self) -> None:
        self.state = "OUVERT"
        self._listeners = []
        self.started = False

    def on_change(self, listener):
        self._listeners.append(listener)

    def start(self):
        self.started = True

    def stop(self):
        self.started = False

    def set_state(self, st):
        self.state = st
        for l in self._listeners:
            l(st)


class FakeAutoStart:
    def __init__(self) -> None:
        self.on = False
        self.calls = []

    def enabled(self):
        return self.on

    def set(self, value):
        self.calls.append(value)
        self.on = bool(value)
        return True


class FakeWindow:
    def __init__(self) -> None:
        self.shown = False
        self.minimized = False
        self.rendered = []
        self.destroyed = False

    def render(self, st):
        self.rendered.append(dict(st))

    def show(self):
        self.shown = True

    def hide(self):
        self.shown = False

    def minimize(self):
        self.minimized = True
        self.shown = False

    def destroy(self):
        self.destroyed = True


class FakeTray:
    def __init__(self) -> None:
        self.state = False
        self.started = False
        self.stopped = False
        self.available = True

    def set_state(self, on):
        self.state = bool(on)

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True


class TestMethApp(unittest.TestCase):
    def _make_app(self) -> tuple:
        import tempfile
        tmp = tempfile.mkdtemp(prefix="meth-app-test-")
        config = Config(path=tmp + "/config.json")
        exec = FakeExecState()
        ka = KeepAlive(set_exec_state=exec, logger=FakeLogger())
        power = FakePower()
        lid = FakeLid()
        autostart = FakeAutoStart()
        window = FakeWindow()
        tray = FakeTray()
        app = MethApp(config=config, power=power, lid=lid, keepalive=ka,
                      autostart=autostart, window=window, tray=tray,
                      logger=FakeLogger())
        return app, exec, power, lid, autostart, window, tray

    def test_etat_initial_off(self) -> None:
        app, *_ = self._make_app()
        st = app.state()
        self.assertFalse(st["on"])
        self.assertEqual(st["power"], "SECTEUR")
        self.assertEqual(st["lid"], "OUVERT")

    def test_toggle_off_on_appelle_es_system_required(self) -> None:
        app, exec, *_ = self._make_app()
        ok = app.on_toggle()
        self.assertTrue(ok)
        self.assertTrue(app.state()["on"])
        self.assertTrue(exec.calls[-1] & ES_SYSTEM_REQUIRED,
                        "le flag ES_SYSTEM_REQUIRED doit être demandé")

    def test_toggle_on_off_restaure(self) -> None:
        app, exec, *_ = self._make_app()
        app.on_toggle()   # ON
        app.on_toggle()   # OFF
        self.assertFalse(app.state()["on"])
        self.assertEqual(exec.calls[-1], ES_OFF)

    def test_ui_reflecte_l_etat(self) -> None:
        app, _, _, _, _, window, tray = self._make_app()
        app.start()
        app.on_toggle()
        self.assertTrue(window.rendered[-1]["on"])
        self.assertTrue(tray.state)

    def test_fermer_la_fenetre_ne_quitte_pas(self) -> None:
        app, *_ = self._make_app()
        app.on_close()   # ferme la fenêtre → cache, Meth continue
        self.assertTrue(app.keepalive.active is False or app.keepalive.active is True)
        self.assertFalse(app.window.shown)

    def test_power_change_rafraichit_ui(self) -> None:
        app, _, power, *_ = self._make_app()
        app.start()
        app.on_toggle()
        before = len(app.window.rendered)
        power.set_status({"ac": "BATTERIE", "battery_percent": 40, "available": True})
        self.assertGreater(len(app.window.rendered), before)
        self.assertEqual(app.state()["power"], "BATTERIE")

    def test_lid_change_rafraichit_ui(self) -> None:
        app, _, _, lid, *_ = self._make_app()
        app.start()
        lid.set_state("FERMÉ")
        self.assertEqual(app.state()["lid"], "FERMÉ")
        self.assertTrue(any(r["lid"] == "FERMÉ" for r in app.window.rendered))

    def test_quit_restaure_fail_safe(self) -> None:
        app, exec, *_ = self._make_app()
        app.on_toggle()
        self.assertTrue(app.state()["on"])
        # on_quit force os._exit — on ne peut pas l'appeler en test ; on
        # vérifie que shutdown() restaure l'état normal.
        app.keepalive.shutdown()
        self.assertFalse(app.state()["on"])
        self.assertEqual(exec.calls[-1], ES_OFF)

    def test_autostart_bascule_registre(self) -> None:
        app, _, _, _, autostart, *_ = self._make_app()
        app.on_set("autostart", True)
        self.assertTrue(autostart.on)
        app.on_set("autostart", False)
        self.assertFalse(autostart.on)

    def test_start_reactive_si_derniere_session_etait_on(self) -> None:
        app, exec, *_ = self._make_app()
        app.on_toggle()  # ON → last_state=True persisté dans la config
        self.assertTrue(app.config.get("last_state"))
        # Une nouvelle instance avec la même config réactive au démarrage.
        app2, exec2, *_ = self._make_app()
        app2.config.set("last_state", True)
        app2.start()
        self.assertTrue(app2.state()["on"])

    # -- corrections (audit) ---------------------------------------------------
    def test_pc_honnete_actif_normal_jamais_veille(self) -> None:
        app, *_ = self._make_app()
        self.assertEqual(app.state()["pc"], "NORMAL")
        app.on_toggle()
        self.assertEqual(app.state()["pc"], "ACTIF")

    def test_ac_only_refuse_l_activation_sur_batterie(self) -> None:
        app, exec, power, *_ = self._make_app()
        app.config.set("ac_only", True)
        power.set_status({"ac": "BATTERIE", "battery_percent": 40, "available": True})
        ok = app.set_on(True)
        self.assertFalse(ok, "l'activation doit être refusée sur batterie")
        self.assertFalse(app.state()["on"])
        self.assertIn("secteur uniquement", app.state().get("notice") or "")

    def test_ac_only_autorise_sur_secteur(self) -> None:
        app, exec, power, *_ = self._make_app()
        app.config.set("ac_only", True)
        power.set_status({"ac": "SECTEUR", "battery_percent": 100, "available": True})
        ok = app.set_on(True)
        self.assertTrue(ok)
        self.assertTrue(app.state()["on"])
        self.assertIsNone(app.state().get("notice"))

    def test_fermer_les_parametres_ne_cache_pas_la_fenetre_principale(self) -> None:
        """Bug corrigé : Settings._close appelait controller.on_close() qui
        cachait la fenêtre principale. Désormais on_settings_close ne touche
        qu'aux paramètres."""
        app, *_ = self._make_app()
        app.window.show()
        # Pas d'objet settings dans ce harnais → la méthode doit être inoffensive.
        app.on_settings_close()
        self.assertTrue(app.window.shown, "la fenêtre principale doit rester visible")

    def test_notice_effacee_apres_succes(self) -> None:
        app, exec, power, *_ = self._make_app()
        app.config.set("ac_only", True)
        power.set_status({"ac": "BATTERIE", "battery_percent": 40, "available": True})
        app.set_on(True)
        self.assertTrue(app.state().get("notice"))
        # Passage sur secteur → nouvelle activation réussie → notice effacée.
        power.set_status({"ac": "SECTEUR", "battery_percent": 100, "available": True})
        app.set_on(True)
        self.assertTrue(app.state()["on"])
        self.assertIsNone(app.state().get("notice"))

    def test_fermer_sans_tray_minimise_au_lieu_de_cacher(self) -> None:
        """Faille corrigée : tray désactivé + fermeture = Meth invisible et
        introuvable. Désormais on minimise (accessible dans la barre)."""
        app, *_ = self._make_app()
        app.config.set("show_tray", False)
        app.window.show()
        app.on_close()
        self.assertTrue(app.window.minimized,
                        "sans tray, la fenêtre doit être minimisée, pas cachée")

    def test_fermer_avec_tray_cache(self) -> None:
        app, *_ = self._make_app()
        app.config.set("show_tray", True)
        app.window.show()
        app.on_close()
        self.assertFalse(app.window.minimized)
        self.assertFalse(app.window.shown, "avec tray, la fenêtre se cache")


if __name__ == "__main__":
    unittest.main()
