"""First-run and in-app provider setup."""
import json

import pytest

from aivillage.config import Config
from aivillage.setup import read_setup, save_provider, setup_path
from aivillage.setup_download import ModelDownload
from run import build_parser


def test_provider_choice_is_persisted_without_secrets(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text('[llm]\nprovider = "ollama"\n', encoding="utf-8")
    save_provider(config_path, "codex_cli")
    assert read_setup(config_path) == {"provider": "codex_cli"}
    assert Config(config_path).get("llm.provider") == "codex_cli"
    assert "key" not in setup_path(config_path).read_text(encoding="utf-8")
    save_provider(config_path, "auto")
    assert Config(config_path).get("llm.provider") == "auto"


def test_corrupt_setup_is_not_overwritten(tmp_path):
    config_path = tmp_path / "config.toml"
    path = setup_path(config_path)
    path.write_text("not json", encoding="utf-8")
    assert read_setup(config_path) == {}
    with pytest.raises(ValueError):
        save_provider(config_path, "openai")
    assert path.read_text(encoding="utf-8") == "not json"


def test_setup_preserves_unrelated_fields_and_rejects_bad_provider(tmp_path):
    config_path = tmp_path / "config.toml"
    path = setup_path(config_path)
    path.write_text(json.dumps({"future_setting": 7}), encoding="utf-8")
    save_provider(config_path, "ollama")
    assert read_setup(config_path) == {"provider": "ollama", "future_setting": 7}
    with pytest.raises(ValueError):
        save_provider(config_path, "not-a-provider")


def test_setup_panel_is_accessible_and_saves_for_next_start(app):
    app._action("settings")
    app._draw(0.016)
    assert "provider_open" in app.ui.hits
    app._action("provider_open")
    app._draw(0.016)
    assert "provider_select:subscription" in app.ui.hits
    app._action("provider_select:subscription")
    app._action("provider_save")
    assert not app.show_provider_setup
    assert read_setup(app.config.path)["provider"] == "subscription"
    assert app.llm.provider == "mock"  # current session remains untouched
    assert Config(app.config.path).get("llm.provider") == "subscription"


def test_setup_card_offers_provider_chooser(app):
    app.llm.available = False
    app._draw(0.016)
    assert "provider_open" in app.ui.hits
    app._action("provider_open")
    app._draw(0.016)
    assert "provider_save" in app.ui.hits


def test_subscription_cli_flags_are_accepted():
    assert build_parser().parse_args(["--provider", "codex_cli"]).provider == "codex_cli"


def test_model_download_is_local_and_explicit(monkeypatch):
    download = ModelDownload()
    assert not download.start("https://example.com")
    assert download.status == "local_only"
    requests_seen = []

    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def raise_for_status(self):
            pass
        def iter_lines(self):
            return iter([b'{"completed":5,"total":10}', b'{"status":"success"}'])

    def post(url, **kwargs):
        requests_seen.append((url, kwargs))
        return Response()

    monkeypatch.setattr("aivillage.setup_download.requests.post", post)
    download.running = True
    download._download("http://localhost:11434")
    download.poll()
    assert download.status == "done" and not download.running
    assert requests_seen[0][0] == "http://localhost:11434/api/pull"
    assert requests_seen[0][1]["json"]["model"] == "llama3.2"


def test_model_download_reports_incomplete_stream(monkeypatch):
    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def raise_for_status(self):
            pass
        def iter_lines(self):
            return iter([b'{"status":"pulling"}'])
    monkeypatch.setattr("aivillage.setup_download.requests.post", lambda *a, **k: Response())
    download = ModelDownload()
    download.running = True
    download._download("http://localhost:11434")
    download.poll()
    assert download.status == "error" and not download.running


def test_official_website_only_opens_on_click(app, monkeypatch):
    opened = []
    monkeypatch.setattr("webbrowser.open", lambda url: opened.append(url) or True)
    app._action("provider_open")
    app._action("provider_select:ollama")
    assert not opened
    app._action("provider_website")
    assert opened == ["https://ollama.com/download"]


def test_ollama_without_model_is_not_reported_ready(config, monkeypatch):
    from aivillage.llm.client import LLMClient
    class Response:
        status_code = 200
        def json(self):
            return {"models": []}
    monkeypatch.setattr("aivillage.llm.client.requests.get", lambda *a, **k: Response())
    config.set("llm.provider", "ollama")
    client = LLMClient(config)
    try:
        assert not client.available
        assert "no model" in client.status
    finally:
        client.stop()


def test_conversation_model_can_be_changed_in_app_without_changing_provider(app):
    import pygame
    save_provider(app.config.path, "codex_cli")
    app._action("settings")
    app._draw(0.016)
    assert "ambient_model_open" in app.ui.hits
    app._action("ambient_model_open")
    for char in "llama3.2:1b":
        app._key(pygame.event.Event(pygame.KEYDOWN, key=0, unicode=char, mod=0))
    app._action("ambient_model_save")
    assert not app.show_ambient_model
    assert app.config.get("llm.ambient_model") == "llama3.2:1b"
    assert app.llm.provider == "mock"
    assert read_setup(app.config.path)["provider"] == "codex_cli"
    assert Config(app.config.path).get("llm.ambient_model") == "llama3.2:1b"


def test_invalid_conversation_model_is_not_saved(app):
    app._action("ambient_model_open")
    app.ambient_model_input = "bad model;!"
    app._action("ambient_model_save")
    assert app.show_ambient_model and app.ambient_model_error
    assert not setup_path(app.config.path).exists()
