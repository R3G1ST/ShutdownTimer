from __future__ import annotations

import math
import time
from itertools import pairwise

from app.config import SettingsManager
from app.timers.engine import TimerEngine, idle_seconds


def _idle_limit_minutes() -> int:
    """Лимит с запасом, чтобы тестовый прогон не дошёл до реального срабатывания."""
    return math.ceil((idle_seconds() + 600) / 60)


def test_idle_mode_starts_and_ticks(
    qtbot, settings: SettingsManager, engine: TimerEngine
) -> None:
    settings.set("mode", "idle")
    settings.set("idle_minutes", _idle_limit_minutes())

    ticks: list[int] = []
    engine.tick.connect(ticks.append)

    with qtbot.waitSignal(engine.started, timeout=3000):
        engine.start()

    assert engine.is_running
    assert engine.remaining >= 500

    qtbot.waitUntil(lambda: len(ticks) >= 2, timeout=5000)
    assert all(b <= a for a, b in pairwise(ticks))

    with qtbot.waitSignal(engine.stopped, timeout=3000):
        engine.stop()
    assert not engine.is_running


def test_idle_mode_ticks_with_one_second_period(
    qtbot, settings: SettingsManager, engine: TimerEngine
) -> None:
    settings.set("mode", "idle")
    settings.set("idle_minutes", _idle_limit_minutes())

    stamps: list[float] = []
    engine.tick.connect(lambda _value: stamps.append(time.monotonic()))

    engine.start()
    qtbot.waitUntil(lambda: len(stamps) >= 4, timeout=8000)

    gap = stamps[-1] - stamps[-2]
    assert 0.7 <= gap <= 2.5, f"период тика idle-режима подозрительный: {gap:.2f} с"

    engine.stop()
    assert not engine.is_running
