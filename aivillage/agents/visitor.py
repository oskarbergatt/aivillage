"""Travellers: procedurally generated strangers who carry the news."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass

from ..assets import sprites
from ..world.pathfinding import astar

TILE = 16

FIRST = ["Corbin", "Tilda", "Milo", "Yara", "Osric", "Nell", "Fen", "Rook", "Isa",
         "Perrin", "Lark", "Soren", "Maud", "Elias", "Bryn", "Odile", "Tam", "Wren"]
LAST = ["Ashdown", "Vell", "Crowther", "Mills", "Harrow", "Fenwick", "Barrow",
        "Quill", "Stane", "Moss", "Pike", "Thorne", "Gale", "Bramwell"]
TRADES = ["cloth peddler", "salt merchant", "map seller", "seed trader",
          "tin smith", "letter carrier", "storyteller", "cheese monger",
          "tool sharpener", "book binder", "rope seller", "dye trader"]
ORIGINS = ["the salt flats", "the northern mills", "the city across the water",
           "the high vineyards", "the old quarry towns", "the river delta",
           "the fog coast", "the eastern steppes", "the pine road"]
HATS = ["", "straw", "cap", "hood"]


@dataclass
class Dispatch:
    headline: str
    tone: str = "neutral"
    topic: str = "world"
    original: str = ""
    source: str = ""
    url: str = ""
    item_id: str = ""
    day: str = ""

    @property
    def colour(self):
        return {"good": (140, 200, 130), "bad": (214, 130, 120),
                "strange": (190, 160, 226)}.get(self.tone, (232, 226, 208))


class Visitor:
    def __init__(self, rng: random.Random, world, dispatch: Dispatch | None = None):
        self.rng = rng
        self.world = world
        self.dispatch = dispatch
        self.name = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
        self.trade = rng.choice(TRADES)
        self.origin = rng.choice(ORIGINS)
        self.skin = rng.randrange(0, 5)
        self.hair = rng.randrange(0, 6)
        self.cloth = rng.randrange(0, 8)
        self.hair_style = rng.choice(["short", "long", "bun", "wild"])
        self.hat = rng.choice(HATS)
        self.version = rng.randrange(0, 50)
        self.apron = rng.random() < 0.4
        self.beard = rng.random() < 0.3
        self.facing = 2
        self.x, self.y = world.points.get("road", (30, 380))
        self.path: list[tuple[float, float]] = []
        self.state = "arriving"      # arriving | ringing | speaking | visiting | leaving | gone
        self.timer = 0.0
        self.frame = 0
        self.anim_t = 0.0
        self.bubble_text = ""
        self.bubble_timer = 0.0
        self.arrived_once = False
        self._go("plaza")

    # -- movement -------------------------------------------------------
    def _go(self, point: str) -> None:
        pt = self.world.points.get(point)
        if not pt:
            return
        start = (int(self.x // TILE), int(self.y // TILE))
        path = astar(start, (pt[0] // TILE, pt[1] // TILE), self.world.is_walkable)
        if path:
            self.path = [(p[0] * TILE + 8, p[1] * TILE + 8) for p in path[1:]]

    def _walk(self, dt: float) -> None:
        if not self.path:
            return
        speed = 27.0 * dt
        while self.path and speed > 0:
            tx, ty = self.path[0]
            dx, dy = tx - self.x, ty - self.y
            dist = math.hypot(dx, dy)
            if dist <= speed or dist < 0.5:
                self.x, self.y = tx, ty
                speed -= dist
                self.path.pop(0)
                continue
            self.x += dx / dist * speed
            self.y += dy / dist * speed
            if abs(dx) > abs(dy):
                self.facing = 2 if dx > 0 else 1
            speed = 0
        self.anim_t += dt * 8
        if self.anim_t >= 1:
            self.anim_t -= 1
            self.frame = (self.frame + 1) % 4

    # -- update ---------------------------------------------------------
    def update(self, dt: float, ctx) -> None:
        if dt <= 0 or self.state == "gone":
            return
        if self.bubble_timer > 0:
            self.bubble_timer -= dt

        if self.path:
            self._walk(dt)
            if not self.path and self.state == "arriving":
                self.state = "ringing"
                self.timer = 3.0
                self.facing = 0
                ctx.on_visitor_arrived(self)
            return

        self.timer -= dt
        if self.state == "ringing":
            if self.timer <= 0:
                self.state = "speaking"
                self.timer = max(9.0, min(22.0, len(self.bubble_text) * 0.09 + 7))
                self._speak(ctx)
        elif self.state == "speaking":
            if self.timer <= 0:
                self.state = "visiting"
                self.timer = 60 * 6
                self._go("market_front")
        elif self.state == "visiting":
            if self.timer <= 0:
                self.state = "leaving"
                self._go("road")
        elif self.state == "leaving":
            if not self.path:
                self.state = "gone"

    def _speak(self, ctx) -> None:
        if self.dispatch:
            self.bubble_text = self.dispatch.headline
        else:
            self.bubble_text = ctx.rumour_for(self)
        self.bubble_timer = max(10.0, len(self.bubble_text) * 0.09 + 5)
        ctx.speak_visitor(self)

    # -- draw -----------------------------------------------------------
    def sprite(self):
        return sprites.villager(self.skin, self.hair, self.cloth, self.hair_style,
                                self.hat, self.version, self.facing, self.frame,
                                self.apron, self.beard)

    @property
    def label(self) -> str:
        return f"{self.name} · {self.trade}"
