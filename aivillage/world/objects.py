"""World objects: buildings, props, crop plots, the town hall site."""
from __future__ import annotations

from dataclasses import dataclass, field

import pygame

from ..assets import sprites


@dataclass
class Obj:
    kind: str
    x: int                       # sprite pixel position (top-left)
    y: int
    sprite: pygame.Surface
    w: int = 1                   # footprint in tiles
    h: int = 1
    solid: bool = True
    night: pygame.Surface | None = None
    sort_y: int | None = None
    data: dict = field(default_factory=dict)

    @property
    def bottom(self) -> int:
        if self.sort_y is not None:
            return self.sort_y
        return self.y + self.sprite.get_height()

    @property
    def footprint(self) -> pygame.Rect:
        """Footprint in tiles, derived from where the sprite's base sits."""
        return pygame.Rect(self.x + 8, self.y + self.sprite.get_height() - self.h * 16,
                           self.w * 16, self.h * 16)

    def image(self, night: bool) -> pygame.Surface:
        if night and self.night is not None:
            return self.night
        return self.sprite


@dataclass
class CropPlot:
    tx: int
    ty: int
    stage: int = 0
    growth: float = 0.0
    watered: float = 0.0

    @property
    def ripe(self) -> bool:
        return self.stage >= 3

    def advance(self, hours: float, raining: bool) -> None:
        water = 1.0 if raining else (1.0 if self.watered > 0 else 0.35)
        self.watered = max(0.0, self.watered - hours)
        self.growth += hours * water * 0.55
        thresholds = (5.0, 12.0, 20.0)
        stage = 0
        for i, t in enumerate(thresholds):
            if self.growth >= t:
                stage = i + 1
        self.stage = min(3, stage)


@dataclass
class BuildSite:
    tx: int
    ty: int
    w: int = 5
    h: int = 4
    progress: float = 0.0
    work: float = 0.0
    queue: list[str] = field(default_factory=lambda: [
        "foundation", "walls", "roof", "bell"])
    active_index: int = 0
    completed: list[str] = field(default_factory=list)

    @property
    def active(self) -> str:
        if 0 <= self.active_index < len(self.queue):
            return self.queue[self.active_index]
        return ""

    @property
    def all_done(self) -> bool:
        return self.active_index >= len(self.queue)

    @property
    def total_progress(self) -> float:
        if not self.queue:
            return 1.0
        done = len(self.completed)
        return min(1.0, (done + self.progress) / len(self.queue))

    def contribute(self, amount: float) -> bool:
        """Returns True when the current stage is finished."""
        if self.progress >= 1.0 or self.all_done:
            return False
        self.progress = min(1.0, self.progress + amount)
        return self.progress >= 1.0

    def next_stage(self) -> str:
        """Mark the active stage complete and return the next stage key."""
        if self.all_done:
            return ""
        current = self.active
        if current and current not in self.completed:
            self.completed.append(current)
        self.active_index += 1
        self.progress = 0.0
        self.work = 0.0
        return self.active


def make_house_obj(name: str, tx: int, ty: int, w: int, h: int, roof: str,
                   seed: int, shop: bool = False, wall=None) -> Obj:
    kwargs = dict(w_tiles=w, h_tiles=h, roof_key=roof, seed=seed, shop_sign=shop)
    if wall is not None:
        kwargs["wall"] = wall
    day, night = sprites.house(**kwargs)
    obj = Obj(kind="house", x=tx * 16 - 8, y=ty * 16 - 28, sprite=day,
              w=w, h=h, solid=True, night=night,
              sort_y=(ty + h) * 16 + 2, data={"name": name, "tx": tx, "ty": ty})
    return obj
