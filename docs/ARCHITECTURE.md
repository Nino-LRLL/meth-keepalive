# Meth — Architecture

Meth is deliberately small and split into testable layers (100% Rust since
v0.3.0):

```
             UI (egui — matte-metal window)
                        ↓
                    App (state machine)
                        ↓
                 backends/ (dispatcher)
                   ↙               ↘
        Windows (windows-sys)  Linux (systemd/sysfs)
```

Layers only depend downward: the UI never touches the OS API, the backends
never know the UI. Each brick is injectable (see `src/app.rs`, the
composition root).

## Structure

```
meth-keepalive/
├── Cargo.toml
├── src/
│   ├── main.rs               # entry point: CLI (on/off/status/autostart) + GUI launcher + singleton
│   ├── lib.rs                # module root
│   ├── keepalive.rs          # ON/OFF engine, activation, fail-safe (injected setter)
│   ├── config.rs             # JSON config (APPDATA / XDG), tolerant load
│   ├── app.rs                # state machine: keepalive + config + autostart + power/lid polling
│   ├── ui.rs                 # egui window, matte-metal disc, settings, dynamic version
│   └── backends/
│       ├── mod.rs            # dispatcher (platform_name + active backend)
│       ├── windows.rs        # SetThreadExecutionState, GetSystemPowerStatus,
│       │                     #   lid (RegisterPowerSettingNotification), autostart (registre), mutex
│       ├── linux.rs          # systemd-inhibit child, sysfs power, ACPI lid,
│       │                     #   autostart (.desktop), flock singleton
│       └── fallback.rs       # honest fallback (macOS/BSD): keep-alive unavailable
├── legacy/python/            # v0.1–v0.2 Python prototype (reference only)
├── docs/                     # this doc, ADRs
└── assets/                   # icon, screenshots, social preview
```

## Key decisions

- **Keep-alive is platform-native.** Windows: `SetThreadExecutionState`
  with `ES_SYSTEM_REQUIRED | ES_CONTINUOUS`. Linux: a `systemd-inhibit
  --what=sleep:handle-lid-switch --mode=block` child process.
- **Fail-safe by design.** Windows clears the execution state when the
  process dies; systemd releases the inhibitor when the child dies. Meth
  also explicitly restores normal state on deactivation and clean shutdown.
- **Honest fallback.** On macOS/BSD (or Linux without systemd), Meth
  refuses — `set_exec_state` returns 0, power/lid stay UNKNOWN. Never a
  simulated keep-alive.
- **UI shows real state.** Power (AC/battery/unknown) and lid
  (open/closed/unknown) are read from the OS on a 2s timer — never invented.
- **Single instance.** Named mutex (Windows) / flock (Linux).

## Tests

`cargo test` — keep-alive, config, app orchestration, per-platform backends
(real Win32/sysfs calls that never panic) plus honest-fallback tests. CI
runs on Windows and Linux.
