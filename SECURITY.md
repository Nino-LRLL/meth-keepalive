# Security Policy

## Philosophy

Meth follows a **minimum-privilege** principle:

- Meth **never** requests administrator rights.
- Meth makes **no permanent** changes to Windows settings. While ON, it asks
  Windows to stay awake via the documented `SetThreadExecutionState` API;
  turning it OFF (or shutting down) restores the previous behavior.
- Meth **never** fakes user input — no synthetic mouse moves, key presses,
  or clicks.
- Meth **never** touches hardware protections — fans, throttling, thermal
  limits, or firmware.
- Meth is **local-first**: no account, no cloud, no telemetry, no network
  access at all.

## Fail-safe behavior

Windows automatically clears the execution state requested by
`SetThreadExecutionState` when the requesting process exits or crashes. This
means:

- If Meth crashes → Windows returns to its normal power behavior.
- If Windows restarts → normal behavior on next boot.
- If the session ends → normal behavior.

Additionally, Meth restores the previous state explicitly on shutdown
(`KeepAlive.shutdown()`).

## Reporting a vulnerability

Please **do not** open a public issue for security vulnerabilities. Report
them privately by opening a GitHub Security Advisory (or email the
maintainers listed in the repository metadata).

We will acknowledge your report within 5 business days and work with you on
a fix. Please include:

- The affected version(s).
- A description of the vulnerability and its impact.
- Steps to reproduce (if possible).

## Scope

This policy covers the Meth repository. Dependencies (`pystray`, `Pillow`,
Tkinter) are covered by their own policies — upgrade them regularly.
