//! Linux backend — keep-alive via a `systemd-inhibit` child process.
//!
//! Spawning `systemd-inhibit --what=sleep:handle-lid-switch --mode=block`
//! holds an inhibitor as long as the child lives: the screen turns off
//! normally but the PC stays awake and lid-close does not sleep. Killing
//! the child releases the inhibitor — fail-safe by design (if Meth dies,
//! systemd releases everything; the PC can never stay blocked awake).
//!
//! Without systemd → honest refusal (returns 0 from `set_exec_state`).
//!
//! Also: power from sysfs (`/sys/class/power_supply/*`), lid from ACPI
//! (`/proc/acpi/button/lid/*/state`, UNKNOWN if absent), autostart via
//! `~/.config/autostart/meth.desktop`, singleton via flock on
//! `/tmp/meth-singleton.lock`.

use std::fs::{self, File, OpenOptions};
use std::io::{BufRead, BufReader};
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Mutex;

use fs2::FileExt;

// ---------------------------------------------------------------------------
// Keep-alive (systemd-inhibit)
// ---------------------------------------------------------------------------

/// Returns the flags "requested" — 0 on refusal (no systemd, spawn error).
pub fn set_exec_state(flags: u32) -> u32 {
    // A nonzero request means ON; ES_OFF (ES_CONTINUOUS alone) means OFF.
    if flags & crate::keepalive::ES_SYSTEM_REQUIRED != 0 {
        if start_inhibit() {
            1 // pretend "previous state" was normal (nonzero = accepted)
        } else {
            0
        }
    } else {
        stop_inhibit();
        0 // OFF always "succeeds": normal state restored
    }
}

static INHIBIT: Mutex<Option<Child>> = Mutex::new(None);
static HAS_SYSTEMD: AtomicBool = AtomicBool::new(true);

fn systemd_available() -> bool {
    // First call probes; result cached so we don't spawn `pidof` every toggle.
    static PROBED: std::sync::atomic::AtomicBool = std::sync::atomic::AtomicBool::new(false);
    if PROBED.swap(true, Ordering::SeqCst) {
        return HAS_SYSTEMD.load(Ordering::Relaxed);
    }
    let ok = Command::new("pidof")
        .arg("systemd")
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .map(|s| s.success())
        .unwrap_or(false);
    HAS_SYSTEMD.store(ok, Ordering::Relaxed);
    ok
}

fn start_inhibit() -> bool {
    if !systemd_available() {
        log::warn!("METH ON refusé : systemd absent — aucun inhibiteur possible");
        return false;
    }
    let mut guard = INHIBIT.lock().unwrap();
    if guard.is_some() {
        return true; // already running
    }
    let child = Command::new("systemd-inhibit")
        .args([
            "--what=sleep:handle-lid-switch",
            "--mode=block",
            "--who=Meth",
            "--why=AI work in progress",
        ])
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn();
    match child {
        Ok(c) => {
            *guard = Some(c);
            log::info!("METH ON — systemd-inhibit actif (sleep + capot bloqués)");
            true
        }
        Err(e) => {
            log::error!("METH ON échec systemd-inhibit: {e}");
            false
        }
    }
}

fn stop_inhibit() {
    let mut guard = INHIBIT.lock().unwrap();
    if let Some(mut child) = guard.take() {
        let _ = child.kill();
        let _ = child.wait();
        log::info!("METH OFF — inhibiteur relâché (système normal)");
    }
}

// ---------------------------------------------------------------------------
// Power status (sysfs)
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AcStatus {
    OnAc,
    OnBattery,
    Unknown,
}

/// Read `/sys/class/power_supply/*/type` + `status`. AC if any Mains/AC
/// supply reports online; Battery if the battery is discharging.
pub fn ac_status() -> AcStatus {
    let Ok(entries) = fs::read_dir("/sys/class/power_supply") else {
        return AcStatus::Unknown;
    };
    let mut saw_battery = false;
    let mut on_ac = false;
    for entry in entries.flatten() {
        let base = entry.path();
        let ty = fs::read_to_string(base.join("type")).unwrap_or_default();
        let ty = ty.trim();
        if ty == "Mains" || ty == "AC" {
            let status = fs::read_to_string(base.join("status")).unwrap_or_default();
            if status.trim() == "Online" {
                on_ac = true;
            }
        } else if ty == "Battery" {
            saw_battery = true;
            let status = fs::read_to_string(base.join("status")).unwrap_or_default();
            if status.trim() == "Discharging" {
                on_ac = false;
            }
        }
    }
    if on_ac {
        AcStatus::OnAc
    } else if saw_battery {
        AcStatus::OnBattery
    } else {
        AcStatus::Unknown
    }
}

// ---------------------------------------------------------------------------
// Lid state (ACPI)
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LidState {
    Open,
    Closed,
    Unknown,
}

/// Read `/proc/acpi/button/lid/*/state` (e.g. "state: open"). Returns
/// UNKNOWN when the file is absent (desktop, VM, non-ACPI).
pub fn lid_state() -> LidState {
    let Ok(entries) = fs::read_dir("/proc/acpi/button/lid") else {
        return LidState::Unknown;
    };
    for entry in entries.flatten() {
        let state_path = entry.path().join("state");
        if let Ok(raw) = fs::read_to_string(&state_path) {
            let raw = raw.to_lowercase();
            if raw.contains("open") {
                return LidState::Open;
            }
            if raw.contains("closed") {
                return LidState::Closed;
            }
        }
    }
    LidState::Unknown
}

// ---------------------------------------------------------------------------
// Autostart (~/.config/autostart/meth.desktop)
// ---------------------------------------------------------------------------

fn autostart_dir() -> Option<PathBuf> {
    let base = std::env::var("XDG_CONFIG_HOME")
        .ok()
        .map(PathBuf::from)
        .or_else(|| dirs::config_dir());
    base.map(|b| b.join("autostart"))
}

pub fn set_autostart(enabled: bool) -> bool {
    let Some(dir) = autostart_dir() else {
        return false;
    };
    let file = dir.join("meth.desktop");
    if !enabled {
        return match fs::remove_file(&file) {
            Ok(()) => true,
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => true,
            Err(e) => {
                log::error!("autostart: suppression échouée: {e}");
                false
            }
        };
    }
    let exe = match std::env::current_exe() {
        Ok(p) => p.display().to_string(),
        Err(_) => return false,
    };
    if fs::create_dir_all(&dir).is_err() {
        return false;
    }
    let desktop = format!(
        "[Desktop Entry]\nType=Application\nName=Meth\nComment=Keep your PC awake while your AI works\nExec={exe}\nX-GNOME-Autostart-enabled=true\n"
    );
    match fs::write(&file, desktop) {
        Ok(()) => true,
        Err(e) => {
            log::error!("autostart: écriture échouée: {e}");
            false
        }
    }
}

// ---------------------------------------------------------------------------
// Singleton (flock)
// ---------------------------------------------------------------------------

static LOCK_PATH: &str = "/tmp/meth-singleton.lock";
static LOCK_FILE: Mutex<Option<File>> = Mutex::new(None);

/// Returns true if this process is the FIRST instance.
pub fn acquire_singleton() -> bool {
    let Ok(file) = OpenOptions::new().create(true).read(true).write(true).open(LOCK_PATH) else {
        return false;
    };
    match file.try_lock_exclusive() {
        Ok(()) => {
            *LOCK_FILE.lock().unwrap() = Some(file);
            true
        }
        Err(_) => false,
    }
}

// ---------------------------------------------------------------------------
// Platform info (for status/UI)
// ---------------------------------------------------------------------------

pub fn os_info() -> (String, String) {
    let os = read_first_line("/etc/os-release", "NAME")
        .unwrap_or_else(|| "Linux".to_string());
    let kernel = fs::read_to_string("/proc/sys/kernel/osrelease")
        .map(|s| s.trim().to_string())
        .unwrap_or_else(|_| "?".to_string());
    (os, kernel)
}

fn read_first_line(path: &str, key: &str) -> Option<String> {
    let f = File::open(path).ok()?;
    let reader = BufReader::new(f);
    for line in reader.lines().flatten() {
        if let Some(val) = line.strip_prefix(&format!("{key}=")) {
            return Some(val.trim_matches('"').to_string());
        }
    }
    None
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn ac_status_never_panics() {
        // Real sysfs on Linux, Unknown on CI containers — never a panic.
        let _ = ac_status();
    }

    #[test]
    fn lid_state_never_panics() {
        let _ = lid_state();
    }

    #[test]
    fn off_always_succeeds() {
        stop_inhibit();
        assert_eq!(set_exec_state(crate::keepalive::ES_OFF), 0);
    }

    #[test]
    fn autostart_toggle_roundtrip() {
        // Uses a temp XDG dir so it never touches the real home.
        let tmp = std::env::temp_dir().join(format!("meth-autostart-{}", std::process::id()));
        let prev = std::env::var_os("XDG_CONFIG_HOME");
        std::env::set_var("XDG_CONFIG_HOME", &tmp);
        assert!(set_autostart(true));
        let desktop = tmp.join("autostart/meth.desktop");
        assert!(desktop.exists());
        assert!(set_autostart(false));
        assert!(!desktop.exists());
        match prev {
            Some(v) => std::env::set_var("XDG_CONFIG_HOME", v),
            None => std::env::remove_var("XDG_CONFIG_HOME"),
        }
        let _ = fs::remove_dir_all(&tmp);
    }
}
