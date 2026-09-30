from __future__ import annotations

import ctypes
import math
import time
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import QObject, Qt, QThread, QTimer, pyqtSignal, pyqtSlot

if TYPE_CHECKING:
    from app.config import SettingsManager

_user32 = ctypes.windll.user32
_kernel32 = ctypes.windll.kernel32
_kernel32.GetTickCount64.restype = ctypes.c_uint64

MODES = ("countdown", "exact", "idle")


class _LastInputInfo(ctypes.Structure):
    _fields_ = [("cb_size", ctypes.c_uint), ("dw_time", ctypes.c_uint)]


def idle_seconds() -> int:
    info = _LastInputInfo()
    info.cb_size = ctypes.sizeof(_LastInputInfo)
    if not _user32.GetLastInputInfo(ctypes.byref(info)):
        return 0
    elapsed_ms = (_kernel32.GetTickCount64() - info.dw_time) & 0xFFFFFFFF
    return int(elapsed_ms // 1000)


def countdown_seconds(minutes: float) -> int:
    return round(max(0.0, _as_float(minutes, 0.0)) * 60)


def exact_seconds(value: str) -> int:
    now = datetime.now().astimezone()
    hour, minute = _parse_hhmm(value)
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return math.ceil((target - now).total_seconds())


def _parse_hhmm(value: str) -> tuple[int, int]:
    try:
        parts = str(value).split(":")
        hour = int(parts[0])
        minute = int(parts[1])
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return hour, minute
    except (IndexError, TypeError, ValueError):
        pass
    return 23, 0


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


class _EngineWorker(QObject):
    tick = pyqtSignal(int)
    warning = pyqtSignal(int)
    completed = pyqtSignal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._timer: QTimer | None = None
        self._mode = "countdown"
        self._running = False
        self._paused = False
        self._target = 0.0
        self._limit = 0
        self._paused_remaining = 0
        self._thresholds: set[int] = set()
        self._fired: set[int] = set()

    def _ensure_timer(self) -> QTimer:
        if self._timer is None:
            timer = QTimer()
            timer.setTimerType(Qt.TimerType.PreciseTimer)
            timer.timeout.connect(self._on_timeout)
            timer.setParent(self)
            self._timer = timer
        return self._timer

    def _compute_remaining(self) -> int:
        if self._paused:
            return self._paused_remaining
        if self._mode == "idle":
            return max(0, self._limit - idle_seconds())
        return max(0, math.ceil(self._target - time.monotonic()))

    def _check_warnings(self, remaining: int) -> None:
        for threshold in sorted(self._thresholds, reverse=True):
            if threshold in self._fired or remaining > threshold:
                continue
            self._fired.add(threshold)
            self.warning.emit(remaining)

    def _rearm_warnings(self, remaining: int) -> None:
        self._fired = {item for item in self._fired if remaining <= item}

    def _finish(self) -> None:
        if self._timer is not None:
            self._timer.stop()
        self._running = False
        self._paused = False
        self.completed.emit()

    @pyqtSlot(object)
    def handle_start(self, params: Any) -> None:
        data = params if isinstance(params, dict) else {}
        mode = str(data.get("mode", "countdown"))
        self._mode = mode if mode in MODES else "countdown"
        self._thresholds = {
            _as_int(item, 0) for item in data.get("warns", []) if _as_int(item, 0) > 0
        }
        self._target = float(data.get("target_mono", time.monotonic()))
        self._limit = _as_int(data.get("idle_limit"), 0)
        self._paused = False
        self._paused_remaining = 0
        self._running = True
        remaining = self._compute_remaining()
        # Пороги, уже просроченные на старте (остаток <= порога), не стреляем:
        # иначе таймер на 60 с выдал бы сразу 3 тоста «осталось 10/5/1 мин»
        self._fired = {item for item in self._thresholds if remaining <= item}
        timer = self._ensure_timer()
        timer.stop()
        self.tick.emit(remaining)
        if remaining <= 0:
            self._finish()
            return
        timer.start(1000 if self._mode == "idle" else 250)

    @pyqtSlot()
    def handle_stop(self) -> None:
        self._running = False
        self._paused = False
        self._fired = set()
        if self._timer is not None:
            self._timer.stop()

    @pyqtSlot()
    def handle_pause(self) -> None:
        if not self._running or self._paused:
            return
        remaining = self._compute_remaining()
        self._paused = True
        self._paused_remaining = remaining
        if self._timer is not None:
            self._timer.stop()
        self.tick.emit(remaining)

    @pyqtSlot()
    def handle_resume(self) -> None:
        if not self._running or not self._paused:
            return
        if self._mode in ("countdown", "exact"):
            self._target = time.monotonic() + self._paused_remaining
        self._paused = False
        remaining = self._compute_remaining()
        self._ensure_timer().start(1000 if self._mode == "idle" else 250)
        self.tick.emit(remaining)

    @pyqtSlot(int)
    def handle_extend(self, seconds: int) -> None:
        if not self._running or seconds <= 0 or self._mode == "idle":
            return
        self._target += seconds
        if self._paused:
            self._paused_remaining += seconds
            remaining = self._paused_remaining
        else:
            remaining = self._compute_remaining()
        self._rearm_warnings(remaining)
        self.tick.emit(remaining)

    @pyqtSlot()
    def _on_timeout(self) -> None:
        if not self._running or self._paused:
            return
        remaining = self._compute_remaining()
        self._check_warnings(remaining)
        if remaining <= 0:
            self.tick.emit(0)
            self._finish()
            return
        self.tick.emit(remaining)


class TimerEngine(QObject):
    tick = pyqtSignal(int)
    warning = pyqtSignal(int)
    completed = pyqtSignal()
    started = pyqtSignal()
    stopped = pyqtSignal()
    cmd_start = pyqtSignal(object)
    cmd_stop = pyqtSignal()
    cmd_pause = pyqtSignal()
    cmd_resume = pyqtSignal()
    cmd_extend = pyqtSignal(int)

    def __init__(self, settings: SettingsManager, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._running = False
        self._paused = False
        self._remaining = 0
        self._worker: _EngineWorker | None = None
        self._thread: QThread | None = None
        self._setup_worker()

    def _setup_worker(self) -> None:
        worker = _EngineWorker()
        thread = QThread()
        worker.moveToThread(thread)
        worker.tick.connect(self._on_worker_tick)
        worker.warning.connect(self._on_worker_warning)
        worker.completed.connect(self._on_worker_completed)
        self.cmd_start.connect(worker.handle_start)
        self.cmd_stop.connect(worker.handle_stop)
        self.cmd_pause.connect(worker.handle_pause)
        self.cmd_resume.connect(worker.handle_resume)
        self.cmd_extend.connect(worker.handle_extend)
        thread.finished.connect(worker.deleteLater)
        thread.start()
        self._worker = worker
        self._thread = thread

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def is_paused(self) -> bool:
        return self._paused

    @property
    def remaining(self) -> int:
        return self._remaining

    def start(self) -> None:
        if self._worker is None:
            return
        params = self._build_params()
        if self._running:
            self.cmd_stop.emit()
        self._running = True
        self._paused = False
        self._remaining = _as_int(params.get("initial_remaining"), 0)
        self.cmd_start.emit(params)
        self.started.emit()
        self.tick.emit(self._remaining)

    def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        self._paused = False
        self._remaining = 0
        if self._worker is not None:
            self.cmd_stop.emit()
        self.stopped.emit()

    def pause(self) -> None:
        if not self._running or self._paused or self._worker is None:
            return
        self._paused = True
        self.cmd_pause.emit()

    def resume(self) -> None:
        if not self._running or not self._paused or self._worker is None:
            return
        self._paused = False
        self.cmd_resume.emit()

    def extend(self, seconds: int) -> None:
        if not self._running or self._worker is None:
            return
        value = _as_int(seconds, 0)
        if value <= 0:
            return
        self.cmd_extend.emit(value)

    def close(self) -> None:
        thread = self._thread
        worker = self._worker
        if thread is None:
            return
        signals = []
        if worker is not None:
            signals.extend([worker.tick, worker.warning, worker.completed])
        signals.extend(
            [self.cmd_start, self.cmd_stop, self.cmd_pause, self.cmd_resume, self.cmd_extend]
        )
        for signal in signals:
            try:
                signal.disconnect()
            except (RuntimeError, TypeError):
                pass
        thread.quit()
        if thread.wait(2000):
            self._thread = None
            self._worker = None

    def _build_params(self) -> dict[str, Any]:
        mode = str(self._settings.get("mode", "countdown"))
        if mode not in MODES:
            mode = "countdown"
        warns: list[int] = []
        leads = self._settings.get("notify_lead_minutes", [10, 5, 1])
        if isinstance(leads, (list, tuple)):
            for lead in leads:
                minutes = _as_int(lead, 0)
                if minutes > 0:
                    warns.append(minutes * 60)
        limit = 0
        target = time.monotonic()
        if mode == "countdown":
            initial = countdown_seconds(
                _as_float(self._settings.get("countdown_minutes", 30), 30.0)
            )
            target += initial
        elif mode == "exact":
            initial = exact_seconds(str(self._settings.get("exact_time", "23:00")))
            target += initial
        else:
            limit = countdown_seconds(
                _as_float(self._settings.get("idle_minutes", 15), 15.0)
            )
            initial = max(0, limit - idle_seconds())
        return {
            "mode": mode,
            "target_mono": target,
            "idle_limit": limit,
            "warns": warns,
            "initial_remaining": initial,
        }

    def _on_worker_tick(self, remaining: int) -> None:
        self._remaining = max(0, _as_int(remaining, 0))
        self.tick.emit(self._remaining)

    def _on_worker_warning(self, remaining: int) -> None:
        self.warning.emit(_as_int(remaining, 0))

    def _on_worker_completed(self) -> None:
        self._running = False
        self._paused = False
        self._remaining = 0
        self.completed.emit()
        self.stopped.emit()

    def __del__(self) -> None:
        try:
            self.close()
        except (AttributeError, OSError, RuntimeError, TypeError):
            return
