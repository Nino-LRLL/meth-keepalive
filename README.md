<p align="center">
  <img src="assets/social-preview.png" alt="Meth — Your AI works. Meth keeps Windows awake." width="100%">
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
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776ab.svg" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/RAM-%7E45_MB-34d868.svg" alt="~45 MB RAM">
  <img src="https://img.shields.io/badge/Status-v0.2.0-34d868.svg" alt="v0.2.0">
</p>

---

Your AI is working.

Windows wants to sleep.

**Meth says no.**

Close your laptop. Your screen turns off. Windows stays alive. Your AI keeps
working.

---

## ✨ Screenshots

| Meth OFF | Meth ON (halo pulsant) |
|:---:|:---:|
| ![Meth OFF](assets/screenshot-off.png) | ![Meth ON](assets/screenshot-on.png) |

## 🧠 Why?

AI agents can work for hours. Windows may put a laptop to sleep when the lid
is closed — killing your build, your agent, your download or your server.

Meth keeps Windows alive while your work is still running.

**One button. No account. No cloud. No admin. No mouse-jiggling hacks.**

## ⚙️ How it works

```
Lid closed        Meth ON
    ↓                ↓
Screen off     Windows stays awake
    ↓                ↓
   └──────→  AI keeps working
```

Meth uses the **native Windows power API** — `SetThreadExecutionState` with
`ES_SYSTEM_REQUIRED` + `ES_CONTINUOUS` — to ask Windows to stay awake. The
screen is **not** kept on: it turns off normally, exactly as it should.

## 🚀 Quick start

### Portable (recommended)

1. Download **`Meth-Portable.zip`** from the
   [Releases](https://github.com/Nino-LRLL/meth-keepalive/releases) page.
2. Unzip anywhere. Double-click **`Meth.exe`**.
3. Click **ON**. Done.

No installation. No Python. No admin.

### From source

```bat
git clone https://github.com/Nino-LRLL/meth-keepalive.git
cd meth-keepalive
pip install -r requirements.txt
python run.py
```

## 🎮 Usage

1. Launch Meth.
2. Click the big **ON** button.
3. Close the laptop. Screen off, the PC stays awake, work continues.
4. Done? Click **OFF** — the PC returns to normal.

Closing the window hides Meth to the **system tray** — it keeps working.
Use **Quit** in the tray menu (or in the window) to stop it completely.

## 🐧 Linux

Meth runs on **any PC — Windows and Linux** (macOS is not supported: Meth
refuses honestly, it never pretends to keep the system awake there).

On Linux, the same one-button behavior uses **systemd** (the standard init
on virtually every modern desktop):

```
Lid closed        Meth ON
    ↓                ↓
Screen off     systemd-inhibit --what=sleep:handle-lid-switch
    ↓                ↓
   └──────→  everything keeps running
```

- The screen turns off normally — only the **system sleep** and the
  **lid-switch action** are inhibited (no suspend, no hibernate).
- **Fail-safe is native**: systemd releases the inhibitor the moment Meth
  exits or crashes — the PC can never stay locked awake.
- No `systemd`? Meth **refuses honestly** (never a fake keep-alive).
- Power is read from sysfs (`/sys/class/power_supply`), lid state from ACPI
  (`/proc/acpi/button/lid`, `INCONNU` when absent), auto-start via
  `~/.config/autostart/meth.desktop`, config in `$XDG_CONFIG_HOME/meth/`.

### Run from source on Linux

```bash
pip install -r requirements.txt
python run.py            # window + tray
python run.py --tray     # start silent in the tray
```

Requires `python3-tk` (tkinter) for the window and `pystray` for the tray
(installed by requirements). The keep-alive itself is 100 % stdlib.

> Note: the tray backend on Linux needs a systray/AppIndicator — if your
> desktop has none, the window is still fully functional.

## ✨ Features

- 🟢 **One big ON/OFF button** — a glowing circle that pulses while active.
- 🖥️ **System tray** — close-to-tray, icon reflects the real state, dynamic
  Activate/Deactivate menu.
- 📊 **Honest status display** — lid (open/closed/unknown), power
  (AC/battery/unknown). Never invented.
- 🔒 **Native keep-alive** — works with OpenCode, Pi, FreeBuff, local LLMs,
  Docker, Python, scripts, compilations, downloads — anything.
- 🛡️ **Fail-safe by design** — Windows clears the execution state (and
  systemd releases the inhibitor) when Meth exits or crashes; explicit
  restore on shutdown too.
- 🔌 **Single instance** — launching Meth twice refuses the second instance.
- 🪶 **Ultra light** — ~45 MB RAM (packaged), zero network, near-zero CPU at
  rest.
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
             UI (MainWindow + Tray + Settings)
                        ↓
                    Meth Core (KeepAlive)
                        ↓
                 src/backends (dispatcher)
                   ↙               ↘
        Windows (ctypes)     Linux (systemd/sysfs)
```

| Layer | Path | Role |
|---|---|---|
| **Core** | `src/Core/` | keep-alive engine (state, activation, fail-safe) |
| **Backends** | `src/backends.py` | dispatcher Windows / Linux / other (honest fallback) |
| **Windows** | `src/Windows/` | `Power`, `Lid`, `System` (exec state, registry auto-start) |
| **Linux** | `src/Linux/` | `Power` (sysfs), `Lid` (ACPI), `System` (systemd-inhibit, .desktop auto-start) |
| **UI** | `src/UI/` | compact 320×460 window, tray, settings |
| **Config** | `src/Config/` | JSON settings in `%APPDATA%\Meth\config.json` |

UI is fully separated from Core and Windows — every layer is testable in
isolation (the suite mocks the Windows API). See
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## 🧪 Tests

```
python -m unittest discover -s tests -v
```

**91 tests** — keep-alive, power, lid parsing (Windows + Linux), config,
app orchestration, auto-start, single-instance — plus a **real**
`SetThreadExecutionState` integration test. CI runs them on Windows and
Linux (91/91 green on both).

## 🗺️ Roadmap

- **v0.1** ✅ — mini UI, ON/OFF, tray, keep-alive, lid detection, restore,
  Windows 10/11, tests, portable build.
- **v0.2** ✅ — **Linux support** (systemd-inhibit, sysfs, ACPI, autostart,
  XDG config), platform dispatcher (`src/backends.py`), honest fallback
  (no macOS), matte-metal Apple-style UI.
- **v0.3** — sessions & heartbeat (an AI can declare « still working »),
  profiles, battery-aware behavior (auto-off on low battery).
- **v1.0** — advanced sessions, heartbeat API, CLI, triggers.
- **v2.0** — first-party integrations (OpenCode, Pi, FreeBuff), SDK.

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) and our
[Code of Conduct](CODE_OF_CONDUCT.md). PRs are welcome — keep it small,
focused and reliable.

## 📄 License

[MIT](LICENSE) — free to use, modify and share.

---

> **Meth.** *Your AI works. Meth keeps the PC awake.*
