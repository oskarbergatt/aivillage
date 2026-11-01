"""Locales, weather mapping and clock arithmetic."""
from __future__ import annotations

from datetime import datetime

from aivillage.config import Config
from aivillage.i18n import I18n
from aivillage.agents.jobs import JOBS
from aivillage.reality.clock import SimClock, SEASONS
from aivillage.reality.geo import Location
from aivillage.reality.weather import (WeatherState, _approx_sun,
                                       seasonal_state, wmo_condition)


class FakeWeather:
    def __init__(self, sunrise=(7, 30), sunset=(17, 0)):
        self.sunrise = sunrise
        self.sunset = sunset

    def sun_times_for(self, day):
        s = day.replace(hour=self.sunrise[0], minute=self.sunrise[1], second=0)
        e = day.replace(hour=self.sunset[0], minute=self.sunset[1], second=0)
        return s, e


def test_locale_tables_have_the_same_keys():
    i18n = I18n()
    en = set(i18n._tables["en"])
    de = set(i18n._tables["de"])
    assert en == de, f"missing in de: {sorted(en - de)} / extra: {sorted(de - en)}"


def test_all_used_keys_exist():
    i18n = I18n()
    needed = ["ui.live", "ui.paused", "ui.chronicle", "ui.saved"]
    for key in needed:
        for lang in ("en", "de"):
            i18n.set_language(lang)
            assert i18n.t(key) != key
    for key in ("weather.clear", "weather.storm", "season.winter",
                "weekday.0", "weekday.6", "job.farmer", "state.work",
                "event.arrived", "event.news", "event.newday"):
        for lang in ("en", "de"):
            i18n.set_language(lang)
            assert i18n.t(key) != key, (lang, key)


def test_job_task_labels_are_translated_and_unknown_text_is_preserved():
    i18n = I18n("de")
    for job in JOBS.values():
        for task in job.tasks:
            assert i18n.task(task) != task, task
    assert i18n.task("model-written sentence") == "model-written sentence"


def test_language_toggle_and_format():
    i18n = I18n()
    i18n.set_language("en")
    assert i18n.t("ui.language") == "language"
    assert i18n.toggle() == "de"
    assert i18n.t("ui.language") == "Sprache"
    assert "Anna" in i18n.t("event.arrived", name="Anna")


def test_wmo_mapping():
    cases = {0: "clear", 2: "partly", 3: "overcast", 45: "fog",
             53: "drizzle", 63: "rain", 73: "snow", 81: "showers",
             95: "storm", 1234: "clear"}
    for code, expected in cases.items():
        assert wmo_condition(code) == expected


def test_seasonal_weather_is_plausible():
    now = datetime(2026, 1, 15, 12, 0)
    state = seasonal_state(54.09, now)
    assert -30 < state.temp_c < 40
    assert state.condition in ("clear", "partly", "overcast", "fog",
                               "drizzle", "rain", "snow", "showers", "storm")
    assert state.sunrise is not None and state.sunset is not None
    assert state.sunrise < state.sunset


def test_sun_times_fall_back_to_approximation():
    sunrise, sunset = _approx_sun(datetime(2026, 6, 21, 12), 54.09)
    assert sunrise < sunset
    assert sunrise.hour < 6
    assert (sunset.hour, sunset.minute) >= (20, 0)


def test_clock_phases_and_seasons(config):
    weather = FakeWeather()
    clock = SimClock(config, weather)
    clock.live = False
    clock.paused = False
    day = datetime(2026, 10, 30)
    clock._sim = day.replace(hour=12)
    assert clock.phase() == "day"
    assert clock.daylight() > 0.8
    assert clock.season() == "autumn"
    assert clock.weekday() == 4
    clock._sim = day.replace(hour=23)
    assert clock.phase() == "night"
    assert clock.daylight() == 0.0
    clock._sim = day.replace(hour=7, minute=10)
    assert clock.phase() == "dawn"


def test_clock_speed_and_live_return(config):
    clock = SimClock(config, FakeWeather())
    clock.set_speed(4)
    assert clock.sim_speed == 4 and not clock.live
    before = clock.now
    clock.update(10.0)
    assert (clock.now - before).total_seconds() == 40
    clock.return_to_live()
    assert clock.is_live
    clock.set_speed(1)
    assert clock.live


def test_clock_never_moves_when_paused(config):
    clock = SimClock(config, FakeWeather())
    clock.live = False
    clock.paused = True
    before = clock.now
    clock.update(30)
    assert clock.now == before


def test_sunday_override_makes_a_day_off(config):
    from aivillage.agents.brain import block_at
    from aivillage.agents.roster import BY_KEY
    sunday = datetime(2026, 11, 1, 10, 0)
    assert block_at(BY_KEY["pip"], sunday) == "free"
    monday = datetime(2026, 11, 2, 10, 0)
    assert block_at(BY_KEY["pip"], monday) == "work"


def test_location_labels():
    loc = Location(54.0887, 12.1405, "Rostock", "Germany", "Europe/Berlin")
    assert loc.label == "Rostock, Germany"
    assert Location(1.0, 2.0, "", "", "UTC").label.startswith("1.00")
