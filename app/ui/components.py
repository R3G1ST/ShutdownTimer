from __future__ import annotations

from collections.abc import Sequence

from PyQt6.QtCore import (
    QAbstractAnimation,
    QEasingCurve,
    QPointF,
    QPropertyAnimation,
    QRectF,
    QSize,
    Qt,
    QVariantAnimation,
    pyqtProperty,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QConicalGradient,
    QFont,
    QFontMetricsF,
    QLinearGradient,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPaintEvent,
    QPen,
    QResizeEvent,
)
from PyQt6.QtWidgets import QFrame, QPushButton, QSizePolicy, QWidget

from app.ui.styles import ACCENT, ACCENT_2, DANGER, TEXT_DIGITS, TEXT_DIM

TRACK_COLOR = QColor(255, 255, 255, 18)
BORDER_COLOR = QColor(255, 255, 255, 26)
BASE_COLOR = QColor(255, 255, 255, 13)
DISABLED_COLOR = QColor(255, 255, 255, 90)
LABEL_IDLE = QColor("#98A1B3")
LABEL_ACTIVE = QColor("#FFFFFF")

_SWITCH_W = 46
_SWITCH_H = 26
_KNOB = 20
_KNOB_MARGIN = 3


def _repolish(widget: QWidget) -> None:
    style = widget.style()
    if style is None:
        return
    style.unpolish(widget)
    style.polish(widget)


class GlassCard(QFrame):
    def __init__(self, parent: QWidget | None = None, radius: int = 16) -> None:
        super().__init__(parent)
        self.setProperty("radius", radius)
        self._radius = float(radius)

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        if self.width() < 24 or self.height() < 4:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(255, 255, 255, 42))
        pen.setWidthF(1.0)
        painter.setPen(pen)
        inset = min(self._radius * 0.7, self.width() / 2)
        painter.drawLine(
            QPointF(float(inset), 0.5),
            QPointF(float(self.width()) - inset, 0.5),
        )


class Chip(QPushButton):
    def __init__(
        self, text: str, parent: QWidget | None = None, active: bool = False
    ) -> None:
        super().__init__(text, parent)
        self.setFixedHeight(36)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.set_active(active)

    @property
    def active(self) -> bool:
        return self.property("active") == "true"

    def set_active(self, value: bool) -> None:
        state = "true" if value else "false"
        if self.property("active") == state:
            return
        self.setProperty("active", state)
        _repolish(self)


class Switch(QPushButton):
    def __init__(self, checked: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(_SWITCH_W, _SWITCH_H)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._knob = self._knob_target(checked)
        self.toggled.connect(self._on_toggled)
        self.setChecked(checked)
        self.update()

    @property
    def checked(self) -> bool:
        return self.isChecked()

    def _knob_target(self, checked: bool) -> float:
        if checked:
            return float(_SWITCH_W - _KNOB - _KNOB_MARGIN)
        return float(_KNOB_MARGIN)

    def _on_toggled(self, checked: bool) -> None:
        animation = QPropertyAnimation(self, b"knob", self)
        animation.setDuration(160)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        animation.setStartValue(self._knob)
        animation.setEndValue(self._knob_target(checked))
        animation.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    def _get_knob(self) -> float:
        return self._knob

    def _set_knob(self, value: float) -> None:
        self._knob = float(value)
        self.update()

    knob = pyqtProperty(float, _get_knob, _set_knob)

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.isEnabled():
            painter.setOpacity(0.4)
        track = QRectF(0, 0, _SWITCH_W, _SWITCH_H)
        checked = self.isChecked()
        path = QPainterPath()
        path.addRoundedRect(track, _SWITCH_H / 2, _SWITCH_H / 2)
        if checked:
            gradient = QLinearGradient(0, 0, _SWITCH_W, _SWITCH_H)
            gradient.setColorAt(0.0, QColor(ACCENT))
            gradient.setColorAt(1.0, QColor(ACCENT_2))
            painter.fillPath(path, QBrush(gradient))
        else:
            painter.fillPath(path, QColor(255, 255, 255, 36))
        pen = QPen(QColor(255, 255, 255, 40))
        pen.setWidthF(1.0)
        painter.setPen(pen)
        painter.drawPath(path)
        center = self._knob + _KNOB_MARGIN + _KNOB / 2
        radius = _KNOB / 2
        knob_color = QColor("#FFFFFF") if checked else QColor("#B9C0CE")
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(knob_color)
        painter.drawEllipse(QRectF(center - radius, _SWITCH_H / 2 - radius, _KNOB, _KNOB))


class SegmentedControl(QWidget):
    currentIndexChanged = pyqtSignal(int)

    def __init__(self, items: Sequence[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._items = [str(item) for item in items] or [""]
        self._index = 0
        self._indicator_x: float | None = None
        self._animation: QVariantAnimation | None = None
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def sizeHint(self) -> QSize:
        metrics = QFontMetricsF(self.font())
        width = sum(metrics.horizontalAdvance(item) for item in self._items)
        return QSize(int(width) + len(self._items) * 26 + 20, 40)

    def currentIndex(self) -> int:
        return self._index

    def setCurrentIndex(self, index: int) -> None:
        if index == self._index or not 0 <= index < len(self._items):
            return
        old_x = self._target_x(self._index)
        self._index = index
        self._animate_to(old_x, self._target_x(index))
        self.update()
        self.currentIndexChanged.emit(index)

    def _metrics(self) -> tuple[float, float]:
        pad = 4.0
        cell = (self.width() - 2 * pad) / max(1, len(self._items))
        return pad, cell

    def _target_x(self, index: int) -> float:
        pad, cell = self._metrics()
        return pad + index * cell + 3.0

    def _animate_to(self, start: float, end: float) -> None:
        if self._animation is not None:
            try:
                self._animation.stop()
            except RuntimeError:
                self._animation = None
        animation = QVariantAnimation(self)
        animation.setDuration(180)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        animation.setStartValue(start)
        animation.setEndValue(end)
        animation.valueChanged.connect(self._on_indicator_value)
        animation.finished.connect(self._on_animation_done)
        self._animation = animation
        animation.start(QVariantAnimation.DeletionPolicy.DeleteWhenStopped)

    def _on_animation_done(self) -> None:
        self._animation = None

    def _animation_running(self) -> bool:
        if self._animation is None:
            return False
        try:
            return self._animation.state() == QAbstractAnimation.State.Running
        except RuntimeError:
            self._animation = None
            return False

    def _on_indicator_value(self, value: object) -> None:
        self._indicator_x = float(value)
        self.update()

    def _indicator_rect(self) -> QRectF:
        _pad, cell = self._metrics()
        x = self._indicator_x
        if x is None:
            x = self._target_x(self._index)
        return QRectF(x, 4.0, max(8.0, cell - 6.0), self.height() - 8.0)

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        enabled = self.isEnabled()
        if not enabled:
            painter.setOpacity(0.45)
        base = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        base_path = QPainterPath()
        base_path.addRoundedRect(base, 14.0, 14.0)
        painter.fillPath(base_path, BASE_COLOR)
        pen = QPen(BORDER_COLOR)
        pen.setWidthF(1.0)
        painter.setPen(pen)
        painter.drawPath(base_path)
        indicator = self._indicator_rect()
        indicator_path = QPainterPath()
        indicator_path.addRoundedRect(indicator, 11.0, 11.0)
        gradient = QLinearGradient(indicator.topLeft(), indicator.topRight())
        gradient.setColorAt(0.0, QColor(ACCENT))
        gradient.setColorAt(1.0, QColor(ACCENT_2))
        painter.fillPath(indicator_path, QBrush(gradient))
        font = QFont(self.font())
        pad, cell = self._metrics()
        for i, item in enumerate(self._items):
            font.setBold(i == self._index)
            painter.setFont(font)
            painter.setPen(LABEL_ACTIVE if i == self._index else LABEL_IDLE)
            rect = QRectF(pad + i * cell, 0.0, cell, self.height())
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, item)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            pad, cell = self._metrics()
            local = event.position().x() - pad
            index = int(local // cell) if cell > 0 else 0
            if 0 <= index < len(self._items):
                event.accept()
                self.setCurrentIndex(index)
                return
        super().mousePressEvent(event)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if not self._animation_running():
            self._indicator_x = None
            self.update()


class ProgressRing(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._progress = 0.0
        self._seconds = 0
        self._danger = False
        self._status = "Остановлен"
        self.setFixedSize(260, 260)

    def set_progress(self, value: float) -> None:
        clamped = min(1.0, max(0.0, float(value)))
        if abs(clamped - self._progress) > 1e-6:
            self._progress = clamped
            self.update()

    def set_seconds(self, value: int) -> None:
        seconds = max(0, int(value))
        if seconds != self._seconds:
            self._seconds = seconds
            self.update()

    def set_danger(self, value: bool) -> None:
        flag = bool(value)
        if flag != self._danger:
            self._danger = flag
            self.update()

    def set_status(self, text: str) -> None:
        if text != self._status:
            self._status = text
            self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        margin = 14.0
        rect = QRectF(self.rect()).adjusted(margin, margin, -margin, -margin)
        center = rect.center()
        ring_width = 14.0
        track_pen = QPen(TRACK_COLOR)
        track_pen.setWidthF(ring_width)
        track_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(track_pen)
        painter.drawArc(rect, 0, 360 * 16)
        if self._progress > 0.002:
            if self._danger:
                arc_pen = QPen(QColor(DANGER))
            else:
                gradient = QConicalGradient(center, -90.0)
                gradient.setColorAt(0.0, QColor(ACCENT))
                gradient.setColorAt(1.0, QColor(ACCENT_2))
                arc_pen = QPen(QBrush(gradient), ring_width)
            arc_pen.setWidthF(ring_width)
            arc_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(arc_pen)
            span = -round(self._progress * 360 * 16)
            painter.drawArc(rect, 90 * 16, span)
        text = f"{self._seconds // 60:02d}:{self._seconds % 60:02d}"
        font = QFont("Consolas")
        font.setPixelSize(76)
        metrics = QFontMetricsF(font)
        inner = rect.width() - ring_width - 8.0
        advance = metrics.horizontalAdvance(text)
        if advance > inner > 0:
            font.setPixelSize(max(24, int(76 * (inner / advance))))
        painter.setFont(font)
        painter.setPen(QColor(DANGER) if self._danger else QColor(TEXT_DIGITS))
        digits_rect = QRectF(margin, center.y() - 62.0, self.width() - 2 * margin, 84.0)
        painter.drawText(
            digits_rect,
            int(Qt.AlignmentFlag.AlignCenter),
            text,
        )
        status_font = QFont("Segoe UI Variable")
        status_font.setPixelSize(15)
        painter.setFont(status_font)
        status_color = QColor(DANGER) if self._danger else QColor(TEXT_DIM)
        painter.setPen(status_color)
        status_rect = QRectF(margin, center.y() + 30.0, self.width() - 2 * margin, 24.0)
        painter.drawText(
            status_rect,
            int(Qt.AlignmentFlag.AlignCenter),
            self._status,
        )
