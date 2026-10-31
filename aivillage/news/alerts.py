"""Bright Sky / DWD weather alerts.

Bright Sky is keyless, so a traveller can carry a real official warning into the
village without an API key.  The service only fetches on its own thread and the
render loop reads ``poll()``; a failed fetch is silent and never blocks play.
"""
from __future__ import annotations

import hashlib
import threading
import time
from dataclasses import dataclass
from datetime import datetime

import requests

API = "https://api.brightsky.dev/alerts"
HEADERS = {"User-Agent": "aivillage/0.2 (local village simulation)"}
SEVERE = {"severe", "extreme", "moderate"}
ALERT_WORDS = ("storm", "thunder", "gale", "snow", "ice", "frost", "heat",
               "heavy rain", "flood", "fog", "wind", "gewitter", "sturm",
               "schnee", "eis", "frost", "hitze", "regen", "nebel", "wind")


@dataclass
class Alert:
    id: str
    headline: str
    description: str
    severity: str
    event: str
    onset: str = ""
    expires: str = ""
    instruction: str = ""
    url: str = ""
    fetched_at: float = 0.0

    @property
    def colour(self):
        return {"extreme": (230, 120, 110), "severe": (224, 152, 100),
                "moderate": (226, 196, 120)}.get(self.severity, (190, 190, 200))


class AlertService:
    def __init__(self, config, locations):
        self.config = config
        self.locations = locations
        self.enabled = bool(config.get("news.alerts_enabled", True))
        self.poll_minutes = max(5, int(config.get("news.alert_poll_minutes", 20)))
        self.alerts: list[Alert] = []
        self.seen: set[str] = set()
        self.last_fetch = 0.0
        self.last_error = ""
        self._new: list[Alert] = []
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    # -- lifecycle -------------------------------------------------------
    def start(self) -> None:
        if not self.enabled or self._thread is not None:
            return
        self._thread = threading.Thread(target=self._loop, daemon=True,
                                        name="alerts")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _loop(self) -> None:
        while not self._stop.is_set():
            self.fetch_once()
            self._stop.wait(self.poll_minutes * 60)

    # -- fetching --------------------------------------------------------
    def fetch_once(self) -> int:
        if not self.enabled:
            return 0
        loc = self.locations.location
        try:
            r = requests.get(API, timeout=10, headers=HEADERS,
                             params={"lat": loc.lat, "lon": loc.lon})
            r.raise_for_status()
            data = r.json()
            now = time.time()
            fresh: list[Alert] = []
            for raw in data.get("alerts", []) or []:
                alert = self._parse(raw, now)
                if alert is None:
                    continue
                fresh.append(alert)
                if alert.id not in self.seen:
                    self.seen.add(alert.id)
                    self._new.append(alert)
            self.alerts = fresh
            self.last_fetch = now
            self.last_error = ""
            return len(fresh)
        except Exception as exc:
            self.last_error = str(exc)[:120]
            return 0

    def _parse(self, raw: dict, now: float) -> Alert | None:
        try:
            event = str(raw.get("event") or raw.get("headline") or "").strip()
            headline = str(raw.get("headline") or event or "Weather warning").strip()
            description = str(raw.get("description") or "").strip()
            severity = str(raw.get("severity") or "moderate").lower()
            text = f"{event} {headline} {description}".lower()
            if severity not in SEVERE and not any(w in text for w in ALERT_WORDS):
                return None
            expires = str(raw.get("expires") or "")
            if expires:
                try:
                    if datetime.fromisoformat(expires.replace("Z", "+00:00")).timestamp() < now:
                        return None
                except Exception:
                    pass
            ident = str(raw.get("id") or "")
            if not ident:
                ident = hashlib.sha1(
                    f"{event}|{headline}|{raw.get('onset', '')}".encode("utf-8")
                ).hexdigest()[:16]
            return Alert(id=ident, headline=headline, description=description,
                         severity=severity, event=event,
                         onset=str(raw.get("onset") or ""),
                         expires=expires,
                         instruction=str(raw.get("instruction") or ""),
                         url=str(raw.get("uri") or ""), fetched_at=now)
        except Exception:
            return None

    # -- access ----------------------------------------------------------
    def poll(self) -> Alert | None:
        """Return the next unread alert, or None. Called from the main thread."""
        return self._new.pop(0) if self._new else None

    def status(self) -> dict:
        return {
            "enabled": self.enabled,
            "active": len(self.alerts),
            "seen": len(self.seen),
            "last_fetch": self.last_fetch,
            "error": self.last_error,
        }

    def clear_seen(self) -> None:
        self.seen.clear()
