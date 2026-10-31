"""Configuration loading with sane defaults.

The village must run with zero setup, so every key here has a default and a
missing config file simply means "use the defaults".
"""
from __future__ import annotations

import copy
import os
import tomllib
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from .runtime_paths import data_root

ROOT = data_root(Path(__file__).resolve().parent.parent)
CONFIG_PATH = ROOT / "config.toml"
EXAMPLE_PATH = ROOT / "config.example.toml"
DATA_DIR = ROOT / "data"
SAVE_DIR = ROOT / "saves"
LOCALE_DIR = Path(__file__).resolve().parent / "locales"
FONT_DIR = Path(__file__).resolve().parent / "assets" / "fonts"

DEFAULTS: dict[str, Any] = {
    "general": {
        "language": "en",
        "window_width": 1440,
        "window_height": 810,
        "zoom": 3,
        "seed": 1234,
        "save_slot": 1,
        "photo_mode": False,
        "seasonal_palette": True,
    },
    "reality": {
        "time_mode": "live",
        "latitude": "auto",
        "longitude": "auto",
        "weather_enabled": True,
        "weather_refresh_s": 900,
        "offline_weather": "last_known",
        "night_on_launch": "live",
    },
    "llm": {
        "provider": "auto",
        "model": "llama3.2",
        "base_url": "",
        "api_key_env": "",
        "temperature": 0.9,
        "max_tokens": 300,
        "cache_entries": 256,
        "timeout_s": 60,
        "ambient_dialogue": True,
        "parallel_ambient": True,
        "ambient_model": "",
        "ambient_reasoning_effort": "low",
        "self_directed": True,
        "self_interval_s": 180,
        "self_failure_backoff_max_s": 1800,
        "cli_model": "",
        "cli_timeout_s": 120,
        "claude_command": "claude",
        "codex_command": "codex",
        "prefer_subscription": False,
    },
    "voice": {
        "enabled": True,
        "speak_ambient": True,
        "volume": 0.85,
        "rate_scale": 1.0,
    },
    "social": {
        "ambient_budget_s": 45,
        "failure_backoff_s": 120,
        "failure_backoff_max_s": 900,
        "work_chatter": False,
        "group_chats": True,
        "group_chance": 0.35,
        "threads": True,
    },
    "news": {
        "enabled": True,
        "poll_minutes": 40,
        "max_dispatches_per_day": 2,
        "tone": "neutral",
        "mute_after_failures": 5,
        "backoff_base_s": 300,
        "backoff_max_s": 21600,
        "alerts_enabled": True,
        "alert_poll_minutes": 20,
        "weights": {
            "world": 0.40,
            "odd": 0.15,
            "science": 0.15,
            "tech": 0.10,
            "sport": 0.10,
            "local": 0.10,
        },
    },
    "visitors": {
        "enabled": True,
        "arrivals_per_day": 3,
        "stay_minutes": 45,
    },
}

PROVIDERS = ("auto", "ollama", "openai", "anthropic", "openai_compatible",
             "claude_cli", "codex_cli", "subscription", "mock", "none")


def _deep_merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


class Config:
    def __init__(self, path: Path = CONFIG_PATH):
        load_dotenv(ROOT / ".env")
        self.path = path
        raw: dict = {}
        if path.exists():
            with open(path, "rb") as fh:
                raw = tomllib.load(fh)
        self._data = _deep_merge(DEFAULTS, raw)
        from .setup import PROVIDERS, read_setup, valid_model_id, valid_gateway
        setup = read_setup(path)
        provider = setup.get("provider")
        if provider in PROVIDERS:
            self.set("llm.provider", provider)
        gateway = setup.get("gateway")
        if provider == "openai_compatible" and isinstance(gateway, dict):
            url, model, key_env = (gateway.get(k) for k in ("url", "model", "key_env"))
            if all(isinstance(v, str) for v in (url, model, key_env)) and valid_gateway(url, model, key_env):
                self.set("llm.base_url", url)
                self.set("llm.model", model)
                self.set("llm.api_key_env", key_env)
        ambient_model = setup.get("ambient_model")
        if isinstance(ambient_model, str) and valid_model_id(ambient_model):
            self.set("llm.ambient_model", ambient_model)
        for d in (DATA_DIR, SAVE_DIR):
            d.mkdir(parents=True, exist_ok=True)

    # -- generic access -------------------------------------------------
    def get(self, dotted: str, default: Any = None) -> Any:
        node: Any = self._data
        for part in dotted.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def set(self, dotted: str, value: Any) -> None:
        parts = dotted.split(".")
        node = self._data
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value

    def section(self, name: str) -> dict:
        return self._data.get(name, {})

    @property
    def language(self) -> str:
        lang = str(self.get("general.language", "en")).lower()
        return lang if lang in ("en", "de") else "en"

    @property
    def seed(self) -> int:
        return int(self.get("general.seed", 1234))

    def write_example_if_missing(self) -> None:
        if not CONFIG_PATH.exists() and EXAMPLE_PATH.exists():
            # Deliberately not auto-copying: defaults already work, and a
            # half-edited config is more confusing than none.
            pass


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)
