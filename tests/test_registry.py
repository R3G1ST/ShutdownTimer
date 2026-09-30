from __future__ import annotations

from typing import Self

import pytest

from app.system import autostart, protocol


class _FakeWinreg:
    """Ин-память реализация ровно тех функций winreg, которые используют модули."""

    HKEY_CURRENT_USER = "HKEY_CURRENT_USER"
    KEY_READ = 0x20019
    KEY_SET_VALUE = 0x20001
    REG_SZ = 1

    def __init__(self) -> None:
        self.keys: set[str] = set()
        self.values: dict[tuple[str, str], str] = {}

    def CreateKey(self, root: object, path: str) -> _FakeKey:
        self.keys.add(path)
        return _FakeKey(self, path)

    def OpenKey(self, root: object, path: str, *_args: object) -> _FakeKey:
        if path not in self.keys:
            raise FileNotFoundError(path)
        return _FakeKey(self, path)

    def QueryValueEx(self, key: _FakeKey, name: str) -> tuple[str, int]:
        if (key.path, name) not in self.values:
            raise FileNotFoundError(name)
        return (self.values[(key.path, name)], self.REG_SZ)

    def SetValueEx(
        self, key: _FakeKey, name: str, _reserved: int, _type: int, data: str
    ) -> None:
        self.values[(key.path, name)] = data

    def DeleteValue(self, key: _FakeKey, name: str) -> None:
        try:
            del self.values[(key.path, name)]
        except KeyError as exc:
            raise FileNotFoundError(name) from exc

    def DeleteKeyEx(self, root: object, path: str, *_args: object) -> None:
        if path not in self.keys:
            raise FileNotFoundError(path)
        self.keys.discard(path)
        for stored in [item for item in self.values if item[0] == path]:
            del self.values[stored]


class _FakeKey:
    def __init__(self, registry: _FakeWinreg, path: str) -> None:
        self._registry = registry
        self.path = path

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_exc: object) -> bool:
        return False


@pytest.fixture
def fake_winreg(monkeypatch: pytest.MonkeyPatch) -> _FakeWinreg:
    fake = _FakeWinreg()
    monkeypatch.setattr(autostart, "winreg", fake)
    monkeypatch.setattr(protocol, "winreg", fake)
    return fake


def test_autostart_roundtrip(fake_winreg: _FakeWinreg) -> None:
    assert autostart.is_enabled() is False

    assert autostart.set_enabled(True, r"C:\apps\ShutdownTimer.exe") is True
    assert autostart.is_enabled() is True
    value = fake_winreg.values[
        (r"Software\Microsoft\Windows\CurrentVersion\Run", "ShutdownTimer")
    ]
    assert value == r'"C:\apps\ShutdownTimer.exe"'

    assert autostart.set_enabled(False, r"C:\apps\ShutdownTimer.exe") is True
    assert autostart.is_enabled() is False


def test_autostart_disable_without_key_succeeds(fake_winreg: _FakeWinreg) -> None:
    assert autostart.set_enabled(False) is True
    assert autostart.is_enabled() is False


def test_autostart_enable_failure_returns_false(
    fake_winreg: _FakeWinreg, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _deny(*_args: object, **_kwargs: object) -> _FakeKey:
        raise OSError("access denied")

    monkeypatch.setattr(fake_winreg, "CreateKey", _deny)
    assert autostart.set_enabled(True) is False


def test_protocol_register_unregister(fake_winreg: _FakeWinreg) -> None:
    assert protocol.is_registered() is False

    assert protocol.register_protocol(r"C:\apps\ShutdownTimer.exe") is True
    assert protocol.is_registered() is True

    command_key = r"Software\Classes\shutdowntimer\shell\open\command"
    assert (
        fake_winreg.values[(command_key, "")]
        == r'"C:\apps\ShutdownTimer.exe" "%1"'
    )
    shell_key = r"Software\Classes\shutdowntimer"
    assert fake_winreg.values[(shell_key, "URL Protocol")] == ""

    protocol.unregister_protocol()
    assert protocol.is_registered() is False
    assert shell_key not in fake_winreg.keys
    assert not any(key.startswith(shell_key) for key in fake_winreg.values)


def test_protocol_is_registered_handles_blank_value(
    fake_winreg: _FakeWinreg,
) -> None:
    command_key = r"Software\Classes\shutdowntimer\shell\open\command"
    fake_winreg.keys.add(command_key)
    fake_winreg.values[(command_key, "")] = "   "
    assert protocol.is_registered() is False

    fake_winreg.values[(command_key, "")] = "x"
    assert protocol.is_registered() is True
