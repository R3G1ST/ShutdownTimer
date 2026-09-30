"""Смоук v1.0.1: полный цикл на собранном exe — старт, 60 с отсчёт, grace, dry-run.

Проверяет регрессию краша: приложение обязано пережить отрисовку кольца
(progress > 0) и завершить таймер без исключений.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time

EXE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "dist", "ShutdownTimer.exe")
APPDATA_DIR = os.path.join(os.environ["APPDATA"], "ShutdownTimer")
SETTINGS = os.path.join(APPDATA_DIR, "settings.json")
BACKUP = SETTINGS + ".smoke_backup"
DRY_LOG = os.path.join(APPDATA_DIR, "dry_run.log")
DRY_BACKUP = DRY_LOG + ".smoke_backup"
ERR = os.path.join(os.environ["TEMP"], "smoke_err.txt")

FULL_CYCLE_SECONDS = 78


def a(s: str) -> str:
    return s.encode("ascii", "backslashreplace").decode("ascii")


def buttons(win) -> list[str]:
    return [b.window_text() for b in win.descendants(control_type="Button")]


def main() -> int:
    running = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq ShutdownTimer.exe"],
        capture_output=True, text=True, check=False,
    )
    if "ShutdownTimer.exe" in running.stdout:
        print("stray instances exist — abort")
        return 2

    os.makedirs(APPDATA_DIR, exist_ok=True)
    backed_settings = os.path.exists(SETTINGS)
    backed_log = os.path.exists(DRY_LOG)
    if backed_settings:
        shutil.copy2(SETTINGS, BACKUP)
    if os.path.exists(DRY_LOG):
        shutil.copy2(DRY_LOG, DRY_BACKUP)
        os.remove(DRY_LOG)  # начинаем с пустого лога — строка только из этого прогона

    with open(SETTINGS, "w", encoding="utf-8") as fh:
        json.dump(
            {
                "mode": "countdown",
                "action": "sleep",
                "countdown_minutes": 1,
                "notify_lead_minutes": [10, 5, 1],
                "grace_seconds": 10,
                "confirm_close_to_tray": False,
                "mini_widget_enabled": False,
            },
            fh, ensure_ascii=False,
        )

    env = dict(os.environ)
    env["SHUTDOWNTIMER_DRY_RUN"] = "1"
    ferr = open(ERR, "w", encoding="utf-8", errors="replace")  # noqa: SIM115
    started_at = time.time()
    parent = subprocess.Popen([EXE], env=env, stderr=ferr, stdout=subprocess.DEVNULL)
    print("parent pid", parent.pid, "exe:", EXE)
    failures: list[str] = []

    try:
        from pywinauto import Application, findwindows

        hwnd = 0
        for _ in range(60):
            found = findwindows.find_windows(title_re=".*Таймер.*")
            if found:
                hwnd = found[0]
                break
            time.sleep(0.5)
        if not hwnd:
            print("no window, parent exit:", parent.poll())
            return 1
        print("window", hex(hwnd))

        app = Application(backend="uia").connect(handle=hwnd)
        win = app.window(handle=hwnd)
        import ctypes

        ctypes.windll.user32.SetForegroundWindow(hwnd)

        btn = win.child_window(title_re="^Запустить$", control_type="Button")
        btn.wait("enabled", timeout=10)
        time.sleep(0.3)
        btn.click()  # UIA Invoke

        time.sleep(2)
        names = buttons(win)
        print("buttons t+2:", [a(t) for t in names])
        if not any("Остановить" in t for t in names):
            failures.append("timer did not start (no «Остановить» at t+2)")

        grace_seen = False
        deadline = time.time() + FULL_CYCLE_SECONDS
        sample_i = 0
        while time.time() < deadline:
            code = parent.poll()
            if code is not None:
                failures.append(f"process died at t+{time.time()-started_at:.0f}s "
                                f"exit=0x{code & 0xFFFFFFFF:08X}")
                break
            sample_i += 1
            if sample_i % 10 == 0:
                try:
                    ctypes.windll.user32.SetForegroundWindow(hwnd)
                    win.capture_as_image()  # принудительная отрисовка
                except Exception as exc:  # noqa: BLE001
                    print("capture:", a(str(exc)))
            if not grace_seen and time.time() - started_at >= 62:
                try:
                    grace_seen = any("Отмена" in t for t in buttons(win))
                except Exception as exc:  # noqa: BLE001
                    print("grace read:", a(str(exc)))
            time.sleep(1)

        alive = parent.poll() is None
        print("alive after full cycle:", alive)
        if not alive and not failures:
            code = parent.returncode or 0
            failures.append(f"process exited 0x{code & 0xFFFFFFFF:08X}")
        if not grace_seen:
            failures.append("grace overlay («Отмена») not seen after t+62s")

        ferr.close()
        log_ok = False
        if os.path.exists(DRY_LOG):
            with open(DRY_LOG, "r", encoding="utf-8", errors="replace") as fh:
                log_ok = "action=sleep" in fh.read()
        print("dry_run.log has action=sleep:", log_ok)
        if not log_ok:
            failures.append("dry_run.log entry missing (action never executed)")

        with open(ERR, "r", encoding="utf-8", errors="replace") as fh:
            err = fh.read().strip()
        if err:
            print("stderr:", a(err[:2500]))
            failures.append("stderr not empty")

        if failures:
            print("SMOKE FAIL:")
            for item in failures:
                print("  -", item)
            return 1
        print("SMOKE OK: full 60s cycle + grace + dry-run action, no crash")
        return 0
    finally:
        subprocess.run(
            ["taskkill", "/IM", "ShutdownTimer.exe", "/F"],
            capture_output=True, check=False,
        )
        try:
            if not ferr.closed:
                ferr.close()
        except Exception as exc:  # noqa: BLE001
            print("ferr close:", a(str(exc)))
        if backed_settings and os.path.exists(BACKUP):
            shutil.move(BACKUP, SETTINGS)
        if backed_log and os.path.exists(DRY_BACKUP):
            shutil.move(DRY_BACKUP, DRY_LOG)
        print("settings/log restored")


if __name__ == "__main__":
    raise SystemExit(main())
