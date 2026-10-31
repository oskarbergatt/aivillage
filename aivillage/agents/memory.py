"""Memories, persistent conversation threads and relationship stages."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Memory:
    text: str
    day: str = ""
    kind: str = "event"
    dispatch_id: str = ""


@dataclass
class ThreadLine:
    speaker: str          # "you" | "them" | a villager's name
    text: str
    day: str = ""


STAGES = (
    (-0.50, "rival"),
    (-0.15, "wary"),
    (0.15, "acquaintance"),
    (0.45, "friendly"),
    (0.75, "friend"),
    (1.01, "close"),
)

PROMPT_WORDS = {
    "rival": "bitter rival",
    "wary": "irritated by",
    "acquaintance": "acquainted",
    "friendly": "friendly",
    "friend": "close friend",
    "close": "very close friend",
}


def relation_stage(value: float) -> str:
    for threshold, stage in STAGES:
        if value < threshold:
            return stage
    return "close"


class MemoryBook:
    MAX = 28
    MAX_THREAD = 24

    def __init__(self) -> None:
        self.entries: list[Memory] = []
        self.affinity: dict[str, float] = {}
        self.thread: list[ThreadLine] = []
        self.social_threads: dict[str, list[ThreadLine]] = {}

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

    def stage(self, other_key: str) -> str:
        return relation_stage(self.about(other_key))

    def relation_word(self, other_key: str) -> str:
        return PROMPT_WORDS.get(self.stage(other_key), "acquainted")

    # -- persistent dialogue --------------------------------------------
    def add_thread(self, speaker: str, text: str, day: str = "") -> None:
        text = " ".join(str(text or "").split())
        if not text:
            return
        self.thread.append(ThreadLine(speaker, text[:400], day))
        if len(self.thread) > self.MAX_THREAD:
            self.thread = self.thread[-self.MAX_THREAD:]

    def thread_recent(self, n: int = 8) -> list[ThreadLine]:
        return self.thread[-n:]

    def thread_prompt(self, n: int = 8) -> list[str]:
        return [f"{line.speaker}: {line.text}" for line in self.thread[-n:]]

    def add_social_thread(self, other_key: str, speaker: str, text: str, day: str = "") -> None:
        text = " ".join(str(text or "").split())[:240]
        if not other_key or not text:
            return
        lines = self.social_threads.setdefault(other_key, [])
        lines.append(ThreadLine(speaker, text, day))
        del lines[:-self.MAX_THREAD]

    def social_prompt(self, other_key: str, n: int = 8) -> list[str]:
        return [f"{line.speaker}: {line.text}" for line in self.social_threads.get(other_key, [])[-n:]]
