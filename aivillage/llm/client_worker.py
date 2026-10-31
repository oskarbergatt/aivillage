"""Extracted methods for LLMClient."""
from __future__ import annotations

from .client_shared import (
    Callable,
    Job,
    Path,
    env,
    hashlib,
    queue,
    requests,
    shutil,
    threading,
)


class ClientWorkerMixin:
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
                    models = [model for model in models if model]
                    if models:
                        wanted = self.config.get("llm.model", "llama3.2")
                        chosen = wanted if wanted in models else models[0]
                        self.provider, self.model, self.base_url = "ollama", chosen, base
                        self.available = True
                        self.status = f"ollama · {chosen}"
                        return
                    if provider == "ollama":
                        self.status = "Ollama is running, but has no model installed"
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
            from ..setup import valid_gateway
            base = str(self.config.get("llm.base_url", "") or "").strip().rstrip("/")
            model = str(self.config.get("llm.model", "local") or "").strip()
            key_env = str(self.config.get("llm.api_key_env", "") or "").strip()
            if valid_gateway(base, model, key_env):
                self.provider = "openai_compatible"
                self.base_url = base
                self.model = model
                self.api_key = env(key_env) if key_env else ""
                self.available = True
                self.status = f"compatible · {base}"
                return
            self.status = "invalid gateway URL, model, or key environment variable"
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

    def _start(self) -> None:
        self._worker = threading.Thread(target=self._run, args=(self._jobs,), daemon=True, name="llm")
        self._worker.start()
        if self.config.get("llm.parallel_ambient", True):
            for index in range(2):
                worker = threading.Thread(target=self._run, args=(self._ambient_jobs,),
                                          daemon=True, name=f"llm-ambient-{index}")
                self._ambient_workers.append(worker)
                worker.start()
            self._ambient_worker = self._ambient_workers[0]

    def stop(self) -> None:
        self._stop.set()
        self._jobs.put(Job("__stop__", "", ""))
        for _ in self._ambient_workers:
            self._ambient_jobs.put(Job("__stop__", "", ""))

    def submit(self, kind: str, system: str, user: str,
               callback: Callable[[dict | None, str], None] | None = None,
               max_tokens: int | None = None, temperature: float | None = None,
               use_cache: bool = True) -> None:
        if not self.available:
            if callback:
                callback(None, "unavailable")
            return
        ambient = kind in ("exchange", "group")
        model = str(self.config.get("llm.ambient_model", "") or "").strip() if ambient else ""
        job = Job(kind, system, user, callback,
                  max_tokens or int(self.config.get("llm.max_tokens", 300)),
                  temperature if temperature is not None else float(
                      self.config.get("llm.temperature", 0.9)),
                  use_cache, model)
        (self._ambient_jobs if ambient and self._ambient_worker else self._jobs).put(job)

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

    def _cache_key(self, job: Job) -> str:
        # Include all output-affecting settings and delimit fields unambiguously.
        from .client_shared import json
        effort = (self.config.get("llm.ambient_reasoning_effort", "low")
                  if self.provider == "codex_cli" and job.kind in ("exchange", "group") else "")
        raw = json.dumps([self.provider, job.model or self.model, self.base_url, job.kind,
                          job.system, job.user, job.max_tokens, job.temperature, effort],
                         ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        return hashlib.sha1(raw).hexdigest()

    def _run(self, jobs) -> None:
        while not self._stop.is_set():
            try:
                job = jobs.get(timeout=0.5)
            except queue.Empty:
                continue
            if job.kind == "__stop__":
                break
            try:
                result = self._execute(job)
                self._results.put((job, result, ""))
            except Exception as exc:
                with self._cache_lock:
                    self.stats.errors += 1
                self._results.put((job, None, str(exc)[:200]))

    def _execute(self, job: Job) -> dict | None:
        key = self._cache_key(job)
        cache_size = max(0, int(self.config.get("llm.cache_entries", 256)))
        with self._cache_lock:
            if job.use_cache and cache_size and key in self._cache:
                self.stats.cached += 1
                self._cache.move_to_end(key)
                return self._cache[key]
        text = self._call(job)
        if not text:
            return None
        with self._cache_lock:
            self.stats.calls += 1
            self.stats.prompt_chars += len(job.system) + len(job.user)
            self.stats.reply_chars += len(text)
        data = None
        from .prompts import parse_json
        data = parse_json(text)
        if data is None:
            # keep a readable fallback so a chat still says something
            return {"line": text.strip()[:280]}
        if job.use_cache and cache_size and data:
            with self._cache_lock:
                self._cache[key] = data
                self._cache.move_to_end(key)
                while len(self._cache) > cache_size:
                    self._cache.popitem(last=False)
        return data

