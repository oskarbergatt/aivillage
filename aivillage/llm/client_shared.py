"""Provider-agnostic LLM client with a background worker.

Nothing here ever blocks the render loop: jobs go in, callbacks come out on the
main thread via poll().
"""
from __future__ import annotations

import hashlib
import json
import os
import queue
import re
import shutil
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import requests

from ..config import DATA_DIR, Config, env

_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def strip_ansi(text: str) -> str:
    return _ANSI.sub("", text or "").strip()


def claude_command(exe: str, system: str, model: str = "",
                   disable_tools: bool = True) -> list[str]:
    """Non-interactive Claude Code invocation (uses the logged-in plan)."""
    cmd = [exe, "-p", "--output-format", "json",
           "--append-system-prompt", system]
    if model:
        cmd += ["--model", model]
    if disable_tools:
        # `--tools` is variadic: leaving it last means it cannot swallow a
        # prompt argument.  The prompt itself is sent over stdin.
        cmd += ["--tools", ""]
    return cmd


def codex_command(exe: str, out_path: str, model: str = "", reasoning_effort: str = "") -> list[str]:
    """Non-interactive Codex invocation (uses the ChatGPT login)."""
    cmd = [exe, "exec", "--skip-git-repo-check", "--ephemeral",
           "--sandbox", "read-only"]
    if model:
        cmd += ["--model", model]
    if reasoning_effort in ("minimal", "low", "medium", "high", "xhigh"):
        cmd += ["-c", f'model_reasoning_effort="{reasoning_effort}"']
    return cmd + ["-o", out_path, "-"]


def spawn_command(cmd: list[str]) -> list[str]:
    """Run npm's .cmd shims through the command interpreter on Windows."""
    if os.name == "nt" and cmd and cmd[0].lower().endswith((".cmd", ".bat")):
        return [os.environ.get("COMSPEC", "cmd.exe"), "/c", *cmd]
    return cmd


def parse_claude_output(text: str) -> str:
    cleaned = strip_ansi(text)
    if not cleaned:
        return ""
    try:
        data = json.loads(cleaned)
    except Exception:
        data = None
    if isinstance(data, dict):
        for key in ("result", "text", "response"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        content = data.get("content")
        if isinstance(content, list):
            joined = "".join(str(part.get("text", "")) for part in content
                             if isinstance(part, dict))
            if joined.strip():
                return joined.strip()
    return cleaned


def parse_codex_output(text: str) -> str:
    """Accept either the plain final message or Codex's JSONL event stream."""
    cleaned = strip_ansi(text)
    if not cleaned:
        return ""
    lines = [line for line in cleaned.splitlines() if line.strip()]
    texts: list[str] = []
    for line in lines:
        if not line.lstrip().startswith("{"):
            continue
        try:
            event = json.loads(line)
        except Exception:
            continue
        if not isinstance(event, dict):
            continue
        for key in ("result", "text", "message"):
            value = event.get(key)
            if isinstance(value, str) and value.strip():
                texts.append(value.strip())
        item = event.get("item")
        if isinstance(item, dict):
            value = item.get("text")
            if isinstance(value, str) and value.strip():
                texts.append(value.strip())
        message = event.get("msg")
        if isinstance(message, dict) and message.get("type") == "agent_message":
            value = message.get("message")
            if isinstance(value, str) and value.strip():
                texts.append(value.strip())
    if texts:
        return texts[-1]
    # Plain output: drop obvious log/header lines and keep the tail.
    body = [line for line in lines if not line.startswith(("--------", "user", "thinking"))]
    return "\n".join(body).strip() or cleaned


@dataclass
class Job:
    kind: str
    system: str
    user: str
    callback: Callable[[dict | None, str], None] | None = None
    max_tokens: int = 300
    temperature: float = 0.9
    use_cache: bool = True
    model: str = ""


@dataclass
class Stats:
    calls: int = 0
    cached: int = 0
    errors: int = 0
    prompt_chars: int = 0
    reply_chars: int = 0

    @property
    def tokens_estimate(self) -> int:
        return (self.prompt_chars + self.reply_chars) // 4


