"""Persist non-secret first-run provider choices separately from user config."""
from __future__ import annotations

import json
import os
import re
import tempfile
from urllib.parse import urlsplit
from pathlib import Path

PROVIDERS = ("auto", "ollama", "subscription", "claude_cli", "codex_cli",
             "openai", "anthropic", "openai_compatible", "mock", "none")

_WEBSITES = {
    "auto": "https://ollama.com/download",
    "ollama": "https://ollama.com/download",
    "subscription": "https://developers.openai.com/codex/cli/",
    "codex_cli": "https://developers.openai.com/codex/cli/",
    "claude_cli": "https://code.claude.com/docs/en/setup",
    "openai": "https://platform.openai.com/api-keys",
    "anthropic": "https://console.anthropic.com/settings/keys",
    "openai_compatible": "https://lmstudio.ai/",
}


def provider_website(provider: str) -> str:
    return _WEBSITES.get(provider, "")


def setup_path(config_path: Path) -> Path:
    return config_path.with_name("aivillage-setup.json")


def read_setup(config_path: Path) -> dict:
    path = setup_path(config_path)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save_provider(config_path: Path, provider: str) -> None:
    if provider not in PROVIDERS:
        raise ValueError("unknown provider")
    _save_setting(config_path, "provider", provider)


def valid_model_id(model: str) -> bool:
    return not model or bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,119}", model))


def save_ambient_model(config_path: Path, model: str) -> None:
    if not valid_model_id(model):
        raise ValueError("invalid model ID")
    _save_setting(config_path, "ambient_model", model)


def valid_gateway(url: str, model: str, key_env: str) -> bool:
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        return False
    return bool(len(url) <= 500 and not any(c.isspace() for c in url)
                and parts.scheme in ("http", "https") and parts.hostname
                and port != 0 and not parts.username and not parts.password
                and not parts.query and not parts.fragment
                and model and valid_model_id(model)
                and (not key_env or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,127}", key_env)))


def save_gateway(config_path: Path, url: str, model: str, key_env: str) -> None:
    if not valid_gateway(url, model, key_env):
        raise ValueError("invalid gateway configuration")
    _save_settings(config_path, {"provider": "openai_compatible",
                                 "gateway": {"url": url.rstrip("/"), "model": model,
                                             "key_env": key_env}})


def _save_setting(config_path: Path, key: str, value: str) -> None:
    _save_settings(config_path, {key: value})


def _save_settings(config_path: Path, values: dict) -> None:
    path = setup_path(config_path)
    if path.exists():
        # Refuse to overwrite a corrupt or unfamiliar document silently.
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("invalid setup file")
    else:
        data = {}
    data.update(values)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".aivillage-setup-", suffix=".tmp", dir=path.parent)
    tmp = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)
