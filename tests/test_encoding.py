from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIPPED_DIRS = {
    ".venv",
    "venv",
    ".git",
    ".ruff_cache",
    ".pytest_cache",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
}
REPLACEMENT_CHAR = chr(0xFFFD)


def _project_files(pattern: str) -> list[Path]:
    return [
        path
        for path in ROOT.rglob(pattern)
        if not SKIPPED_DIRS.intersection(path.parts)
    ]


def test_all_python_sources_are_utf8() -> None:
    files = _project_files("*.py")
    assert files, "не найдено ни одного .py файла"
    for path in files:
        text = path.read_text(encoding="utf-8")
        assert REPLACEMENT_CHAR not in text, (
            f"кракозябры в {path.relative_to(ROOT)}"
        )


def test_russian_ui_strings_are_readable() -> None:
    main_window = (ROOT / "app" / "ui" / "main_window.py").read_text(encoding="utf-8")
    components = (ROOT / "app" / "ui" / "components.py").read_text(encoding="utf-8")
    tray = (ROOT / "app" / "tray.py").read_text(encoding="utf-8")

    assert "Таймер автоотключения ПК" in main_window
    assert "Обратный отсчёт" in main_window
    assert "Гибернация" in main_window
    assert "Остановлен" in components
    assert "Открыть ShutdownTimer" in tray


def test_readme_is_utf8() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert REPLACEMENT_CHAR not in text
    assert "Скриншоты" in text
