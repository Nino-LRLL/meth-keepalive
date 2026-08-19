# Changelog

All notable changes to Meth are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Linux : backend natif** (`src/Linux/`) — Meth fonctionne aussi sur les
  PC Linux (pas macOS) :
  - keep-alive via **systemd-inhibit** (`--what=sleep:handle-lid-switch
    --mode=block`) : capot fermé → l'écran s'éteint normalement, le PC
    reste éveillé, tout ce qui tourne continue. Fail-safe natif : si Meth
    meurt, systemd relâche l'inhibiteur. Sans systemd → refus honnête.
  - alimentation lue depuis sysfs (`/sys/class/power_supply`) ;
  - capot lu depuis ACPI (`/proc/acpi/button/lid`), INCONNU si absent ;
  - autostart via `~/.config/autostart/meth.desktop` ;
  - instance unique via lockfile flock (`/tmp/meth-singleton.lock`).
- **`src/backends.py`** : dispatcher de plateforme (Windows / Linux / autre
  → repli honnête : jamais de keep-alive simulé). `App`, `run.py` et
  `Config` passent par cette couche.
- **Tests Linux** (fixtures sysfs/proc, systemd mocké) + tests backends —
  la suite passe maintenant **à la fois sur Windows et Linux** (CI
  `ubuntu-latest` réparée : 3 modules ne s'importaient pas sans `winreg`).
- **Config** : `$XDG_CONFIG_HOME/meth/config.json` sur Linux (au lieu de
  `%APPDATA%`).

### Changed

- **UI purifiée — métal MAT (style Apple sobre)** : le disque ON/OFF n'est
  plus « bombé » brillant — dégradé radial à faible contraste, simple
  liseré de lumière sur l'arête supérieure, anneau usiné fin ; le disque
  reste gris métal dans les DEUX états, le vert est réduit à un point +
  un liseré d'anneau + le texte ACTIF ; fond à contraste adouci ; pulse
  ON encore plus discret (halo neutre, liseré vert à peine oscillant).
- **Honnêteté d'affichage** : le sous-texte du disque OFF passe de
  « · VEILLE · » à « · NORMAL · » (Meth ne sait pas si le PC dort — le
  PC est ACTIF ou NORMAL, jamais VEILLE). Version affichée dynamiquement
  (plus de « v0.1.0 » codé en dur), libellé paramètres neutre
  (« au démarrage » au lieu de « avec Windows » — Meth tourne aussi
  sous Linux).
- **UI épurée style Apple (gris / noir métal)** : palette neutre sans teinte
  bleue (noirs profonds, gris Apple `#2c2c2e` / `#8e8e93` / `#f5f5f7`),
  disque ON/OFF en métal bombé (dégradé radial + reflet supérieur, anneau
  fin), header « M E T H » centré en lettres espacées, lignes d'état façon
  Réglages Apple (séparateurs fins, pastille + texte), fenêtre 320×458.
- **Barre de titre sombre (DWM)** sur la fenêtre principale ET les
  paramètres, appliquée à chaque affichage réel (`<Map>`) — plus de barre
  blanche qui cassait le look sombre.
- **Palette partagée** : les paramètres importent les couleurs de
  MainWindow (source unique, fini la dérive de teinte entre fenêtres).
- Social preview + captures README régénérées dans le même langage visuel.

## [0.1.0] - 2026-08-18

### Added

- Compact 320×460 mini window (modern dark UI, canvas ON/OFF button with
  glowing pulsing halo).
- One-click ON/OFF keep-alive button (Canvas) with a light pulse animation
  (respects hidden window, stops when hidden).
- Native keep-alive via `SetThreadExecutionState`
  (`ES_SYSTEM_REQUIRED` + `ES_CONTINUOUS`) — the screen turns off normally,
  Windows stays awake.
- System Tray: close-to-tray (window hides, Meth keeps running), tray icon
  reflects ON/OFF, dynamic "Activate/Deactivate" menu label, "Quit" really
  stops Meth.
- Lid detection via `RegisterPowerSettingNotification`
  (`GUID_LIDSWITCH_STATE_CHANGE`): open / closed / unknown (honest).
- Power state detection via `GetSystemPowerStatus`: AC / battery / unknown.
- Settings page: start with Windows (registry), show in tray,
  AC-only enforcement (honest refusal on battery with visible notice).
- Fail-safe: Windows clears the execution state when Meth exits/crashes;
  explicit restore on shutdown.
- JSON config in `%APPDATA%\Meth\config.json` (no permanent Windows changes).
- Single-instance guard (named mutex) — launching Meth twice exits the second
  instance cleanly.
- "Quit" button in the main window (available even when the tray is
  disabled).
- 56 unit tests (Windows API mocked) + real API integration test.
- English and French README, SECURITY.md, CONTRIBUTING.md,
  CODE_OF_CONDUCT.md, MIT LICENSE, docs/ARCHITECTURE.md.
- GitHub Actions CI: unit tests on Windows + Linux, portable build.
- Packaging: PyInstaller spec (portable exe + build scripts).

### Fixed

- **Lid detection silently broken on 64-bit** — `LRESULT` is a 64-bit
  `LONG_PTR`; the WndProc used `c_long`, so `CreateWindowExW` failed silently
  and the lid state stayed "unknown" forever. Fixed with `c_ssize_t` +
  full ctypes signatures (verified on real hardware).
- **Closing the settings window hid the main window** — `Settings._close`
  called the main window's close handler. Now `on_settings_close` only
  touches the settings.
- **Opening settings twice crashed** — after destroy, `deiconify()` raised
  TclError. Now the settings window is rebuilt cleanly.
- **"PC: VEILLE" was dishonest** — the PC is not necessarily asleep when
  Meth is OFF. Now shows ACTIF / NORMAL.
- **`ac_only` was decorative** — now enforced: activation on battery is
  refused with an honest on-screen notice.
- **Tray menu label never updated** — pystray requires callable item texts;
  the Activate/Deactivate label now reflects the real state.
- **Invisible Meth when tray disabled** — closing the window now minimizes
  (taskbar) instead of hiding, so Meth is never lost.
- **Duplicate processes** — single-instance mutex prevents two Meth
  instances fighting over the execution state.
- **Lid thread cleanup** — `stop()` now joins the thread and destroys the
  hidden window + unregisters the power notification.

### Security

- Minimum-privilege: never requests admin, never fakes input, never touches
  hardware protections, no network access.
