//! Meth — platform backends (Windows + Linux, not macOS).
//!
//! Selects the native implementation for the current platform:
//! - Windows → `windows.rs`   (SetThreadExecutionState, registry, …)
//! - Linux   → `linux.rs`     (systemd-inhibit, sysfs, ACPI, autostart)
//! - other (macOS, BSD, …) → honest fallback: the app runs, but the
//!   keep-alive is unavailable (`set_exec_state` → 0, Power/Lid → UNKNOWN).
//!   Meth never claims to keep the system awake when it has no way to.

#[cfg(target_os = "windows")]
pub mod windows;
#[cfg(target_os = "linux")]
pub mod linux;
#[cfg(not(any(target_os = "windows", target_os = "linux")))]
pub mod fallback;

/// Platform name reported in the UI/status ("windows" | "linux" | "other").
pub fn platform_name() -> &'static str {
    if cfg!(target_os = "windows") {
        "windows"
    } else if cfg!(target_os = "linux") {
        "linux"
    } else {
        "other"
    }
}

// Re-export the active backend behind one stable API.
#[cfg(target_os = "windows")]
pub use windows as active;
#[cfg(target_os = "linux")]
pub use linux as active;
#[cfg(not(any(target_os = "windows", target_os = "linux")))]
pub use fallback as active;
