from __future__ import annotations

import winreg

from app.paths import exe_path

_KEY = r"Software\Classes\shutdowntimer"
_COMMAND_KEY = _KEY + r"\shell\open\command"


def is_registered() -> bool:
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _COMMAND_KEY, 0, winreg.KEY_READ
        ) as key:
            value, _ = winreg.QueryValueEx(key, "")
    except OSError:
        return False
    return bool(str(value).strip())


def register_protocol(exe_path_value: str | None = None) -> bool:
    path = exe_path_value if exe_path_value is not None else exe_path()
    command = f'"{path}" "%1"'
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _KEY) as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "URL:ShutdownTimer Protocol")
            winreg.SetValueEx(key, "URL Protocol", 0, winreg.REG_SZ, "")
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _COMMAND_KEY) as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, command)
        return True
    except OSError:
        return False


def unregister_protocol() -> None:
    for suffix in (r"\shell\open\command", r"\shell\open", r"\shell", ""):
        try:
            winreg.DeleteKeyEx(winreg.HKEY_CURRENT_USER, _KEY + suffix)
        except OSError:
            pass
