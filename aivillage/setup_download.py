"""Download the default local model on request, away from the render loop."""
from __future__ import annotations

import queue
import threading
from urllib.parse import urlsplit

import requests

MODEL = "llama3.2"


class ModelDownload:
    def __init__(self):
        self.messages: queue.Queue[tuple[str, str]] = queue.Queue()
        self.running = False
        self.status = "idle"
        self.detail = ""

    def start(self, base_url: str) -> bool:
        if self.running:
            return False
        try:
            parsed = urlsplit(base_url or "http://127.0.0.1:11434")
            if (parsed.scheme not in ("http", "https") or parsed.hostname not in
                    ("localhost", "127.0.0.1", "::1") or parsed.username or parsed.password):
                self.status = "local_only"
                return False
        except ValueError:
            self.status = "local_only"
            return False
        self.running = True
        self.status = "downloading"
        threading.Thread(target=self._download, args=(base_url.rstrip("/"),),
                         daemon=True, name="model-download").start()
        return True

    def _download(self, base_url: str) -> None:
        try:
            with requests.post(f"{base_url or 'http://127.0.0.1:11434'}/api/pull",
                               json={"model": MODEL, "stream": True},
                               stream=True, timeout=(3, 120), allow_redirects=False) as response:
                response.raise_for_status()
                complete = False
                for line in response.iter_lines():
                    if not line:
                        continue
                    import json
                    event = json.loads(line)
                    if event.get("error"):
                        raise RuntimeError(str(event["error"]))
                    if event.get("status") == "success":
                        complete = True
                    if event.get("total") and event.get("completed") is not None:
                        pct = min(100, max(0, int(100 * event["completed"] / event["total"])))
                        self.messages.put(("progress", str(pct)))
                if not complete:
                    raise RuntimeError("download ended before completion")
            self.messages.put(("done", ""))
        except Exception as exc:
            self.messages.put(("error", str(exc)[:200]))

    def poll(self) -> None:
        while True:
            try:
                status, detail = self.messages.get_nowait()
            except queue.Empty:
                break
            self.detail = detail
            self.status = status
            if status in ("done", "error"):
                self.running = False
