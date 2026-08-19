# Meth — Legacy Python implementation (v0.1 – v0.2)

> **This folder is kept for reference only.** Since **v0.3.0** Meth is
> rewritten in **100% Rust** (see the [root README](../README.md)) — one
> native binary, no Python runtime.

This directory contains the original Python prototype:
- `src/` — Core (KeepAlive), Config, Windows/Linux backends, tkinter UI, tray
- `tests/` — 91 unit tests (Windows + Linux)
- `run.py` — entry point
- `build.bat` / `Meth.spec` — PyInstaller packaging

It is kept so the design decisions (ADR 0001–0004), the test contracts and
the honest-fallback philosophy remain available as reference.

**Do not use it for new work** — build from `cargo` instead.
