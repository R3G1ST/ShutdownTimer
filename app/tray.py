from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon


class TrayController(QObject):
    open_requested = pyqtSignal()
    extend_requested = pyqtSignal()
    cancel_requested = pyqtSignal()
    quit_requested = pyqtSignal()

    def __init__(self, icon: QIcon, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._menu = QMenu()
        self._action_open = self._menu.addAction("Открыть ShutdownTimer")
        self._action_extend = self._menu.addAction("Продлить на 5 мин")
        self._action_cancel = self._menu.addAction("Отмена таймера")
        self._menu.addSeparator()
        self._action_quit = self._menu.addAction("Выход")
        self._tray = QSystemTrayIcon(icon, self)
        self._tray.setContextMenu(self._menu)
        self._action_open.triggered.connect(self.open_requested.emit)
        self._action_extend.triggered.connect(self.extend_requested.emit)
        self._action_cancel.triggered.connect(self.cancel_requested.emit)
        self._action_quit.triggered.connect(self.quit_requested.emit)
        self._tray.activated.connect(self._on_activated)
        self.set_running(False, "")
        self._tray.show()

    @property
    def is_visible(self) -> bool:
        return self._tray.isVisible()

    def set_running(self, running: bool, info: str = "") -> None:
        self._action_extend.setEnabled(running)
        self._action_cancel.setEnabled(running)
        self._tray.setToolTip(info or "ShutdownTimer")

    def hide(self) -> None:
        self._tray.hide()

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.open_requested.emit()
