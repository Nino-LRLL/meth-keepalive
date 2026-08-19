//! Honest fallback backend — used on unsupported platforms (macOS, BSD, …).
//!
//! The app runs and shows its UI, but the keep-alive is UNAVAILABLE:
//! `set_exec_state` always returns 0 (refusal) and Power/Lid stay
//! UNKNOWN. Meth never claims to keep the system awake when it has no
//! native way to — no simulated success.

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

/// Always refuses (returns 0) — no native keep-alive on this platform.
pub fn set_exec_state(_flags: u32) -> u32 {
    log::warn!("keep-alive indisponible sur cette plateforme (macOS/BSD)");
    0
}

pub fn ac_status() -> AcStatus {
    AcStatus::Unknown
}

pub fn lid_state() -> LidState {
    LidState::Unknown
}

pub fn set_autostart(_enabled: bool) -> bool {
    log::warn!("autostart indisponible sur cette plateforme");
    false
}

pub fn acquire_singleton() -> bool {
    // Portable-ish singleton via a lock file in the temp dir.
    use fs2::FileExt;
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
    fn power_and_lid_unknown() {
        assert_eq!(ac_status(), AcStatus::Unknown);
        assert_eq!(lid_state(), LidState::Unknown);
    }
}
