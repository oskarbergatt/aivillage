"""Tiny i18n layer. Runtime-switchable between en and de."""
from __future__ import annotations

import json
from typing import Any

from .config import LOCALE_DIR

_FALLBACK = {
    "app.title": "aivillage",
    "ui.day": "Day",
    "ui.live": "LIVE",
    "ui.paused": "PAUSED",
    "ui.ff": "FAST-FORWARD",
    "ui.return_live": "Return to live",
    "ui.sleep_until_dawn": "Sleep until dawn",
    "ui.wood": "wood",
    "ui.stone": "stone",
    "ui.food": "food",
    "ui.coin": "coin",
    "ui.mute": "mute",
    "ui.speed": "speed",
    "ui.chronicle": "Chronicle",
    "ui.close": "close",
    "ui.thought": "thinking",
    "ui.talking": "talking",
    "ui.working": "working",
    "ui.free_time": "free time",
    "ui.sleeping": "sleeping",
    "ui.eating": "eating",
    "ui.walking": "walking",
    "ui.idle": "idle",
    "ui.assembly": "gathered",
    "ui.needs": "Needs",
    "ui.hunger": "hunger",
    "ui.energy": "energy",
    "ui.social": "social",
    "ui.fun": "fun",
    "ui.traits": "Traits",
    "ui.curiosity": "curiosity",
    "ui.sociability": "sociability",
    "ui.diligence": "diligence",
    "ui.grumpiness": "grumpiness",
    "ui.creativity": "creativity",
    "ui.relationships": "Relationships",
    "ui.job": "Job",
    "ui.task": "Task",
    "ui.queue": "Today",
    "ui.chat_hint": "Press T to talk to {name}",
    "ui.chat_placeholder": "Say something…",
    "ui.no_llm": "No language model configured",
    "ui.no_llm_hint": "Run Ollama or add an API key in .env, then restart.",
    "ui.setup": "LLM setup",
    "ui.weather": "Weather",
    "ui.offline_weather": "offline weather",
    "ui.sources": "dispatches",
    "ui.no_news": "The roads are quiet. No dispatches yet.",
    "ui.diary": "Diary",
    "ui.speaking": "speaking",
    "ui.night": "night",
    "ui.hint_pan": "WASD / drag to pan · wheel to zoom · click a villager",
    "ui.news_from": "from",
    "ui.away": "away",
    "ui.arriving": "arriving",
    "ui.leave": "leaves",
    "ui.language": "language",
    "ui.more": "more",
    "ui.select_lang": "F2 language · C chronicle · M mute · S save",
    "job.blacksmith": "Blacksmith",
    "job.farmer": "Farmer",
    "job.artist": "Artist",
    "job.baker": "Baker",
    "job.herbalist": "Herbalist",
    "job.builder": "Builder",
    "job.fisher": "Fisher",
    "job.forager": "Forager",
    "state.work": "working",
    "state.free": "free time",
    "state.sleep": "sleeping",
    "state.meal": "eating",
    "state.break": "taking a break",
    "state.walk": "walking",
    "state.idle": "idle",
    "state.talk": "talking",
    "state.shop": "at the market",
    "weather.clear": "clear",
    "weather.partly": "partly cloudy",
    "weather.overcast": "overcast",
    "weather.fog": "fog",
    "weather.drizzle": "drizzle",
    "weather.rain": "rain",
    "weather.snow": "snow",
    "weather.showers": "showers",
    "weather.storm": "thunderstorm",
    "season.winter": "winter",
    "season.spring": "spring",
    "season.summer": "summer",
    "season.autumn": "autumn",
    "weekday.0": "Monday",
    "weekday.1": "Tuesday",
    "weekday.2": "Wednesday",
    "weekday.3": "Thursday",
    "weekday.4": "Friday",
    "weekday.5": "Saturday",
    "weekday.6": "Sunday",
}


class I18n:
    def __init__(self, language: str = "en"):
        self.language = language
        self._tables: dict[str, dict[str, str]] = {}
        for lang in ("en", "de"):
            path = LOCALE_DIR / f"{lang}.json"
            table = {}
            if path.exists():
                try:
                    table = json.loads(path.read_text(encoding="utf-8"))
                except Exception:
                    table = {}
            self._tables[lang] = table

    def set_language(self, language: str) -> None:
        if language in self._tables:
            self.language = language

    def toggle(self) -> str:
        self.language = "de" if self.language == "en" else "en"
        return self.language

    def t(self, key: str, **kwargs: Any) -> str:
        value = self._tables.get(self.language, {}).get(key)
        if value is None:
            value = _FALLBACK.get(key, key)
        if kwargs:
            try:
                return value.format(**kwargs)
            except Exception:
                return value
        return value

    # convenience for things like state names
    def state(self, name: str) -> str:
        return self.t(f"state.{name}")

    def job(self, name: str) -> str:
        return self.t(f"job.{name}")

    def weather(self, name: str) -> str:
        return self.t(f"weather.{name}")


I18N = I18n()
