"""Real-world calendar: holidays, festivals and weekday routines.

The village mirrors the player's date, so the calendar is computed from the
real day rather than stored.  Keys are translated through the locale tables;
the module itself never emits display text.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

# Fixed-date observances.  We include the widely observed German holidays plus
# a few village-appropriate seasonal festivals.  Regional one-off holidays are
# deliberately left out: guessing the player's Bundesland would be worse than
# ignoring it.
FIXED = {
    (1, 1): "new_year",
    (1, 6): "epiphany",
    (2, 14): "valentine",
    (3, 8): "womens_day",
    (4, 30): "walpurgis",
    (5, 1): "may_day",
    (6, 21): "summer_solstice",
    (8, 15): "assumption",
    (9, 21): "harvest_festival",
    (9, 22): "autumn_equinox",
    (10, 3): "unity_day",
    (10, 31): "reformation_day",
    (11, 1): "all_saints",
    (11, 11): "martins_day",
    (12, 6): "st_nicholas",
    (12, 21): "winter_solstice",
    (12, 24): "christmas_eve",
    (12, 25): "christmas",
    (12, 26): "second_christmas",
    (12, 31): "new_years_eve",
}

# Days that close the workshops and send everyone into the square.  A few fixed
# observances are quietly working days (Valentine's, Epiphany in most states),
# so they are excluded.
REST_DAYS = {
    "new_year", "may_day", "unity_day", "reformation_day", "all_saints",
    "christmas_eve", "christmas", "second_christmas", "new_years_eve",
    "good_friday", "easter_monday", "ascension", "whit_monday",
}

# Festivals do not stop work entirely: the village gathers at noon, eats, and
# goes back to a short day.
FESTIVALS = {"harvest_festival", "summer_solstice", "winter_solstice",
             "walpurgis", "martins_day", "st_nicholas", "autumn_equinox"}

MOON_NAMES = ("new", "waxing_crescent", "first_quarter", "waxing_gibbous",
              "full", "waning_gibbous", "last_quarter", "waning_crescent")


def easter_sunday(year: int) -> date:
    """Anonymous Gregorian computus (Meeus/Jones/Butcher)."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def _movable(year: int) -> dict[date, str]:
    e = easter_sunday(year)
    return {
        e - timedelta(days=2): "good_friday",
        e: "easter",
        e + timedelta(days=1): "easter_monday",
        e + timedelta(days=39): "ascension",
        e + timedelta(days=49): "whit_sunday",
        e + timedelta(days=50): "whit_monday",
        e + timedelta(days=60): "corpus_christi",
    }


def holiday_key(when: date | datetime) -> str:
    """Return the holiday key for a date, or '' when it is an ordinary day."""
    day = when.date() if isinstance(when, datetime) else when
    key = FIXED.get((day.month, day.day), "")
    if key:
        return key
    return _movable(day.year).get(day, "")


def is_rest_day(when: date | datetime) -> bool:
    day = when.date() if isinstance(when, datetime) else when
    if day.weekday() == 6:            # Sunday
        return True
    return holiday_key(day) in REST_DAYS


def festival_key(when: date | datetime) -> str:
    key = holiday_key(when)
    return key if key in FESTIVALS else ""


def routine_key(when: date | datetime) -> str:
    """The weekday routine that overrides an ordinary schedule."""
    day = when.date() if isinstance(when, datetime) else when
    if holiday_key(day) in REST_DAYS:
        return "holiday"
    if festival_key(day):
        return "festival"
    if day.weekday() == 5:
        return "market"
    if day.weekday() == 0:
        return "repairs"
    return ""


def special_day(when: date | datetime) -> tuple[str, str]:
    """('holiday'|'festival'|'', key) for chronicles and toasts."""
    key = holiday_key(when)
    if key in REST_DAYS:
        return "holiday", key
    if key in FESTIVALS:
        return "festival", key
    return "", key


def moon_phase(when: date | datetime) -> str:
    """Approximate lunar phase from a known new moon (2000-01-06 18:14 UTC)."""
    day = when.date() if isinstance(when, datetime) else when
    # Days since the reference new moon; the synodic month is 29.530588853 d.
    ref = date(2000, 1, 6)
    days = (day - ref).days % 29.530588853
    index = int((days / 29.530588853) * 8 + 0.5) % 8
    return MOON_NAMES[index]


def calendar_line_key(when: date | datetime) -> str:
    kind, key = special_day(when)
    if kind:
        return key
    routine = routine_key(when)
    return routine


@dataclass
class DayInfo:
    date: date
    holiday: str = ""
    festival: str = ""
    routine: str = ""
    rest: bool = False
    moon: str = "new"

    @property
    def label_key(self) -> str:
        return self.holiday or self.festival or self.routine


def day_info(when: date | datetime) -> DayInfo:
    day = when.date() if isinstance(when, datetime) else when
    kind, key = special_day(day)
    return DayInfo(
        date=day,
        holiday=key if kind == "holiday" else "",
        festival=key if kind == "festival" else "",
        routine=routine_key(day),
        rest=is_rest_day(day),
        moon=moon_phase(day),
    )
