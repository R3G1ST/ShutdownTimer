from __future__ import annotations

from string import Template

from PyQt6.QtWidgets import QApplication

BG = "#0A0E14"
TEXT = "#E6EAF2"
TEXT_BRIGHT = "#F4F7FB"
TEXT_DIGITS = "#E9EEF8"
TEXT_DIM = "#8B93A7"
TEXT_HINT = "#7D8698"
TEXT_LABEL = "#A9B1C1"
ACCENT = "#7C6CFF"
ACCENT_2 = "#38BDF8"
SUCCESS = "#34D399"
DANGER = "#FB7185"
DANGER_DEEP = "#F43F5E"
CARD_BG = "rgba(255, 255, 255, 0.06)"
CARD_BG_HOVER = "rgba(255, 255, 255, 0.09)"
BORDER = "rgba(255, 255, 255, 0.12)"
BORDER_SOFT = "rgba(255, 255, 255, 0.10)"
BORDER_LIGHT = "rgba(255, 255, 255, 0.16)"
FONT_FAMILY = '"Segoe UI Variable", "Segoe UI", sans-serif'
FONT_MONO = "Consolas, monospace"

_TEMPLATE = Template(
    """
QWidget {
    background: transparent;
    color: $TEXT;
    font-family: $FONT_FAMILY;
    font-size: 13px;
}
QLabel#windowTitle {
    font-size: 15px;
    font-weight: bold;
    color: $TEXT_BRIGHT;
}
QLabel#sectionTitle {
    font-size: 12px;
    font-weight: bold;
    color: $TEXT_LABEL;
}
QLabel#caption {
    font-size: 13px;
    color: $TEXT_LABEL;
}
QLabel#hint {
    font-size: 12px;
    color: $TEXT_HINT;
}
QLabel#unitLabel {
    font-size: 12px;
    color: $TEXT_DIM;
}
QLabel#graceTitle {
    font-size: 26px;
    font-weight: bold;
    color: $TEXT_BRIGHT;
}
QLabel#graceHint {
    font-size: 13px;
    color: $TEXT_DIM;
}
QLabel#miniDigits {
    font-family: $FONT_MONO;
    font-size: 26px;
    color: $TEXT_DIGITS;
}
QLabel#dryBadge {
    font-size: 12px;
    font-weight: bold;
    color: $DANGER;
    background: rgba(251, 113, 133, 0.14);
    border: 1px solid rgba(251, 113, 133, 0.45);
    border-radius: 8px;
    padding: 5px 12px;
}
QFrame#led {
    background: #5A6274;
    border: none;
    border-radius: 5px;
}
QFrame#led[running="true"] {
    background: $SUCCESS;
}
QToolTip {
    background: #131826;
    color: $TEXT;
    border: 1px solid $BORDER_LIGHT;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}
GlassCard {
    background: $CARD_BG;
    border: 1px solid $BORDER;
    border-radius: 16px;
}
GlassCard[radius="30"] {
    border-radius: 30px;
    background: rgba(10, 14, 20, 0.90);
    border: 1px solid $BORDER_LIGHT;
}
GlassCard[radius="27"] {
    border-radius: 27px;
    background: rgba(10, 14, 20, 0.90);
    border: 1px solid $BORDER_LIGHT;
}
GlassCard[radius="20"] {
    border-radius: 20px;
}
GlassCard[radius="14"] {
    border-radius: 14px;
}
GlassCard[radius="12"] {
    border-radius: 12px;
}
GlassCard[radius="14"]:hover {
    background: $CARD_BG_HOVER;
    border-color: $BORDER_LIGHT;
}
GlassCard[radius="12"]:hover {
    background: $CARD_BG_HOVER;
    border-color: $BORDER_LIGHT;
}
GlassCard[radius="30"]:hover {
    background: rgba(13, 18, 26, 0.94);
    border-color: rgba(255, 255, 255, 0.24);
}
GlassCard[radius="27"]:hover {
    background: rgba(13, 18, 26, 0.94);
    border-color: rgba(255, 255, 255, 0.24);
}
#rootCard {
    background: $BG;
    border: 1px solid $BORDER;
    border-radius: 20px;
}
#confirmBanner {
    background: rgba(251, 113, 133, 0.12);
    border: 1px solid rgba(251, 113, 133, 0.38);
    border-radius: 12px;
}
#graceOverlay {
    background: rgba(10, 14, 20, 0.96);
    border: 1px solid $BORDER;
    border-radius: 20px;
}
QPushButton {
    background: transparent;
    border: none;
    border-radius: 8px;
    color: $TEXT;
    font-size: 13px;
}
QPushButton:hover {
    background: rgba(255, 255, 255, 0.06);
}
QPushButton:pressed {
    background: rgba(255, 255, 255, 0.10);
}
QPushButton:disabled {
    color: rgba(255, 255, 255, 0.35);
}
QPushButton#headerBtn {
    border-radius: 8px;
    color: $TEXT_LABEL;
    font-size: 15px;
}
QPushButton#headerBtn:hover {
    background: rgba(255, 255, 255, 0.10);
    color: #FFFFFF;
}
QPushButton#headerBtn:pressed {
    background: rgba(255, 255, 255, 0.16);
}
QPushButton#headerBtnClose {
    border-radius: 8px;
    color: $TEXT_LABEL;
    font-size: 14px;
}
QPushButton#headerBtnClose:hover {
    background: rgba(251, 113, 133, 0.18);
    color: $DANGER;
}
QPushButton#headerBtnClose:pressed {
    background: rgba(251, 113, 133, 0.30);
    color: #FFE4E8;
}
QPushButton#primaryBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 $ACCENT, stop:1 $ACCENT_2);
    border: none;
    border-radius: 14px;
    color: #FFFFFF;
    font-size: 15px;
    font-weight: bold;
    padding: 0 30px;
}
QPushButton#primaryBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8C7DFF, stop:1 #5CCBFA);
}
QPushButton#primaryBtn:pressed {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6A5AE8, stop:1 #2BAEE6);
}
QPushButton#primaryBtn[danger="true"] {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 $DANGER, stop:1 $DANGER_DEEP);
}
QPushButton#primaryBtn[danger="true"]:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FF8A9B, stop:1 #F65574);
}
QPushButton#primaryBtn[danger="true"]:pressed {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #E14A66, stop:1 #D22F4E);
}
QPushButton#primaryBtn:disabled {
    background: rgba(124, 108, 255, 0.35);
    color: rgba(255, 255, 255, 0.55);
}
QPushButton#extendBtn {
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid $BORDER_SOFT;
    border-radius: 14px;
    color: #C7CCD8;
    font-size: 14px;
    padding: 0 22px;
}
QPushButton#extendBtn:hover {
    background: rgba(255, 255, 255, 0.11);
    border-color: $BORDER_LIGHT;
    color: #FFFFFF;
}
QPushButton#extendBtn:pressed {
    background: rgba(255, 255, 255, 0.15);
}
QPushButton#extendBtn:disabled {
    color: rgba(255, 255, 255, 0.40);
    background: rgba(255, 255, 255, 0.03);
    border-color: rgba(255, 255, 255, 0.06);
}
QPushButton#bannerQuitBtn {
    background: rgba(251, 113, 133, 0.16);
    border: 1px solid rgba(251, 113, 133, 0.55);
    border-radius: 10px;
    color: #FDA4AF;
    font-size: 13px;
    padding: 7px 16px;
}
QPushButton#bannerQuitBtn:hover {
    background: rgba(251, 113, 133, 0.26);
    color: #FFE4E8;
}
QPushButton#bannerHideBtn {
    background: rgba(255, 255, 255, 0.07);
    border: 1px solid $BORDER_SOFT;
    border-radius: 10px;
    color: #C7CCD8;
    font-size: 13px;
    padding: 7px 16px;
}
QPushButton#bannerHideBtn:hover {
    background: rgba(255, 255, 255, 0.12);
    border-color: $BORDER_LIGHT;
    color: #FFFFFF;
}
QPushButton#deepToggle {
    color: $TEXT_DIM;
    font-size: 13px;
    padding: 6px 2px;
    text-align: left;
}
QPushButton#deepToggle:hover {
    color: #C7CCD8;
    background: transparent;
}
QPushButton#deepToggle:pressed {
    color: #9BA3B5;
    background: transparent;
}
QPushButton#miniAction {
    background: rgba(255, 255, 255, 0.07);
    border: 1px solid $BORDER;
    border-radius: 15px;
    color: #C7CCD8;
    font-size: 14px;
}
QPushButton#miniAction:hover {
    background: rgba(255, 255, 255, 0.15);
    border-color: rgba(255, 255, 255, 0.26);
    color: #FFFFFF;
}
QPushButton#miniAction:pressed {
    background: rgba(124, 108, 255, 0.35);
    border-color: $ACCENT;
}
Chip {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid $BORDER_SOFT;
    border-radius: 10px;
    color: #A7B0C0;
    font-size: 13px;
    padding: 0 14px;
}
Chip:hover {
    background: rgba(255, 255, 255, 0.10);
    border-color: $BORDER_LIGHT;
    color: $TEXT_DIGITS;
}
Chip:pressed {
    background: rgba(255, 255, 255, 0.14);
}
Chip[active="true"] {
    background: rgba(124, 108, 255, 0.24);
    border: 1px solid $ACCENT;
    color: #DCD7FF;
}
Chip[active="true"]:hover {
    background: rgba(124, 108, 255, 0.32);
    border-color: #9C90FF;
    color: #EEE9FF;
}
Chip:disabled {
    color: rgba(255, 255, 255, 0.35);
    background: rgba(255, 255, 255, 0.03);
    border-color: rgba(255, 255, 255, 0.06);
}
Switch {
    background: transparent;
    border: none;
}
QSpinBox, QTimeEdit {
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid $BORDER_SOFT;
    border-radius: 12px;
    padding: 6px 12px;
    color: $TEXT_DIGITS;
    font-size: 15px;
    selection-background-color: $ACCENT;
    selection-color: #FFFFFF;
}
QSpinBox:focus, QTimeEdit:focus {
    border: 1px solid $ACCENT;
    background: rgba(124, 108, 255, 0.12);
}
QSpinBox:disabled, QTimeEdit:disabled {
    color: rgba(255, 255, 255, 0.35);
    background: rgba(255, 255, 255, 0.03);
    border-color: rgba(255, 255, 255, 0.06);
}
QSpinBox::up-button, QSpinBox::down-button,
QTimeEdit::up-button, QTimeEdit::down-button {
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 0px;
    height: 0px;
    border: none;
    background: transparent;
}
QScrollArea {
    border: none;
    background: transparent;
}
QScrollBar:vertical {
    background: rgba(255, 255, 255, 0.05);
    width: 10px;
    margin: 3px;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background: rgba(255, 255, 255, 0.18);
    min-height: 32px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: rgba(255, 255, 255, 0.30);
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
    background: transparent;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: transparent;
}
QScrollBar:horizontal {
    height: 0px;
    background: transparent;
}
QScrollBar::handle:horizontal {
    background: transparent;
    height: 0px;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
    background: transparent;
}
QSizeGrip {
    background: transparent;
}
"""
)

_TOKENS = {
    name: value
    for name, value in globals().items()
    if isinstance(value, str) and not name.startswith("__")
}


def build_stylesheet() -> str:
    return _TEMPLATE.substitute(**_TOKENS)


def apply_stylesheet() -> None:
    app = QApplication.instance()
    if not isinstance(app, QApplication) or app.styleSheet():
        return
    app.setStyleSheet(build_stylesheet())
