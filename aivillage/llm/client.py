"""Provider-agnostic LLM client with a background worker.

Nothing here ever blocks the render loop: jobs go in, callbacks come out on the
main thread via poll().
"""
from __future__ import annotations

import hashlib
import json
import os
import queue
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable

import requests

from ..config import Config, env


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
    def _resolve(self) -> None:
        provider = str(self.config.get("llm.provider", "auto")).lower()
        if provider == "mock":
            self.provider, self.model, self.available = "mock", "mock", True
            self.status = "mock provider"
            return
        if provider not in ("auto", "ollama", "openai", "anthropic", "openai_compatible"):
            self.provider = "none"
            self.status = "no provider configured"
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
        self.provider = "none"
        self.available = False
        if self.status in ("not checked", ""):
            self.status = "no model available — run Ollama or set an API key"

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

    def _mock(self, job: Job) -> str:
        payload = json.loads(job.user) if job.user.strip().startswith("{") else {}
        if job.kind == "exchange":
            return json.dumps({"lines": [
                {"speaker": "a", "text": "The roof still leaks, you know."},
                {"speaker": "b", "text": "Everything leaks. That is what roofs are for."},
                {"speaker": "a", "text": "That is not what roofs are for."},
            ]})
        if job.kind == "dispatch":
            return json.dumps({"headline": "A strange wind carried word from the far city.",
                               "tone": "strange", "topic": "politics"})
        if job.kind == "rumour":
            return json.dumps({"headline": "A fair is gathering in the next town, they say.",
                               "tone": "good", "topic": "people"})
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
