from __future__ import annotations

import threading
from itertools import pairwise

from app.config import SettingsManager
from app.timers.engine import TimerEngine


def test_countdown_starts_ticks_and_counts_down(
    qtbot, settings: SettingsManager, engine: TimerEngine
) -> None:
    settings.set("countdown_minutes", 2 / 60)  # ровно 2 секунды
    ticks: list[int] = []
    engine.tick.connect(ticks.append)

    with qtbot.waitSignal(engine.started, timeout=3000):
        engine.start()

    assert engine.is_running
    assert engine.remaining > 0

    qtbot.waitUntil(lambda: len(ticks) >= 3, timeout=4000)
    qtbot.waitUntil(lambda: ticks[-1] < ticks[0], timeout=5000)
    # отсчёт не растёт: значения недекрементны
    assert all(b <= a for a, b in pairwise(ticks))


def test_pause_freezes_remaining_and_resume_continues(
    qtbot, settings: SettingsManager, engine: TimerEngine
) -> None:
    settings.set("countdown_minutes", 1)  # 60 с
    ticks: list[int] = []
    engine.tick.connect(ticks.append)

    engine.start()
    qtbot.waitUntil(lambda: len(ticks) >= 2, timeout=3000)

    engine.pause()
    qtbot.wait(150)  # даём догнать отложенные тики
    assert engine.is_paused
    frozen = engine.remaining
    assert frozen > 0
    seen = len(ticks)

    qtbot.wait(700)
    assert len(ticks) == seen, "во время паузы не должно приходить тиков"
    assert engine.remaining == frozen

    engine.resume()
    assert not engine.is_paused
    qtbot.waitUntil(lambda: engine.remaining < frozen, timeout=3000)

    engine.stop()


def test_extend_increases_remaining(
    qtbot, settings: SettingsManager, engine: TimerEngine
) -> None:
    settings.set("countdown_minutes", 2)  # 120 с
    engine.start()
    qtbot.waitUntil(lambda: engine.remaining > 0, timeout=3000)
    before = engine.remaining

    with qtbot.waitSignal(engine.tick, timeout=3000):
        engine.extend(300)

    qtbot.waitUntil(lambda: engine.remaining >= before + 295, timeout=3000)
    assert engine.is_running

    engine.stop()


def test_stop_emits_stopped(qtbot, settings: SettingsManager, engine: TimerEngine) -> None:
    settings.set("countdown_minutes", 5)
    engine.start()
    assert engine.is_running

    with qtbot.waitSignal(engine.stopped, timeout=3000):
        engine.stop()

    assert not engine.is_running
    assert engine.remaining == 0


def test_short_countdown_completes_and_stops(
    qtbot, settings: SettingsManager, engine: TimerEngine
) -> None:
    settings.set("countdown_minutes", 1 / 60)  # 1 секунда
    stopped: list[int] = []
    engine.stopped.connect(lambda: stopped.append(1))

    with qtbot.waitSignal(engine.completed, timeout=6000):
        engine.start()

    qtbot.waitUntil(lambda: bool(stopped), timeout=3000)
    assert not engine.is_running
    assert engine.remaining == 0


def test_warning_emits_once_per_threshold(
    qtbot, settings: SettingsManager, engine: TimerEngine
) -> None:
    settings.set("countdown_minutes", 2 / 60)
    settings.set("notify_lead_minutes", [1])  # порог 60 с
    warnings: list[int] = []
    engine.warning.connect(warnings.append)

    with qtbot.waitSignal(engine.completed, timeout=6000):
        engine.start()

    qtbot.wait(400)
    assert len(warnings) == 1, warnings
    assert warnings[0] <= 60


def test_extend_rearms_warning_threshold(
    qtbot, settings: SettingsManager, engine: TimerEngine
) -> None:
    settings.set("countdown_minutes", 2 / 60)
    settings.set("notify_lead_minutes", [1])
    warnings: list[int] = []
    engine.warning.connect(warnings.append)

    engine.start()
    qtbot.waitUntil(lambda: bool(warnings), timeout=4000)

    worker = engine._worker
    assert worker is not None
    qtbot.wait(100)
    assert 60 in worker._fired, "сработавший порог должен быть в _fired"

    engine.extend(300)
    qtbot.wait(200)
    assert 60 not in worker._fired, "после продления порог должен перевзвестись"
    assert len(warnings) == 1, warnings

    engine.stop()


def test_repeated_start_stop_does_not_leak_threads(
    qtbot, settings: SettingsManager, engine: TimerEngine
) -> None:
    settings.set("countdown_minutes", 10)
    base_threads = threading.active_count()
    first_thread = engine._thread
    assert first_thread is not None

    for _ in range(20):
        engine.start()
        qtbot.wait(25)
        engine.stop()
        qtbot.wait(5)

    assert engine._thread is first_thread, "внутренний поток не должен пересоздаваться"
    assert first_thread.isRunning()
    assert not engine.is_running
    assert threading.active_count() <= base_threads + 1

    # движок остаётся рабочим после серии перезапусков
    ticks: list[int] = []
    engine.tick.connect(ticks.append)
    engine.start()
    qtbot.waitUntil(lambda: len(ticks) >= 1, timeout=3000)
    engine.stop()
    assert not engine.is_running


def test_close_terminates_worker_thread(qtbot, settings: SettingsManager) -> None:
    created = TimerEngine(settings)
    thread = created._thread
    assert thread is not None
    created.start()
    qtbot.wait(60)
    created.stop()
    created.close()

    assert created._thread is None, "поток воркера должен корректно завершиться"
    assert not thread.isRunning()
    created.close()  # повторный вызов безопасен
