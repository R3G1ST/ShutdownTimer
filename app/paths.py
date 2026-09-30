from __future__ import annotations

import os
import sys


def is_frozen() -> bool:
    return hasattr(sys, "_MEIPASS")


def resource_path(rel: str) -> str:
    if is_frozen():
        return os.path.join(sys._MEIPASS, rel)
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, rel)


def exe_path() -> str:
    if is_frozen():
        return sys.executable
    return os.path.abspath(sys.argv[0])
