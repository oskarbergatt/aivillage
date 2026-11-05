from __future__ import annotations

import json

from aivillage.save import load_village


def test_version_one_save_is_migrated_before_loading(tmp_path):
    path = tmp_path / "village.json"
    path.write_text(json.dumps({
        "version": 1,
        "seed": 17,
        "day_number": 4,
        "chronicle": [],
        "agents": {},
    }), encoding="utf-8")

    loaded = load_village(path)

    assert loaded is not None
    assert loaded["version"] == 2
    assert loaded["story_arc"] == {}
    assert loaded["diaries"] == {}


def test_future_save_version_is_rejected(tmp_path):
    path = tmp_path / "village.json"
    path.write_text(json.dumps({"version": 999, "seed": 17}), encoding="utf-8")

    assert load_village(path) is None
