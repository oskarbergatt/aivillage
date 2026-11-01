"""Villager agents: schedule, priority ladder, movement, work, chat."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from functools import lru_cache

from ..assets import sprites
from ..reality.calendar import is_rest_day, routine_key
from ..world.pathfinding import astar
from .animator import Animator
from .jobs import JOBS, job_for
from .memory import MemoryBook
from .needs import Needs
from .persona import Persona

TILE = 16

# Kept as derived views so older call sites keep working, while the registry
# stays the single source of truth.
TASKS = {key: list(job.tasks) for key, job in JOBS.items()}
TOOLS = {key: job.tool for key, job in JOBS.items() if job.tool}
YIELD = {key: (job.resource, job.amount) for key, job in JOBS.items()
         if job.resource}


@lru_cache(maxsize=2048)
def _tool_sprite(skin: int, hair: int, cloth: int, hair_style: str, hat: str,
                 version: int, facing: int, frame: int, apron: bool, beard: bool,
                 tool: str) -> "sprites.pygame.Surface":
    base = sprites.villager(skin, hair, cloth, hair_style, hat, version,
                            facing, frame, apron, beard)
    return sprites.villager_with_tool(base, tool)


@dataclass
class Bubble:
    text: str
    timer: float = 4.5
    pending: bool = False
    kind: str = "speech"
    color: tuple[int, int, int] = (240, 232, 210)


def block_at(persona: Persona, when) -> str:
    minute = when.hour * 60 + when.minute
    routine = routine_key(when)
    if not persona.nocturnal:
        # Sundays keep a short village workday, even when a fixed holiday
        # (such as All Saints' Day) falls on the same date.
        if when.weekday() == 6:
            if 7 * 60 <= minute < 22 * 60:
                if not persona.is_child and 10 * 60 <= minute < 14 * 60:
                    return "work"
                return "free"
            return "sleep"
        if routine in ("holiday", "festival") or is_rest_day(when):
            return "free" if 7 * 60 <= minute < 22 * 60 else "sleep"
        if not persona.is_child:
            if routine == "market" and 9 * 60 <= minute < 14 * 60:
                return "market"
            if routine == "repairs" and persona.job == "builder" \
                    and 9 * 60 <= minute < 12 * 60:
                return "repair"
    best = "idle"
    for start_h, end_h, kind in persona.schedule:
        start = int(start_h * 60)
        end = int(end_h * 60)
        if end <= start:
            end += 1440
        for offset in (0, 1440):
            m = minute + offset
            if start <= m < end:
                return kind
    return best


