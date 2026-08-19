<p align="center">
  <img src="assets/social-preview.png" alt="Meth — Your AI works. Meth keeps the PC awake." width="100%">
</p>

<h1 align="center">Meth</h1>

<p align="center">
  <b>The plugin that makes your AI never sleep while it still has work to do.</b>
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
  <a href="#fr">🇫🇷 Lire en français</a>
</p>

---

Your AI is working.

Windows wants to sleep.

**Meth says no.**

Close your laptop. Your screen turns off. The PC stays awake. Your AI keeps
working.

---

## ✨ Screenshots

| Meth OFF | Meth ON |
|:---:|:---:|
| ![Meth OFF](assets/screenshot-off.png) | ![Meth ON](assets/screenshot-on.png) |

## 🧠 Why?

AI agents can work for hours. Windows may put a laptop to sleep when the lid
is closed — killing your build, your agent, your download or your server.

Meth keeps the PC awake while your work is still running.

**One button. No account. No cloud. No admin. No mouse-jiggling hacks.**

## ⚙️ How it works

```
Lid closed        Meth ON
    ↓                ↓
Screen off     System stays awake
    ↓                ↓
   └──────→  AI keeps working
```

Meth uses the **native OS power APIs**:
- Windows: `SetThreadExecutionState(ES_SYSTEM_REQUIRED | ES_CONTINUOUS)`.
- Linux: a `systemd-inhibit --what=sleep:handle-lid-switch --mode=block`
  child process.

The screen is **not** kept on: it turns off normally, exactly as it should.
Only the system sleep (and the lid-close action on Linux) is inhibited.

## 🚀 Quick start

### Portable (recommended, Windows)

1. Download **`Meth-Portable.zip`** from the
   [Releases](https://github.com/Nino-LRLL/meth-keepalive/releases) page.
2. Unzip anywhere. Double-click **`Meth.exe`**.
3. Click **ON**. Done.

No installation. No Python. No admin.

### From source (Windows & Linux)

```bash
git clone https://github.com/Nino-LRLL/meth-keepalive.git
cd meth-keepalive
cargo build --release
./target/release/meth          # open the window
./target/release/meth on       # CLI: keep awake
./target/release/meth off      # CLI: restore normal
./target/release/meth status   # CLI: print state
```

## 🎮 Usage

1. Launch Meth.
2. Click the big **ON** button.
3. Close the laptop. Screen off, the PC stays awake, work continues.
4. Done? Click **OFF** — the PC returns to normal.

The window shows the **real** state: ON/OFF, power source (AC / battery /
unknown) and lid state (open / closed / unknown) — never invented.

## 🐧 Linux

Meth runs on **any PC — Windows and Linux** (macOS is not supported: Meth
refuses honestly, it never pretends to keep the system awake there).

- The screen turns off normally — only the **system sleep** and the
  **lid-switch action** are inhibited (no suspend, no hibernate).
- **Fail-safe is native**: systemd releases the inhibitor the moment Meth
  exits or crashes — the PC can never stay locked awake.
- No `systemd`? Meth **refuses honestly** (never a fake keep-alive).
- Power is read from sysfs (`/sys/class/power_supply`), lid state from ACPI
  (`/proc/acpi/button/lid`, unknown when absent), auto-start via
  `~/.config/autostart/meth.desktop`, config in `$XDG_CONFIG_HOME/meth/`.

## 🗺️ Supported platforms (honest matrix)

| OS | Keep-alive | Power/Lid status | Autostart | How |
|---|---|---|---|---|
| **Windows 10/11** | ✅ | ✅ | ✅ | `SetThreadExecutionState` + Win32 |
| **ReactOS** | ✅ | ✅ | ✅ | same Win32 API (cross-built `x86_64-pc-windows-gnu`) |
| **Arch Linux** | ✅ | ✅ | ✅ | systemd-inhibit |
| **Gentoo** | ✅ (systemd **or** logind) | ✅ | ✅ | systemd-inhibit → logind D-Bus fallback |
| **Slackware** | ✅ (with elogind) | ✅ | ✅ | logind D-Bus (`org.freedesktop.login1`) |
| **Dragora** | ✅ (with elogind) | ✅ | ✅ | logind D-Bus |
| **Artix / Devuan / Void / Alpine** | ✅ (with elogind) | ✅ | ✅ | logind D-Bus |
| **FreeBSD / OpenBSD / NetBSD / DragonFly** | ❌ (no public inhibit API) | ✅ (sysctl where available) | ❌ | `bsd.rs` backend — honest refusal |
| **macOS** | ❌ | ❌ | ❌ | honest fallback (never fake) |
| **SerenityOS / Redox / TempleOS** | ❌ | ❌ | ❌ | no power-inhibit API, no compatible toolchain — see below |

### Why some OSes are NOT supported (honest)

- **TempleOS** — single-user OS with its own compiler (HolyC), no third-party
  binaries, no standard network stack, no power management API. A Rust
  binary cannot run there.
- **SerenityOS / Redox OS** — no public userspace API to inhibit system
  sleep, and the GUI stack (egui) has no backend for them. Refusing
  honestly is better than pretending.
- **TaurusOS / unknown distros** — if it runs Linux with `systemd` or
  `elogind`, Meth works via the logind fallback. If not, Meth refuses
  honestly rather than faking keep-alive.

## ✨ Features

- 🟢 **One big ON/OFF button** — a matte-metal disc, sober Apple-style.
- 📊 **Honest status display** — lid (open/closed/unknown), power
  (AC/battery/unknown). Never invented.
- 🔒 **Native keep-alive** — works with OpenCode, Pi, FreeBuff, local LLMs,
  Docker, Python, scripts, compilations, downloads — anything.
- 🛡️ **Fail-safe by design** — Windows clears the execution state (and
  systemd releases the inhibitor) when Meth exits or crashes; explicit
  restore on shutdown too.
- 🔌 **Single instance** — launching Meth twice refuses the second instance.
- ⚡ **100% Rust** — one native binary, no Python, no runtime, near-zero
  CPU at rest, tiny RAM.
- 🔐 **Local-first** — no account, no cloud, no telemetry, no internet.

## 🛡️ Safety

- **Minimum privileges** — never requests administrator rights.
- **No permanent changes** — OFF restores the previous behavior.
- **Fail-safe** — crash or reboot → normal power behavior automatically.
- **No hardware hacks** — fans, throttling, thermal protections untouched.
- **No fake input** — no synthetic mouse moves, key presses or clicks.
- **Battery warning** — keeping the PC awake with the lid closed uses more
  power. Prefer AC for long tasks.

See [SECURITY.md](SECURITY.md) for details.

## 🏗️ Architecture

```
             UI (egui — matte-metal window)
                        ↓
                    App (state machine)
                        ↓
                 backends/ (dispatcher)
                   ↙               ↘
        Windows (windows-sys)  Linux (systemd/sysfs)
```

| Layer | Path | Role |
|---|---|---|
| **Core** | `src/keepalive.rs` | keep-alive engine (state, activation, fail-safe) |
| **Backends** | `src/backends/` | `windows.rs` / `linux.rs` / `fallback.rs` (honest fallback) |
| **App** | `src/app.rs` | ON/OFF state, config persistence, autostart, power/lid polling |
| **Config** | `src/config.rs` | JSON settings in `%APPDATA%\Meth\config.json` / `$XDG_CONFIG_HOME/meth/` |
| **UI** | `src/ui.rs` | egui window, matte-metal disc, settings |
| **CLI** | `src/main.rs` | `on` / `off` / `status` / `autostart` / GUI launcher |

The UI is fully separated from the backends — every layer is testable in
isolation. The Python prototype (v0.1–v0.2) is kept in
[`legacy/python/`](legacy/python/README.md) for reference.

## 🧪 Tests

```bash
cargo test
```

**17 tests (Windows) / 18 tests (Linux)** — keep-alive, power, lid parsing,
config, app orchestration, auto-start, single-instance, honest fallback,
plus real Win32/sysfs integration calls that never panic. CI runs them on
Windows and Linux.

## 🗺️ Roadmap

- **v0.1** ✅ — mini UI, ON/OFF, keep-alive, lid detection, restore,
  Windows 10/11, tests, portable build.
- **v0.2** ✅ — **Linux support** (systemd-inhibit, sysfs, ACPI, autostart,
  XDG config), platform dispatcher, honest fallback (no macOS).
- **v0.3** ✅ — **100% Rust rewrite** (single native binary), CLI, egui UI,
  matte-metal style.
- **v0.4** — system tray (tray-icon), sessions & heartbeat (an AI can
  declare « still working »), battery-aware behavior (auto-off on low battery),
  logind-only distros (Gentoo/OpenRC, Slackware, Dragora) documented &
  tested on real hardware.
- **v1.0** — advanced sessions, heartbeat API, triggers, first-party
  integrations (OpenCode, Pi, FreeBuff).

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) and our
[Code of Conduct](CODE_OF_CONDUCT.md). PRs are welcome — keep it small,
focused and reliable.

## 📄 License

[MIT](LICENSE) — free to use, modify and share.

---

<a name="fr"></a>
## 🇫🇷 Version française

> **Meth.** *Ton IA travaille. Meth garde le PC éveillé.*

Meth est l'extension **« l'IA qui ne dort pas »** : quand elle est activée,
ferme le capot → l'écran s'éteint normalement mais **le PC reste actif et
tout ce qui tourne continue** (IA, build, téléchargement, serveur).

- **100 % Rust** — un seul binaire natif (Windows `meth.exe`, Linux `meth`).
- **Windows** : API native `SetThreadExecutionState` + statut capot/alim.
- **Linux** : `systemd-inhibit` (fail-safe natif), sysfs, ACPI.
- **Honnêteté** : sans systemd, sans plateforme supportée → refus clair,
  jamais de keep-alive simulé. Le capot/l'alimentation affichés sont les
  vrais états lus sur le système.

### Démarrage rapide

```bash
cargo build --release
./target/release/meth          # fenêtre
./target/release/meth on       # activer (CLI)
./target/release/meth off      # désactiver (CLI)
./target/release/meth status   # état réel
```

### Installer sur Windows

```bat
cargo build --release
copy target\release\meth.exe Meth.exe
rem -> double-clic sur Meth.exe, puis clique sur ON
```

> **Meth.** *Your AI works. Meth keeps the PC awake.*
