from __future__ import annotations

from PyQt6.QtCore import QPoint, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QGuiApplication, QIcon, QMouseEvent
from PyQt6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.paths import resource_path
from app.ui import animations
from app.ui.components import GlassCard
from app.ui.styles import apply_stylesheet


class MiniWidget(QWidget):
    extend_requested = pyqtSignal()
    cancel_requested = pyqtSignal()
    show_main_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        apply_stylesheet()
        self.setFixedSize(252, 66)
        self.setWindowTitle("Таймер автоотключения ПК")
        self.setWindowIcon(QIcon(resource_path("resources/icon.ico")))
        self._running = False
        self._drag_offset: QPoint | None = None
        self._build_ui()
        self._move_to_corner()
        self._pulse_timer = QTimer(self)
        self._pulse_timer.setInterval(950)
        self._pulse_timer.timeout.connect(self._on_pulse)
        self._apply_running_state()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(6, 6, 6, 6)
        outer.setSpacing(0)
        self._card = GlassCard(self, radius=27)
        shadow = QGraphicsDropShadowEffect(self._card)
        shadow.setBlurRadius(26.0)
        shadow.setOffset(0.0, 6.0)
        shadow.setColor(QColor(0, 0, 0, 130))
        self._card.setGraphicsEffect(shadow)
        outer.addWidget(self._card)
        layout = QHBoxLayout(self._card)
        layout.setContentsMargins(14, 0, 8, 0)
        layout.setSpacing(6)
        self._led = QFrame(self._card)
        self._led.setObjectName("led")
        self._led.setFixedSize(10, 10)
        self._digits = QLabel("00:00")
        self._digits.setObjectName("miniDigits")
        self._digits.setMinimumWidth(74)
        plus_btn = self._make_button("+", "Продлить на 5 минут")
        cancel_btn = self._make_button("✕", "Отменить таймер")
        home_btn = self._make_button("⌂", "Открыть главное окно")
        plus_btn.clicked.connect(lambda *_args: self.extend_requested.emit())
        cancel_btn.clicked.connect(lambda *_args: self.cancel_requested.emit())
        home_btn.clicked.connect(lambda *_args: self.show_main_requested.emit())
        layout.addWidget(self._led, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._digits, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addStretch(1)
        layout.addWidget(plus_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(cancel_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(home_btn, 0, Qt.AlignmentFlag.AlignVCenter)

    def _make_button(self, text: str, tip: str) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName("miniAction")
        button.setFixedSize(30, 30)
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        button.setToolTip(tip)
        return button

    def _move_to_corner(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry()
        x = area.right() - self.width() + 1 - 32
        y = area.bottom() - self.height() + 1 - 24
        self.move(x, y)

    def set_time(self, seconds: int | str, running: bool = True) -> None:
        if isinstance(seconds, str):
            text = seconds.strip() or "00:00"
        else:
            value = max(0, int(seconds))
            text = f"{value // 60:02d}:{value % 60:02d}"
        self._digits.setText(text)
        self._fit_digits_font(text)
        self._running = bool(running)
        self._apply_running_state()

    def _fit_digits_font(self, text: str) -> None:
        length = len(text)
        if length > 6:
            size = 19
        elif length > 5:
            size = 22
        else:
            size = 0
        if size:
            self._digits.setStyleSheet(
                f"font-family: Consolas, monospace; font-size: {size}px;"
                " color: #E9EEF8;"
            )
        else:
            self._digits.setStyleSheet("")

    def _apply_running_state(self) -> None:
        state = "true" if self._running else "false"
        if self._led.property("running") != state:
            self._led.setProperty("running", state)
            style = self._led.style()
            if style is not None:
                style.unpolish(self._led)
                style.polish(self._led)
            self._led.update()
        if self._running:
            if not self._pulse_timer.isActive():
                self._pulse_timer.start()
        else:
            self._pulse_timer.stop()
            effect = self._led.graphicsEffect()
            if isinstance(effect, QGraphicsOpacityEffect):
                effect.setOpacity(1.0)

    def _on_pulse(self) -> None:
        if self._running:
            animations.pulse(self._led, 850, 0.3)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_offset is not None and event.buttons() & (
            Qt.MouseButton.LeftButton
        ):
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_offset = None
        super().mouseReleaseEvent(event)
