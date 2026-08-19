"""Meth Windows — Lid (détection du capot).

Windows n'expose pas l'état du capot via une API de requête simple ; le
mécanisme documenté est un ABONNEMENT aux changements d'état d'alimentation :

    RegisterPowerSettingNotification(hwnd, &GUID_LIDSWITCH_STATE_CHANGE,
                                     DEVICE_NOTIFY_WINDOW_HANDLE)

reçoit WM_POWERBROADCAST / PBT_POWERSETTINGCHANGE avec une structure
POWERBROADCAST_SETTING dont les Data indiquent l'état du capot (0 = fermé,
1 = ouvert).

Meth fait son propre enregistrement en stdlib :
- une fenêtre Windows CACHÉE est créée (CreateWindowEx) pour recevoir le
  message — sans UI visible ;
- un thread de messages la sert (GetMessage / DispatchMessage) ;
- l'état est publié aux abonnés dès qu'il change.

Honnêteté : si l'enregistrement échoue (ex. poste fixe sans capot, droits,
API indisponible), l'état reste « INCONNU » — jamais inventé. Sur un
portable Windows 10/11, GUID_LIDSWITCH_STATE_CHANGE fonctionne.
"""
from __future__ import annotations

import ctypes
import struct
import threading
import time
from ctypes import wintypes
from typing import Callable, List, Optional

# GUID_LIDSWITCH_STATE_CHANGE (Microsoft, publiquement documenté).
GUID_LIDSWITCH_STATE_CHANGE = bytes.fromhex(
    "C8D4C1D4"   # Data1 (little-endian : D4C1D4C8)
    "02D4"       # Data2
    "40FB"       # Data3
    "809ADB21665FC6EA"  # Data4
)

# Valeurs documentées de l'événement.
LID_CLOSED = 0
LID_OPEN = 1

WM_POWERBROADCAST = 0x0218
PBT_POWERSETTINGCHANGE = 0x8013
DEVICE_NOTIFY_WINDOW_HANDLE = 0x00000000

# Fenêtre cachée : classe + proc par défaut.
# Sur 64 bits, LRESULT est un LONG_PTR (64 bits) — utiliser c_ssize_t,
# pas c_long (sinon la fenêtre cachée échoue à la création).
WNDPROC = ctypes.WINFUNCTYPE(
    ctypes.c_ssize_t, wintypes.HWND, wintypes.UINT,
    wintypes.WPARAM, wintypes.LPARAM)


class WNDCLASSW(ctypes.Structure):
    """Équivalent ctypes de WNDCLASSW (winuser.h) — ctypes ne l'expose pas."""
    _fields_ = [
        ("style", wintypes.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HANDLE),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
    ]


class POWERBROADCAST_SETTING(ctypes.Structure):
    _fields_ = [
        ("PowerSetting", ctypes.c_byte * 16),
        ("DataLength", wintypes.DWORD),
        ("Data", wintypes.DWORD),  # 1er DWORD : état capot pour LIDSWITCH
    ]


class Lid:
    """Abonnement aux changements d'état du capot (best-effort, honnête).

    ``listener(state)`` reçoit "OUVERT" / "FERMÉ" / "INCONNU" à chaque
    changement. ``start()`` lance le thread de messages ; ``stop()``
    libère proprement. ``state`` reflète le dernier état connu.
    """

    def __init__(self, logger: Optional[Callable[[str, str], None]] = None) -> None:
        self._logger = logger
        self._listeners: List[Callable[[str], None]] = []
        self._state: str = "INCONNU"
        self._thread: Optional[threading.Thread] = None
        self._hwnd = None
        self._reg_handle = None
        self._stop_event = threading.Event()
        # Le WNDPROC doit SURVIVRE tant que la fenêtre existe (sinon le GC
        # libère le callback → RegisterClassW/CreateWindow échouent).
        self._wnd_proc_ref = None

    def log(self, level: str, msg: str) -> None:
        if self._logger:
            try:
                self._logger(level, msg)
            except Exception:
                pass

    @property
    def state(self) -> str:
        return self._state

    def on_change(self, listener: Callable[[str], None]) -> None:
        if listener not in self._listeners:
            self._listeners.append(listener)

    def _publish(self, state: str) -> None:
        if state == self._state:
            return
        self._state = state
        self.log("info", f"capot: {state}")
        for listener in list(self._listeners):
            try:
                listener(state)
            except Exception:
                pass

    # -- partie native (ctypes, thread dédié) ---------------------------------
    def _message_loop(self) -> None:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        # 1. Classe de fenêtre cachée. (argtypes explicites : hInstance est
        #    un HANDLE 64 bits — sans signature, ctypes tronque/overflow.)
        kernel32.GetModuleHandleW.restype = wintypes.HMODULE
        kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
        kernel32.GetLastError.restype = wintypes.DWORD
        user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]
        user32.RegisterClassW.restype = wintypes.ATOM
        user32.CreateWindowExW.argtypes = [
            wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
            ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
            wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID]
        user32.CreateWindowExW.restype = wintypes.HWND

        wc = WNDCLASSW()
        self._wnd_proc_ref = WNDPROC(self._wnd_proc)
        wc.lpfnWndProc = self._wnd_proc_ref
        wc.hInstance = kernel32.GetModuleHandleW(None)
        wc.lpszClassName = "MethLidWindow"
        atom = user32.RegisterClassW(ctypes.byref(wc))
        if not atom:
            self.log("error", "Lid: RegisterClassW a échoué → capot INCONNU")
            return

        # 2. Fenêtre cachée (0x00 = pas de styles visibles).
        hwnd = user32.CreateWindowExW(
            0, "MethLidWindow", "MethLid", 0,
            0, 0, 0, 0, None, None, wc.hInstance, None)
        if not hwnd:
            self.log("error", "Lid: CreateWindow a échoué → capot INCONNU")
            return
        self._hwnd = hwnd

        # 3. Abonnement aux changements d'état du capot.
        #    RegisterPowerSettingNotification(HWND, GUID*, DEVICE_NOTIFY_WINDOW_HANDLE)
        user32.RegisterPowerSettingNotification.restype = wintypes.HANDLE
        user32.RegisterPowerSettingNotification.argtypes = [
            wintypes.HWND, ctypes.c_void_p, wintypes.DWORD]
        guid_buf = ctypes.create_string_buffer(GUID_LIDSWITCH_STATE_CHANGE, 16)
        handle = user32.RegisterPowerSettingNotification(
            hwnd, ctypes.cast(guid_buf, ctypes.c_void_p),
            DEVICE_NOTIFY_WINDOW_HANDLE)
        if not handle:
            self.log("error", "Lid: RegisterPowerSettingNotification a échoué"
                              " → capot INCONNU")
            return
        self._reg_handle = handle
        self.log("debug", "Lid: abonnement capot actif (GUID_LIDSWITCH)")

        # 4. Boucle de messages (bloquante, propre).
        user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND,
                                       wintypes.UINT, wintypes.UINT]
        user32.GetMessageW.restype = ctypes.c_int
        user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
        user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
        msg = wintypes.MSG()
        while not self._stop_event.is_set():
            ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if ret <= 0:
                break
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

    def _wnd_proc(self, hwnd, uMsg, wParam, lParam):
        if uMsg == WM_POWERBROADCAST and wParam == PBT_POWERSETTINGCHANGE:
            try:
                data = ctypes.string_at(lParam, ctypes.sizeof(POWERBROADCAST_SETTING))
                setting = POWERBROADCAST_SETTING.from_buffer_copy(data)
                lid_state = setting.Data
                self._publish("FERMÉ" if lid_state == LID_CLOSED else "OUVERT")
            except Exception:
                pass
        try:
            user32 = ctypes.windll.user32
            user32.DefWindowProcW.restype = ctypes.c_ssize_t
            user32.DefWindowProcW.argtypes = [
                wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
            return user32.DefWindowProcW(hwnd, uMsg, wParam, lParam)
        except Exception:
            return 0

    # -- cycle de vie ----------------------------------------------------------
    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._message_loop, name="MethLid", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._hwnd:
            try:
                ctypes.windll.user32.PostMessageW(self._hwnd, 0x0012, 0, 0)  # WM_QUIT
            except Exception:
                pass
        # Attend la fin du thread (timeout) puis détruit la fenêtre cachée.
        if self._thread is not None:
            try:
                self._thread.join(timeout=1.5)
            except Exception:
                pass
        if self._hwnd:
            try:
                ctypes.windll.user32.DestroyWindow(self._hwnd)
            except Exception:
                pass
            self._hwnd = None
        if self._reg_handle:
            try:
                ctypes.windll.user32.UnregisterPowerSettingNotification(
                    self._reg_handle)
            except Exception:
                pass
            self._reg_handle = None
        self._thread = None
