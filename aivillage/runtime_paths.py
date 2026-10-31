"""Writable application data locations for packaged builds."""
from __future__ import annotations

import os
import platform
import sys
from pathlib import Path


def data_root(source_root: Path) -> Path:
    """Keep source runs unchanged; packaged apps write outside the bundle."""
    if not getattr(sys, "frozen", False):
        return source_root
    system = platform.system()
    if system == "Windows":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    elif system == "Darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        configured = os.environ.get("XDG_DATA_HOME", "")
        base = Path(configured) if configured and Path(configured).is_absolute() else Path.home() / ".local" / "share"
    return base / "aivillage"
