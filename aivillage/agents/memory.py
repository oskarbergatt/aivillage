"""Memories and relationships."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Memory:
    text: str
    day: str = ""
    kind: str = "event"
    dispatch_id: str = ""


class MemoryBook:
    MAX = 28

    def __init__(self) -> None:
        self.entries: list[Memory] = []
        self.affinity: dict[str, float] = {}

    def add(self, text: str, day: str = "", kind: str = "event",
            dispatch_id: str = "") -> None:
        self.entries.append(Memory(text, day, kind, dispatch_id))
        if len(self.entries) > self.MAX:
            self.entries = self.entries[-self.MAX:]

    def recent(self, n: int = 6, kind: str | None = None) -> list[str]:
        pool = [m for m in self.entries if kind is None or m.kind == kind]
        return [m.text for m in pool[-n:]]

    def about(self, other_key: str) -> float:
        return self.affinity.get(other_key, 0.0)

    def adjust(self, other_key: str, delta: float) -> float:
        v = max(-1.0, min(1.0, self.affinity.get(other_key, 0.0) + delta))
        self.affinity[other_key] = v
        return v

    def relation_word(self, other_key: str) -> str:
        v = self.about(other_key)
        if v > 0.55:
            return "close friend"
        if v > 0.2:
            return "friendly"
        if v < -0.5:
            return "bitter rival"
        if v < -0.2:
            return "irritated by"
        return "acquainted"
