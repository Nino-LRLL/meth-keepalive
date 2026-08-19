//! Meth Core — KeepAlive engine.
//!
//! The engine that keeps the system awake while your AI works.
//!
//! Native mechanism (Windows): `SetThreadExecutionState(ES_CONTINUOUS |
//! ES_SYSTEM_REQUIRED)`.
//! - `ES_SYSTEM_REQUIRED` prevents SYSTEM sleep (the PC stays active).
//! - `ES_DISPLAY_REQUIRED` is NOT used: the screen may (and should) turn
//!   off — Meth never keeps the display on (lid closed → screen off).
//! - Windows automatically resets the execution state when the process
//!   dies (crash, shutdown, restart): the fail-safe is native, no
//!   dangerous state can persist. Meth also explicitly restores normal
//!   state on deactivation and clean shutdown.
//!
//! Linux: a `systemd-inhibit --what=sleep:handle-lid-switch` child process
//! is spawned; killing it releases the inhibitor (fail-safe by design).
//!
//! This module is deliberately independent of the OS API: the real
//! execution is injected (`set_exec_state`) so it is fully testable
//! without Windows or systemd.

/// ES_SYSTEM_REQUIRED — keep the system awake.
pub const ES_SYSTEM_REQUIRED: u32 = 0x0000_0001;
/// ES_CONTINUOUS — apply continuously until explicitly reset.
pub const ES_CONTINUOUS: u32 = 0x8000_0000;
/// ES_OFF — ES_CONTINUOUS alone releases all requests (normal state).
pub const ES_OFF: u32 = ES_CONTINUOUS;

/// Injected setter: receives flags, returns previous flags.
/// A return of 0 means the platform refused the request (e.g. no native
/// keep-alive available on this OS).
pub type ExecStateFn = Box<dyn Fn(u32) -> u32 + Send>;

pub struct KeepAlive {
    set_exec_state: ExecStateFn,
    active: bool,
    last_flags: Option<u32>,
}

impl KeepAlive {
    pub fn new(set_exec_state: ExecStateFn) -> Self {
        KeepAlive {
            set_exec_state,
            active: false,
            last_flags: None,
        }
    }

    pub fn active(&self) -> bool {
        self.active
    }

    /// Activate Meth: ask the OS to stay awake. Idempotent.
    pub fn activate(&mut self) -> bool {
        if self.active {
            log::debug!("activate(): déjà actif, rien à faire");
            return true;
        }
        let previous = (self.set_exec_state)(ES_CONTINUOUS | ES_SYSTEM_REQUIRED);
        if previous == 0 {
            log::error!("activate(): la plateforme a refusé la demande (0)");
            return false;
        }
        self.active = true;
        self.last_flags = Some(previous);
        log::info!("METH ON — le système reste actif");
        true
    }

    /// Deactivate Meth: restore normal behavior. Idempotent.
    pub fn deactivate(&mut self) -> bool {
        if !self.active {
            log::debug!("deactivate(): déjà inactif, rien à faire");
            return true;
        }
        (self.set_exec_state)(ES_OFF);
        self.active = false;
        self.last_flags = None;
        log::info!("METH OFF — comportement normal restauré");
        true
    }

    /// Clean shutdown: ALWAYS restore normal state (fail-safe).
    pub fn shutdown(&mut self) {
        log::debug!("shutdown(): restauration fail-safe");
        (self.set_exec_state)(ES_OFF);
        self.active = false;
        self.last_flags = None;
    }

    /// Explicit fail-safe: restore the previous flags if memorized.
    pub fn restore_previous(&mut self) -> Option<u32> {
        if let Some(flags) = self.last_flags {
            if flags != ES_OFF {
                (self.set_exec_state)(flags);
            }
            Some(flags)
        } else {
            None
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn logger_setter(calls: std::sync::Arc<std::sync::Mutex<Vec<u32>>>) -> ExecStateFn {
        Box::new(move |flags: u32| {
            calls.lock().unwrap().push(flags);
            // Previous state reported by the (mock) OS: a pre-existing
            // ES_DISPLAY_REQUIRED request from another app — NOT ES_OFF.
            0x0000_0002
        })
    }

    fn calls() -> std::sync::Arc<std::sync::Mutex<Vec<u32>>> {
        std::sync::Arc::new(std::sync::Mutex::new(Vec::new()))
    }

    #[test]
    fn activate_sets_system_required() {
        let calls = calls();
        let mut ka = KeepAlive::new(logger_setter(calls.clone()));
        assert!(ka.activate());
        assert!(ka.active());
        let recorded = calls.lock().unwrap();
        assert_eq!(recorded[0], ES_CONTINUOUS | ES_SYSTEM_REQUIRED);
    }

    #[test]
    fn activate_is_idempotent() {
        let calls = calls();
        let mut ka = KeepAlive::new(logger_setter(calls.clone()));
        assert!(ka.activate());
        assert!(ka.activate());
        assert_eq!(calls.lock().unwrap().len(), 1);
    }

    #[test]
    fn deactivate_restores_normal_state() {
        let calls = calls();
        let mut ka = KeepAlive::new(logger_setter(calls.clone()));
        ka.activate();
        assert!(ka.deactivate());
        assert!(!ka.active());
        assert_eq!(calls.lock().unwrap()[1], ES_OFF);
    }

    #[test]
    fn deactivate_is_idempotent() {
        let calls = calls();
        let mut ka = KeepAlive::new(logger_setter(calls.clone()));
        ka.deactivate();
        ka.deactivate();
        assert_eq!(calls.lock().unwrap().len(), 0);
    }

    #[test]
    fn shutdown_always_restores() {
        let calls = calls();
        let mut ka = KeepAlive::new(logger_setter(calls.clone()));
        ka.activate();
        ka.shutdown();
        assert!(!ka.active());
        assert_eq!(calls.lock().unwrap()[1], ES_OFF);
    }

    #[test]
    fn refusal_returns_false_and_stays_inactive() {
        let mut ka = KeepAlive::new(Box::new(|_| 0));
        assert!(!ka.activate());
        assert!(!ka.active());
    }

    #[test]
    fn restore_previous_uses_memorized_flags() {
        let calls = calls();
        let mut ka = KeepAlive::new(logger_setter(calls.clone()));
        ka.activate();
        let restored = ka.restore_previous();
        assert_eq!(restored, Some(0x0000_0002));
        assert_eq!(calls.lock().unwrap().len(), 2);
    }
}
