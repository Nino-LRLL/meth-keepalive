# Meth — Architecture

Meth est volontairement petit et séparé en couches testables :

```
             UI (MainWindow + Tray + Settings)
                        ↓
                    Meth Core (KeepAlive)
                        ↓
             Windows Power API (ctypes, stdlib)
                        ↓
                      Windows
```

Les couches ne dépendent que vers le bas : l'UI ne connaît pas l'API
Windows, le Core ne connaît pas l'UI. Chaque brique est injectable (voir
`src/App.py`, la composition root).

## Structure

```
Meth/
├── src/
│   ├── Core/
│   │   └── KeepAlive.py      # état ON/OFF, activation, fail-safe, logs
│   ├── Windows/
│   │   ├── Power.py          # GetSystemPowerStatus (secteur/batterie)
│   │   ├── Lid.py            # RegisterPowerSettingNotification (capot)
│   │   └── System.py         # SetThreadExecutionState + AutoStart (registre)
│   ├── UI/
│   │   ├── MainWindow.py     # fenêtre compacte 300×400 (Tkinter)
│   │   ├── Tray.py           # pystray (icône, menu, quitter)
│   │   └── Settings.py       # paramètres (Tkinter)
│   ├── Config/
│   │   └── Config.py         # JSON dans %APPDATA%\Meth\config.json
│   └── App.py                # composition root + contrôleur
├── tests/                    # 45 tests (API Windows mockée)
├── docs/
├── .github/workflows/ci.yml  # CI : tests (Windows + Linux) + build exe
├── Meth.spec                 # PyInstaller (portable)
├── build.bat / build.sh      # scripts de build
├── run.py                    # point d'entrée
└── README.md / README.fr.md
```

## Couche Windows (ctypes, stdlib pur)

### Keep-alive — `SetThreadExecutionState`

- **ON** : `ES_CONTINUOUS | ES_SYSTEM_REQUIRED` → Windows reste actif, même
  capot fermé. L'écran s'éteint normalement (on ne demande pas
  `ES_DISPLAY_REQUIRED`).
- **OFF** : `ES_CONTINUOUS` seul (ou `ES_OFF`) → comportement normal.
- **Fail-safe natif** : Windows efface l'état d'exécution quand le processus
  qui l'a demandé meurt (crash, fin de session, reboot). Impossible de
  laisser Windows « coincé » en veille désactivée.

### Capot — `RegisterPowerSettingNotification`

Windows n'expose pas l'état du capot par une API de requête simple. Meth
s'abonne au GUID `GUID_LIDSWITCH_STATE_CHANGE` (documenté publiquement) avec
une fenêtre cachée qui reçoit `WM_POWERBROADCAST` /
`PBT_POWERSETTINGCHANGE`. Les données indiquent l'état (0 = fermé,
1 = ouvert).

**Important (64 bits)** : `LRESULT` est un `LONG_PTR` (64 bits). Le WNDPROC
et `DefWindowProcW` doivent utiliser `ctypes.c_ssize_t` — avec `c_long`,
`CreateWindowExW` échoue silencieusement et le capot reste « INCONNU ».

Honnêteté : si l'abonnement échoue (poste fixe, droits, API indisponible),
l'état reste « INCONNU » — jamais inventé.

### Alimentation — `GetSystemPowerStatus`

SECTEUR / BATTERIE (+ pourcentage) / INCONNUE. Polling léger toutes les 2 s
(événementiel, quasi aucun CPU).

### Démarrage Windows — `AutoStart`

Clé registre `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` — pas
d'admin nécessaire, uniquement si l'utilisateur coche l'option.

## Couche Core — `KeepAlive`

- `active` : état ON/OFF.
- `activate() / deactivate()` : appelle `set_exec_state` (injectable) et
  journalise.
- `shutdown()` : restauration fail-safe explicite (appelée au quit et à la
  fermeture).
- Logs : tout est journalisé (`[meth:level] msg`), chaque action est
  traçable.

## Couche UI

- **MainWindow** : ~300×400, sombre, bouton ON/OFF dominant, statuts capot /
  PC / énergie, bouton ⚙ paramètres. Fermer la fenêtre = cacher (Meth
  continue en tray).
- **Tray** (pystray) : icône reflète l'état ON/OFF, menu
  Ouvrir / Activer-Désactiver / Paramètres / À propos / Quitter. Quitter
  appelle `App.on_quit()` → restauration fail-safe + arrêt réel.
- **Settings** : démarrage avec Windows, affichage tray, (placeholder)
  secteur uniquement.

## Fail-safe (résumé)

| Événement | Comportement |
|---|---|
| Meth crash | Windows efface l'état d'exécution → comportement normal |
| Windows redémarre | comportement normal au boot |
| Session expirée | comportement normal |
| Quitter Meth | `shutdown()` restaure explicitement |
| Fenêtre fermée (X) | Meth continue en tray — rien n'est relâché |
