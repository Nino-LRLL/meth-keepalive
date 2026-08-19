//! Meth App — the state machine tying KeepAlive + Config + backends.
//!
//! Owns the ON/OFF state, persists it to config, applies autostart, and
//! exposes Power/Lid status for the UI. Platform-agnostic: all backend
//! calls go through `backends::active`.

use std::path::PathBuf;
use std::sync::atomic::AtomicBool;
use std::sync::Arc;
use std::time::{Duration, Instant};

use crate::backends::active as backend;
use crate::config::Config;
use crate::keepalive::KeepAlive;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PowerState {
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

pub struct App {
    pub config: Config,
    pub config_path: PathBuf,
    keepalive: KeepAlive,
    pub autostart: bool,
    pub power: PowerState,
    pub lid: LidState,
    pub platform: &'static str,
    last_poll: Instant,
    pub available: bool,
}

impl App {
    pub fn new() -> Self {
        let (config, config_path) = Config::load(&Config::default_path());
        let available = cfg!(any(target_os = "windows", target_os = "linux"));

        let mut app = App {
            config,
            config_path,
            keepalive: KeepAlive::new(Box::new(backend::set_exec_state)),
            autostart: false,
            power: PowerState::Unknown,
            lid: LidState::Unknown,
            platform: crate::backends::platform_name(),
            last_poll: Instant::now() - Duration::from_secs(5),
            available,
        };
        app.autostart = app.config.autostart;
        app.poll_status();
        // Restore last ON state after a restart (ADR 0004).
        if app.config.last_state {
            app.set_on(true);
        }
        app
    }

    /// Refresh Power + Lid status (cheap, call on a timer).
    pub fn poll_status(&mut self) {
        self.power = match backend::ac_status() {
            backend::AcStatus::OnAc => PowerState::OnAc,
            backend::AcStatus::OnBattery => PowerState::OnBattery,
            backend::AcStatus::Unknown => PowerState::Unknown,
        };
        self.lid = match backend::lid_state() {
            backend::LidState::Open => LidState::Open,
            backend::LidState::Closed => LidState::Closed,
            backend::LidState::Unknown => LidState::Unknown,
        };
        self.last_poll = Instant::now();
    }

    pub fn maybe_poll(&mut self) {
        if self.last_poll.elapsed() >= Duration::from_secs(2) {
            self.poll_status();
        }
    }

    pub fn on(&self) -> bool {
        self.keepalive.active()
    }

    /// Toggle keep-alive; persists `last_state` and syncs autostart.
    pub fn set_on(&mut self, value: bool) -> bool {
        if value == self.keepalive.active() {
            return true;
        }
        let ok = if value {
            self.keepalive.activate()
        } else {
            self.keepalive.deactivate()
        };
        if ok {
            self.config.last_state = value;
            self.config.save(&self.config_path);
        }
        ok
    }

    /// Apply autostart to the real system (registry / .desktop).
    pub fn apply_autostart(&mut self, enabled: bool) -> bool {
        let ok = backend::set_autostart(enabled);
        if ok {
            self.autostart = enabled;
            self.config.autostart = enabled;
            self.config.save(&self.config_path);
        }
        ok
    }

    /// Clean shutdown: always restore normal state (fail-safe).
    pub fn shutdown(&mut self) {
        self.keepalive.shutdown();
        self.config.save(&self.config_path);
    }

    /// True when the current platform actually supports keep-alive.
    pub fn keepalive_available(&self) -> bool {
        self.available
    }
}

// Thread-safe snapshot used by the tray thread.
pub struct SharedState {
    pub on: AtomicBool,
    pub available: AtomicBool,
}

impl SharedState {
    pub fn new(on: bool, available: bool) -> Arc<Self> {
        Arc::new(SharedState {
            on: AtomicBool::new(on),
            available: AtomicBool::new(available),
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn app_constructs_without_panicking() {
        let app = App::new();
        // On any platform, the app must construct cleanly.
        let _ = app.platform;
    }

    #[test]
    fn poll_status_never_panics() {
        let mut app = App::new();
        app.poll_status();
    }

    #[test]
    fn toggle_reflects_real_state() {
        let mut app = App::new();
        app.set_on(false);
        assert_eq!(app.on(), false);
        app.set_on(true);
        if app.keepalive_available() {
            assert_eq!(app.on(), true);
            app.set_on(false);
            assert_eq!(app.on(), false);
        }
    }
}
