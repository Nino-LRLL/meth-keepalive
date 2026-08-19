<p align="center">
  <img src="assets/social-preview.png" alt="Meth — Ton IA travaille. Meth garde le PC éveillé." width="100%">
</p>

<h1 align="center">Meth</h1>

<p align="center">
  <b>L'extension qui fait que ton IA ne dort jamais tant qu'elle a du travail.</b>
</p>

<p align="center">
  <a href="https://github.com/Nino-LRLL/meth-keepalive/actions/workflows/ci.yml">
    <img src="https://github.com/Nino-LRLL/meth-keepalive/actions/workflows/ci.yml/badge.svg" alt="CI">
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT">
  </a>
  <img src="https://img.shields.io/badge/Platform-Windows%20%2F%20Linux-0078d6.svg" alt="Windows 10/11 + Linux">
  <img src="https://img.shields.io/badge/Language-Rust-orange.svg" alt="100% Rust">
  <img src="https://img.shields.io/badge/Status-v0.3.0-34d868.svg" alt="v0.3.0">
</p>

<p align="center">
  <a href="README.md">🇬🇧 English version</a>
</p>

---

Ton IA travaille.

Windows veut dormir.

**Meth dit non.**

Ferme ton PC portable. L'écran s'éteint. Le PC reste actif. Ton IA continue
de travailler.

---

## ✨ Captures d'écran

| Meth OFF | Meth ON |
|:---:|:---:|
| ![Meth OFF](assets/screenshot-off.png) | ![Meth ON](assets/screenshot-on.png) |

## 🧠 Pourquoi ?

Les agents IA peuvent travailler pendant des heures. Windows met le PC
portable en veille quand on ferme le capot — tuant ton build, ton agent, ton
téléchargement ou ton serveur.

Meth garde le PC éveillé pendant que ton travail tourne encore.

**Un bouton. Aucun compte. Aucun cloud. Pas d'admin. Aucun hack de souris.**

## ⚙️ Comment ça marche

```
Capot fermé        Meth ON
    ↓                ↓
Écran éteint    Le système reste actif
    ↓                ↓
   └──────→  L'IA continue de travailler
```

Meth utilise les **API natives d'alimentation** :
- Windows : `SetThreadExecutionState(ES_SYSTEM_REQUIRED | ES_CONTINUOUS)`.
- Linux : un processus enfant `systemd-inhibit --what=sleep:handle-lid-switch
  --mode=block`.

L'écran **n'est pas** maintenu allumé : il s'éteint normalement, comme il
faut. Seule la veille système (et l'action capot fermé sur Linux) est
bloquée.

## 🚀 Démarrage rapide

### Portable (recommandé, Windows)

1. Télécharge **`Meth-Portable.zip`** depuis la page
   [Releases](https://github.com/Nino-LRLL/meth-keepalive/releases).
2. Décompresse n'importe où. Double-clic sur **`Meth.exe`**.
3. Clique sur **ON**. C'est fait.

Aucune installation. Pas de Python. Pas d'admin.

### Depuis les sources (Windows & Linux)

```bash
git clone https://github.com/Nino-LRLL/meth-keepalive.git
cd meth-keepalive
cargo build --release
./target/release/meth          # ouvre la fenêtre
./target/release/meth on       # CLI : activer
./target/release/meth off      # CLI : restaurer le comportement normal
./target/release/meth status   # CLI : état réel
```

## 🎮 Utilisation

1. Lance Meth.
2. Clique sur le gros bouton **ON**.
3. Ferme le PC portable. Écran éteint, PC actif, le travail continue.
4. Terminé ? Clique sur **OFF** — le PC retrouve son comportement normal.

La fenêtre affiche l'état **réel** : ON/OFF, source d'alimentation (secteur /
batterie / inconnue) et état du capot (ouvert / fermé / inconnu) — jamais
inventé.

## 🐧 Linux

Meth fonctionne sur **n'importe quel PC — Windows et Linux** (macOS n'est
pas supporté : Meth refuse honnêtement, il ne prétend jamais maintenir le
système éveillé là-bas).

- L'écran s'éteint normalement — seules la **veille système** et l'**action
  capot fermé** sont inhibées (ni suspension, ni hibernation).
- **Fail-safe natif** : systemd relâche l'inhibiteur dès que Meth s'arrête
  ou crashe — le PC ne peut jamais rester bloqué éveillé.
- Pas de `systemd` ? Meth **refuse honnêtement** (jamais de faux keep-alive).
- L'alimentation est lue depuis sysfs (`/sys/class/power_supply`), le capot
  depuis ACPI (`/proc/acpi/button/lid`, inconnu si absent), le démarrage
  auto via `~/.config/autostart/meth.desktop`, la config dans
  `$XDG_CONFIG_HOME/meth/`.

## 🗺️ Plateformes supportées (matrice honnête)

| OS | Keep-alive | Statut alim/capot | Autostart | Mécanisme |
|---|---|---|---|---|
| **Windows 10/11** | ✅ | ✅ | ✅ | `SetThreadExecutionState` + Win32 |
| **ReactOS** | ✅ | ✅ | ✅ | même API Win32 (cross-build `x86_64-pc-windows-gnu`) |
| **Arch Linux** | ✅ | ✅ | ✅ | systemd-inhibit |
| **Gentoo** | ✅ (systemd **ou** logind) | ✅ | ✅ | systemd-inhibit → repli logind D-Bus |
| **Slackware** | ✅ (avec elogind) | ✅ | ✅ | logind D-Bus (`org.freedesktop.login1`) |
| **Dragora** | ✅ (avec elogind) | ✅ | ✅ | logind D-Bus |
| **Artix / Devuan / Void / Alpine** | ✅ (avec elogind) | ✅ | ✅ | logind D-Bus |
| **FreeBSD / OpenBSD / NetBSD / DragonFly** | ❌ (pas d'API d'inhibition publique) | ✅ (sysctl quand dispo) | ❌ | backend `bsd.rs` — refus honnête |
| **macOS** | ❌ | ❌ | ❌ | repli honnête (jamais simulé) |
| **SerenityOS / Redox / TempleOS** | ❌ | ❌ | ❌ | pas d'API power-inhibit, pas de toolchain compatible — voir plus bas |

### Pourquoi certains OS ne sont PAS supportés (honnête)

- **TempleOS** — OS mono-utilisateur avec son propre compilateur (HolyC),
  pas de binaires tiers, pas de pile réseau standard, pas d'API de gestion
  d'alimentation. Un binaire Rust ne peut pas y tourner.
- **SerenityOS / Redox OS** — pas d'API utilisateur publique pour inhiber
  la veille système, et la pile graphique (egui) n'a pas de backend pour
  eux. Refuser honnêtement vaut mieux que prétendre.
- **TaurusOS / distros inconnues** — si ça tourne Linux avec `systemd` ou
  `elogind`, Meth fonctionne via le repli logind. Sinon, Meth refuse
  honnêtement plutôt que de simuler un keep-alive.

## ✨ Fonctionnalités

- 🟢 **Un gros bouton ON/OFF** — un disque métal mat, sobre, style épuré.
- 📊 **État honnête** — capot (ouvert/fermé/inconnu), alimentation
  (secteur/batterie/inconnue). Jamais inventé.
- 🔒 **Keep-alive natif** — fonctionne avec OpenCode, Pi, FreeBuff, les LLM
  locaux, Docker, Python, scripts, compilations, téléchargements — tout.
- 🛡️ **Fail-safe de conception** — Windows efface l'état d'exécution (et
  systemd relâche l'inhibiteur) quand Meth s'arrête ou crashe ; restauration
  explicite à l'arrêt propre aussi.
- 🔌 **Instance unique** — lancer Meth deux fois refuse la seconde instance.
- ⚡ **100 % Rust** — un seul binaire natif, pas de Python, pas de runtime,
  CPU quasi nul au repos, RAM minimale.
- 🔐 **Local d'abord** — aucun compte, aucun cloud, aucune télémétrie,
  aucun internet.

## 🛡️ Sécurité

- **Privilèges minimaux** — ne demande jamais de droits administrateur.
- **Aucune modification permanente** — OFF restaure le comportement précédent.
- **Fail-safe** — crash ou redémarrage → comportement d'alimentation normal
  automatiquement.
- **Aucun hack matériel** — ventilateurs, throttling, protections thermiques
  intouchées.
- **Aucune entrée simulée** — pas de faux mouvements de souris, touches ou clics.
- **Avertissement batterie** — garder le PC éveillé capot fermé consomme plus
  d'énergie. Préfère le secteur pour les longues tâches.

Voir [SECURITY.md](SECURITY.md) pour les détails.

## 🏗️ Architecture

```
             UI (egui — fenêtre métal mat)
                        ↓
                    App (machine à états)
                        ↓
                 backends/ (dispatcher)
                   ↙               ↘
        Windows (windows-sys)  Linux (systemd/sysfs)
```

| Couche | Chemin | Rôle |
|---|---|---|
| **Core** | `src/keepalive.rs` | moteur keep-alive (état, activation, fail-safe) |
| **Backends** | `src/backends/` | `windows.rs` / `linux.rs` / `fallback.rs` (repli honnête) |
| **App** | `src/app.rs` | état ON/OFF, persistance config, autostart, polling power/capot |
| **Config** | `src/config.rs` | JSON dans `%APPDATA%\Meth\config.json` / `$XDG_CONFIG_HOME/meth/` |
| **UI** | `src/ui.rs` | fenêtre egui, disque métal mat, réglages |
| **CLI** | `src/main.rs` | `on` / `off` / `status` / `autostart` / lanceur GUI |

L'UI est totalement séparée des backends — chaque couche est testable
isolément. Le prototype Python (v0.1–v0.2) est conservé dans
[`legacy/python/`](legacy/python/README.md) pour référence.

## 🧪 Tests

```bash
cargo test
```

**17 tests (Windows) / 18 tests (Linux)** — keep-alive, alimentation, capot,
config, orchestration, autostart, instance unique, repli honnête, plus des
appels Win32/sysfs réels qui ne paniquent jamais. La CI les exécute sur
Windows et Linux.

## 🗺️ Feuille de route

- **v0.1** ✅ — mini UI, ON/OFF, keep-alive, détection capot, restauration,
  Windows 10/11, tests, build portable.
- **v0.2** ✅ — **support Linux** (systemd-inhibit, sysfs, ACPI, autostart,
  config XDG), dispatcher de plateforme, repli honnête (pas macOS).
- **v0.3** ✅ — **réécriture 100 % Rust** (un seul binaire natif), CLI, UI
  egui, style métal mat.
- **v0.4** — zone de notification système (tray-icon), sessions & heartbeat
  (une IA peut déclarer « je travaille encore »), comportement batterie
  (arrêt auto en batterie faible), distros logind-only (Gentoo/OpenRC,
  Slackware, Dragora) documentées et testées sur matériel réel.
- **v1.0** — sessions avancées, API heartbeat, déclencheurs, intégrations
  premières (OpenCode, Pi, FreeBuff).

## 🤝 Contribuer

Voir [CONTRIBUTING.md](CONTRIBUTING.md) et notre
[Code de Conduite](CODE_OF_CONDUCT.md). Les PRs sont bienvenues — restez
simple, ciblé et fiable.

## 📄 Licence

[MIT](LICENSE) — libre d'utilisation, de modification et de partage.

---

> **Meth.** *Ton IA travaille. Meth garde le PC éveillé.*
