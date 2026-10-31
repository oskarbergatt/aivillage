"""Subscription CLI connectors: command shape, parsing and resolution."""
from __future__ import annotations

import json
from pathlib import Path

from aivillage.llm.client import (Job, LLMClient, claude_command,
                                  codex_command, parse_claude_output,
                                  parse_codex_output, spawn_command, strip_ansi)


class FakeProc:
    def __init__(self, stdout: str = "", stderr: str = "", code: int = 0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = code


def test_claude_command_keeps_the_prompt_on_stdin():
    cmd = claude_command("claude", "be a villager")
    assert cmd[0] == "claude"
    assert "-p" in cmd
    assert "--append-system-prompt" in cmd
    assert cmd[-2:] == ["--tools", ""]
    assert "be a villager" in cmd


def test_codex_command_uses_an_output_file():
    cmd = codex_command("codex", "out.txt", "gpt-5")
    assert cmd[:2] == ["codex", "exec"]
    assert "--sandbox" in cmd and "read-only" in cmd
    assert cmd[-5:] == ["--model", "gpt-5", "-o", "out.txt", "-"]


def test_parse_claude_output():
    assert parse_claude_output('{"result": "hello"}') == "hello"
    assert parse_claude_output('{"content": [{"text": "a"}, {"text": "b"}]}') == "ab"
    assert parse_claude_output("plain reply") == "plain reply"
    assert "\x1b" not in strip_ansi("\x1b[31mred\x1b[0m")


def test_parse_codex_output():
    events = "\n".join([
        json.dumps({"type": "started"}),
        json.dumps({"msg": {"type": "agent_message", "message": "first"}}),
        json.dumps({"type": "item.completed", "item": {"type": "agent_message",
                                                       "text": "second"}}),
    ])
    assert parse_codex_output(events) == "second"
    assert parse_codex_output("plain final message") == "plain final message"


def test_spawn_command_wraps_cmd_shims(monkeypatch):
    monkeypatch.setattr("aivillage.llm.client.os.name", "nt")
    cmd = spawn_command([r"C:\npm\claude.CMD", "-p"])
    assert cmd[1] == "/c"
    assert cmd[2].endswith("claude.CMD")
    plain = spawn_command([r"C:\tools\claude.exe", "-p"])
    assert plain[0].endswith("claude.exe")


def test_explicit_claude_subscription_resolves(config, monkeypatch):
    config.set("llm.provider", "claude_cli")
    monkeypatch.setattr("aivillage.llm.client.shutil.which",
                        lambda name: r"C:\fake\claude.CMD" if name == "claude" else None)
    client = LLMClient(config)
    try:
        assert client.available
        assert client.provider == "claude_cli"
        assert client.cli_path.endswith("claude.CMD")
        assert "claude" in client.status
    finally:
        client.stop()


def test_subscription_falls_back_to_codex(config, monkeypatch):
    config.set("llm.provider", "subscription")
    monkeypatch.setattr("aivillage.llm.client.shutil.which",
                        lambda name: r"C:\fake\codex.CMD" if name == "codex" else None)
    client = LLMClient(config)
    try:
        assert client.available
        assert client.provider == "codex_cli"
    finally:
        client.stop()


def test_missing_subscription_cli_is_reported(config, monkeypatch):
    config.set("llm.provider", "claude_cli")
    monkeypatch.setattr("aivillage.llm.client.shutil.which", lambda name: None)
    client = LLMClient(config)
    try:
        assert not client.available
        assert client.provider == "none"
        assert "subscription CLI" in client.status
    finally:
        client.stop()


def test_claude_call_reads_the_json_result(config, monkeypatch):
    client = LLMClient(config)
    client.provider = "claude_cli"
    client.cli_path = "claude"
    seen = {}

    def fake(cmd, prompt, timeout):
        seen["cmd"] = cmd
        seen["prompt"] = prompt
        return FakeProc(stdout='{"result": "a villager replies"}')

    monkeypatch.setattr(client, "_run_cli", fake)
    try:
        text = client._call_cli(Job("chat", "system", "user prompt"))
        assert text == "a villager replies"
        assert seen["prompt"] == "user prompt"
    finally:
        client.stop()


def test_codex_call_prefers_the_last_message_file(config, monkeypatch):
    client = LLMClient(config)
    client.provider = "codex_cli"
    client.cli_path = "codex"

    def fake(cmd, prompt, timeout):
        path = Path(cmd[-2])
        path.write_text("codex final", encoding="utf-8")
        return FakeProc(stdout="noise")

    monkeypatch.setattr(client, "_run_cli", fake)
    try:
        text = client._call_cli(Job("chat", "system", "user prompt"))
        assert text == "codex final"
    finally:
        client.stop()


def test_cli_failure_is_loud(config, monkeypatch):
    import pytest
    client = LLMClient(config)
    client.provider = "claude_cli"
    client.cli_path = "claude"
    monkeypatch.setattr(client, "_run_cli",
                        lambda cmd, prompt, timeout: FakeProc(
                            stdout="", stderr="Error: not logged in", code=1))
    try:
        with pytest.raises(RuntimeError):
            client._call_cli(Job("chat", "system", "user prompt"))
    finally:
        client.stop()


def test_cli_failure_with_stdout_is_not_treated_as_dialogue(config, monkeypatch):
    import pytest
    client = LLMClient(config)
    client.provider = "codex_cli"
    client.cli_path = "codex"
    monkeypatch.setattr(client, "_run_cli", lambda *a: FakeProc(
        stdout='{"type":"error","message":"subscription unavailable"}', code=1))
    try:
        with pytest.raises(RuntimeError, match="subscription unavailable"):
            client._call_cli(Job("exchange", "system", "prompt"))
    finally:
        client.stop()


def test_codex_low_effort_is_only_used_for_ambient_dialogue(config, monkeypatch):
    client = LLMClient(config)
    client.provider = "codex_cli"
    client.cli_path = "codex"
    commands = []
    def fake(cmd, prompt, timeout):
        commands.append(cmd)
        Path(cmd[-2]).write_text('{"line":"ok"}', encoding="utf-8")
        return FakeProc()
    monkeypatch.setattr(client, "_run_cli", fake)
    try:
        client._call_cli(Job("exchange", "system", "prompt", model="fast-model"))
        client._call_cli(Job("chat", "system", "prompt"))
        assert 'model_reasoning_effort="low"' in commands[0]
        assert "fast-model" in commands[0]
        assert not any("model_reasoning_effort" in item for item in commands[1])
    finally:
        client.stop()
