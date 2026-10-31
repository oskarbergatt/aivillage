"""Non-blocking GitHub release checks for packaged builds."""
from __future__ import annotations

import json
import threading
from urllib.request import Request, urlopen

REPOSITORY = "oskarbergatt/aivillage"


def check_latest(callback) -> None:
    def worker():
        try:
            request = Request(
                f"https://api.github.com/repos/{REPOSITORY}/releases/latest",
                headers={"Accept": "application/vnd.github+json", "User-Agent": "aivillage-updater"})
            with urlopen(request, timeout=8) as response:
                data = json.loads(response.read(512_000))
            tag = str(data.get("tag_name", "")).lstrip("v")
            url = str(data.get("html_url", ""))
            if tag and url.startswith(f"https://github.com/{REPOSITORY}/releases/"):
                callback(tag, url)
        except Exception:
            pass  # Updates are optional; offline or API failures must not affect play.

    threading.Thread(target=worker, daemon=True, name="release-check").start()


def newer_version(latest: str, current: str) -> bool:
    try:
        def parts(value):
            result = tuple(int(piece) for piece in value.split(".") if piece.isdigit())
            return result + (0,) * max(0, 3 - len(result))
        return parts(latest) > parts(current)
    except (TypeError, ValueError):
        return False
