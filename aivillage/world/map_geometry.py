"""Extracted methods for World."""
from __future__ import annotations

from .map_shared import (
    GRASS,
    H,
    Obj,
    PATH,
    PLAZA,
    TILE,
    W,
    WATER,
)


class MapGeometryMixin:
    @property
    def W(self) -> int:
        return len(self.tiles[0])

    @property
    def H(self) -> int:
        return len(self.tiles)

    def inside(self, tx: int, ty: int) -> bool:
        return 0 <= tx < W and 0 <= ty < H

    @staticmethod
    def tile_center(tx: int, ty: int) -> tuple[int, int]:
        return tx * TILE + TILE // 2, ty * TILE + TILE // 2

    @staticmethod
    def pixel_to_tile(px: float, py: float) -> tuple[int, int]:
        return int(px // TILE), int(py // TILE)

    def tile(self, tx: int, ty: int) -> int:
        if not self.inside(tx, ty):
            return GRASS
        return self.tiles[ty][tx]

    def is_walkable(self, tx: int, ty: int) -> bool:
        if not self.inside(tx, ty):
            return False
        if self.blocked[ty][tx]:
            return False
        return self.tiles[ty][tx] != WATER

    def set_tile(self, tx: int, ty: int, kind: int) -> None:
        if self.inside(tx, ty):
            self.tiles[ty][tx] = kind
            if kind != GRASS:
                self.variant[ty][tx] = self.rng.randrange(0, 16)

    def block(self, tx: int, ty: int, w: int = 1, h: int = 1) -> None:
        for y in range(ty, ty + h):
            for x in range(tx, tx + w):
                if self.inside(x, y):
                    self.blocked[y][x] = True

    def carve_path(self, x0: int, y0: int, x1: int, y1: int) -> None:
        x, y = x0, y0
        while x != x1:
            x += 1 if x1 > x else -1
            if self.tile(x, y) not in (WATER, PLAZA):
                self.set_tile(x, y, PATH)
        while y != y1:
            y += 1 if y1 > y else -1
            if self.tile(x, y) not in (WATER, PLAZA):
                self.set_tile(x, y, PATH)

    def free_spot(self, tx: int, ty: int, radius: int = 1) -> bool:
        for yy in range(ty - radius, ty + radius + 1):
            for xx in range(tx - radius, tx + radius + 1):
                if not self.inside(xx, yy):
                    return False
                if self.blocked[yy][xx] or self.tiles[yy][xx] != GRASS:
                    return False
        return True

    def add(self, obj: Obj) -> Obj:
        self.objects.append(obj)
        fp = obj.footprint
        if obj.solid:
            tx, ty = fp.x // TILE, fp.y // TILE
            self.block(tx, ty, fp.w // TILE, fp.h // TILE)
        return obj

