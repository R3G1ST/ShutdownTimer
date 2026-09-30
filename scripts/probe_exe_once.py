"""Один чистый прогон установленного exe: клик «Запустить» → ждём краш."""
from __future__ import annotations

import json
import os
import subprocess
import time

EXE = r"C:\Users\R3G1S\AppData\Local\Programs\ShutdownTimer\ShutdownTimer.exe"
APPDATA_DIR = os.path.join(os.environ["APPDATA"], "ShutdownTimer")
SETTINGS = os.path.join(APPDATA_DIR, "settings.json")
BACKUP = SETTINGS + ".probe_backup"
ERR = os.path.join(os.environ["TEMP"], "probe1_err.txt")


def a(s: str) -> str:
    return s.encode("ascii", "backslashreplace").decode("ascii")


def main() -> int:
    running = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq ShutdownTimer.exe"],
        capture_output=True,
        text=True,
        check=False,
    )
    if "ShutdownTimer.exe" in running.stdout:
        print("stray instances exist — abort")
        return 2

    backed = os.path.exists(SETTINGS)
    if backed:
        import shutil

        shutil.copy2(SETTINGS, BACKUP)

    os.makedirs(APPDATA_DIR, exist_ok=True)
    with open(SETTINGS, "w", encoding="utf-8") as fh:
        json.dump(
            {
                "mode": "countdown",
                "action": "sleep",
                "countdown_minutes": 1,
                "notify_lead_minutes": [10, 5, 1],
                "grace_seconds": 10,
                "confirm_close_to_tray": False,
                "mini_widget_enabled": True,
            },
            fh,
            ensure_ascii=False,
        )

    env = dict(os.environ)
    env["SHUTDOWNTIMER_DRY_RUN"] = "1"
    ferr = open(ERR, "w", encoding="utf-8", errors="replace")  # noqa: SIM115
    parent = subprocess.Popen([EXE], env=env, stderr=ferr, stdout=subprocess.DEVNULL)
    print("parent pid", parent.pid)

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
        btn = win.child_window(title_re="^Запустить$", control_type="Button")
        btn.wait("enabled", timeout=10)
        time.sleep(0.3)
        btn.click()  # UIA Invoke — не зависит от перекрытия окна мышью

        time.sleep(1.5)
        texts = [b.window_text() for b in win.descendants(control_type="Button")]
        print("buttons after click:", [a(t) for t in texts])
        started = any("Остановить" in t for t in texts)
        print("timer started:", started)

        deadline = time.time() + 30
        code = None
        while time.time() < deadline:
            code = parent.poll()
            if code is not None:
                break
            time.sleep(0.5)
        if code is None:
            print("alive after 30s (no crash), killing tree")
            subprocess.run(
                ["taskkill", "/PID", str(parent.pid), "/T", "/F"], check=False
            )
            code = parent.wait(timeout=10)
        print(f"parent exit: {code} (0x{code & 0xFFFFFFFF:08X})")
        ferr.close()
        with open(ERR, "r", encoding="utf-8", errors="replace") as fh:
            err = fh.read()
        print("stderr:", a(err.strip()[:2500]) or "(empty)")
        if (code & 0xFFFFFFFF) == 0xC0000409:
            print("RESULT: CRASH 0xC0000409 reproduced on installed exe")
            return 0
        print("RESULT: no crash")
        return 1
    finally:
        subprocess.run(
            ["taskkill", "/IM", "ShutdownTimer.exe", "/F"],
            capture_output=True,
            check=False,
        )
        if backed and os.path.exists(BACKUP):
            import shutil

            shutil.move(BACKUP, SETTINGS)
            print("settings restored")


if __name__ == "__main__":
    raise SystemExit(main())
