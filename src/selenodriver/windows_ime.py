from __future__ import annotations

"""Legacy Windows OS-input helpers.

These functions remain importable for compatibility. Selenodriver's input modes
do not use global Windows IME state or SendInput; ``mode="ime"`` and its
``mode="jamo"`` alias use the renderer-scoped CDP IME composition API instead.
"""

import ctypes
import os
import time
from ctypes import wintypes
from typing import Any


VK_HANGUL = 0x15
KEYEVENTF_KEYUP = 0x0002
INPUT_KEYBOARD = 1


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class _INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("ki", _KEYBDINPUT)]


def is_windows() -> bool:
    return os.name == "nt"


def _apis() -> tuple[Any, Any] | None:
    if not is_windows():
        return None
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    imm32 = ctypes.WinDLL("imm32", use_last_error=True)
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    imm32.ImmGetDefaultIMEWnd.argtypes = [wintypes.HWND]
    imm32.ImmGetDefaultIMEWnd.restype = wintypes.HWND
    user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.SendMessageW.restype = wintypes.LPARAM
    user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(_INPUT), ctypes.c_int]
    user32.SendInput.restype = wintypes.UINT
    user32.VkKeyScanW.argtypes = [wintypes.WCHAR]
    user32.VkKeyScanW.restype = ctypes.c_short
    return user32, imm32


def is_korean_input() -> bool | None:
    """Return the foreground window's IME native state on Windows."""
    apis = _apis()
    if apis is None:
        return None
    user32, imm32 = apis
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return None
    ime_hwnd = imm32.ImmGetDefaultIMEWnd(hwnd)
    if not ime_hwnd:
        return None
    conversion_mode = user32.SendMessageW(ime_hwnd, 0x0283, 0x0001, 0)
    return bool(conversion_mode & 0x0001)


def _send_vk(vk: int, flags: int = 0) -> None:
    apis = _apis()
    if apis is None:
        raise OSError("Windows SendInput is unavailable")
    user32, _ = apis
    input_event = _INPUT(
        type=INPUT_KEYBOARD,
        ki=_KEYBDINPUT(wVk=vk, dwFlags=flags),
    )
    if user32.SendInput(1, ctypes.byref(input_event), ctypes.sizeof(_INPUT)) != 1:
        raise ctypes.WinError(ctypes.get_last_error())


def press_hangul_key() -> None:
    try:
        _send_vk(VK_HANGUL)
        _send_vk(VK_HANGUL, KEYEVENTF_KEYUP)
    except Exception:
        pyautogui = _optional_pyautogui()
        if pyautogui is None:
            raise
        pyautogui.press("hangul")


def ensure_korean_input() -> bool:
    state = is_korean_input()
    if state is True:
        return True
    if state is None:
        return False
    press_hangul_key()
    time.sleep(0.03)
    return is_korean_input() is True


def ensure_english_input() -> bool:
    state = is_korean_input()
    if state is False:
        return True
    if state is None:
        return False
    press_hangul_key()
    time.sleep(0.03)
    return is_korean_input() is False


def send_os_text(text: str, *, delay: float = 0.0) -> None:
    """Send ASCII/2-beolsik key text through Windows SendInput."""
    try:
        apis = _apis()
        if apis is None:
            raise OSError("Windows SendInput is unavailable")
        user32, _ = apis
        chars = list(str(text))
        for index, char in enumerate(chars):
            encoded = user32.VkKeyScanW(char)
            if encoded == -1:
                raise ValueError(f"Cannot map character to a Windows key: {char!r}")
            value = encoded & 0xFF
            shift_state = (encoded >> 8) & 0xFF
            if shift_state & 1:
                _send_vk(0x10)
            _send_vk(value)
            _send_vk(value, KEYEVENTF_KEYUP)
            if shift_state & 1:
                _send_vk(0x10, KEYEVENTF_KEYUP)
            if delay > 0 and index < len(chars) - 1:
                time.sleep(delay)
    except Exception:
        pyautogui = _optional_pyautogui()
        if pyautogui is None:
            raise
        pyautogui.write(str(text), interval=max(0.0, delay))


def _optional_pyautogui() -> Any | None:
    try:
        import pyautogui
    except ImportError:
        return None
    return pyautogui
