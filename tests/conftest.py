from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Qt в тестах всегда безэкранный: окна не мешают, поведение детерминировано.
os.environ["QT_QPA_PLATFORM"] = "offscreen"
# Ни один тест не должен дать реальному ПК выключиться.
os.environ["SHUTDOWNTIMER_DRY_RUN"] = "1"


@pytest.fixture(autouse=True)
def dry_run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Гарантирует DRY-RUN и переводит APPDATA в tmp (реальные настройки/логи не трогаем)."""
    monkeypatch.setenv("SHUTDOWNTIMER_DRY_RUN", "1")
    appdata = tmp_path / "appdata"
    appdata.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("APPDATA", str(appdata))
    return appdata


@pytest.fixture
def settings(tmp_path: Path):
    from app.config import SettingsManager

    return SettingsManager(path=str(tmp_path / "settings.json"))


@pytest.fixture
def tmp_settings(settings):
    return settings


@pytest.fixture
def engine(qapp, settings):
    from app.timers.engine import TimerEngine

    created = TimerEngine(settings)
    try:
        yield created
    finally:
        created.close()
