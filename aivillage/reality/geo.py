"""Work out where the player actually is, so the weather is real."""
from __future__ import annotations

import json
import threading
from dataclasses import dataclass, asdict
from pathlib import Path

import requests

from ..config import DATA_DIR

CACHE = DATA_DIR / "location.json"
DEFAULT = (54.0887, 12.1405, "Rostock", "Germany", "Europe/Berlin")


@dataclass
class Location:
    lat: float
    lon: float
    city: str
    country: str
    timezone: str
    detected: bool = True
    source: str = "ip"

    @property
    def label(self) -> str:
        if self.city and self.country:
            return f"{self.city}, {self.country}"
        return f"{self.lat:.2f}, {self.lon:.2f}"


def _load_cache() -> Location | None:
    if not CACHE.exists():
        return None
    try:
        data = json.loads(CACHE.read_text(encoding="utf-8"))
        return Location(**data)
    except Exception:
        return None


def _save_cache(loc: Location) -> None:
    try:
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps(asdict(loc), indent=2), encoding="utf-8")
    except Exception:
        pass


def _from_ip() -> Location | None:
    try:
        r = requests.get("https://ipwho.is/", timeout=8,
                         headers={"User-Agent": "aivillage/0.1"})
        data = r.json()
        if not data.get("success"):
            return None
        tz = (data.get("timezone") or {}).get("id", "UTC")
        return Location(float(data["latitude"]), float(data["longitude"]),
                        data.get("city", ""), data.get("country", ""), tz)
    except Exception:
        return None


def geocode(name: str) -> Location | None:
    try:
        r = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": name, "count": 1, "language": "en", "format": "json"},
            timeout=8, headers={"User-Agent": "aivillage/0.1"})
        results = r.json().get("results") or []
        if not results:
            return None
        g = results[0]
        return Location(float(g["latitude"]), float(g["longitude"]),
                        g.get("name", name), g.get("country", ""),
                        g.get("timezone", "UTC"), source="geocode")
    except Exception:
        return None


class LocationService:
    """Resolves the location in the background; never blocks startup."""

    def __init__(self, config):
        self.config = config
        self.location: Location = _load_cache() or Location(*DEFAULT, detected=False,
                                                            source="default")
        self._thread: threading.Thread | None = None

    def resolve_now(self) -> Location:
        lat = self.config.get("reality.latitude", "auto")
        lon = self.config.get("reality.longitude", "auto")
        if lat != "auto" and lon != "auto":
            loc = Location(float(lat), float(lon), "", "", "UTC", source="config")
            self.location = loc
            return loc
        found = _from_ip()
        if found:
            self.location = found
            _save_cache(found)
            return found
        cached = _load_cache()
        if cached:
            cached.detected = False
            cached.source = "cache"
            self.location = cached
            return cached
        self.location = Location(*DEFAULT, detected=False, source="default")
        return self.location

    def resolve_async(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self.resolve_now, daemon=True,
                                        name="location")
        self._thread.start()

    def set_city(self, name: str) -> Location | None:
        loc = geocode(name)
        if loc:
            self.location = loc
            _save_cache(loc)
        return loc
