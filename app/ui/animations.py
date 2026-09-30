from __future__ import annotations

from PyQt6.QtCore import (
    QAbstractAnimation,
    QEasingCurve,
    QParallelAnimationGroup,
    QPoint,
    QPropertyAnimation,
    QVariantAnimation,
)
from PyQt6.QtWidgets import QGraphicsOpacityEffect, QWidget


def _opacity_effect(widget: QWidget) -> QGraphicsOpacityEffect:
    effect = widget.graphicsEffect()
    if isinstance(effect, QGraphicsOpacityEffect):
        return effect
    created = QGraphicsOpacityEffect(widget)
    created.setOpacity(1.0)
    widget.setGraphicsEffect(created)
    return created


def fade_in(widget: QWidget, duration: int = 200) -> QPropertyAnimation:
    effect = _opacity_effect(widget)
    animation = QPropertyAnimation(effect, b"opacity", widget)
    animation.setDuration(max(1, duration))
    animation.setStartValue(0.0)
    animation.setEndValue(1.0)
    animation.setEasingCurve(QEasingCurve.Type.OutCubic)
    animation.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
    return animation


def slide_down(
    widget: QWidget, duration: int = 150, distance: int = 14
) -> QParallelAnimationGroup:
    group = QParallelAnimationGroup(widget)
    effect = _opacity_effect(widget)
    fade = QPropertyAnimation(effect, b"opacity", widget)
    fade.setDuration(max(1, duration))
    fade.setStartValue(0.0)
    fade.setEndValue(1.0)
    fade.setEasingCurve(QEasingCurve.Type.OutCubic)
    target = widget.pos()
    move = QPropertyAnimation(widget, b"pos", widget)
    move.setDuration(max(1, duration))
    move.setStartValue(QPoint(target.x(), target.y() - max(0, distance)))
    move.setEndValue(target)
    move.setEasingCurve(QEasingCurve.Type.OutCubic)
    group.addAnimation(fade)
    group.addAnimation(move)
    group.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)
    return group


def pulse(
    widget: QWidget, duration: int = 700, minimum: float = 0.35
) -> QVariantAnimation:
    existing = getattr(widget, "_st_pulse_animation", None)
    if existing is not None:
        try:
            if existing.state() == QAbstractAnimation.State.Running:
                return existing
            existing.deleteLater()
        except RuntimeError:
            pass
    effect = _opacity_effect(widget)
    animation = QVariantAnimation(widget)
    animation.setDuration(max(1, duration))
    animation.setEasingCurve(QEasingCurve.Type.OutCubic)
    animation.setKeyValueAt(0.0, 1.0)
    animation.setKeyValueAt(0.5, min(max(float(minimum), 0.0), 1.0))
    animation.setKeyValueAt(1.0, 1.0)
    animation.valueChanged.connect(effect.setOpacity)
    animation.finished.connect(lambda: effect.setOpacity(1.0))
    widget._st_pulse_animation = animation
    animation.start()
    return animation
