"""Guard the module split and ensure extracted modules import independently."""
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def test_python_modules_remain_manageable():
    oversized = []
    for directory in (ROOT / "aivillage", ROOT / "tests"):
        for path in directory.rglob("*.py"):
            count = len(path.read_text(encoding="utf-8").splitlines())
            if count > 320:
                oversized.append((str(path.relative_to(ROOT)), count))
    assert not oversized, oversized


def test_extracted_modules_are_independently_importable():
    modules = (
        "aivillage.app_social", "aivillage.app_persistence",
        "aivillage.agents.agent_routine", "aivillage.assets.sprite_characters",
        "aivillage.llm.client_providers", "aivillage.news.pipeline_dispatch",
        "aivillage.render.ui_dialogs", "aivillage.world.map_landmarks",
    )
    for module in modules:
        result = subprocess.run([sys.executable, "-c", f"import {module}"],
                                cwd=ROOT, capture_output=True, text=True, timeout=20)
        assert result.returncode == 0, (module, result.stderr)
