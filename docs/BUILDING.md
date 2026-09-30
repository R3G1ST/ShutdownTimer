# Сборка ShutdownTimer

Приложение: **ShutdownTimer** — «Таймер автоотключения ПК».
Версия: **1.0.1**. Точка входа: `main.py` (корень репозитория). Иконка: `resources/icon.ico`.

## Требования

- Windows x64
- Python 3.12 (64-бит)
- [Inno Setup 6](https://jrsoftware.org/isinfo.php) — только для инсталлятора
- Репозиторий клонирован локально

## Локальная сборка (Windows)

### 1. Виртуальное окружение и зависимости

```powershell
cd <корень репозитория ShutdownTimer>

python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
```

`requirements.txt` — рантайм (PyQt6, winotify), `requirements-dev.txt` — инструменты сборки и проверки (pyinstaller, ruff, pytest, pytest-qt, pillow).

### 2. Проверки перед сборкой (опционально, но рекомендуется)

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest -q
```

Если тестов ещё нет, pytest завершится с кодом 5 («no tests collected») — это нормально.

### 3. EXE (one-file)

```powershell
.\scripts\build_exe.ps1
```

Скрипт:

- запускается из корня репозитория (сам определяет корень по своему расположению);
- чистит каталоги `build\` и `dist\`;
- активирует `.venv\Scripts\python.exe` (если окружения нет — использует глобальный `python`);
- выполняет `python -m PyInstaller build.spec --noconfirm --clean`;
- проверяет, что `dist\ShutdownTimer.exe` создан, и выводит его размер.

Ручной эквивалент:

```powershell
.\.venv\Scripts\python.exe -m PyInstaller build.spec --noconfirm --clean
```

### 4. Инсталлятор (Inno Setup 6)

```powershell
.\scripts\build_installer.ps1
```

Скрипт сначала выполняет полную сборку EXE (шаг 3), затем запускает ISCC для `installer\setup.iss`. ISCC ищется по очереди в:

1. `%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe`
2. `C:\Program Files (x86)\Inno Setup 6\ISCC.exe`
3. `C:\Program Files\Inno Setup 6\ISCC.exe`

Ручной эквивалент:

```powershell
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\setup.iss
```

## Структура артефактов

```
ShutdownTimer/
├── main.py                      # точка входа
├── build.spec                   # спецификация PyInstaller (one-file, windowed)
├── resources/icon.ico           # иконка приложения и инсталлятора
├── build/                       # временные файлы PyInstaller (можно удалять)
├── dist/
│   └── ShutdownTimer.exe        # portable-приложение, one-file
├── installer/
│   ├── setup.iss                # скрипт Inno Setup 6
│   └── Output/
│       └── ShutdownTimer-Setup-1.0.1.exe   # инсталлятор
├── scripts/
│   ├── build_exe.ps1            # сборка EXE
│   └── build_installer.ps1      # сборка EXE + инсталлятора
└── .github/workflows/release.yml # CI: сборка и публикация релиза
```

| Артефакт | Путь | Описание |
|----------|------|----------|
| Portable EXE | `dist\ShutdownTimer.exe` | One-file, без установки, без консоли |
| Инсталлятор | `installer\Output\ShutdownTimer-Setup-1.0.1.exe` | Inno Setup, LZMA2/ultra, установка в профиль пользователя (без прав администратора) |

Приложение работает и portable (просто запустите `dist\ShutdownTimer.exe`). Реестр-протокол `shutdowntimer://` приложение регистрирует само; инсталлятор дополнительно регистрирует протокол в HKCU и снимает его при деинсталляции.

## Сборка инсталлятора вручную (без скриптов)

1. Соберите EXE: `.\scripts\build_exe.ps1` (обязательно — инсталлятор берёт файл из `dist\ShutdownTimer.exe`).
2. Запустите ISCC на `installer\setup.iss`.

Убедитесь, что `dist\ShutdownTimer.exe` существует до запуска ISCC, иначе компиляция установщика завершится ошибкой.

## CI/CD: релиз через GitHub Actions

Workflow: `.github/workflows/release.yml` (`Build and Release`).

Триггеры:

- push тега вида `v*` (например `v1.0.1`);
- ручной запуск (`workflow_dispatch`) — собирает артефакты без публикации.

Что делает (runner `windows-latest`, shell `pwsh`):

1. Checkout + Python 3.12.
2. `pip install -r requirements.txt -r requirements-dev.txt`.
3. `ruff check .` — при находках шаг падает.
4. `python -m pytest -q` — падает только при exit code 1 (тесты не прошли) или 2 (ошибка вызова); код 5 («no tests collected») считается успехом.
5. `python -m PyInstaller build.spec --noconfirm --clean`.
6. ISCC (`/Q`) на `installer\setup.iss` — путь к ISCC определяется проверкой `Test-Path` по кандидатам (предустановлен на `windows-latest`).
7. Публикация релиза: `softprops/action-gh-release@v2` c `dist/ShutdownTimer.exe` и `installer/Output/ShutdownTimer-Setup-*.exe`, `generate_release_notes: true`.

### Как выпустить релиз

1. Убедитесь, что версия **1.0.1** указана в `build.spec` (имя EXE), `installer/setup.iss` (`MyAppVersion`) и `package.json`/`__init__.py` проекта (если есть).
2. Создайте и запушьте тег:

```powershell
git tag v1.0.1
git push origin v1.0.1
```

3. Actions выполнит сборку и создаст GitHub Release с двумя артефактами: `ShutdownTimer.exe` и `ShutdownTimer-Setup-1.0.1.exe`.

## Режим безопасной отладки (dry run)

Переменная окружения:

```powershell
$env:SHUTDOWNTIMER_DRY_RUN = "1"
```

- ПК **не выключается** — все команды отключения заменяются на запись в лог.
- Лог пишется в `%APPDATA%\ShutdownTimer\dry_run.log`.

Полезно при разработке и в CI, чтобы проверить таймер без реального завершения сессии. Значение `0` или отсутствие переменной — обычный режим работы.
