"""Persist the village between sessions (small, human-readable JSON)."""
from __future__ import annotations

import json
import time
from pathlib import Path

from .config import SAVE_DIR

SAVE_PATH = SAVE_DIR / "village.json"
VERSION = 1


def save_village(data: dict, path: Path = SAVE_PATH) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = dict(data)
        payload["version"] = VERSION
        payload["saved_at"] = time.time()
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=1, ensure_ascii=False),
                       encoding="utf-8")
        tmp.replace(path)
        return True
    except Exception:
        return False


def load_village(path: Path = SAVE_PATH) -> dict | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("version") != VERSION:
            return None
        return data
    except Exception:
        return None


def delete_save(path: Path = SAVE_PATH) -> None:
    try:
        path.unlink(missing_ok=True)
    except Exception:
        pass
