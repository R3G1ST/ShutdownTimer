from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from app.system import actions


def test_is_dry_run_reads_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHUTDOWNTIMER_DRY_RUN", "1")
    assert actions.is_dry_run() is True

    monkeypatch.setenv("SHUTDOWNTIMER_DRY_RUN", "0")
    assert actions.is_dry_run() is False

    monkeypatch.setenv("SHUTDOWNTIMER_DRY_RUN", "")
    assert actions.is_dry_run() is False

    monkeypatch.delenv("SHUTDOWNTIMER_DRY_RUN", raising=False)
    assert actions.is_dry_run() is False


def test_perform_dry_run_writes_log(dry_run: Path) -> None:
    result = actions.perform("shutdown", grace_seconds=7, dry_run=True)

    assert "[DRY-RUN]" in result
    log = dry_run / "ShutdownTimer" / "dry_run.log"
    assert log.exists()
    content = log.read_text(encoding="utf-8")
    assert "[DRY-RUN]" in content
    assert "action=shutdown" in content
    assert "grace=7" in content


def test_perform_dry_run_for_every_action(dry_run: Path) -> None:
    for action in actions.ACTIONS:
        result = actions.perform(action, grace_seconds=3, dry_run=True)
        assert "[DRY-RUN]" in result
        assert action in result

    content = (dry_run / "ShutdownTimer" / "dry_run.log").read_text(encoding="utf-8")
    for action in actions.ACTIONS:
        assert f"action={action}" in content


def test_perform_uses_environment_when_flag_is_omitted(dry_run: Path) -> None:
    # autouse-фикстура выставила SHUTDOWNTIMER_DRY_RUN=1 -> без явного флага тоже dry-run
    result = actions.perform("restart")
    assert "[DRY-RUN]" in result


def test_cancel_is_dry_run(dry_run: Path) -> None:
    result = actions.cancel()

    assert "[DRY-RUN]" in result
    assert "action=cancel" in result
    log = dry_run / "ShutdownTimer" / "dry_run.log"
    assert "action=cancel" in log.read_text(encoding="utf-8")


def test_no_subprocess_is_spawned(monkeypatch: pytest.MonkeyPatch, dry_run: Path) -> None:
    calls: list[object] = []

    def _boom(*args: object, **kwargs: object) -> None:
        calls.append(args)
        raise AssertionError("subprocess.run called during dry-run!")

    monkeypatch.setattr(subprocess, "run", _boom)

    actions.perform("shutdown", grace_seconds=1, dry_run=True)
    actions.perform("restart", grace_seconds=1, dry_run=True)
    actions.perform("sleep", grace_seconds=1, dry_run=True)
    actions.perform("hibernate", grace_seconds=1, dry_run=True)
    actions.cancel()

    assert calls == []


def test_unknown_action_reports_error_without_side_effects() -> None:
    result = actions.perform("nuke", dry_run=True)
    assert "[DRY-RUN]" in result
