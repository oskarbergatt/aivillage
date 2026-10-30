"""The village clock: it *is* the player's clock unless they fast-forward."""
from __future__ import annotations

from datetime import datetime, timedelta


SEASONS = {12: "winter", 1: "winter", 2: "winter",
           3: "spring", 4: "spring", 5: "spring",
           6: "summer", 7: "summer", 8: "summer",
           9: "autumn", 10: "autumn", 11: "autumn"}


class SimClock:
    SPEEDS = (1, 2, 4, 8)

    def __init__(self, config, weather):
        self.config = config
        self.weather = weather
        self.live = str(config.get("reality.time_mode", "live")) == "live"
        self.sim_speed = 1
        self.paused = False
        self._sim = datetime.now()
        self._last_real = datetime.now()
        self._last_sim = self._sim

    # -- ticking --------------------------------------------------------
    def update(self, dt: float) -> None:
        if self.paused:
            return
        if self.live:
            now = datetime.now()
            # if the machine slept, jump cleanly instead of drifting
            self._sim = now
        else:
            self._sim += timedelta(seconds=dt * self.sim_speed)

    @property
    def now(self) -> datetime:
        return self._sim

    @property
    def real_now(self) -> datetime:
        return datetime.now()

    @property
    def is_live(self) -> bool:
        return self.live and self.sim_speed == 1

    def set_speed(self, speed: int) -> None:
        if speed <= 1:
            self.live = True
            self.sim_speed = 1
            self.paused = False
            self._sim = datetime.now()
            return
        self.sim_speed = max(2, min(8, speed))
        self.live = False
        self.paused = False

    def toggle_pause(self) -> None:
        self.paused = not self.paused

    def return_to_live(self) -> None:
        self.live = True
        self.sim_speed = 1
        self.paused = False
        self._sim = datetime.now()

    def sleep_until_dawn(self) -> None:
        sunrise, _ = self.weather.sun_times_for(self._sim)
        if sunrise <= self._sim:
            sunrise, _ = self.weather.sun_times_for(self._sim + timedelta(days=1))
        self.live = False
        self.sim_speed = 1
        self.paused = False
        self._sim = sunrise + timedelta(minutes=8)

    def skip(self, minutes: float) -> None:
        self._sim += timedelta(minutes=minutes)

    # -- time of day ----------------------------------------------------
    def sun_times(self) -> tuple[datetime, datetime]:
        return self.weather.sun_times_for(self._sim)

    def phase(self) -> str:
        sunrise, sunset = self.sun_times()
        t = self._sim
        dawn_lo = sunrise - timedelta(minutes=50)
        dawn_hi = sunrise + timedelta(minutes=55)
        dusk_lo = sunset - timedelta(minutes=60)
        dusk_hi = sunset + timedelta(minutes=40)
        if dawn_lo <= t < dawn_hi:
            return "dawn"
        if dawn_hi <= t < dusk_lo:
            return "day"
        if dusk_lo <= t < dusk_hi:
            return "dusk"
        return "night"

    def daylight(self) -> float:
        """0 at deep night, 1 at noon — used by the tint pass."""
        sunrise, sunset = self.sun_times()
        t = self._sim
        if t < sunrise - timedelta(minutes=50) or t > sunset + timedelta(minutes=40):
            return 0.0
        if sunrise <= t <= sunset:
            noon = sunrise + (sunset - sunrise) / 2
            span = max(1.0, (sunset - sunrise).total_seconds() / 2)
            dist = abs((t - noon).total_seconds()) / span
            return 0.55 + 0.45 * (1 - dist)
        if t < sunrise:
            f = (t - (sunrise - timedelta(minutes=50))).total_seconds() / 3000
            return max(0.0, min(0.55, f * 0.55))
        f = 1 - (t - sunset).total_seconds() / 2400
        return max(0.0, min(0.55, f * 0.55))

    def is_night(self) -> bool:
        return self.phase() == "night"

    def season(self) -> str:
        return SEASONS.get(self._sim.month, "autumn")

    def weekday(self) -> int:
        return self._sim.weekday()

    def clock_text(self) -> str:
        return self._sim.strftime("%H:%M")

    def date_text(self) -> str:
        return self._sim.strftime("%d %b").lstrip("0")
