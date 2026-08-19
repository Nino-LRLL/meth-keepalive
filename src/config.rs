//! Meth Config — local settings, one JSON file in the user data folder.
//!
//! Windows: `%APPDATA%/Meth/config.json`
//! Linux:   `$XDG_CONFIG_HOME/meth/config.json` (or `~/.config/meth/`)
//!
//! Tolerant loading: missing file → defaults; corrupt file → defaults +
//! warning (never crashes at startup). No cloud, no account: everything local.

use serde::{Deserialize, Serialize};
use std::fs;
use std::io;
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Config {
    /// Start Meth automatically at user login.
    pub autostart: bool,
    /// Show in the system tray.
    pub show_tray: bool,
    /// Only keep awake while on AC power (prepared for a later version).
    pub ac_only: bool,
    /// ON/OFF state at last clean exit (UI memory).
    pub last_state: bool,
}

impl Default for Config {
    fn default() -> Self {
        Config {
            autostart: false,
            show_tray: true,
            ac_only: false,
            last_state: false,
        }
    }
}

impl Config {
    /// Default config file location for the current platform.
    pub fn default_path() -> PathBuf {
        if let Some(dir) = dirs::config_dir() {
            let folder = if cfg!(target_os = "windows") {
                dir.join("Meth")
            } else {
                dir.join("meth")
            };
            folder.join("config.json")
        } else {
            // Last-resort fallback: next to the executable (never used on
            // supported platforms, kept for robustness).
            std::env::current_exe()
                .unwrap_or_else(|_| PathBuf::from("meth"))
                .with_file_name("config.json")
        }
    }

    /// Load from `path`, falling back to defaults on any error.
    pub fn load(path: &PathBuf) -> (Self, PathBuf) {
        let cfg = match fs::read_to_string(path) {
            Ok(raw) => match serde_json::from_str::<Config>(&raw) {
                Ok(c) => c,
                Err(_) => {
                    log::warn!("config illisible ({path:?}) → défauts");
                    Config::default()
                }
            },
            Err(e) if e.kind() == io::ErrorKind::NotFound => {
                log::debug!("config absente ({path:?}) → défauts");
                Config::default()
            }
            Err(e) => {
                log::warn!("config illisible ({path:?}): {e} → défauts");
                Config::default()
            }
        };
        (cfg, path.clone())
    }

    /// Persist to disk. Returns false on write failure (never panics).
    pub fn save(&self, path: &PathBuf) -> bool {
        if let Some(parent) = path.parent() {
            if let Err(e) = fs::create_dir_all(parent) {
                log::error!("config: échec création dossier: {e}");
                return false;
            }
        }
        match serde_json::to_string_pretty(self) {
            Ok(raw) => match fs::write(path, raw) {
                Ok(()) => {
                    log::debug!("config enregistrée: {path:?}");
                    true
                }
                Err(e) => {
                    log::error!("config: échec écriture: {e}");
                    false
                }
            },
            Err(e) => {
                log::error!("config: sérialisation échouée: {e}");
                false
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn defaults_on_missing_file() {
        let tmp = std::env::temp_dir().join(format!("meth-test-{}.json", std::process::id()));
        let _ = fs::remove_file(&tmp);
        let (cfg, _) = Config::load(&tmp);
        assert!(!cfg.autostart);
        assert!(cfg.show_tray);
        assert!(!cfg.last_state);
        let _ = fs::remove_file(&tmp);
    }

    #[test]
    fn defaults_on_corrupt_file() {
        let tmp = std::env::temp_dir().join(format!("meth-test-corrupt-{}.json", std::process::id()));
        fs::write(&tmp, "{ not json !!").unwrap();
        let (cfg, _) = Config::load(&tmp);
        assert_eq!(cfg.autostart, false);
        let _ = fs::remove_file(&tmp);
    }

    #[test]
    fn roundtrip_persists_all_fields() {
        let tmp = std::env::temp_dir().join(format!("meth-test-rt-{}.json", std::process::id()));
        let mut cfg = Config::default();
        cfg.autostart = true;
        cfg.ac_only = true;
        cfg.last_state = true;
        assert!(cfg.save(&tmp));
        let (loaded, _) = Config::load(&tmp);
        assert!(loaded.autostart);
        assert!(loaded.ac_only);
        assert!(loaded.last_state);
        assert!(loaded.show_tray);
        let _ = fs::remove_file(&tmp);
    }

    #[test]
    fn save_failure_returns_false_not_panic() {
        // A path that cannot be created on ANY platform: a directory whose
        // name is a NUL byte is impossible on both Windows and POSIX.
        let bad = PathBuf::from("\u{0}/definitely/not/a/valid/path/config.json");
        assert!(!Config::default().save(&bad));
    }
}
