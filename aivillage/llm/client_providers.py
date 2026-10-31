"""Extracted methods for LLMClient."""
from __future__ import annotations

from .client_shared import (
    Any,
    DATA_DIR,
    Job,
    Path,
    claude_command,
    codex_command,
    json,
    os,
    parse_claude_output,
    parse_codex_output,
    requests,
    spawn_command,
    strip_ansi,
    subprocess,
    tempfile,
)


class ClientProvidersMixin:
    def _call(self, job: Job) -> str:
        timeout = float(self.config.get("llm.timeout_s", 60))
        model = job.model or self.model
        if self.provider == "mock":
            return self._mock(job)
        if self.provider in ("claude_cli", "codex_cli"):
            return self._call_cli(job)
        if self.provider == "ollama":
            r = requests.post(f"{self.base_url}/api/chat", timeout=timeout, json={
                "model": model,
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
                              json={"model": model, "temperature": job.temperature,
                                    "max_tokens": job.max_tokens,
                                    "messages": [{"role": "system", "content": job.system},
                                                 {"role": "user", "content": job.user}]})
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
        if self.provider == "anthropic":
            r = requests.post("https://api.anthropic.com/v1/messages", timeout=timeout,
                              headers={"x-api-key": self.api_key,
                                       "anthropic-version": "2023-06-01"},
                              json={"model": model, "max_tokens": job.max_tokens,
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
            r = requests.post(url, timeout=timeout, headers=headers, allow_redirects=False,
                              json={"model": model, "temperature": job.temperature,
                                    "max_tokens": job.max_tokens,
                                    "messages": [{"role": "system", "content": job.system},
                                                 {"role": "user", "content": job.user}]})
            r.raise_for_status()
            if 300 <= r.status_code < 400:
                raise RuntimeError("gateway redirects are not supported")
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
        model = job.model or str(self.config.get("llm.cli_model", "") or "")
        if self.provider == "claude_cli":
            proc = self._run_cli(
                claude_command(self.cli_path, job.system, model), job.user, timeout)
            text = parse_claude_output(proc.stdout or "")
            try:
                result = json.loads(strip_ansi(proc.stdout or ""))
            except (ValueError, TypeError):
                result = None
            if isinstance(result, dict) and result.get("is_error"):
                raise RuntimeError(text[:200] or "claude CLI failed")
            if proc.returncode != 0:
                detail = strip_ansi(proc.stderr or text or "")[:200]
                raise RuntimeError(detail or "claude CLI failed")
            return text
        fd, out_path = tempfile.mkstemp(prefix="aivillage-", suffix=".txt")
        os.close(fd)
        try:
            effort = (str(self.config.get("llm.ambient_reasoning_effort", "low") or "").lower()
                      if job.kind in ("exchange", "group") else "")
            proc = self._run_cli(
                codex_command(self.cli_path, out_path, model, effort),
                f"{job.system}\n\n{job.user}", timeout)
            text = ""
            try:
                text = Path(out_path).read_text(
                    encoding="utf-8", errors="replace").strip()
            except OSError:
                text = ""
            if not text:
                text = parse_codex_output(proc.stdout or "")
            if proc.returncode != 0:
                detail = strip_ansi(proc.stderr or text or "")[:200]
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

    @property
    def label(self) -> str:
        if self.available:
            return self.status
        return self.status or "no language model"

    def cost_text(self) -> str:
        return f"{self.stats.calls} calls · ~{self.stats.tokens_estimate} tokens"

