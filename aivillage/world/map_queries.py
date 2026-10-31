"""Extracted methods for World."""
from __future__ import annotations

from .map_shared import (
    GRASS,
    H,
    Obj,
    PATH,
    PLAZA,
    SAND,
    W,
    WATER,
    pygame,
    random,
    sprites,
)


class MapQueriesMixin:
    def _scatter_decor(self) -> None:
        rng = self.rng
        for _ in range(70):
            tx, ty = rng.randrange(0, W), rng.randrange(0, H)
            if not self.free_spot(tx, ty, 1):
                continue
            self.add(Obj("flower", tx * 16, ty * 16, sprites.flower_patch(rng.randrange(0, 8)),
                         solid=False, sort_y=ty * 16 + 15))
        for _ in range(22):
            tx, ty = rng.randrange(1, W - 1), rng.randrange(1, H - 1)
            if not self.free_spot(tx, ty, 1):
                continue
            rock = sprites.rock(rng.randrange(0, 8))
            self.add(Obj("rock", tx * 16 + 3, ty * 16 + 4, rock, solid=True,
                         sort_y=ty * 16 + 16))
        for _ in range(26):
            tx, ty = rng.randrange(1, W - 1), rng.randrange(1, H - 1)
            if not self.free_spot(tx, ty, 1):
                continue
            b = sprites.bush(rng.randrange(0, 8))
            self.add(Obj("bush", tx * 16, ty * 16 + 2, b, solid=False,
                         sort_y=ty * 16 + 14))

    def random_walkable(self, rng: random.Random, cx: int | None = None,
                        cy: int | None = None, radius: int = 8) -> tuple[int, int]:
        for _ in range(80):
            if cx is None:
                tx, ty = rng.randrange(1, W - 1), rng.randrange(1, H - 1)
            else:
                tx = cx + rng.randint(-radius, radius)
                ty = cy + rng.randint(-radius, radius)
            if self.is_walkable(tx, ty):
                return tx, ty
        return 31, 23

    def tile_surface(self, tx: int, ty: int, frame: int) -> pygame.Surface:
        kind = self.tiles[ty][tx]
        v = self.variant[ty][tx]
        if kind == GRASS:
            return sprites.tile_grass(v % 16)
        if kind == PATH:
            return sprites.tile_path(v % 8)
        if kind == PLAZA:
            return sprites.tile_plaza(v % 4)
        if kind == WATER:
            return sprites.tile_water(frame % 2)
        if kind == SAND:
            return sprites.tile_sand(v % 8)
        return sprites.tile_soil(v % 4)

    def sorted_objects(self) -> list[Obj]:
        return sorted(self.objects, key=lambda o: o.bottom)

