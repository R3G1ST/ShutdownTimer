"""Скриншоты для README (docs/screenshots/*.png).

Запуск:  python scripts/capture_screenshots.py
Рендер идёт на реальной windows-платформе (offscreen не имеет базы шрифтов —
глифы рисуются квадратами) и только в DRY-RUN (системные действия не выполняются).
Настройки берутся из временного файла — пользовательские настройки не трогаются.
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault("SHUTDOWNTIMER_DRY_RUN", "1")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PyQt6.QtCore import QPropertyAnimation
from PyQt6.QtGui import QColor, QIcon, QImage, QPainter
from PyQt6.QtWidgets import QApplication

from app.config import SettingsManager
from app.paths import resource_path
from app.timers.engine import TimerEngine
from app.tray import TrayController

from app.ui.main_window import CHROME_HEIGHT, DEEP_CLOSED_TEXT, MainWindow  # isort: skip
from app.ui.mini_widget import MiniWidget

OUT_DIR = ROOT / "docs" / "screenshots"
BG = "#05060f"
MIN_BYTES = 2048


def pump(app: QApplication, rounds: int = 6) -> None:
    for _ in range(rounds):
        app.processEvents()
        time.sleep(0.03)


def save_shot(pixmap, path: Path) -> None:
    image = QImage(pixmap.size(), QImage.Format.Format_RGB32)
    image.fill(QColor(BG))
    painter = QPainter(image)
    painter.drawPixmap(0, 0, pixmap)
    painter.end()
    if not image.save(str(path), "PNG"):
        raise RuntimeError(f"не удалось сохранить {path}")


def new_settings(tag: str) -> SettingsManager:
    tmp = Path(tempfile.gettempdir()) / f"st_shot_{tag}.json"
    if tmp.exists():
        tmp.unlink()
    settings = SettingsManager(path=str(tmp))
    settings.set("countdown_minutes", 30)
    settings.set("grace_seconds", 10)
    settings.set("mini_widget_enabled", True)
    settings.save()
    return settings


def presentable(window: MainWindow) -> None:
    """Вид окна как при обычном (не DRY-RUN) запуске + высота вровень с содержимым.

    В DRY-RUN окно само раскрывает глубокие настройки ради бейджа — для скриншота
    README это лишний шум. Таймер при этом не запускается, системные действия
    не выполняются.
    """
    # анимация высоты от первого show() могла ещё идти — глушим, иначе
    # она вернёт окно к «grown» высоте уже после resize
    for animation in window.findChildren(QPropertyAnimation):
        animation.stop()
    window._deep_open = False
    window._deep_toggle.setText(DEEP_CLOSED_TEXT)
    # одного maximumHeight(0) мало: дочерние виджеты deep_box всё равно
    # перерисовываются — прячем целиком (layout сам уберёт из потока)
    window._deep_box.setMaximumHeight(0)
    window._deep_box.hide()
    if window._content_layout is not None:
        window._content_layout.activate()
    hint = window._content.sizeHint().height() + CHROME_HEIGHT + 28
    window.resize(window.width(), max(660, hint))
    window.update()


def shot_main_window(app: QApplication, _icon: QIcon) -> Path:
    settings = new_settings("window")
    engine = TimerEngine(settings)
    window = MainWindow(settings, engine)
    window.show()
    pump(app)
    presentable(window)
    pump(app)
    path = OUT_DIR / "main_window.png"
    save_shot(window.grab(), path)
    window.hide()
    engine.close()
    return path


def shot_mini_widget(app: QApplication, _icon: QIcon) -> Path:
    widget = MiniWidget()
    widget.set_time(4 * 60 + 14, running=True)
    widget.show()
    pump(app)
    path = OUT_DIR / "mini_widget.png"
    save_shot(widget.grab(), path)
    widget.hide()
    return path


def shot_tray_menu(app: QApplication, icon: QIcon) -> Path:
    tray = TrayController(icon)
    tray.set_running(True, "Осталось 04:14")
    menu = tray._menu
    menu.show()
    pump(app, 8)
    path = OUT_DIR / "tray_menu.png"
    save_shot(menu.grab(), path)
    menu.hide()
    tray.hide()
    return path


def shot_completed_overlay(app: QApplication, icon: QIcon) -> Path:
    settings = new_settings("grace")
    engine = TimerEngine(settings)
    window = MainWindow(settings, engine)
    window.show()
    pump(app)
    presentable(window)
    pump(app)
    window._on_engine_completed()
    pump(app, 8)
    window._grace_timer.stop()
    path = OUT_DIR / "completed_overlay.png"
    save_shot(window.grab(), path)
    window._hide_grace_overlay()
    window.hide()
    engine.close()
    return path


def verify(path: Path) -> tuple[bool, str]:
    from PIL import Image

    if not path.exists():
        return False, "файл не создан"
    size = path.stat().st_size
    if size < MIN_BYTES:
        return False, f"слишком маленький ({size} Б)"
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            width, height = image.size
            if width < 200 or height < 50:
                return False, f"подозрительный размер {width}x{height}"
            sample = image.convert("RGB").resize((32, 32))
            colors = len(sample.getcolors(1024) or [])
            if colors < 8:
                return False, f"картинка почти однотонная ({colors} цветов)"
    except Exception as error:  # noqa: BLE001
        return False, f"не читается: {error}"
    return True, f"{width}x{height}, {size} Б, {colors} цветов"


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication(sys.argv)
    icon = QIcon(resource_path("resources/icon.ico"))

    produced = [
        shot_main_window(app, icon),
        shot_mini_widget(app, icon),
        shot_tray_menu(app, icon),
        shot_completed_overlay(app, icon),
    ]

    failed = 0
    for path in produced:
        ok, detail = verify(path)
        print(f"[{'OK  ' if ok else 'FAIL'}] {path.relative_to(ROOT)}: {detail}")
        failed += 0 if ok else 1
    print(f"failed={failed}/{len(produced)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
