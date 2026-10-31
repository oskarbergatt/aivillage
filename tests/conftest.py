"""Shared test setup: headless pygame, no audio, no network side effects."""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame  # noqa: E402
import pytest  # noqa: E402

from aivillage.config import Config  # noqa: E402
from aivillage.reality.weather import WeatherState, _approx_sun  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _pygame():
    pygame.init()
    pygame.font.init()
    yield
    pygame.quit()


@pytest.fixture(autouse=True)
def _fresh_pygame():
    """VillageApp.shutdown() calls pygame.quit(); re-arm before each test."""
    if not pygame.get_init():
        pygame.init()
    if not pygame.font.get_init():
        pygame.font.init()
    from aivillage.assets import font
    font.clear_cache()
    yield


@pytest.fixture()
def config(tmp_path):
    cfg = Config(tmp_path / "config.toml")
    cfg.set("llm.provider", "mock")
    cfg.set("news.enabled", False)
    cfg.set("voice.enabled", False)
    cfg.set("general.language", "en")
    return cfg


@pytest.fixture()
def app(config, tmp_path, monkeypatch):
    from aivillage.app import VillageApp
    from aivillage.llm.client import LLMClient

    monkeypatch.setattr("aivillage.app.save_village", lambda *a, **k: True)
    monkeypatch.setattr("aivillage.app.make_llm", lambda cfg: LLMClient(cfg))
    application = VillageApp(config, new_game=True, seed=7)
    application.news.enabled = False
    # A fixed, ordinary Thursday: real-date holidays must not make CI flaky.
    from datetime import datetime
    fixed = datetime(2026, 10, 29, 10, 0)
    sunrise, sunset = _approx_sun(fixed, 54.09)
    application.weather_service.state = WeatherState(
        code=0, condition="clear", temp_c=15.0, wind=4.0, is_day=True,
        sunrise=sunrise, sunset=sunset, source="live")
    application.clock.live = False
    application.clock.sim_speed = 1
    application.clock.paused = False
    application.clock._sim = fixed
    application.current_day_key = fixed.strftime("%Y-%m-%d")
    yield application
    application.shutdown()
