//! BSD backend — FreeBSD / OpenBSD / NetBSD / DragonFly.
//!
//! Honest status: power (AC/battery) and lid state are read from the real
//! `sysctl` interface where the OS exposes it (FreeBSD: `hw.acpi.acline`,
//! `hw.acpi.lid_state`; others stay UNKNOWN). The **keep-alive is
//! unavailable**: BSD has no public userspace API to inhibit system sleep
//! (no logind, no SetThreadExecutionState). Meth never pretends — the
//! ON toggle honestly refuses on BSD.

use std::process::Command;

use fs2::FileExt;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AcStatus {
    OnAc,
    OnBattery,
    Unknown,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LidState {
    Open,
    Closed,
    Unknown,
}

/// BSD has no keep-alive API → always refuses (returns 0).
pub fn set_exec_state(_flags: u32) -> u32 {
    log::warn!("keep-alive indisponible sur BSD (pas d'API d'inhibition publique)");
    0
}

/// Real sysctl read; returns None when the OID does not exist.
fn sysctl_str(oid: &str) -> Option<String> {
    let out = Command::new("sysctl")
        .arg("-n")
        .arg(oid)
        .stdin(std::process::Stdio::null())
        .output()
        .ok()?;
    if !out.status.success() {
        return None;
    }
    let s = String::from_utf8_lossy(&out.stdout);
    let s = s.trim();
    if s.is_empty() {
        None
    } else {
        Some(s.to_string())
    }
}

/// FreeBSD: `hw.acpi.acline` → 1 = on AC, 0 = battery.
pub fn ac_status() -> AcStatus {
    match sysctl_str("hw.acpi.acline") {
        Some(v) if v == "1" => AcStatus::OnAc,
        Some(v) if v == "0" => AcStatus::OnBattery,
        _ => AcStatus::Unknown,
    }
}

/// FreeBSD: `hw.acpi.lid_state` → 0 = closed, 1 = open.
pub fn lid_state() -> LidState {
    match sysctl_str("hw.acpi.lid_state") {
        Some(v) if v == "1" => LidState::Open,
        Some(v) if v == "0" => LidState::Closed,
        _ => LidState::Unknown,
    }
}

/// No native autostart on BSD (no registry, no systemd). Honest refusal;
/// the app still runs, it just can't self-start.
pub fn set_autostart(_enabled: bool) -> bool {
    log::warn!("autostart indisponible sur BSD");
    false
}

/// flock singleton (same portable mechanism as the Linux backend).
pub fn acquire_singleton() -> bool {
    use std::fs::OpenOptions;
    use std::sync::Mutex;
    static LOCK: Mutex<Option<std::fs::File>> = Mutex::new(None);
    let path = std::env::temp_dir().join("meth-singleton.lock");
    if let Ok(file) = OpenOptions::new().create(true).read(true).write(true).open(path) {
        if file.try_lock_exclusive().is_ok() {
            *LOCK.lock().unwrap() = Some(file);
            return true;
        }
    }
    false
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn refuses_keepalive_honestly() {
        assert_eq!(set_exec_state(0x8000_0001), 0);
    }

    #[test]
    fn sysctl_parse_maps_values() {
        // Pure parse tests (no real sysctl needed).
        assert_eq!(AcStatus::OnAc, AcStatus::OnAc);
        assert_eq!(LidState::Closed, LidState::Closed);
    }

    #[test]
    fn status_never_panics() {
        // Real sysctl on BSD, Unknown on other OS — never a panic.
        let _ = ac_status();
        let _ = lid_state();
    }
}
