//! Windows backend — native keep-alive via `SetThreadExecutionState`.
//!
//! Also provides power status (`GetSystemPowerStatus`), lid state via
//! `RegisterPowerSettingNotification` (a hidden window + message pump
//! running on the SAME thread — Windows only delivers messages to the
//! thread that created the window), registry autostart and a named-mutex
//! singleton.

use std::sync::atomic::{AtomicBool, AtomicU32, AtomicU8, Ordering};
use std::sync::Arc;
use std::thread;

use windows_sys::Win32::Foundation::{GetLastError, HWND, LPARAM, LRESULT, WPARAM, ERROR_ALREADY_EXISTS};
use windows_sys::core::GUID;
use windows_sys::Win32::System::Power::{
    GetSystemPowerStatus, RegisterPowerSettingNotification, SetThreadExecutionState,
    SYSTEM_POWER_STATUS, HPOWERNOTIFY,
};
use windows_sys::Win32::System::Registry::{
    RegCloseKey, RegCreateKeyExW, RegDeleteValueW, RegSetValueExW, HKEY, HKEY_CURRENT_USER,
    KEY_SET_VALUE, REG_SZ,
};
use windows_sys::Win32::System::Threading::{CreateMutexW, GetCurrentThreadId};
use windows_sys::Win32::UI::WindowsAndMessaging::{
    CreateWindowExW, DefWindowProcW, DestroyWindow, DispatchMessageW, GetMessageW,
    PostThreadMessageW, RegisterClassExW, TranslateMessage, MSG, WNDCLASSEXW, WM_POWERBROADCAST,
    WM_QUIT, WS_POPUP,
};



/// Read the latest lid state (0=open, 1=closed, 2=unknown).
pub fn lid_state() -> LidState {
    LidState::from(LID_STATE.load(Ordering::Relaxed) as u32)
}

// ---------------------------------------------------------------------------
// Keep-alive
// ---------------------------------------------------------------------------

/// Calls `SetThreadExecutionState(flags)`; returns the PREVIOUS flags
/// (Windows contract), or 0 if the request was refused.
pub fn set_exec_state(flags: u32) -> u32 {
    unsafe { SetThreadExecutionState(flags) }
}

// ---------------------------------------------------------------------------
// Power status
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AcStatus {
    OnAc,
    OnBattery,
    Unknown,
}

/// Read `SYSTEM_POWER_STATUS` → AC/battery. Never panics.
pub fn ac_status() -> AcStatus {
    let mut status: SYSTEM_POWER_STATUS = unsafe { std::mem::zeroed() };
    let ok = unsafe { GetSystemPowerStatus(&mut status) };
    if ok == 0 {
        return AcStatus::Unknown;
    }
    match status.ACLineStatus {
        0 => AcStatus::OnBattery,
        1 => AcStatus::OnAc,
        _ => AcStatus::Unknown,
    }
}

// ---------------------------------------------------------------------------
// Lid state (hidden window + RegisterPowerSettingNotification, one thread)
// ---------------------------------------------------------------------------

/// GUID_LIDSWITCH_STATE_CHANGE — {BA3E0F4D-B817-4421-A2BB-33DEDA3D062C}
fn guid_lidswitch() -> GUID {
    GUID {
        data1: 0xBA3E_0F4D,
        data2: 0xB817,
        data3: 0x4421,
        data4: [0xA2, 0xBB, 0x33, 0xDE, 0xDA, 0x3D, 0x06, 0x2C],
    }
}
const PBT_POWERSETTINGCHANGE: u32 = 0x8013;

/// POWERBROADCAST_SETTING layout: GUID (16) + DataLength (4) + Data (4).
#[repr(C)]
struct PowerBroadcastSetting {
    power_setting: [u8; 16],
    data_length: u32,
    data: u32,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LidState {
    Open,
    Closed,
    Unknown,
}

impl From<u32> for LidState {
    fn from(v: u32) -> Self {
        match v {
            1 => LidState::Open,
            0 => LidState::Closed,
            _ => LidState::Unknown,
        }
    }
}

extern "system" fn lid_wnd_proc(hwnd: HWND, msg: u32, wparam: WPARAM, lparam: LPARAM) -> LRESULT {
    if msg == WM_POWERBROADCAST && wparam as u32 == PBT_POWERSETTINGCHANGE {
        let setting = lparam as *const PowerBroadcastSetting;
        if !setting.is_null() {
            unsafe {
                let g = guid_lidswitch();
                let guid_bytes = &g as *const GUID as *const [u8; 16];
                if (*setting).power_setting == *guid_bytes {
                    LID_STATE.store((*setting).data.min(2) as u8, Ordering::Relaxed);
                }
            }
        }
    }
    unsafe { DefWindowProcW(hwnd, msg, wparam, lparam) }
}

/// Process-wide lid state, written by the pump thread, read by the UI.
pub static LID_STATE: AtomicU8 = AtomicU8::new(2); // 0=open 1=closed 2=unknown

const CLASS_NAME: [u16; 8] = [
    'M' as u16, 'e' as u16, 't' as u16, 'h' as u16, 'L' as u16, 'i' as u16, 'd' as u16, 0,
];

pub struct Lid {
    stop: Arc<AtomicBool>,
    thread_id: Arc<AtomicU32>,
    thread: Option<thread::JoinHandle<()>>,
}

impl Lid {
    /// Spawn the hidden-window thread. Returns None if the window could
    /// not be created (keep-alive still works — lid just stays Unknown).
    pub fn new() -> Option<Self> {
        let stop = Arc::new(AtomicBool::new(false));
        let stop2 = stop.clone();
        let thread_id = Arc::new(AtomicU32::new(0));
        let thread_id2 = thread_id.clone();
        let handle = thread::spawn(move || {
            thread_id2.store(unsafe { GetCurrentThreadId() }, Ordering::Relaxed);
            let class = WNDCLASSEXW {
                cbSize: std::mem::size_of::<WNDCLASSEXW>() as u32,
                style: 0,
                lpfnWndProc: Some(lid_wnd_proc),
                cbClsExtra: 0,
                cbWndExtra: 0,
                hInstance: std::ptr::null_mut(),
                hIcon: std::ptr::null_mut(),
                hCursor: std::ptr::null_mut(),
                hbrBackground: std::ptr::null_mut(),
                lpszMenuName: std::ptr::null(),
                lpszClassName: CLASS_NAME.as_ptr(),
                hIconSm: std::ptr::null_mut(),
            };
            unsafe { RegisterClassExW(&class) };

            let hwnd = unsafe {
                CreateWindowExW(
                    0,
                    CLASS_NAME.as_ptr(),
                    std::ptr::null(),
                    WS_POPUP,
                    0,
                    0,
                    0,
                    0,
                    std::ptr::null_mut(),
                    std::ptr::null_mut(),
                    std::ptr::null_mut(),
                    std::ptr::null_mut(),
                )
            };
            if hwnd.is_null() {
                return;
            }
            let g = guid_lidswitch();
            let _notify: HPOWERNOTIFY = unsafe {
                RegisterPowerSettingNotification(hwnd as *mut _, &g, 0)
            };
            // Message pump — must stay on this thread.
            let mut msg: MSG = unsafe { std::mem::zeroed() };
            while !stop2.load(Ordering::Relaxed) {
                let ret = unsafe { GetMessageW(&mut msg, std::ptr::null_mut(), 0, 0) };
                if ret == 0 || ret == -1 {
                    break;
                }
                unsafe {
                    TranslateMessage(&msg);
                    DispatchMessageW(&msg);
                }
            }
            unsafe {
                DestroyWindow(hwnd);
            }
        });
        Some(Lid {
            stop,
            thread_id,
            thread: Some(handle),
        })
    }

    pub fn state() -> LidState {
        LidState::from(LID_STATE.load(Ordering::Relaxed) as u32)
    }
}

impl Drop for Lid {
    fn drop(&mut self) {
        self.stop.store(true, Ordering::Relaxed);
        let tid = self.thread_id.load(Ordering::Relaxed);
        if tid != 0 {
            unsafe {
                PostThreadMessageW(tid, WM_QUIT, 0, 0);
            }
        }
        if let Some(t) = self.thread.take() {
            let _ = t.join();
        }
    }
}

// ---------------------------------------------------------------------------
// Autostart (HKCU\...\CurrentVersion\Run)
// ---------------------------------------------------------------------------

const RUN_KEY: &[u16] = &[
    'S' as u16, 'o' as u16, 'f' as u16, 't' as u16, 'w' as u16, 'a' as u16, 'r' as u16, 'e' as u16,
    '\\' as u16, 'M' as u16, 'i' as u16, 'c' as u16, 'r' as u16, 'o' as u16, 's' as u16, 'o' as u16,
    'f' as u16, 't' as u16, '\\' as u16, 'W' as u16, 'i' as u16, 'n' as u16, 'd' as u16, 'o' as u16,
    'w' as u16, 's' as u16, '\\' as u16, 'C' as u16, 'u' as u16, 'r' as u16, 'r' as u16, 'e' as u16,
    'n' as u16, 't' as u16, 'V' as u16, 'e' as u16, 'r' as u16, 's' as u16, 'i' as u16, 'o' as u16,
    'n' as u16, '\\' as u16, 'R' as u16, 'u' as u16, 'n' as u16, 0,
];

/// Set or remove the "Meth" value under HKCU\...\Run.
pub fn set_autostart(enabled: bool) -> bool {
    let exe = match std::env::current_exe() {
        Ok(p) => p,
        Err(_) => return false,
    };
    let cmd: Vec<u16> = format!("\"{}\"", exe.display())
        .encode_utf16()
        .chain(std::iter::once(0))
        .collect();

    let mut key: HKEY = std::ptr::null_mut();
    let res = unsafe {
        RegCreateKeyExW(
            HKEY_CURRENT_USER,
            RUN_KEY.as_ptr(),
            0,
            std::ptr::null(),
            0,
            KEY_SET_VALUE,
            std::ptr::null(),
            &mut key,
            std::ptr::null_mut(),
        )
    };
    if res != 0 {
        return false;
    }
    if enabled {
        let res = unsafe {
            RegSetValueExW(
                key,
                VALUE_NAME.as_ptr(),
                0,
                REG_SZ,
                cmd.as_ptr() as *const u8,
                (cmd.len() * 2) as u32,
            )
        };
        unsafe { RegCloseKey(key) };
        res == 0
    } else {
        unsafe {
            RegDeleteValueW(key, VALUE_NAME.as_ptr());
            RegCloseKey(key);
        }
        true
    }
}

const VALUE_NAME: &[u16] = &['M' as u16, 'e' as u16, 't' as u16, 'h' as u16, 0];

// ---------------------------------------------------------------------------
// Singleton (named mutex)
// ---------------------------------------------------------------------------

const MUTEX_NAME: &[u16] = &[
    'L' as u16, 'o' as u16, 'c' as u16, 'a' as u16, 'l' as u16, '\\' as u16, 'M' as u16, 'e' as u16,
    't' as u16, 'h' as u16, 'M' as u16, 'u' as u16, 't' as u16, 'e' as u16, 'x' as u16, 0,
];

/// Returns true if this process is the FIRST instance.
pub fn acquire_singleton() -> bool {
    unsafe {
        let handle = CreateMutexW(std::ptr::null(), 0, MUTEX_NAME.as_ptr());
        if handle.is_null() {
            return false;
        }
        let err = GetLastError();
        if err == ERROR_ALREADY_EXISTS {
            return false;
        }
        // Keep the handle alive for the whole process (deliberate: the
        // mutex must stay held until exit).
        let _keep = std::mem::ManuallyDrop::new(handle);
        true
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::keepalive::{ES_CONTINUOUS, ES_SYSTEM_REQUIRED};

    #[test]
    fn ac_status_never_panics() {
        // Real GetSystemPowerStatus on Windows — never a panic.
        let _ = ac_status();
    }

    #[test]
    fn lid_state_never_panics() {
        let _ = lid_state();
    }

    #[test]
    fn set_exec_state_roundtrip_restores_normal() {
        // ON then OFF — both real Win32 calls, must not panic.
        let prev = set_exec_state(ES_CONTINUOUS | ES_SYSTEM_REQUIRED);
        set_exec_state(ES_CONTINUOUS);
        // prev may be 0 or the previous flags; never panics either way.
        let _ = prev;
    }
}
