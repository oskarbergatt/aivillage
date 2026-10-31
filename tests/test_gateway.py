"""Custom gateway persistence, security validation, and real HTTP integration."""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from aivillage.config import Config
from aivillage.llm.client import Job, LLMClient
from aivillage.setup import read_setup, save_gateway, valid_gateway


@pytest.mark.parametrize("url", ["file:///tmp/x", "https://user:secret@example.com/v1",
                                  "https://example.com/v1?api_key=secret", "https://example.com/#secret",
                                  "https://example.com:bad/v1", "https://example.com/a b"])
def test_rejects_unsafe_gateway_urls(url):
    assert not valid_gateway(url, "model", "MY_KEY")


def test_gateway_setup_saves_no_secret_and_preserves_existing_data(tmp_path):
    path = tmp_path / "config.toml"
    (tmp_path / "aivillage-setup.json").write_text('{"other": 42}', encoding="utf-8")
    save_gateway(path, "https://example.test/v1/", "org/model", "MY_GATEWAY_KEY")
    setup = read_setup(path)
    assert setup["other"] == 42 and setup["provider"] == "openai_compatible"
    assert setup["gateway"] == {"url": "https://example.test/v1", "model": "org/model", "key_env": "MY_GATEWAY_KEY"}
    cfg = Config(path)
    assert cfg.get("llm.base_url") == "https://example.test/v1"
    assert cfg.get("llm.api_key_env") == "MY_GATEWAY_KEY"


def test_gateway_uses_environment_key_and_chat_completions(config, monkeypatch):
    seen = []
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            seen.append((self.path, self.headers.get("Authorization"), body))
            response = json.dumps({"choices": [{"message": {"content": "hello"}}]}).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv("MY_GATEWAY_KEY", "test-secret")
    config.set("llm.provider", "openai_compatible")
    config.set("llm.base_url", f"http://127.0.0.1:{server.server_port}/v1")
    config.set("llm.model", "gateway-model")
    config.set("llm.api_key_env", "MY_GATEWAY_KEY")
    client = LLMClient(config)
    try:
        assert client._call(Job("chat", "system", "user")) == "hello"
        assert seen[0][0:2] == ("/v1/chat/completions", "Bearer test-secret")
        assert seen[0][2]["model"] == "gateway-model"
        assert "test-secret" not in client.label
    finally:
        client.stop()
        server.shutdown()
        server.server_close()
        thread.join(3)


def test_gateway_ui_saves_and_restarts_without_secret(app):
    app._action("provider_open")
    app._action("provider_select:openai_compatible")
    app._draw(0.016)
    assert "gateway_open" in app.ui.hits
    app._action("gateway_open")
    app.gateway_values = ["http://localhost:1234/v1", "my-model", "CUSTOM_KEY"]
    app._draw(0.016)
    assert "gateway_field:0" in app.ui.hits
    app._action("gateway_save")
    assert not app.show_gateway and not app.show_provider_setup
    assert Config(app.config.path).get("llm.model") == "my-model"
    assert app.llm.provider == "mock"


def test_gateway_ui_rejects_credential_in_url(app):
    app._action("gateway_open")
    app.gateway_values = ["https://user:password@example.com/v1", "model", ""]
    app._action("gateway_save")
    assert app.show_gateway and app.gateway_error
    assert not (app.config.path.parent / "aivillage-setup.json").exists()


def test_gateway_does_not_send_default_openai_key(config, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "unrelated-secret")
    config.set("llm.provider", "openai_compatible")
    config.set("llm.base_url", "https://example.test/v1")
    config.set("llm.api_key_env", "")
    client = LLMClient(config)
    try:
        assert client.available and not client.api_key
    finally:
        client.stop()


def test_gateway_refuses_redirects(config, monkeypatch):
    class Response:
        status_code = 302
        def raise_for_status(self):
            pass
    config.set("llm.provider", "openai_compatible")
    config.set("llm.base_url", "https://example.test/v1")
    client = LLMClient(config)
    sent = []
    monkeypatch.setattr("aivillage.llm.client.requests.post",
                        lambda *args, **kwargs: sent.append(kwargs) or Response())
    try:
        with pytest.raises(RuntimeError, match="redirect"):
            client._call(Job("chat", "system", "user"))
        assert sent[0]["allow_redirects"] is False
    finally:
        client.stop()
