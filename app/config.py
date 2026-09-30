from __future__ import annotations

import json
import os
from typing import Any

DEFAULTS: dict[str, Any] = {
    "mode": "countdown",
    "action": "shutdown",
    "countdown_minutes": 30,
    "exact_time": "23:00",
    "idle_minutes": 15,
    "notify_lead_minutes": [10, 5, 1],
    "grace_seconds": 10,
    "autostart": False,
    "confirm_close_to_tray": True,
    "mini_widget_enabled": True,
    "dry_run": False,
}


def _default_path() -> str:
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, "ShutdownTimer", "settings.json")


class SettingsManager:
    """JSON в %APPDATA%\\ShutdownTimer\\settings.json"""

    def __init__(self, path: str | None = None) -> None:
        self._path = path or _default_path()
        self._data: dict[str, Any] = {}
        self.load()

    @property
    def path(self) -> str:
        return self._path

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def save(self) -> None:
        directory = os.path.dirname(self._path)
        tmp_path = self._path + ".tmp"
        try:
            if directory:
                os.makedirs(directory, exist_ok=True)
            with open(tmp_path, "w", encoding="utf-8") as handle:
                json.dump(self._data, handle, ensure_ascii=False, indent=2)
            os.replace(tmp_path, self._path)
        except OSError:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except OSError:
                pass

    def load(self) -> None:
        data: dict[str, Any] = {}
        try:
            with open(self._path, "r", encoding="utf-8") as handle:
                loaded = json.load(handle)
            if isinstance(loaded, dict):
                data = loaded
        except (OSError, ValueError):
            data = {}
        for key, value in DEFAULTS.items():
            data.setdefault(key, _copy(value))
        self._data = data


def _copy(value: Any) -> Any:
    if isinstance(value, list):
        return list(value)
    if isinstance(value, dict):
        return dict(value)
    return value
