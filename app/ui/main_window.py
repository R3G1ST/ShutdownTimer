from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import (
    QEasingCurve,
    QPoint,
    QPropertyAnimation,
    QRect,
    Qt,
    QTime,
    QTimer,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QCloseEvent,
    QColor,
    QGuiApplication,
    QHideEvent,
    QIcon,
    QMouseEvent,
    QPixmap,
    QResizeEvent,
    QShowEvent,
)
from PyQt6.QtWidgets import (
    QAbstractSpinBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizeGrip,
    QSpinBox,
    QStackedWidget,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from app.paths import resource_path
from app.ui import animations
from app.ui.components import (
    Chip,
    GlassCard,
    ProgressRing,
    SegmentedControl,
    Switch,
)
from app.ui.styles import apply_stylesheet

if TYPE_CHECKING:
    from app.config import SettingsManager
    from app.timers.engine import TimerEngine

MODE_KEYS = ("countdown", "exact", "idle")
MODE_TITLES = ("Обратный отсчёт", "Точное время", "Простой мыши")
ACTIONS = (
    ("shutdown", "⛔ Выключение"),
    ("sleep", "💤 Сон"),
    ("restart", "⟳ Перезагрузка"),
    ("hibernate", "🌙 Гибернация"),
)
ACTION_LABELS = {
    "shutdown": "Выключение",
    "sleep": "Сон",
    "restart": "Перезагрузка",
    "hibernate": "Гибернация",
}
PRESETS = (15, 30, 60, 120)
DEFAULT_WIDTH = 980
DEFAULT_HEIGHT = 660
MIN_WIDTH = 900
MIN_HEIGHT = 620
CHROME_HEIGHT = 80
DEEP_CLOSED_TEXT = "Глубокие настройки ▾"
DEEP_OPEN_TEXT = "Глубокие настройки ▴"


def _to_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_time(value: str) -> QTime:
    try:
        parts = value.split(":")
        parsed = QTime(int(parts[0]), int(parts[1]))
        if parsed.isValid():
            return parsed
    except (IndexError, ValueError):
        pass
    return QTime(23, 0)


def _refresh_style(widget: QWidget) -> None:
    style = widget.style()
    if style is None:
        return
    style.unpolish(widget)
    style.polish(widget)


class _TitleBar(QFrame):
    def __init__(self, host: QWidget, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._host = host
        self._offset: QPoint | None = None

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._offset = (
                event.globalPosition().toPoint() - self._host.frameGeometry().topLeft()
            )
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self._host.move(event.globalPosition().toPoint() - self._offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._offset = None
        super().mouseReleaseEvent(event)


class MainWindow(QWidget):
    request_start = pyqtSignal()
    request_stop = pyqtSignal()
    request_extend = pyqtSignal()
    request_quit = pyqtSignal()
    autostart_toggled = pyqtSignal(bool)

    def __init__(
        self,
        settings: SettingsManager,
        engine: TimerEngine,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._settings = settings
        self._engine = engine
        self._running = False
        self._total = 0
        self._grace_active = False
        self._grace_pair = False
        self._grace_left = 0
        self._deep_open = False
        self._grown_height = 0
        apply_stylesheet()
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowTitle("Таймер автоотключения ПК")
        self.setWindowIcon(QIcon(resource_path("resources/icon.ico")))
        self._build_ui()
        self.setMinimumSize(MIN_WIDTH, MIN_HEIGHT)
        self.resize(DEFAULT_WIDTH, DEFAULT_HEIGHT)
        self._grace_timer = QTimer(self)
        self._grace_timer.setInterval(1000)
        self._grace_timer.timeout.connect(self._on_grace_tick)
        self._danger_timer = QTimer(self)
        self._danger_timer.setInterval(950)
        self._danger_timer.timeout.connect(self._on_danger_pulse)
        self._exact_timer = QTimer(self)
        self._exact_timer.setInterval(30000)
        self._exact_timer.timeout.connect(self._on_exact_refresh)
        self._connect_engine()
        self._load_initial_values()
        self._sync_display()
        self._exact_timer.start()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 14)
        outer.setSpacing(0)
        self._root = GlassCard(self, radius=20)
        self._root.setObjectName("rootCard")
        shadow = QGraphicsDropShadowEffect(self._root)
        shadow.setBlurRadius(48.0)
        shadow.setOffset(0.0, 14.0)
        shadow.setColor(QColor(0, 0, 0, 150))
        self._root.setGraphicsEffect(shadow)
        outer.addWidget(self._root)
        root_layout = QVBoxLayout(self._root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        root_layout.addWidget(self._build_title_bar())
        self._banner = self._build_banner()
        root_layout.addWidget(self._banner)
        self._banner.hide()
        self._scroll = self._build_content()
        root_layout.addWidget(self._scroll, 1)
        self._grace = self._build_grace_overlay()
        self._grace.hide()
        self._size_grip = QSizeGrip(self)

    def _build_title_bar(self) -> _TitleBar:
        bar = _TitleBar(self, self._root)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(18, 8, 8, 8)
        layout.setSpacing(8)
        icon_label = QLabel(bar)
        pixmap = QPixmap(resource_path("resources/icon.ico"))
        if not pixmap.isNull():
            icon_label.setPixmap(
                pixmap.scaled(
                    24,
                    24,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        icon_label.setFixedSize(24, 24)
        title = QLabel("Таймер автоотключения ПК")
        title.setObjectName("windowTitle")
        min_btn = QPushButton("—")
        min_btn.setObjectName("headerBtn")
        min_btn.setFixedSize(34, 30)
        min_btn.setToolTip("Свернуть в трей")
        close_btn = QPushButton("✕")
        close_btn.setObjectName("headerBtnClose")
        close_btn.setFixedSize(34, 30)
        close_btn.setToolTip("Закрыть")
        min_btn.clicked.connect(self._on_minimize)
        close_btn.clicked.connect(self._on_close_clicked)
        layout.addWidget(icon_label)
        layout.addWidget(title)
        layout.addStretch(1)
        layout.addWidget(min_btn)
        layout.addWidget(close_btn)
        return bar

    def _build_banner(self) -> QWidget:
        wrapper = QWidget(self._root)
        layout = QHBoxLayout(wrapper)
        layout.setContentsMargins(16, 6, 16, 10)
        frame = GlassCard(wrapper, radius=12)
        frame.setObjectName("confirmBanner")
        inner = QHBoxLayout(frame)
        inner.setContentsMargins(14, 8, 12, 8)
        inner.setSpacing(10)
        text = QLabel("Закрыть? Приложение продолжит работать в трее.")
        quit_btn = QPushButton("Выйти полностью")
        quit_btn.setObjectName("bannerQuitBtn")
        hide_btn = QPushButton("Свернуть")
        hide_btn.setObjectName("bannerHideBtn")
        quit_btn.clicked.connect(lambda *_args: self.request_quit.emit())
        hide_btn.clicked.connect(lambda *_args: self._hide_banner())
        inner.addWidget(text, 1)
        inner.addWidget(quit_btn)
        inner.addWidget(hide_btn)
        layout.addWidget(frame)
        return wrapper

    def _build_content(self) -> QScrollArea:
        scroll = QScrollArea(self._root)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setAutoFillBackground(False)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 16, 20, 16)
        content_layout.setSpacing(10)
        self._content = content
        self._content_layout = content_layout
        self._segment = SegmentedControl(list(MODE_TITLES))
        self._segment.currentIndexChanged.connect(self._on_mode_changed)
        content_layout.addWidget(self._segment)
        self._stack = QStackedWidget()
        self._stack.setFixedHeight(54)
        self._stack.addWidget(self._build_countdown_panel())
        self._stack.addWidget(self._build_exact_panel())
        self._stack.addWidget(self._build_idle_panel())
        content_layout.addWidget(self._stack)
        self._build_action_section()
        self._build_ring_section()
        self._build_buttons()
        self._build_deep_section()
        scroll.setWidget(content)
        return scroll

    def _create_spin(self, minimum: int, maximum: int, width: int) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(minimum, maximum)
        spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        spin.setFixedWidth(width)
        spin.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        return spin

    def _create_unit_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("unitLabel")
        return label

    def _build_countdown_panel(self) -> QWidget:
        panel = QWidget()
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        self._minutes_spin = self._create_spin(0, 999, 78)
        self._seconds_spin = self._create_spin(0, 59, 70)
        minutes_pill = GlassCard(panel, radius=14)
        minutes_layout = QHBoxLayout(minutes_pill)
        minutes_layout.setContentsMargins(12, 5, 12, 5)
        minutes_layout.setSpacing(6)
        minutes_layout.addWidget(self._minutes_spin)
        minutes_layout.addWidget(self._create_unit_label("мин"))
        seconds_pill = GlassCard(panel, radius=14)
        seconds_layout = QHBoxLayout(seconds_pill)
        seconds_layout.setContentsMargins(12, 5, 12, 5)
        seconds_layout.setSpacing(6)
        seconds_layout.addWidget(self._seconds_spin)
        seconds_layout.addWidget(self._create_unit_label("сек"))
        layout.addWidget(minutes_pill)
        layout.addWidget(seconds_pill)
        layout.addSpacing(4)
        self._preset_chips: dict[int, Chip] = {}
        for minutes in PRESETS:
            chip = Chip(f"{minutes} мин")
            chip.clicked.connect(
                lambda *_args, value=minutes: self._apply_preset(value)
            )
            self._preset_chips[minutes] = chip
            layout.addWidget(chip)
        layout.addStretch(1)
        self._minutes_spin.valueChanged.connect(self._on_countdown_changed)
        self._seconds_spin.valueChanged.connect(self._on_countdown_changed)
        return panel

    def _build_exact_panel(self) -> QWidget:
        panel = QWidget()
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        pill = GlassCard(panel, radius=14)
        pill_layout = QHBoxLayout(pill)
        pill_layout.setContentsMargins(12, 5, 12, 5)
        self._time_edit = QTimeEdit()
        self._time_edit.setDisplayFormat("HH:mm")
        self._time_edit.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self._time_edit.setFixedWidth(116)
        self._time_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pill_layout.addWidget(self._time_edit)
        self._exact_hint = QLabel("")
        self._exact_hint.setObjectName("hint")
        layout.addWidget(pill)
        layout.addWidget(self._exact_hint, 1)
        self._time_edit.timeChanged.connect(self._on_exact_changed)
        return panel

    def _build_idle_panel(self) -> QWidget:
        panel = QWidget()
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        pill = GlassCard(panel, radius=14)
        pill_layout = QHBoxLayout(pill)
        pill_layout.setContentsMargins(12, 5, 12, 5)
        pill_layout.setSpacing(8)
        self._idle_spin = self._create_spin(1, 240, 84)
        pill_layout.addWidget(self._idle_spin)
        pill_layout.addWidget(self._create_unit_label("минут бездействия"))
        self._idle_hint = QLabel("")
        self._idle_hint.setObjectName("hint")
        layout.addWidget(pill)
        layout.addWidget(self._idle_hint, 1)
        self._idle_spin.valueChanged.connect(self._on_idle_changed)
        return panel

    def _build_action_section(self) -> None:
        card = GlassCard(self._content, radius=16)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(16, 9, 16, 9)
        layout.setSpacing(9)
        caption = QLabel("Действие при завершении")
        caption.setObjectName("sectionTitle")
        layout.addWidget(caption)
        self._action_chips: dict[str, Chip] = {}
        for key, text in ACTIONS:
            chip = Chip(text)
            chip.clicked.connect(
                lambda *_args, action=key: self._set_action(action)
            )
            self._action_chips[key] = chip
            layout.addWidget(chip)
        layout.addStretch(1)
        self._content_layout.addWidget(card)

    def _build_ring_section(self) -> None:
        holder = QWidget()
        layout = QHBoxLayout(holder)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._ring = ProgressRing()
        layout.addStretch(1)
        layout.addWidget(self._ring)
        layout.addStretch(1)
        self._content_layout.addWidget(holder)

    def _build_buttons(self) -> None:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        self._toggle_btn = QPushButton("Запустить")
        self._toggle_btn.setObjectName("primaryBtn")
        self._toggle_btn.setFixedHeight(48)
        self._toggle_btn.setProperty("danger", "false")
        self._extend_btn = QPushButton("+5 мин")
        self._extend_btn.setObjectName("extendBtn")
        self._extend_btn.setFixedHeight(48)
        self._extend_btn.setFixedWidth(132)
        self._extend_btn.setEnabled(False)
        self._toggle_btn.clicked.connect(self._on_toggle_clicked)
        self._extend_btn.clicked.connect(lambda *_args: self.request_extend.emit())
        layout.addWidget(self._toggle_btn, 1)
        layout.addWidget(self._extend_btn)
        self._content_layout.addWidget(row)

    def _build_deep_section(self) -> None:
        self._deep_toggle = QPushButton(DEEP_CLOSED_TEXT)
        self._deep_toggle.setObjectName("deepToggle")
        self._deep_toggle.clicked.connect(lambda *_args: self._toggle_deep())
        self._content_layout.addWidget(self._deep_toggle)
        self._deep_box = QWidget(self._content)
        self._deep_layout = QVBoxLayout(self._deep_box)
        self._deep_layout.setContentsMargins(0, 0, 0, 0)
        self._deep_layout.setSpacing(8)
        if self._is_dry_run():
            badge = QLabel("DRY-RUN: система не выключится")
            badge.setObjectName("dryBadge")
            badge_row = QWidget(self._deep_box)
            badge_layout = QHBoxLayout(badge_row)
            badge_layout.setContentsMargins(0, 0, 0, 0)
            badge_layout.addWidget(badge)
            badge_layout.addStretch(1)
            self._deep_layout.addWidget(badge_row)
        self._autostart_switch = Switch(
            checked=bool(self._settings.get("autostart"))
        )
        self._mini_switch = Switch(
            checked=bool(self._settings.get("mini_widget_enabled"))
        )
        self._tray_switch = Switch(
            checked=bool(self._settings.get("confirm_close_to_tray"))
        )
        self._lead_spin = self._create_spin(0, 60, 96)
        self._grace_spin = self._create_spin(0, 300, 96)
        self._lead_spin.setFixedHeight(34)
        self._grace_spin.setFixedHeight(34)
        self._add_deep_row("Автозагрузка", self._autostart_switch)
        self._add_deep_row("Мини-виджет", self._mini_switch)
        self._add_deep_row(
            "Сворачивать в трей при закрытии", self._tray_switch
        )
        self._add_deep_row("Предупреждать за (мин)", self._lead_spin)
        self._add_deep_row("Пауза перед действием (сек)", self._grace_spin)
        self._content_layout.addWidget(self._deep_box)
        if self._is_dry_run():
            self._deep_open = True
            self._deep_toggle.setText(DEEP_OPEN_TEXT)
            self._deep_box.setMaximumHeight(1 << 24)
        else:
            self._deep_box.setMaximumHeight(0)
        self._autostart_switch.toggled.connect(
            lambda value, *_args: self.autostart_toggled.emit(bool(value))
        )
        self._mini_switch.toggled.connect(
            lambda value, *_args: self._save_setting(
                "mini_widget_enabled", bool(value)
            )
        )
        self._tray_switch.toggled.connect(
            lambda value, *_args: self._save_setting(
                "confirm_close_to_tray", bool(value)
            )
        )
        self._lead_spin.valueChanged.connect(self._on_lead_changed)
        self._grace_spin.valueChanged.connect(self._on_grace_changed)

    def _add_deep_row(self, title: str, control: QWidget) -> None:
        row = GlassCard(self._deep_box, radius=12)
        row.setFixedHeight(48)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(16, 6, 14, 6)
        layout.setSpacing(12)
        label = QLabel(title)
        layout.addWidget(label, 1)
        layout.addWidget(control, 0, Qt.AlignmentFlag.AlignVCenter)
        self._deep_layout.addWidget(row)

    def _build_grace_overlay(self) -> QFrame:
        overlay = QFrame(self._root)
        overlay.setObjectName("graceOverlay")
        layout = QVBoxLayout(overlay)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(10)
        layout.addStretch(1)
        self._grace_title = QLabel("")
        self._grace_title.setObjectName("graceTitle")
        self._grace_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._grace_hint = QLabel("Нажмите «Отмена», чтобы прервать действие")
        self._grace_hint.setObjectName("graceHint")
        self._grace_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._grace_btn = QPushButton("Отмена")
        self._grace_btn.setObjectName("primaryBtn")
        self._grace_btn.setProperty("danger", "true")
        self._grace_btn.setFixedSize(200, 50)
        self._grace_btn.clicked.connect(self._on_grace_cancel)
        layout.addWidget(self._grace_title, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._grace_hint, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(8)
        layout.addWidget(self._grace_btn, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addStretch(1)
        return overlay

    def _connect_engine(self) -> None:
        engine = self._engine
        engine.tick.connect(self.update_time)
        engine.started.connect(self._on_engine_started)
        engine.stopped.connect(self._on_engine_stopped)
        engine.completed.connect(self._on_engine_completed)
        engine.warning.connect(self._on_engine_warning)

    def _load_initial_values(self) -> None:
        mode = str(self._settings.get("mode", "countdown"))
        index = MODE_KEYS.index(mode) if mode in MODE_KEYS else 0
        self._segment.blockSignals(True)
        self._segment.setCurrentIndex(index)
        self._segment.blockSignals(False)
        self._stack.setCurrentIndex(index)
        total = self._configured_countdown_seconds()
        self._minutes_spin.blockSignals(True)
        self._seconds_spin.blockSignals(True)
        self._minutes_spin.setValue(total // 60)
        self._seconds_spin.setValue(total % 60)
        self._minutes_spin.blockSignals(False)
        self._seconds_spin.blockSignals(False)
        self._time_edit.blockSignals(True)
        self._time_edit.setTime(
            _parse_time(str(self._settings.get("exact_time", "23:00")))
        )
        self._time_edit.blockSignals(False)
        idle = min(240, max(1, _to_int(self._settings.get("idle_minutes"), 15)))
        self._idle_spin.blockSignals(True)
        self._idle_spin.setValue(idle)
        self._idle_spin.blockSignals(False)
        lead = 0
        leads = self._settings.get("notify_lead_minutes")
        if isinstance(leads, (list, tuple)):
            for item in leads:
                value = _to_int(item, 0)
                if value > 0:
                    lead = value
                    break
        self._lead_spin.blockSignals(True)
        self._lead_spin.setValue(min(60, max(0, lead)))
        self._lead_spin.blockSignals(False)
        grace = min(300, max(0, _to_int(self._settings.get("grace_seconds"), 10)))
        self._grace_spin.blockSignals(True)
        self._grace_spin.setValue(grace)
        self._grace_spin.blockSignals(False)
        self._refresh_action_chips()
        self._refresh_presets(total)
        self._refresh_exact_hint()
        self._refresh_idle_hint()

    def _is_dry_run(self) -> bool:
        return bool(self._settings.get("dry_run")) or os.environ.get(
            "SHUTDOWNTIMER_DRY_RUN"
        ) == "1"

    def _save_setting(self, key: str, value: Any) -> None:
        self._settings.set(key, value)
        self._settings.save()

    def _current_mode(self) -> str:
        index = self._segment.currentIndex()
        if 0 <= index < len(MODE_KEYS):
            return MODE_KEYS[index]
        return "countdown"

    def _on_mode_changed(self, index: int) -> None:
        if 0 <= index < len(MODE_KEYS):
            self._save_setting("mode", MODE_KEYS[index])
        if 0 <= index < self._stack.count():
            self._stack.setCurrentIndex(index)
            panel = self._stack.currentWidget()
            if panel is not None:
                animations.slide_down(panel, 150, 12)
        if index == 1:
            self._refresh_exact_hint()
        self._sync_display()

    def _on_countdown_changed(self, _value: int) -> None:
        minutes = self._minutes_spin.value()
        seconds = self._seconds_spin.value()
        total = minutes * 60 + seconds
        stored: Any = minutes if seconds == 0 else minutes + seconds / 60.0
        self._save_setting("countdown_minutes", stored)
        self._refresh_presets(total)
        self._sync_display()

    def _apply_preset(self, minutes: int) -> None:
        self._minutes_spin.blockSignals(True)
        self._seconds_spin.blockSignals(True)
        self._minutes_spin.setValue(minutes)
        self._seconds_spin.setValue(0)
        self._minutes_spin.blockSignals(False)
        self._seconds_spin.blockSignals(False)
        self._on_countdown_changed(minutes)

    def _refresh_presets(self, total_seconds: int) -> None:
        for value, chip in self._preset_chips.items():
            chip.set_active(value * 60 == total_seconds)

    def _on_exact_changed(self, time: QTime) -> None:
        self._save_setting("exact_time", time.toString("HH:mm"))
        self._refresh_exact_hint()
        self._sync_display()

    def _refresh_exact_hint(self) -> None:
        target = self._time_edit.time()
        current = QTime.currentTime()
        if target > current:
            text = f"Сработает сегодня в {target.toString('HH:MM')}"
        else:
            text = f"Время уже прошло — сработает завтра в {target.toString('HH:MM')}"
        self._exact_hint.setText(text)

    def _on_idle_changed(self, value: int) -> None:
        self._save_setting("idle_minutes", int(value))
        self._refresh_idle_hint()
        self._sync_display()

    def _refresh_idle_hint(self) -> None:
        value = self._idle_spin.value()
        self._idle_hint.setText(
            f"Сработает после {value} минут без движения мыши и клавиатуры"
        )

    def _on_lead_changed(self, value: int) -> None:
        leads: list[int] = [int(value)] if value > 0 else []
        self._save_setting("notify_lead_minutes", leads)

    def _on_grace_changed(self, value: int) -> None:
        self._save_setting("grace_seconds", int(value))

    def _set_action(self, key: str) -> None:
        self._save_setting("action", key)
        self._refresh_action_chips()

    def _refresh_action_chips(self) -> None:
        current = str(self._settings.get("action", "shutdown"))
        for key, chip in self._action_chips.items():
            chip.set_active(key == current)

    def _on_toggle_clicked(self, *_args: Any) -> None:
        if self._running:
            self.request_stop.emit()
            return
        if (
            self._current_mode() == "countdown"
            and self._configured_countdown_seconds() <= 0
        ):
            # 0:00 означало бы мгновенное срабатывание действия — не даём стартовать
            return
        self.request_start.emit()

    def _on_minimize(self) -> None:
        self._hide_banner()
        self.hide()

    def _on_close_clicked(self) -> None:
        if bool(self._settings.get("confirm_close_to_tray")):
            self._show_banner()
        else:
            self.request_quit.emit()

    def _show_banner(self) -> None:
        if self._banner.isVisible():
            self._hide_banner()
            return
        self._banner.show()
        animations.slide_down(self._banner, 160, 10)

    def _hide_banner(self) -> None:
        self._banner.hide()

    def _set_timer_fields_enabled(self, enabled: bool) -> None:
        self._segment.setEnabled(enabled)
        self._minutes_spin.setEnabled(enabled)
        self._seconds_spin.setEnabled(enabled)
        self._time_edit.setEnabled(enabled)
        self._idle_spin.setEnabled(enabled)
        for chip in self._preset_chips.values():
            chip.setEnabled(enabled)
        for chip in self._action_chips.values():
            chip.setEnabled(enabled)

    def _on_engine_started(self) -> None:
        self._running = True
        self._total = 0
        self._set_timer_fields_enabled(False)
        self._toggle_btn.setText("Остановить")
        self._toggle_btn.setProperty("danger", "true")
        _refresh_style(self._toggle_btn)
        self._extend_btn.setEnabled(True)
        animations.pulse(self._ring, 600)

    def _on_engine_stopped(self) -> None:
        if self._grace_active and self._grace_pair:
            self._grace_pair = False
        else:
            self._hide_grace_overlay()
        self._running = False
        self._total = 0
        self._danger_timer.stop()
        self._set_timer_fields_enabled(True)
        self._toggle_btn.setText("Запустить")
        self._toggle_btn.setProperty("danger", "false")
        _refresh_style(self._toggle_btn)
        self._extend_btn.setEnabled(False)
        self._sync_display()
        animations.fade_in(self._ring, 180)

    def _on_engine_completed(self) -> None:
        action = str(self._settings.get("action", "shutdown"))
        label = ACTION_LABELS.get(action, "Выключение")
        self._grace_left = max(0, _to_int(self._settings.get("grace_seconds"), 10))
        self._grace_active = True
        self._grace_pair = True
        self._show_grace_overlay(label)

    def _on_engine_warning(self, _seconds: int) -> None:
        animations.pulse(self._ring, 700)

    def _show_grace_overlay(self, label: str) -> None:
        if self._grace_left > 0:
            self._grace_title.setText(f"{label} через {self._grace_left}…")
        else:
            self._grace_title.setText(f"{label}…")
        self._grace.show()
        self._grace.raise_()
        self._grace_timer.start()

    def _on_grace_tick(self) -> None:
        self._grace_left -= 1
        if self._grace_left < 0:
            self._hide_grace_overlay()
            return
        action = str(self._settings.get("action", "shutdown"))
        label = ACTION_LABELS.get(action, "Выключение")
        if self._grace_left > 0:
            self._grace_title.setText(f"{label} через {self._grace_left}…")
        else:
            self._grace_title.setText(f"{label}…")

    def _hide_grace_overlay(self) -> None:
        self._grace_timer.stop()
        self._grace.hide()
        self._grace_active = False
        self._grace_pair = False

    def _on_grace_cancel(self) -> None:
        self._hide_grace_overlay()
        self.request_stop.emit()

    def _on_danger_pulse(self) -> None:
        animations.pulse(self._ring, 850, 0.35)

    def _on_exact_refresh(self) -> None:
        self._refresh_exact_hint()
        if self._current_mode() == "exact":
            self._sync_display()

    def update_time(self, seconds: int) -> None:
        value = max(0, int(seconds))
        if self._running and value > self._total:
            self._total = value
        self._render(value)

    def _render(self, value: int) -> None:
        danger = False
        progress = 0.0
        if self._running:
            total = self._total if self._total > 0 else max(value, 1)
            progress = min(1.0, value / total)
            danger = value < 60
        self._ring.set_seconds(value)
        self._ring.set_progress(progress)
        self._ring.set_danger(danger)
        self._ring.set_status(self._status_text(value))
        if danger:
            if not self._danger_timer.isActive():
                self._danger_timer.start()
        elif self._danger_timer.isActive():
            self._danger_timer.stop()

    def _status_text(self, value: int) -> str:
        if not self._running:
            return "Остановлен"
        formatted = f"{value // 60:02d}:{value % 60:02d}"
        if self._current_mode() == "idle":
            return f"Простой: {formatted}"
        return f"Осталось {formatted}"

    def _sync_display(self) -> None:
        if self._running:
            return
        self._render(self._configured_seconds())

    def _configured_seconds(self) -> int:
        mode = self._current_mode()
        if mode == "exact":
            target = self._time_edit.time()
            delta = QTime.currentTime().secsTo(target)
            if delta <= 0:
                delta += 86400
            return int(delta)
        if mode == "idle":
            return self._idle_spin.value() * 60
        return self._configured_countdown_seconds()

    def _configured_countdown_seconds(self) -> int:
        raw = self._settings.get("countdown_minutes", 30)
        try:
            minutes = float(raw)
        except (TypeError, ValueError):
            minutes = 30.0
        return max(0, round(minutes * 60))

    def _toggle_deep(self) -> None:
        self._deep_open = not self._deep_open
        self._deep_toggle.setText(
            DEEP_OPEN_TEXT if self._deep_open else DEEP_CLOSED_TEXT
        )
        self._deep_box.setMaximumHeight(1 << 24)
        full = self._deep_box.sizeHint().height()
        if self._deep_open:
            start, end = 0, full
        else:
            start, end = self._deep_box.height(), 0
        animation = QPropertyAnimation(self._deep_box, b"maximumHeight", self)
        animation.setDuration(200)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        animation.setStartValue(int(start))
        animation.setEndValue(int(end))
        animation.finished.connect(self._on_deep_anim_finished)
        animation.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    def _on_deep_anim_finished(self) -> None:
        self._deep_box.setMaximumHeight(1 << 24 if self._deep_open else 0)
        if self._deep_open:
            self._grow_to_fit()
        else:
            QTimer.singleShot(0, self._maybe_shrink)

    def _grow_to_fit(self) -> None:
        if self._content_layout is not None:
            self._content_layout.activate()
        hint = self._content.sizeHint().height()
        desired = hint + CHROME_HEIGHT
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            desired = min(desired, screen.availableGeometry().height() - 40)
        desired = max(desired, MIN_HEIGHT)
        if desired <= self.height() + 4:
            return
        self._grown_height = desired
        self._animate_height(desired)

    def _maybe_shrink(self) -> None:
        if self._deep_open or self._grown_height <= 0:
            return
        if abs(self.height() - self._grown_height) > 6:
            return
        if self._content_layout is not None:
            self._content_layout.activate()
        hint = self._content.sizeHint().height()
        desired = hint + CHROME_HEIGHT
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            desired = min(desired, screen.availableGeometry().height() - 40)
        desired = max(desired, DEFAULT_HEIGHT)
        if desired >= self.height() - 4:
            return
        self._grown_height = 0
        self._animate_height(desired)

    def _animate_height(self, target: int) -> None:
        geometry = self.geometry()
        animation = QPropertyAnimation(self, b"geometry", self)
        animation.setDuration(200)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        animation.setStartValue(geometry)
        animation.setEndValue(
            QRect(
                geometry.x(),
                geometry.y(),
                geometry.width(),
                int(target),
            )
        )
        animation.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    def _sync_grace_geometry(self) -> None:
        self._grace.setGeometry(self._root.rect())

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._size_grip.setGeometry(
            max(0, self.width() - 28), max(0, self.height() - 28), 28, 28
        )
        self._size_grip.raise_()
        self._sync_grace_geometry()

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        QTimer.singleShot(0, self._after_show)

    def _after_show(self) -> None:
        self._sync_grace_geometry()
        if self._deep_open:
            self._grow_to_fit()

    def hideEvent(self, event: QHideEvent) -> None:
        self._banner.hide()
        super().hideEvent(event)

    def closeEvent(self, event: QCloseEvent) -> None:
        event.ignore()
        if bool(self._settings.get("confirm_close_to_tray")):
            self.hide()
        else:
            self.request_quit.emit()
