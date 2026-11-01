"""Release discovery and integrity-checked installer downloads."""
from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import subprocess
import tempfile
import threading
from urllib.parse import urlparse
from pathlib import Path
from urllib.request import Request, urlopen

REPOSITORY = "oskarbergatt/aivillage"
API_URL = f"https://api.github.com/repos/{REPOSITORY}/releases/latest"
MAX_DOWNLOAD = 1_500_000_000


def newer_version(latest: str, current: str) -> bool:
    try:
        def parts(value):
            if not re.fullmatch(r"\d+(\.\d+){0,3}", value):
                raise ValueError("invalid version")
            result = tuple(int(piece) for piece in value.split("."))
            return result + (0,) * max(0, 4 - len(result))
        return parts(latest) > parts(current)
    except (TypeError, ValueError):
        return False


def installer_for(assets: list[dict], system: str | None = None) -> tuple[dict, dict] | None:
    system = system or platform.system()
    suffix = {"Windows": ".exe", "Darwin": ".dmg", "Linux": ".deb"}.get(system)
    if not suffix:
        return None
    installer = next((a for a in assets if str(a.get("name", "")).lower().endswith(suffix)), None)
    sums = next((a for a in assets if a.get("name") == "SHA256SUMS.txt"), None)
    return (installer, sums) if installer and sums else None


def _validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in (
            "github.com", "api.github.com", "release-assets.githubusercontent.com",
            "objects.githubusercontent.com"):
        raise ValueError("Update URL is not an approved GitHub HTTPS host")


def _request(url: str, limit: int = MAX_DOWNLOAD) -> bytes:
    _validate_url(url)
    request = Request(url, headers={"User-Agent": "aivillage-updater"})
    with urlopen(request, timeout=30) as response:
        final_host = urlparse(response.geturl()).hostname
        if final_host not in ("github.com", "release-assets.githubusercontent.com",
                              "objects.githubusercontent.com"):
            raise ValueError("Installer redirected to an unapproved host")
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError("Update download exceeds the safety limit")
    return data


def _expected_hash(checksums: bytes, filename: str) -> str:
    for line in checksums.decode("ascii", "strict").splitlines():
        match = re.fullmatch(r"([0-9a-fA-F]{64})\s+\*?([^\s]+)", line.strip())
        if match and Path(match.group(2)).name == filename:
            return match.group(1).lower()
    raise ValueError("No SHA-256 checksum was published for this installer")


def download_verified_installer(installer_url: str, checksum_url: str,
                                filename: str) -> Path:
    _validate_url(installer_url)
    _validate_url(checksum_url)
    if Path(filename).name != filename or not filename.startswith("aivillage-"):
        raise ValueError("Invalid installer filename")
    checksums = _request(checksum_url, 256_000)
    expected = _expected_hash(checksums, filename)
    payload = _request(installer_url)
    actual = hashlib.sha256(payload).hexdigest()
    if actual != expected:
        raise ValueError("Installer checksum verification failed")
    target_dir = Path(tempfile.gettempdir()) / "aivillage-updates"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / filename
    temp = target.with_suffix(target.suffix + ".part")
    temp.write_bytes(payload)
    os.replace(temp, target)
    return target


def launch_installer(path: Path, system: str | None = None) -> None:
    system = system or platform.system()
    if system == "Windows":
        subprocess.Popen([str(path)], close_fds=True)
    elif system == "Darwin":
        subprocess.Popen(["open", str(path)], close_fds=True)
    elif system == "Linux":
        subprocess.Popen(["xdg-open", str(path)], close_fds=True)
    else:
        raise RuntimeError("Automatic installer launch is not supported on this platform")


def check_latest(callback) -> None:
    def worker():
        try:
            request = Request(API_URL, headers={"Accept": "application/vnd.github+json",
                                                "User-Agent": "aivillage-updater"})
            with urlopen(request, timeout=8) as response:
                data = json.loads(response.read(512_000))
            tag = str(data.get("tag_name", ""))
            version = tag.removeprefix("v")
            release_url = str(data.get("html_url", ""))
            if not re.fullmatch(r"\d+(\.\d+){0,3}", version):
                return
            if not release_url.startswith(f"https://github.com/{REPOSITORY}/releases/"):
                return
            selected = installer_for(data.get("assets", []))
            if not selected:
                callback({"version": version, "url": release_url, "installer": None})
                return
            installer, sums = selected
            callback({"version": version, "url": release_url,
                      "installer": {"name": installer["name"],
                                    "url": installer["browser_download_url"],
                                    "checksums_url": sums["browser_download_url"]}})
        except Exception:
            pass  # Update checks are optional and must never affect play.

    threading.Thread(target=worker, daemon=True, name="release-check").start()


def install_update(info: dict, callback) -> None:
    def worker():
        try:
            asset = info["installer"]
            path = download_verified_installer(asset["url"], asset["checksums_url"], asset["name"])
            launch_installer(path)
            callback(True, "")
        except Exception as exc:
            callback(False, str(exc)[:220])

    threading.Thread(target=worker, daemon=True, name="release-installer").start()
