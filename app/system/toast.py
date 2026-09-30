from __future__ import annotations

from winotify import Notification

from app.paths import resource_path


def notify(
    title: str,
    message: str,
    buttons: list[tuple[str, str]] | None = None,
    icon_path: str | None = None,
) -> bool:
    try:
        icon = icon_path or resource_path("resources/icon.ico")
        toast = Notification(
            app_id="ShutdownTimer",
            title=title,
            msg=message,
            icon=icon,
            duration="short",
        )
        for label, launch in (buttons or [])[:5]:
            toast.add_actions(label, launch)
        toast.show()
        return True
    except (AttributeError, KeyError, OSError, TypeError, ValueError):
        return False
