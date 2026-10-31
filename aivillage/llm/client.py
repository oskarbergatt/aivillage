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


def codex_command(exe: str, out_path: str, model: str = "") -> list[str]:
    """Non-interactive Codex invocation (uses the ChatGPT login)."""
    cmd = [exe, "exec", "--skip-git-repo-check", "--ephemeral",
           "--sandbox", "read-only"]
    if model:
        cmd += ["--model", model]
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


class LLMClient:
    def __init__(self, config: Config):
        self.config = config
        self.provider = "none"
        self.model = ""
        self.api_key = ""
        self.base_url = ""
        self.cli_path = ""
        self.available = False
        self.status = "not checked"
        self.stats = Stats()
        self._cache: dict[str, dict] = {}
        self._jobs: queue.Queue[Job] = queue.Queue()
        self._results: queue.Queue[tuple[Job, dict | None, str]] = queue.Queue()
        self._worker: threading.Thread | None = None
        self._stop = threading.Event()
        self._resolve()
        self._start()

    # -- provider resolution --------------------------------------------
    def _find_cli(self, name: str) -> str:
        configured = str(self.config.get(f"llm.{name}_command", name) or name)
        found = shutil.which(configured) or shutil.which(name)
        return found or ""

    def _try_cli(self, provider: str) -> bool:
        """Pick a logged-in subscription CLI.

        `subscription` prefers Claude and falls back to Codex; the explicit
        providers only try their own executable.
        """
        order = {"claude_cli": ("claude",), "codex_cli": ("codex",),
                 "subscription": ("claude", "codex")}.get(provider, ())
        for name in order:
            exe = self._find_cli(name)
            if not exe:
                continue
            self.provider = "claude_cli" if name == "claude" else "codex_cli"
            self.cli_path = exe
            self.model = str(self.config.get("llm.cli_model", "") or "")
            self.available = True
            self.status = f"{name} subscription · {Path(exe).stem}"
            return True
        return False

    def _resolve(self) -> None:
        provider = str(self.config.get("llm.provider", "auto")).lower()
        if provider == "mock":
            self.provider, self.model, self.available = "mock", "mock", True
            self.status = "mock provider"
            return
        if provider not in ("auto", "ollama", "openai", "anthropic",
                            "openai_compatible", "claude_cli", "codex_cli",
                            "subscription"):
            self.provider = "none"
            self.status = "no provider configured"
            return

        if provider in ("claude_cli", "codex_cli", "subscription"):
            if self._try_cli(provider):
                return
            self.provider = "none"
            self.available = False
            self.status = ("no subscription CLI found — install Claude Code "
                           "or Codex, or set an API key")
            return

        if (provider == "auto"
                and bool(self.config.get("llm.prefer_subscription", False))
                and self._try_cli("subscription")):
            return

        if provider in ("auto", "ollama"):
            base = self.config.get("llm.base_url") or env("OLLAMA_HOST", "http://localhost:11434")
            base = str(base).rstrip("/")
            try:
                r = requests.get(f"{base}/api/tags", timeout=1.6)
                if r.status_code == 200:
                    models = [m.get("name", "") for m in r.json().get("models", [])]
                    wanted = self.config.get("llm.model", "llama3.2")
                    chosen = wanted if wanted in models else (models[0] if models else wanted)
                    self.provider, self.model, self.base_url = "ollama", chosen, base
                    self.available = True
                    self.status = f"ollama · {chosen}"
                    return
            except Exception:
                if provider == "ollama":
                    self.status = f"ollama unreachable at {base}"
        if provider in ("auto", "openai"):
            key = env("OPENAI_API_KEY") or env(str(self.config.get("llm.api_key_env", "")))
            if key:
                self.provider = "openai"
                self.api_key = key
                self.model = env("OPENAI_MODEL", "gpt-4o-mini")
                self.available = True
                self.status = f"openai · {self.model}"
                return
        if provider in ("auto", "anthropic"):
            key = env("ANTHROPIC_API_KEY")
            if key:
                self.provider = "anthropic"
                self.api_key = key
                self.model = env("ANTHROPIC_MODEL", "claude-3-5-haiku-latest")
                self.available = True
                self.status = f"anthropic · {self.model}"
                return
        if provider == "openai_compatible":
            base = str(self.config.get("llm.base_url", "")).rstrip("/")
            if base:
                self.provider = "openai_compatible"
                self.base_url = base
                self.model = str(self.config.get("llm.model", "local"))
                self.available = True
                self.status = f"compatible · {base}"
                return
        # A signed-in CLI is a perfectly good last resort for `auto`.
        if provider == "auto" and self._try_cli("subscription"):
            return
        self.provider = "none"
        self.available = False
        if self.status in ("not checked", ""):
            self.status = ("no model available — run Ollama, set an API key, "
                           "or sign in to Claude Code / Codex")

    def retry_resolve(self) -> None:
        if not self.available:
            self._resolve()

    # -- lifecycle -------------------------------------------------------
    def _start(self) -> None:
        self._worker = threading.Thread(target=self._run, daemon=True, name="llm")
        self._worker.start()

    def stop(self) -> None:
        self._stop.set()
        self._jobs.put(Job("__stop__", "", ""))

    # -- public API ------------------------------------------------------
    def submit(self, kind: str, system: str, user: str,
               callback: Callable[[dict | None, str], None] | None = None,
               max_tokens: int | None = None, temperature: float | None = None,
               use_cache: bool = True) -> None:
        if not self.available:
            if callback:
                callback(None, "unavailable")
            return
        job = Job(kind, system, user, callback,
                  max_tokens or int(self.config.get("llm.max_tokens", 300)),
                  temperature if temperature is not None else float(
                      self.config.get("llm.temperature", 0.9)),
                  use_cache)
        self._jobs.put(job)

    def poll(self) -> None:
        while True:
            try:
                job, result, error = self._results.get_nowait()
            except queue.Empty:
                break
            if job.callback:
                try:
                    job.callback(result, error)
                except Exception:
                    pass

    # -- worker ----------------------------------------------------------
    def _cache_key(self, job: Job) -> str:
        raw = f"{self.provider}|{self.model}|{job.system}|{job.user}".encode()
        return hashlib.sha1(raw).hexdigest()

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                job = self._jobs.get(timeout=0.5)
            except queue.Empty:
                continue
            if job.kind == "__stop__":
                break
            try:
                result = self._execute(job)
                self._results.put((job, result, ""))
            except Exception as exc:
                self.stats.errors += 1
                self._results.put((job, None, str(exc)[:200]))

    def _execute(self, job: Job) -> dict | None:
        key = self._cache_key(job)
        if job.use_cache and key in self._cache:
            self.stats.cached += 1
            return self._cache[key]
        text = self._call(job)
        if not text:
            return None
        self.stats.calls += 1
        self.stats.prompt_chars += len(job.system) + len(job.user)
        self.stats.reply_chars += len(text)
        data = None
        from .prompts import parse_json
        data = parse_json(text)
        if data is None:
            # keep a readable fallback so a chat still says something
            data = {"line": text.strip()[:280]}
        if job.use_cache:
            self._cache[key] = data
        return data

    def _call(self, job: Job) -> str:
        timeout = float(self.config.get("llm.timeout_s", 60))
        if self.provider == "mock":
            return self._mock(job)
        if self.provider in ("claude_cli", "codex_cli"):
            return self._call_cli(job)
        if self.provider == "ollama":
            r = requests.post(f"{self.base_url}/api/chat", timeout=timeout, json={
                "model": self.model,
                "messages": [{"role": "system", "content": job.system},
                             {"role": "user", "content": job.user}],
                "stream": False,
                "options": {"temperature": job.temperature,
                            "num_predict": job.max_tokens},
            })
            r.raise_for_status()
            return r.json().get("message", {}).get("content", "")
        if self.provider == "openai":
            r = requests.post("https://api.openai.com/v1/chat/completions",
                              timeout=timeout,
                              headers={"Authorization": f"Bearer {self.api_key}"},
                              json={"model": self.model, "temperature": job.temperature,
                                    "max_tokens": job.max_tokens,
                                    "messages": [{"role": "system", "content": job.system},
                                                 {"role": "user", "content": job.user}]})
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
        if self.provider == "anthropic":
            r = requests.post("https://api.anthropic.com/v1/messages", timeout=timeout,
                              headers={"x-api-key": self.api_key,
                                       "anthropic-version": "2023-06-01"},
                              json={"model": self.model, "max_tokens": job.max_tokens,
                                    "temperature": job.temperature,
                                    "system": job.system,
                                    "messages": [{"role": "user", "content": job.user}]})
            r.raise_for_status()
            return "".join(block.get("text", "") for block in r.json().get("content", []))
        if self.provider == "openai_compatible":
            base = self.base_url
            url = base if base.endswith("/chat/completions") else base + "/chat/completions"
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            r = requests.post(url, timeout=timeout, headers=headers,
                              json={"model": self.model, "temperature": job.temperature,
                                    "max_tokens": job.max_tokens,
                                    "messages": [{"role": "system", "content": job.system},
                                                 {"role": "user", "content": job.user}]})
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
        return ""

    def _run_cli(self, cmd: list[str], prompt: str, timeout: float):
        kwargs: dict[str, Any] = {
            "input": prompt, "capture_output": True, "text": True,
            "encoding": "utf-8", "errors": "replace", "timeout": timeout,
            "cwd": str(DATA_DIR),
        }
        if os.name == "nt":
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            return subprocess.run(spawn_command(cmd), **kwargs)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                f"subscription CLI timed out after {int(timeout)}s") from exc

    def _call_cli(self, job: Job) -> str:
        """Talk to a logged-in Claude Code or Codex subscription."""
        timeout = float(self.config.get("llm.cli_timeout_s", 120) or 120)
        model = str(self.config.get("llm.cli_model", "") or "")
        if self.provider == "claude_cli":
            proc = self._run_cli(
                claude_command(self.cli_path, job.system, model), job.user, timeout)
            text = parse_claude_output(proc.stdout or "")
            if proc.returncode != 0 and not text:
                detail = strip_ansi(proc.stderr or "")[:200]
                raise RuntimeError(detail or "claude CLI failed")
            return text
        fd, out_path = tempfile.mkstemp(prefix="aivillage-", suffix=".txt")
        os.close(fd)
        try:
            proc = self._run_cli(
                codex_command(self.cli_path, out_path, model),
                f"{job.system}\n\n{job.user}", timeout)
            text = ""
            try:
                text = Path(out_path).read_text(
                    encoding="utf-8", errors="replace").strip()
            except OSError:
                text = ""
            if not text:
                text = parse_codex_output(proc.stdout or "")
            if proc.returncode != 0 and not text:
                detail = strip_ansi(proc.stderr or "")[:200]
                raise RuntimeError(detail or "codex CLI failed")
            return text
        finally:
            try:
                os.unlink(out_path)
            except OSError:
                pass

    def _mock(self, job: Job) -> str:
        payload = json.loads(job.user) if job.user.strip().startswith("{") else {}
        if job.kind == "exchange":
            return json.dumps({"lines": [
                {"speaker": "a", "text": "The roof still leaks, you know."},
                {"speaker": "b", "text": "Everything leaks. That is what roofs are for."},
                {"speaker": "a", "text": "That is not what roofs are for."},
            ]})
        if job.kind == "group":
            return json.dumps({"lines": [
                {"speaker": "Pip Hollow", "text": "The turnips are sulking again."},
                {"speaker": "Orin Bell", "text": "Feed them, then. That is what I do."},
                {"speaker": "Marrow Vane", "text": "You feed everything, Orin."},
            ]})
        if job.kind == "alert":
            return json.dumps({"headline": "A hard wind is coming; tie down the boats.",
                               "tone": "bad", "topic": "weather"})
        if job.kind == "dispatch":
            return json.dumps({"headline": "A strange wind carried word from the far city.",
                               "tone": "strange", "topic": "politics"})
        if job.kind == "rumour":
            return json.dumps({"headline": "A fair is gathering in the next town, they say.",
                               "tone": "good", "topic": "people"})
        if job.kind == "self":
            return json.dumps({
                "ambition": "To leave the village a little better than I found it.",
                "bio": "Mock bio: a villager with a new notion of who they might be.",
                "quirk": "hums while deciding anything important",
                "hat": "cap",
                "outfit": 3,
            })
        return json.dumps({"line": "Mock reply: the village is listening."})

    # -- convenience -----------------------------------------------------
    @property
    def label(self) -> str:
        if self.available:
            return self.status
        return self.status or "no language model"

    def cost_text(self) -> str:
        return f"{self.stats.calls} calls · ~{self.stats.tokens_estimate} tokens"


_ACTIVE: LLMClient | None = None


def client(config: Config) -> LLMClient:
    global _ACTIVE
    if _ACTIVE is None:
        _ACTIVE = LLMClient(config)
    return _ACTIVE
