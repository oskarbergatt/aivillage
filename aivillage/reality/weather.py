"""Real weather from Open-Meteo, with a seasonal fallback when offline."""
from __future__ import annotations

import json
import math
import random
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

import requests

from ..config import DATA_DIR

CACHE = DATA_DIR / "weather.json"
API = "https://api.open-meteo.com/v1/forecast"


def wmo_condition(code: int) -> str:
    if code == 0:
        return "clear"
    if code in (1, 2):
        return "partly"
    if code == 3:
        return "overcast"
    if code in (45, 48):
        return "fog"
    if 51 <= code <= 57:
        return "drizzle"
    if 61 <= code <= 67:
        return "rain"
    if 71 <= code <= 77 or code in (85, 86):
        return "snow"
    if 80 <= code <= 82:
        return "showers"
    if 95 <= code <= 99:
        return "storm"
    return "clear"


@dataclass
class HourForecast:
    when: datetime
    temp_c: float
    code: int
    condition: str


@dataclass
class WeatherState:
    code: int = 0
    condition: str = "clear"
    temp_c: float = 12.0
    wind: float = 5.0
    is_day: bool = True
    sunrise: datetime | None = None
    sunset: datetime | None = None
    fetched_at: float = 0.0
    source: str = "sim"
    hourly: list[HourForecast] = field(default_factory=list)

    @property
    def wet(self) -> bool:
        return self.condition in ("rain", "drizzle", "showers", "storm")

    @property
    def snowy(self) -> bool:
        return self.condition == "snow"

    @property
    def severe(self) -> bool:
        return self.condition in ("storm", "snow")


def _parse(dt: str) -> datetime:
    try:
        return datetime.fromisoformat(dt)
    except Exception:
        return datetime.now()


def _approx_sun(day: datetime, lat: float) -> tuple[datetime, datetime]:
    """Rough sunrise/sunset for offline mode."""
    day_of_year = day.timetuple().tm_yday
    decl = 23.44 * math.sin(math.radians((360 / 365) * (day_of_year - 81)))
    lat_r = math.radians(max(-66.0, min(66.0, lat)))
    cos_h = -math.tan(lat_r) * math.tan(math.radians(decl))
    cos_h = max(-1.0, min(1.0, cos_h))
    half = math.degrees(math.acos(cos_h)) / 15.0
    noon = day.replace(hour=12, minute=8, second=0, microsecond=0)
    return noon - timedelta(hours=half), noon + timedelta(hours=half)


def seasonal_state(lat: float, now: datetime) -> WeatherState:
    """Deterministic-ish weather driven by season and hour, for offline play."""
    month = now.month
    # northern hemisphere seasons
    base = {12: 2, 1: 1, 2: 2, 3: 6, 4: 10, 5: 15, 6: 19,
            7: 21, 8: 20, 9: 16, 10: 11, 11: 6}.get(month, 12)
    if lat < 0:
        base = 22 - base
    rng = random.Random(f"{now.date()}-{now.hour}-{lat:.1f}")
    diurnal = -3 if now.hour < 6 or now.hour > 21 else (3 if 10 <= now.hour <= 17 else 0)
    temp = base + diurnal + rng.uniform(-3, 3)
    roll = rng.random()
    if base < 2 and roll < 0.35:
        cond, code = "snow", 73
    elif roll < 0.20:
        cond, code = "rain", 63
    elif roll < 0.30:
        cond, code = "overcast", 3
    elif roll < 0.55:
        cond, code = "partly", 2
    elif roll < 0.64:
        cond, code = "fog", 45
    else:
        cond, code = "clear", 0
    sunrise, sunset = _approx_sun(now, lat)
    return WeatherState(code=code, condition=cond, temp_c=round(temp, 1),
                        wind=rng.uniform(2, 18), is_day=sunrise <= now <= sunset,
                        sunrise=sunrise, sunset=sunset, source="sim")


class WeatherService:
    def __init__(self, config, locations):
        self.config = config
        self.locations = locations
        self.state: WeatherState = self._load_cache() or seasonal_state(
            locations.location.lat, datetime.now())
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.last_error: str = ""

    # -- cache ----------------------------------------------------------
    def _load_cache(self) -> WeatherState | None:
        if not CACHE.exists():
            return None
        try:
            data = json.loads(CACHE.read_text(encoding="utf-8"))
            state = WeatherState(
                code=data["code"], condition=data["condition"],
                temp_c=data["temp_c"], wind=data.get("wind", 5),
                is_day=data.get("is_day", True),
                sunrise=_parse(data["sunrise"]) if data.get("sunrise") else None,
                sunset=_parse(data["sunset"]) if data.get("sunset") else None,
                fetched_at=data.get("fetched_at", 0), source="cache")
            state.hourly = [HourForecast(_parse(h["when"]), h["temp_c"], h["code"],
                                         h["condition"]) for h in data.get("hourly", [])]
            # A stale cache is still better than nothing, but mark it.
            if time.time() - state.fetched_at > 3600:
                state.source = "cache"
            return state
        except Exception:
            return None

    def _save_cache(self, state: WeatherState) -> None:
        try:
            CACHE.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "code": state.code, "condition": state.condition,
                "temp_c": state.temp_c, "wind": state.wind,
                "is_day": state.is_day, "fetched_at": state.fetched_at,
                "sunrise": state.sunrise.isoformat() if state.sunrise else None,
                "sunset": state.sunset.isoformat() if state.sunset else None,
                "hourly": [{"when": h.when.isoformat(), "temp_c": h.temp_c,
                            "code": h.code, "condition": h.condition}
                           for h in state.hourly[:48]],
            }
            CACHE.write_text(json.dumps(data, indent=1), encoding="utf-8")
        except Exception:
            pass

    # -- fetching -------------------------------------------------------
    def fetch(self) -> WeatherState | None:
        loc = self.locations.location
        try:
            r = requests.get(API, timeout=12, headers={"User-Agent": "aivillage/0.1"},
                             params={
                                 "latitude": loc.lat, "longitude": loc.lon,
                                 "current": "temperature_2m,weather_code,wind_speed_10m,is_day",
                                 "hourly": "temperature_2m,weather_code",
                                 "daily": "sunrise,sunset",
                                 "timezone": "auto", "forecast_days": 2,
                             })
            r.raise_for_status()
            data = r.json()
            cur = data.get("current", {})
            daily = data.get("daily", {})
            sun_up = _parse(daily["sunrise"][0]) if daily.get("sunrise") else None
            sun_down = _parse(daily["sunset"][0]) if daily.get("sunset") else None
            state = WeatherState(
                code=int(cur.get("weather_code", 0)),
                condition=wmo_condition(int(cur.get("weather_code", 0))),
                temp_c=float(cur.get("temperature_2m", 12)),
                wind=float(cur.get("wind_speed_10m", 5)),
                is_day=bool(cur.get("is_day", 1)),
                sunrise=sun_up, sunset=sun_down,
                fetched_at=time.time(), source="live")
            hourly = data.get("hourly", {})
            times = hourly.get("time", []) or []
            temps = hourly.get("temperature_2m", []) or []
            codes = hourly.get("weather_code", []) or []
            for i, when in enumerate(times[:48]):
                c = int(codes[i]) if i < len(codes) else 0
                state.hourly.append(HourForecast(_parse(when),
                                                 float(temps[i]) if i < len(temps) else 12.0,
                                                 c, wmo_condition(c)))
            self.state = state
            self._save_cache(state)
            self.last_error = ""
            return state
        except Exception as exc:
            self.last_error = str(exc)[:120]
            return None

    def _loop(self) -> None:
        interval = max(300, int(self.config.get("reality.weather_refresh_s", 900)))
        while not self._stop.is_set():
            self.fetch()
            self._stop.wait(interval)

    def start(self) -> None:
        if not self.config.get("reality.weather_enabled", True):
            return
        self._thread = threading.Thread(target=self._loop, daemon=True, name="weather")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    # -- access ---------------------------------------------------------
    def current(self, now: datetime | None = None) -> WeatherState:
        if self.state.source == "sim" or not self.config.get("reality.weather_enabled", True):
            lat = self.locations.location.lat
            return seasonal_state(lat, now or datetime.now())
        return self.state

    def forecast_in(self, hours: float, now: datetime | None = None) -> HourForecast | None:
        now = now or datetime.now()
        target = now + timedelta(hours=hours)
        best = None
        for h in self.state.hourly:
            if best is None or abs((h.when - target).total_seconds()) < \
                    abs((best.when - target).total_seconds()):
                best = h
        return best

    def sun_times(self, now: datetime | None = None) -> tuple[datetime, datetime]:
        now = now or datetime.now()
        st = self.state
        if st.sunrise and st.sunset and st.sunrise.date() == now.date():
            return st.sunrise, st.sunset
        return self.sun_times_for(now)

    def sun_times_for(self, day: datetime) -> tuple[datetime, datetime]:
        for h in (self.state.sunrise, self.state.sunset):
            if h and h.date() == day.date():
                return self.state.sunrise, self.state.sunset
        return _approx_sun(day, self.locations.location.lat)
