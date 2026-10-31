"""Persist the village between sessions (small, human-readable JSON).

Five independent slots plus a legacy ``village.json`` that is treated as slot 1.
Writes are atomic (temp file + replace) so a crash cannot leave half a save.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from .config import SAVE_DIR

SAVE_PATH = SAVE_DIR / "village.json"
SLOTS = 5
VERSION = 1


def slot_path(slot: int = 1) -> Path:
    slot = max(1, min(SLOTS, int(slot)))
    if slot == 1:
        return SAVE_DIR / "village-1.json"
    return SAVE_DIR / f"village-{slot}.json"


def legacy_path() -> Path:
    return SAVE_PATH


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


def load_slot(slot: int = 1) -> tuple[dict | None, Path]:
    """Load a slot, falling back to the pre-v0.2 legacy save for slot 1."""
    path = slot_path(slot)
    data = load_village(path)
    if data is None and slot == 1:
        path = legacy_path()
        data = load_village(path)
    return data, path


def list_slots() -> list[dict]:
    out = []
    for slot in range(1, SLOTS + 1):
        path = slot_path(slot)
        exists = path.exists()
        if slot == 1 and not exists and legacy_path().exists():
            path = legacy_path()
            exists = True
        saved_at = 0.0
        day = 1
        if exists:
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                saved_at = float(raw.get("saved_at", 0) or 0)
                day = int(raw.get("day_number", 1) or 1)
            except Exception:
                saved_at = 0.0
        out.append({"slot": slot, "path": path, "exists": exists,
                    "saved_at": saved_at, "day": day})
    return out
