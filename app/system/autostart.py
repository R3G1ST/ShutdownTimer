from __future__ import annotations

import winreg

from app.paths import exe_path

_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_NAME = "ShutdownTimer"


def is_enabled() -> bool:
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_READ
        ) as key:
            value, _ = winreg.QueryValueEx(key, _NAME)
    except OSError:
        return False
    return bool(str(value).strip())


def set_enabled(enable: bool, exe_path_value: str | None = None) -> bool:
    path = exe_path_value if exe_path_value is not None else exe_path()
    try:
        if enable:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as key:
                winreg.SetValueEx(key, _NAME, 0, winreg.REG_SZ, f'"{path}"')
            return True
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.DeleteValue(key, _NAME)
        return True
    except FileNotFoundError:
        return not enable
    except OSError:
        return False
