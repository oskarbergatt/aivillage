"""Villager agents: schedule, priority ladder, movement, work, chat."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from functools import lru_cache

from ..assets import sprites
from ..world.pathfinding import astar
from .animator import Animator
from .memory import MemoryBook
from .needs import Needs
from .persona import Persona

TILE = 16

TASKS = {
    "farmer": ["watering the plots", "pulling weeds", "harvesting turnips", "sowing seeds"],
    "builder": ["fitting a beam", "sawing planks", "hammering nails", "checking the level"],
    "baker": ["kneading dough", "watching the oven", "carrying loaves to market"],
    "blacksmith": ["heating iron", "hammering a blade", "quenching steel"],
    "fisher": ["casting the line", "waiting for a bite", "reeling in"],
    "artist": ["sketching the plaza", "mixing pigment", "painting the light"],
    "herbalist": ["gathering herbs", "sorting roots", "brewing a tincture"],
    "forager": ["searching the treeline", "collecting mushrooms", "checking snares"],
}

TOOLS = {"farmer": "hoe", "builder": "hammer", "baker": "basket",
         "blacksmith": "hammer", "fisher": "rod", "artist": "brush",
         "herbalist": "basket", "forager": "basket"}

YIELD = {"farmer": ("food", 3), "builder": ("progress", 0.05),
         "baker": ("food", 2), "blacksmith": ("coin", 2),
         "fisher": ("food", 1), "artist": ("coin", 1),
         "herbalist": ("food", 1), "forager": ("wood", 2)}


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
    if when.weekday() == 6 and not persona.nocturnal:
        return "free" if 7 * 60 <= minute < 22 * 60 else "sleep"
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


class Agent:
    def __init__(self, persona: Persona, world, rng: random.Random):
        self.persona = persona
        self.key = persona.key
        self.world = world
        self.rng = rng
        home = world.points.get(f"home_{persona.home}", world.points.get("plaza", (500, 360)))
        self.x = float(home[0])
        self.y = float(home[1])
        self.facing = 0
        self.path: list[tuple[float, float]] = []
        self.state = "idle"          # action state
        self.intent = "idle"         # schedule block
        self.block = ""
        self.target: str | None = None
        self.action_timer = 0.0
        self.needs = Needs(
            hunger=rng.uniform(55, 90),
            energy=rng.uniform(65, 95),
            social=rng.uniform(35, 70),
            fun=rng.uniform(35, 70),
        )
        self.memory = MemoryBook()
        self.animator = Animator()
        self.bubble: Bubble | None = None
        self.task_name = ""
        self.task_progress = 0.0
        self.task_time = rng.uniform(0, 90)
        self.partner: str | None = None
        self.talk_timer = 0.0
        self.napping = False
        self.eating = False
        self.selected = False
        self.home_point = f"home_{persona.home}"

    # -- basics ---------------------------------------------------------
    @property
    def name(self) -> str:
        return self.persona.name

    @property
    def moving(self) -> bool:
        return bool(self.path)

    def tile(self) -> tuple[int, int]:
        return int(self.x // TILE), int(self.y // TILE)

    def distance_to(self, other: "Agent") -> float:
        return math.hypot(self.x - other.x, self.y - other.y)

    def face_toward(self, px: float, py: float) -> None:
        dx, dy = px - self.x, py - self.y
        if abs(dx) > abs(dy):
            self.facing = 2 if dx > 0 else 1
        elif abs(dy) > 2:
            self.facing = 0 if dy > 0 else 3

    def say(self, text: str, seconds: float = 5.0, pending: bool = False,
            kind: str = "speech", color=(240, 232, 210)) -> None:
        self.bubble = Bubble(text, seconds, pending, kind, color)

    # -- movement -------------------------------------------------------
    def go_to_tile(self, tx: int, ty: int, exact: tuple[int, int] | None = None) -> bool:
        start = self.tile()
        path = astar(start, (tx, ty), self.world.is_walkable)
        if not path:
            self.path = []
            return False
        # A* retargets blocked goals to the nearest walkable tile; honour where
        # it actually arrived instead of teleporting into a wall or the pond.
        pts = [(p[0] * TILE + TILE // 2, p[1] * TILE + TILE // 2) for p in path[1:]]
        if exact and self.world.is_walkable(tx, ty):
            pts.append(exact)
        self.path = pts
        return True

    def go_to_point(self, name: str, jitter: int = 0) -> bool:
        pt = self.world.points.get(name)
        if pt is None:
            return False
        tx, ty = pt[0] // TILE, pt[1] // TILE
        if jitter:
            tx += self.rng.randint(-jitter, jitter)
            ty += self.rng.randint(-jitter, jitter)
        if not self.world.is_walkable(tx, ty):
            if not self.go_to_tile(tx, ty):
                return False
        else:
            self.go_to_tile(tx, ty, exact=pt)
        self.target = name
        return True

    def _walk(self, dt: float) -> None:
        if not self.path:
            return
        speed = 30.0 * (0.9 + self.persona.trait("diligence") * 0.25)
        budget = speed * dt
        while self.path and budget > 0:
            tx, ty = self.path[0]
            dx, dy = tx - self.x, ty - self.y
            dist = math.hypot(dx, dy)
            if dist <= budget or dist < 0.5:
                self.x, self.y = tx, ty
                budget -= dist
                self.path.pop(0)
                continue
            self.x += dx / dist * budget
            self.y += dy / dist * budget
            self.face_toward(tx, ty)
            budget = 0
        if self.path:
            nx, ny = self.path[0]
            self.face_toward(nx, ny)

    # -- schedule / decisions -------------------------------------------
    def _scheduled_block(self, clock) -> str:
        block = block_at(self.persona, clock.now)
        if self.napping:
            if self.needs.energy < 68:
                return "sleep"
            self.napping = False
        if self.eating and self.needs.hunger < 62:
            return "meal"
        self.eating = False
        if self.needs.energy < 9 and block != "sleep":
            self.napping = True
            return "sleep"
        if self.needs.hunger < 11 and block not in ("meal", "sleep"):
            self.eating = True
            return "meal"
        return block

    def _choose_intent(self, block: str, ctx) -> None:
        self.intent = block
        self.task_progress = 0.0
        weather = ctx.weather
        stormy = weather.condition in ("storm", "snow") or (
            weather.wet and self.persona.job not in ("baker", "blacksmith", "builder"))

        if block == "sleep":
            self.state = "walk"
            self.go_to_point(self.home_point, jitter=1)
            self.task_name = "heading home to sleep"
            return
        if block == "meal":
            self.state = "walk"
            target = "tavern_door" if self.rng.random() < 0.6 else "home_orin"
            self.go_to_point(target, jitter=1)
            self.task_name = "going to eat"
            return
        if block == "work":
            if stormy and self.persona.job not in ("builder",):
                self._choose_intent("break", ctx)
                return
            work = self.persona.work
            self.state = "walk"
            ok = self.go_to_point(work, jitter=1)
            if not ok:
                self.go_to_point("plaza", jitter=3)
            self.task_name = "heading to work"
            return
        if block == "break":
            self.state = "walk"
            self.go_to_point(self.persona.work, jitter=2)
            self.task_name = "taking shelter"
            return
        # free time
        self.state = "walk"
        self._new_wander_target(ctx)
        self.task_name = "looking for company"

    def _new_wander_target(self, ctx) -> None:
        r = self.rng.random()
        if r < 0.45:
            self.go_to_point("plaza", jitter=3)
        elif r < 0.65:
            friends = [a for a in ctx.agents if a is not self]
            if friends:
                other = self.rng.choice(friends)
                self.go_to_point(other.home_point, jitter=2)
        elif r < 0.8:
            self.go_to_point("market_front", jitter=2)
        else:
            town = self.world.points.get("plaza", (500, 360))
            tx, ty = self.world.random_walkable(self.rng, town[0] // TILE, town[1] // TILE, 6)
            self.go_to_tile(tx, ty)

    # -- main update ----------------------------------------------------
    def update(self, dt: float, ctx) -> None:
        """dt is already scaled by the time multiplier."""
        if dt <= 0:
            return
        if self.bubble:
            self.bubble.timer -= dt
            if self.bubble.timer <= 0:
                self.bubble = None

        if self.talk_timer > 0:
            self.talk_timer -= dt
            self.animator.update(dt, False, False)
            partner = ctx.agent_by_key.get(self.partner or "")
            if partner:
                self.face_toward(partner.x, partner.y)
            if self.talk_timer <= 0:
                self.partner = None
                self.state = "free"
                self.action_timer = 6
            return

        self.needs.decay(dt / 60.0, self.state if self.state not in ("walk",) else "walk",
                         self.persona.trait("diligence"))

        if self.state == "assembly":
            self.action_timer -= dt
            self.animator.update(dt, False, False)
            if self.action_timer <= 0:
                self.state = "free"
                self.action_timer = 2
            return

        block = self._scheduled_block(ctx.clock)
        if block != self.block:
            self.block = block
            self._choose_intent(block, ctx)

        if self.path:
            self.state = "walk" if self.state in ("walk", "idle", "free") else self.state
            self._walk(dt)
            self.animator.update(dt, True, False)
            if not self.path:
                self._arrived(ctx)
            return

        # arrived / stationary behaviour
        self.animator.update(dt, False, self.state == "work")
        if self.state == "work":
            self._work(dt, ctx)
        elif self.state == "sleep":
            pass
        elif self.state == "meal":
            self.action_timer -= dt
            if self.action_timer <= 0:
                self.state = "idle"
                self.action_timer = 5
        elif self.state in ("free", "break", "idle"):
            self.action_timer -= dt
            if self.action_timer <= 0:
                if self.block == "free":
                    self.state = "walk"
                    self._new_wander_target(ctx)
                else:
                    self.action_timer = self.rng.uniform(10, 25)
        # if we are supposed to be elsewhere, re-choose
        elif self.state == "walk":
            self._arrived(ctx)

    def _arrived(self, ctx) -> None:
        if self.intent == "sleep":
            self.state = "sleep"
            return
        if self.intent == "meal":
            self.state = "meal"
            self.needs.eat(58)
            self.action_timer = ctx.rng.uniform(4, 9) * 60
            if self.bubble is None and self.rng.random() < 0.35:
                line = ctx.flavour_meal(self)
                if line:
                    self.say(line, 4.0, color=(240, 224, 190))
            return
        if self.intent == "work":
            self.state = "work"
            self._pick_task()
            return
        if self.intent == "break":
            self.state = "break"
            self.action_timer = 30
            return
        self.state = "free"
        self.action_timer = ctx.rng.uniform(12, 35) * 60

    # -- work ------------------------------------------------------------
    def _pick_task(self) -> None:
        options = TASKS.get(self.persona.job, ["working"])
        self.task_name = self.rng.choice(options)
        self.task_progress = 0.0
        self.task_time = self.rng.uniform(2.0, 4.5) * 60

    def _work(self, dt: float, ctx) -> None:
        if not self.task_name:
            self._pick_task()
        if self.persona.job == "builder":
            self.task_progress += dt
        else:
            self.task_progress += dt
        if self.task_progress >= self.task_time:
            self._complete_task(ctx)
            self._pick_task()

    def _complete_task(self, ctx) -> None:
        job = self.persona.job
        resource, amount = YIELD.get(job, ("food", 1))
        if job == "farmer":
            ctx.tend_plot(self)
        if resource == "progress":
            ctx.build(amount, self)
        else:
            ctx.gain(resource, amount, self)
        self.needs.energy -= 1.0
        self.needs.fun += 1.0

    # -- social ----------------------------------------------------------
    def available_for_chat(self) -> bool:
        return (self.state in ("free", "meal", "break", "idle")
                and self.talk_timer <= 0 and not self.path
                and self.bubble is None)

    def begin_talk(self, other: "Agent", seconds: float) -> None:
        self.partner = other.key
        self.talk_timer = seconds
        self.state = "talk"
        self.face_toward(other.x, other.y)
        self.needs.socialise(6)

    def end_talk(self) -> None:
        self.talk_timer = 0
        self.partner = None
        self.state = "free"
        self.action_timer = 5

    def attend_assembly(self, speaker_x: float, speaker_y: float, seconds: float) -> None:
        self.state = "assembly"
        self.action_timer = seconds
        self.talk_timer = 0
        self.face_toward(speaker_x, speaker_y)
        self.path = []

    def sprite(self) -> "sprites.pygame.Surface":
        look = self.persona.look
        tool = TOOLS.get(self.persona.job) if self.state == "work" else None
        if tool:
            return _tool_sprite(look.skin, look.hair, look.cloth, look.hair_style,
                                look.hat, look.version, self.facing,
                                self.animator.frame, look.apron, look.beard, tool)
        return sprites.villager(
            look.skin, look.hair, look.cloth, look.hair_style, look.hat,
            look.version, self.facing, self.animator.frame,
            look.apron, look.beard)
