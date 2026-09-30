from __future__ import annotations

import json
from pathlib import Path

from app.config import DEFAULTS, SettingsManager


def test_defaults_when_file_is_missing(tmp_path: Path) -> None:
    manager = SettingsManager(path=str(tmp_path / "absent.json"))
    for key, value in DEFAULTS.items():
        assert manager.get(key) == value, key
    assert manager.get("no_such_key") is None


def test_set_save_load_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    manager = SettingsManager(path=str(path))
    manager.set("countdown_minutes", 45)
    manager.set("action", "sleep")
    manager.set("mode", "exact")
    manager.set("exact_time", "07:35")
    manager.set("notify_lead_minutes", [7, 3])
    manager.set("grace_seconds", 42)
    manager.save()

    again = SettingsManager(path=str(path))
    assert again.get("countdown_minutes") == 45
    assert again.get("action") == "sleep"
    assert again.get("mode") == "exact"
    assert again.get("exact_time") == "07:35"
    assert again.get("notify_lead_minutes") == [7, 3]
    assert again.get("grace_seconds") == 42


def test_save_is_atomic_and_produces_valid_json(tmp_path: Path) -> None:
    directory = tmp_path / "nested" / "dir"
    path = directory / "settings.json"
    manager = SettingsManager(path=str(path))
    manager.set("mode", "idle")
    manager.save()

    assert path.exists()
    assert not Path(str(path) + ".tmp").exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    assert data["mode"] == "idle"


def test_missing_keys_fall_back_to_defaults(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"mode": "exact"}), encoding="utf-8")

    manager = SettingsManager(path=str(path))
    assert manager.get("mode") == "exact"
    assert manager.get("action") == DEFAULTS["action"]
    assert manager.get("grace_seconds") == DEFAULTS["grace_seconds"]
    assert manager.get("mini_widget_enabled") == DEFAULTS["mini_widget_enabled"]


def test_corrupt_file_falls_back_to_defaults(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text("{ это не json", encoding="utf-8")

    manager = SettingsManager(path=str(path))
    assert manager.get("mode") == DEFAULTS["mode"]


def test_defaults_are_not_shared_between_instances(tmp_path: Path) -> None:
    first = SettingsManager(path=str(tmp_path / "a.json"))
    first.set("notify_lead_minutes", [1])
    second = SettingsManager(path=str(tmp_path / "b.json"))
    assert second.get("notify_lead_minutes") == DEFAULTS["notify_lead_minutes"]
    assert second.get("notify_lead_minutes") is not first.get("notify_lead_minutes")
