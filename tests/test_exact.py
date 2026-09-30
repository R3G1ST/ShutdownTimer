from __future__ import annotations

from datetime import datetime as real_datetime
from datetime import timedelta

import pytest

import app.timers.engine as engine_module
from app.config import SettingsManager
from app.timers.engine import TimerEngine, exact_seconds


def test_exact_seconds_two_minutes_ahead(monkeypatch: pytest.MonkeyPatch) -> None:
    base = real_datetime.now().astimezone().replace(second=0, microsecond=0)

    class _FrozenDateTime:
        @classmethod
        def now(cls) -> real_datetime:
            return base

    monkeypatch.setattr(engine_module, "datetime", _FrozenDateTime)

    target = (base + timedelta(minutes=2)).strftime("%H:%M")
    assert exact_seconds(target) == 120


def test_exact_seconds_two_minutes_ahead_midnight_wrap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = real_datetime(2026, 1, 1, 23, 59, 0).astimezone()

    class _FrozenDateTime:
        @classmethod
        def now(cls) -> real_datetime:
            return base

    monkeypatch.setattr(engine_module, "datetime", _FrozenDateTime)

    assert exact_seconds("00:01") == 120


def test_engine_exact_mode_remaining_approximately_two_minutes(
    monkeypatch: pytest.MonkeyPatch,
    settings: SettingsManager,
    engine: TimerEngine,
) -> None:
    base = real_datetime.now().astimezone().replace(second=0, microsecond=0)

    class _FrozenDateTime:
        @classmethod
        def now(cls) -> real_datetime:
            return base

    monkeypatch.setattr(engine_module, "datetime", _FrozenDateTime)

    target = (base + timedelta(minutes=2)).strftime("%H:%M")
    settings.set("mode", "exact")
    settings.set("exact_time", target)

    engine.start()
    try:
        assert abs(engine.remaining - 120) <= 3, engine.remaining
        assert engine.is_running
    finally:
        engine.stop()


def test_exact_seconds_defaults_on_garbage() -> None:
    assert exact_seconds("") > 0
    assert exact_seconds("99:99") > 0
    assert exact_seconds("ab:cd") > 0
