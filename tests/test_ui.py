from __future__ import annotations

from PyQt6.QtWidgets import QApplication

from app.config import SettingsManager
from app.timers.engine import TimerEngine
from app.ui.components import Chip, ProgressRing, SegmentedControl, Switch
from app.ui.main_window import MainWindow
from app.ui.mini_widget import MiniWidget
from app.ui.styles import apply_stylesheet, build_stylesheet


def test_build_stylesheet_returns_non_empty_string() -> None:
    css = build_stylesheet()
    assert isinstance(css, str)
    assert len(css) > 1000
    assert "#0A0E14" in css
    assert "QPushButton#primaryBtn" in css


def test_apply_stylesheet_sets_stylesheet_on_app(qapp: QApplication) -> None:
    apply_stylesheet()
    assert qapp.styleSheet()


def test_main_window_is_created_signals_exist_and_show(
    qtbot, settings: SettingsManager, engine: TimerEngine
) -> None:
    window = MainWindow(settings, engine)
    qtbot.addWidget(window)

    for name in (
        "request_start",
        "request_stop",
        "request_extend",
        "request_quit",
        "autostart_toggled",
    ):
        assert hasattr(window, name), name

    window.show()
    qtbot.wait(100)
    assert window.isVisible()
    window.hide()


def test_engine_tick_updates_main_window_display(
    qtbot, settings: SettingsManager, engine: TimerEngine
) -> None:
    window = MainWindow(settings, engine)
    qtbot.addWidget(window)

    engine.started.emit()
    engine.tick.emit(754)
    qtbot.wait(50)

    ring = window._ring
    assert ring._seconds == 754
    assert ring._status == "Осталось 12:34"
    assert abs(ring._progress - 1.0) < 1e-6
    assert window._toggle_btn.text() == "Остановить"

    engine.stopped.emit()
    qtbot.wait(50)
    assert window._toggle_btn.text() == "Запустить"
    assert ring._status == "Остановлен"
    window.hide()


def test_main_window_start_button_requests_start(
    qtbot, settings: SettingsManager, engine: TimerEngine
) -> None:
    settings.set("countdown_minutes", 30)
    window = MainWindow(settings, engine)
    qtbot.addWidget(window)

    with qtbot.waitSignal(window.request_start, timeout=2000):
        window._toggle_btn.click()


def test_zero_countdown_does_not_start_timer(
    qtbot, settings: SettingsManager, engine: TimerEngine
) -> None:
    """0 мин 0 сек не должно запускать мгновенное срабатывание действия."""
    settings.set("countdown_minutes", 0)
    window = MainWindow(settings, engine)
    qtbot.addWidget(window)

    emitted: list[int] = []
    window.request_start.connect(lambda: emitted.append(1))
    window._toggle_btn.click()
    qtbot.wait(80)

    assert emitted == []


def test_mini_widget_set_time(qtbot) -> None:
    widget = MiniWidget()
    qtbot.addWidget(widget)

    widget.set_time(754, True)
    assert widget._digits.text() == "12:34"
    assert widget._running is True

    widget.set_time(45, False)
    assert widget._digits.text() == "00:45"
    assert widget._running is False

    widget.set_time("09:09")
    assert widget._digits.text() == "09:09"


def test_segmented_control_changes_index(qtbot) -> None:
    control = SegmentedControl(["Один", "Два", "Три"])
    qtbot.addWidget(control)

    received: list[int] = []
    control.currentIndexChanged.connect(received.append)

    control.setCurrentIndex(2)
    assert control.currentIndex() == 2
    assert received == [2]

    control.setCurrentIndex(2)
    assert received == [2], "повторный индекс не должен дублировать сигнал"

    control.setCurrentIndex(99)
    assert control.currentIndex() == 2


def test_chip_active_state(qtbot) -> None:
    chip = Chip("Выключение")
    qtbot.addWidget(chip)
    assert chip.active is False

    chip.set_active(True)
    assert chip.active is True
    assert chip.property("active") == "true"

    chip.set_active(False)
    assert chip.active is False


def test_switch_toggles(qtbot) -> None:
    switch = Switch(checked=False)
    qtbot.addWidget(switch)
    assert switch.checked is False

    switch.setChecked(True)
    qtbot.wait(80)
    assert switch.checked is True

    switch.setChecked(False)
    qtbot.wait(80)
    assert switch.checked is False


def test_progress_ring_set_progress_does_not_crash(qtbot) -> None:
    ring = ProgressRing()
    qtbot.addWidget(ring)

    ring.set_progress(0.5)
    assert abs(ring._progress - 0.5) < 1e-9
    ring.set_progress(5.0)
    assert ring._progress == 1.0
    ring.set_progress(-3)
    assert ring._progress == 0.0

    ring.set_seconds(754)
    ring.set_danger(True)
    ring.set_status("Осталось 12:34")
    ring.show()
    qtbot.wait(80)
    assert ring.isVisible()
    ring.hide()


def test_progress_ring_gradient_paint_renders_without_exception(qtbot) -> None:
    """Регрессия краша 0xC0000409: QPen(QBrush) без ширины -> TypeError в paintEvent."""
    from PyQt6.QtGui import QImage

    ring = ProgressRing()
    qtbot.addWidget(ring)
    ring.set_seconds(45)
    ring.set_progress(0.75)
    ring.set_danger(False)
    ring.set_status("Осталось 00:45")

    image = QImage(300, 300, QImage.Format.Format_ARGB32)
    image.fill(0)
    ring.render(image)  # принудительный paintEvent с градиентной веткой
    assert not image.isNull()
