"""Воспроизведение краша v1.0.0: countdown 60с + action=sleep, dry-run.

Запуск (stderr перенаправляется Qt fatal-сообщением):
  .venv\\Scripts\\python.exe scripts\\repro_crash.py 2> repro_err.txt
Код выхода 0xC0000409 (3221225786 unsigned / -1073740791 signed) = краш.
"""
from __future__ import annotations

import os
import sys
import tempfile

os.environ["SHUTDOWNTIMER_DRY_RUN"] = "1"
_REPRO_APPDATA = os.path.join(tempfile.gettempdir(), "st_repro_appdata")
os.environ["APPDATA"] = _REPRO_APPDATA

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from app.config import SettingsManager
from app.paths import resource_path
from app.system import actions, toast
from app.timers.engine import TimerEngine
from app.tray import TrayController
from app.ui.main_window import MainWindow
from app.ui.mini_widget import MiniWidget

PROTOCOL_SCHEME = "shutdowntimer://"
ACTION_LABELS = {
    "shutdown": "Выключение",
    "restart": "Перезагрузка",
    "sleep": "Сон",
    "hibernate": "Гибернация",
}


def format_time(seconds: int) -> str:
    value = max(0, int(seconds))
    return f"{value // 60:02d}:{value % 60:02d}"


def main() -> int:
    def _excepthook(exc_type, exc, tb) -> None:
        import traceback

        print("PYTHON UNHANDLED EXCEPTION:", file=sys.stderr)
        traceback.print_exception(exc_type, exc, tb, file=sys.stderr)
        sys.stderr.flush()

    sys.excepthook = _excepthook

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("ShutdownTimer")
    icon = QIcon(resource_path("resources/icon.ico"))
    app.setWindowIcon(icon)

    settings = SettingsManager()
    # Сценарий пользователя: 1 минута + сон + мини-виджет
    settings.set("mode", "countdown")
    settings.set("countdown_minutes", 1)
    settings.set("action", "sleep")
    settings.set("mini_widget_enabled", True)
    settings.save()

    engine = TimerEngine(settings)
    tray = TrayController(icon)
    window = MainWindow(settings, engine)
    widget = MiniWidget()

    action_pending = False

    def show_window() -> None:
        window.show()
        window.raise_()
        window.activateWindow()

    def on_tick(seconds: int) -> None:
        formatted = format_time(seconds)
        if widget.isVisible():
            widget.set_time(formatted)
        tray.set_running(True, f"Осталось {formatted}")

    def on_started() -> None:
        tray.set_running(True)
        if settings.get("mini_widget_enabled"):
            widget.show()

    def on_stopped() -> None:
        widget.hide()
        tray.set_running(False, "")

    def on_warning(seconds: int) -> None:
        action = str(settings.get("action", "shutdown"))
        label = ACTION_LABELS.get(action, action)
        toast.notify(
            title="Таймер скоро завершится",
            message=f"Осталось {format_time(seconds)} — {label}",
            buttons=[
                ("+5 мин", PROTOCOL_SCHEME + "extend/300"),
                ("Отмена", PROTOCOL_SCHEME + "cancel"),
            ],
        )

    def on_completed() -> None:
        nonlocal action_pending
        action = str(settings.get("action", "shutdown"))
        label = ACTION_LABELS.get(action, action)
        grace = int(settings.get("grace_seconds") or 10)
        dry = actions.is_dry_run() or bool(settings.get("dry_run"))
        prefix = "[DRY-RUN] " if dry else ""
        toast.notify(
            title="Время вышло",
            message=f"{prefix}{label} через {grace} с",
            buttons=[("Отмена", PROTOCOL_SCHEME + "cancel")],
        )
        action_pending = not dry
        if dry:
            import threading

            threading.Thread(
                target=actions.perform,
                kwargs={
                    "action": action,
                    "grace_seconds": grace,
                    "dry_run": True,
                },
                daemon=True,
            ).start()

    engine.tick.connect(on_tick)
    engine.started.connect(on_started)
    engine.stopped.connect(on_stopped)
    engine.warning.connect(on_warning)
    engine.completed.connect(on_completed)

    window.request_start.connect(lambda *args: engine.start())
    window.request_stop.connect(lambda *args: engine.stop())
    window.request_extend.connect(lambda *args: engine.extend(300))

    widget.show_main_requested.connect(lambda *args: show_window())
    widget.extend_requested.connect(lambda *args: engine.extend(300))
    widget.cancel_requested.connect(lambda *args: engine.stop())

    def _on_quit() -> None:
        engine.stop()
        engine.close()

    def _finish() -> None:
        _on_quit()
        app.quit()

    app.aboutToQuit.connect(_on_quit)

    window.show()
    print("[repro] window shown, starting engine in 2s...", flush=True)

    def _start() -> None:
        print("[repro] engine.start()", flush=True)
        engine.start()

    def _timeout() -> None:
        print(
            "[repro] 90s elapsed WITHOUT crash — exit 0",
            flush=True,
        )
        _finish()

    QTimer.singleShot(2000, _start)
    QTimer.singleShot(92000, _timeout)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
