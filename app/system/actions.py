from __future__ import annotations

import ctypes
import os
import subprocess
from datetime import datetime

ACTIONS = ("shutdown", "restart", "sleep", "hibernate")

_ERRORS = (
    OSError,
    ValueError,
    TypeError,
    AttributeError,
    KeyError,
    subprocess.SubprocessError,
    ctypes.ArgumentError,
)


def _log_path() -> str:
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, "ShutdownTimer", "dry_run.log")


def _as_int(value: object, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _stamp() -> str:
    return f"{datetime.now().astimezone():%Y-%m-%d %H:%M:%S}"


def is_dry_run() -> bool:
    return os.environ.get("SHUTDOWNTIMER_DRY_RUN") == "1"


def _append_log(line: str) -> str:
    path = _log_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except OSError as exc:
        return f"error: {exc}"
    return line


def _run(command: list[str]) -> None:
    subprocess.run(command, creationflags=subprocess.CREATE_NO_WINDOW, check=False)


def perform(action: str, *, grace_seconds: int = 10, dry_run: bool | None = None) -> str:
    enabled = is_dry_run() if dry_run is None else bool(dry_run)
    grace = max(0, _as_int(grace_seconds, 0))
    if enabled:
        return _append_log(f"{_stamp()} [DRY-RUN] action={action} grace={grace}")
    try:
        if action == "shutdown":
            _run(["shutdown", "/s", "/t", str(grace)])
            return f"Запланировано выключение через {grace} с"
        if action == "restart":
            _run(["shutdown", "/r", "/t", str(grace)])
            return f"Запланирована перезагрузка через {grace} с"
        if action == "sleep":
            if not ctypes.windll.powrprof.SetSuspendState(0, 1, 0):
                return "error: не удалось перевести компьютер в сон"
            return "Компьютер переведён в сон"
        if action == "hibernate":
            if not ctypes.windll.powrprof.SetSuspendState(1, 1, 0):
                return "error: не удалось включить гибернацию"
            return "Гибернация включена"
        return f"error: неизвестное действие {action}"
    except _ERRORS as exc:
        return f"error: {exc}"


def cancel() -> str:
    if is_dry_run():
        return _append_log(f"{_stamp()} [DRY-RUN] action=cancel")
    try:
        _run(["shutdown", "/a"])
        return "Запланированное отключение отменено"
    except _ERRORS as exc:
        return f"error: {exc}"
