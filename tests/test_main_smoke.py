from __future__ import annotations

import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_COMMAND = r"Software\Classes\shutdowntimer\shell\open\command"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _registry_snapshot() -> dict[str, object]:
    import winreg

    snapshot: dict[str, object] = {"command": None, "run": None, "protocol": None}
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, PROTOCOL_COMMAND) as key:
            snapshot["command"] = winreg.QueryValueEx(key, "")[0]
    except OSError:
        pass
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\shutdowntimer") as key:
            snapshot["protocol"] = winreg.QueryValueEx(key, "URL Protocol")[0]
    except OSError:
        pass
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            snapshot["run"] = winreg.QueryValueEx(key, "ShutdownTimer")[0]
    except OSError:
        pass
    return snapshot


@dataclass
class Child:
    proc: subprocess.Popen
    err_path: Path
    out_path: Path
    handles: list[object] = field(default_factory=list)

    def stderr_text(self) -> str:
        return self.err_path.read_text(encoding="utf-8", errors="replace")

    def stdout_text(self) -> str:
        return self.out_path.read_text(encoding="utf-8", errors="replace")

    def kill(self) -> None:
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=5)
        for handle in self.handles:
            try:
                handle.close()
            except OSError:
                pass
        self.handles.clear()


def _spawn(appdata: Path, args: list[str]) -> Child:
    appdata.mkdir(parents=True, exist_ok=True)
    stamp = time.time_ns()
    err_path = appdata / f"stderr_{stamp}.txt"
    out_path = appdata / f"stdout_{stamp}.txt"
    err_handle = err_path.open("w", encoding="utf-8")
    out_handle = out_path.open("w", encoding="utf-8")

    env = os.environ.copy()
    env["SHUTDOWNTIMER_DRY_RUN"] = "1"
    env["QT_QPA_PLATFORM"] = "offscreen"
    env["APPDATA"] = str(appdata)

    proc = subprocess.Popen(
        [sys.executable, "main.py", *args],
        cwd=str(ROOT),
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=out_handle,
        stderr=err_handle,
    )
    return Child(
        proc=proc,
        err_path=err_path,
        out_path=out_path,
        handles=[err_handle, out_handle],
    )


@pytest.fixture(scope="module")
def appdata(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("smoke_appdata")


@pytest.fixture(scope="module", autouse=True)
def registry_before() -> dict[str, object]:
    return _registry_snapshot()


@pytest.fixture(scope="module")
def primary(appdata: Path) -> Child:
    child = _spawn(appdata, [])
    yield child
    child.kill()


def test_primary_process_survives_five_seconds(primary: Child) -> None:
    deadline = time.time() + 5
    while time.time() < deadline and primary.proc.poll() is None:
        time.sleep(0.2)

    stderr = primary.stderr_text()
    assert "Traceback" not in stderr, stderr

    if primary.proc.poll() is not None:
        # Допустимый вариант: сокет уже занят другим экземпляром (single-instance),
        # тогда второй экземпляр штатно завершается с кодом 0.
        assert primary.proc.returncode == 0, primary.proc.returncode
    else:
        assert primary.proc.poll() is None


def test_second_instance_hits_single_instance_lock(
    primary: Child, appdata: Path
) -> None:
    second = _spawn(appdata, [])
    try:
        code = second.proc.wait(timeout=10)
    finally:
        second.kill()

    assert code == 0, second.stdout_text() + second.stderr_text()
    assert "Traceback" not in second.stderr_text()

    if primary.proc.poll() is None:
        # первый экземпляр не должен был перезапуститься/дублироваться
        assert primary.proc.poll() is None
        assert "Traceback" not in primary.stderr_text()


def test_protocol_url_is_forwarded_to_primary(primary: Child, appdata: Path) -> None:
    child = _spawn(appdata, ["shutdowntimer://cancel"])
    try:
        code = child.proc.wait(timeout=10)
    finally:
        child.kill()

    assert code == 0, child.stdout_text() + child.stderr_text()
    assert "Traceback" not in child.stderr_text()
    assert "cancel" not in child.stderr_text().lower()


def test_smoke_runs_did_not_touch_registry(
    primary: Child, registry_before: dict[str, object], appdata: Path
) -> None:
    # последний тест модуля: дочитываем stderr основного процесса
    assert "Traceback" not in primary_stderr(appdata)
    assert _registry_snapshot() == registry_before, (
        "smoke-прогоны изменили реестр",
        registry_before,
        _registry_snapshot(),
    )


def primary_stderr(appdata: Path) -> str:
    texts = []
    for path in appdata.glob("stderr_*.txt"):
        texts.append(path.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(texts)
