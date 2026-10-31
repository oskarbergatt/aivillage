"""Needs decay and mood."""
from __future__ import annotations

from dataclasses import dataclass


def clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


@dataclass
class Needs:
    hunger: float = 70.0      # 100 = fed
    energy: float = 85.0
    social: float = 55.0
    fun: float = 55.0

    def decay(self, minutes: float, activity: str, diligence: float = 0.5) -> None:
        h = minutes / 60.0
        rate = {"sleep": 0.0, "work": 1.25, "walk": 1.0, "meal": 0.6,
                "free": 0.9, "idle": 0.7, "talk": 0.8, "assembly": 0.9,
                "school": 0.7, "play": 1.15}.get(activity, 1.0)
        self.hunger = clamp(self.hunger - 4.4 * h * rate)
        self.fun = clamp(self.fun - 3.6 * h * rate)
        self.social = clamp(self.social - 4.0 * h * (0.6 + diligence * 0.8))
        if activity == "sleep":
            self.energy = clamp(self.energy + 11.0 * h)
        else:
            self.energy = clamp(self.energy - 4.8 * h * rate)

    def eat(self, amount: float = 42.0) -> None:
        self.hunger = clamp(self.hunger + amount)

    def rest(self, minutes: float) -> None:
        self.energy = clamp(self.energy + minutes * 0.22)

    def socialise(self, amount: float = 18.0) -> None:
        self.social = clamp(self.social + amount)
        self.fun = clamp(self.fun + amount * 0.5)

    def mood(self, grumpiness: float = 0.4) -> float:
        base = (self.hunger * 0.32 + self.energy * 0.3 +
                self.social * 0.2 + self.fun * 0.18)
        return clamp(base - (grumpiness - 0.4) * 18.0 - 6.0)

    def mood_word(self) -> str:
        m = self.mood()
        if m > 78:
            return "bright"
        if m > 62:
            return "steady"
        if m > 45:
            return "tired"
        if m > 30:
            return "sour"
        return "miserable"

    @property
    def starving(self) -> bool:
        return self.hunger < 15

    @property
    def exhausted(self) -> bool:
        return self.energy < 12
