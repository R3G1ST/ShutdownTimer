from __future__ import annotations

import sys
import threading
from collections.abc import Callable, Sequence
from typing import Any

from PyQt6.QtGui import QIcon
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtWidgets import QApplication

from app.config import SettingsManager
from app.paths import resource_path
from app.system import actions, autostart, protocol, toast
from app.timers.engine import TimerEngine
from app.tray import TrayController
from app.ui.main_window import MainWindow
from app.ui.mini_widget import MiniWidget

SOCKET_NAME = "ShutdownTimer.single"
PROTOCOL_SCHEME = "shutdowntimer://"
ACTION_LABELS = {
    "shutdown": "Выключение",
    "restart": "Перезагрузка",
    "sleep": "Сон",
    "hibernate": "Гибернация",
}


def is_protocol_url(value: str) -> bool:
    return value.lower().startswith(PROTOCOL_SCHEME)


def format_time(seconds: int) -> str:
    value = max(0, int(seconds))
    return f"{value // 60:02d}:{value % 60:02d}"


def to_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def run_async(target: Callable[..., Any], **kwargs: Any) -> None:
    threading.Thread(target=target, kwargs=kwargs, daemon=True).start()


def forward_argv(argv: Sequence[str]) -> bool:
    socket = QLocalSocket()
    socket.connectToServer(SOCKET_NAME)
    if not socket.waitForConnected(1000):
        return False
    socket.write("\n".join(argv).encode("utf-8"))
    socket.flush()
    socket.waitForBytesWritten(1000)
    socket.disconnectFromServer()
    return True


def accept_connection(server: QLocalServer, handler: Callable[[list[str]], None]) -> None:
    socket = server.nextPendingConnection()
    if socket is None:
        return
    socket.waitForReadyRead(1000)
    raw = bytes(socket.readAll()).decode("utf-8", errors="replace")
    socket.disconnectFromServer()
    handler([line for line in raw.split("\n")])


def main() -> None:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("ShutdownTimer")
    icon = QIcon(resource_path("resources/icon.ico"))
    app.setWindowIcon(icon)

    if forward_argv(sys.argv):
        sys.exit(0)

    settings = SettingsManager()
    engine = TimerEngine(settings)
    tray = TrayController(icon)
    window = MainWindow(settings, engine)
    widget = MiniWidget()

    # DRY-RUN — тестовый режим: систему (реестр) не модифицируем
    dry_run_mode = actions.is_dry_run() or bool(settings.get("dry_run"))
    if not dry_run_mode:
        if not protocol.is_registered():
            protocol.register_protocol()
        if settings.get("autostart") and not autostart.is_enabled():
            autostart.set_enabled(True)

    def show_window() -> None:
        window.show()
        window.raise_()
        window.activateWindow()

    def handle_quit() -> None:
        engine.stop()
        app.quit()

    action_pending = False

    def cancel_all() -> None:
        nonlocal action_pending
        engine.stop()
        if action_pending:
            action_pending = False
            run_async(actions.cancel)

    def handle_autostart(enabled: Any) -> None:
        value = bool(enabled)
        settings.set("autostart", value)
        settings.save()
        autostart.set_enabled(value)

    def handle_url(url: str) -> None:
        path = url[len(PROTOCOL_SCHEME) :].strip("/")
        parts = [part for part in path.split("/") if part]
        if not parts:
            return
        command = parts[0].lower()
        if command == "cancel":
            cancel_all()
        elif command == "open":
            show_window()
        elif command == "extend":
            if not engine.is_running or len(parts) < 2:
                return
            seconds = to_int(parts[1], 0)
            if seconds > 0:
                engine.extend(seconds)

    def handle_args(args: Sequence[str]) -> None:
        values = [value.strip('"') for value in list(args)[1:] if value]
        if not values:
            show_window()
            return
        for value in values:
            if is_protocol_url(value):
                handle_url(value)
            elif value != "--autostart":
                show_window()

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
        grace = to_int(settings.get("grace_seconds"), 10)
        dry = actions.is_dry_run() or bool(settings.get("dry_run"))
        prefix = "[DRY-RUN] " if dry else ""
        toast.notify(
            title="Время вышло",
            message=f"{prefix}{label} через {grace} с",
            buttons=[("Отмена", PROTOCOL_SCHEME + "cancel")],
        )
        action_pending = not dry
        run_async(actions.perform, action=action, grace_seconds=grace, dry_run=dry)

    def on_quit() -> None:
        engine.stop()
        engine.close()

    engine.tick.connect(on_tick)
    engine.started.connect(on_started)
    engine.stopped.connect(on_stopped)
    engine.warning.connect(on_warning)
    engine.completed.connect(on_completed)

    window.request_start.connect(lambda *args: engine.start())
    window.request_stop.connect(lambda *args: cancel_all())
    window.request_extend.connect(lambda *args: engine.extend(300))
    window.request_quit.connect(lambda *args: handle_quit())
    window.autostart_toggled.connect(lambda value, *args: handle_autostart(value))

    widget.show_main_requested.connect(lambda *args: show_window())
    widget.extend_requested.connect(lambda *args: engine.extend(300))
    widget.cancel_requested.connect(lambda *args: cancel_all())

    tray.open_requested.connect(lambda *args: show_window())
    tray.extend_requested.connect(lambda *args: engine.extend(300))
    tray.cancel_requested.connect(lambda *args: cancel_all())
    tray.quit_requested.connect(lambda *args: handle_quit())

    server = QLocalServer()
    server.newConnection.connect(lambda: accept_connection(server, handle_args))
    QLocalServer.removeServer(SOCKET_NAME)
    server.listen(SOCKET_NAME)

    app.aboutToQuit.connect(on_quit)

    args = list(sys.argv)
    start_hidden = any(value == "--autostart" for value in args[1:]) or any(
        is_protocol_url(value) for value in args[1:]
    )
    if args[1:]:
        handle_args(args)
    if not start_hidden:
        show_window()

    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        engine.stop()
        engine.close()
        sys.exit(0)


if __name__ == "__main__":
    main()
