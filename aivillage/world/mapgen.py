"""Village generation. Hand-placed landmarks, procedural edges."""
from __future__ import annotations

import math
import random

import pygame

from ..assets import sprites
from ..assets.palette import P
from .objects import BuildSite, CropPlot, Obj, make_house_obj

GRASS, PATH, PLAZA, WATER, SAND, SOIL = range(6)

W, H = 64, 48
TILE = 16


class World:
    def __init__(self, seed: int = 1234):
        self.seed = seed
        self.rng = random.Random(seed)
        self.tiles = [[GRASS] * W for _ in range(H)]
        self.variant = [[self.rng.randrange(0, 16) for _ in range(W)] for _ in range(H)]
        self.blocked = [[False] * W for _ in range(H)]
        self.objects: list[Obj] = []
        self.plots: list[CropPlot] = []
        self.buildings: dict[str, Obj] = {}
        self.points: dict[str, tuple[int, int]] = {}
        self.build_site: BuildSite | None = None
        self.road_y = 23
        self._generate()

    # -- dimensions ------------------------------------------------------
    @property
    def W(self) -> int:
        return len(self.tiles[0])

    @property
    def H(self) -> int:
        return len(self.tiles)

    # -- geometry helpers ----------------------------------------------
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

    # -- generation -----------------------------------------------------
    def _generate(self) -> None:
        rng = self.rng

        # plaza
        for y in range(20, 26):
            for x in range(27, 37):
                self.set_tile(x, y, PLAZA)

        # pond
        pcx, pcy, prx, pry = 50, 34, 6, 4
        for y in range(H):
            for x in range(W):
                d = ((x - pcx) / prx) ** 2 + ((y - pcy) / pry) ** 2
                if d <= 1.0:
                    self.tiles[y][x] = WATER
                elif d <= 1.5 and self.tiles[y][x] == GRASS:
                    self.tiles[y][x] = SAND

        # main road from the west edge, and the south road out of the plaza
        for x in range(0, 27):
            self.set_tile(x, self.road_y, PATH)
        self.set_tile(26, 22, PATH)
        for y in range(22, 47):
            self.set_tile(32, y, PATH)
        for y in range(23, 28):
            self.set_tile(19, y, PATH)

        # farm soil
        for y in range(25, 28):
            for x in range(10, 14):
                self.set_tile(x, y, SOIL)
        for i in range(3):
            self.plots.append(CropPlot(10 + i, 25 + (i % 3), self.rng.randrange(0, 3)))
        for y in range(25, 28):
            for x in range(10, 14):
                if not any(p.tx == x and p.ty == y for p in self.plots) and rng.random() < 0.7:
                    self.plots.append(CropPlot(x, y, rng.randrange(0, 4)))

        # buildings: id, tx, ty, w, h, roof, shop
        layout = [
            ("pip", 13, 13, 5, 4, "roof_green", False),
            ("orin", 20, 12, 5, 4, "roof_ochre", True),
            ("marrow", 37, 12, 5, 4, "roof_plum", True),
            ("bram", 44, 18, 4, 3, "roof_blue", False),
            ("wisp", 48, 24, 4, 3, "roof_green", False),
            ("hazel", 18, 30, 4, 3, "roof_green", False),
            ("sable", 26, 30, 4, 3, "roof_plum", False),
            ("nim", 40, 32, 4, 3, "roof_blue", False),
            ("tavern", 24, 19, 4, 3, "roof_red", True),
        ]
        for i, (name, tx, ty, w, h, roof, shop) in enumerate(layout):
            obj = make_house_obj(name, tx, ty, w, h, roof, seed=i * 7 + self.seed,
                                 shop=shop)
            self.add(obj)
            self.buildings[name] = obj
            door = (tx + w // 2, ty + h)
            self.points[f"home_{name}"] = self.tile_center(*door)
            self.carve_path(tx + w // 2, ty + h, 31, 26)

        # point of interest objects
        self._add_point_obj("well", sprites.well(), 28, 20, 2, 2, sort_off=0)
        self._add_point_obj("bell", sprites.bell_post(), 32, 24, 1, 1)
        self._add_point_obj("market", sprites.market_stall(), 34, 26, 3, 2)
        self._add_point_obj("bench_a", sprites.bench(), 28, 25, 2, 1, solid=False)
        self._add_point_obj("bench_b", sprites.bench(), 34, 25, 2, 1, solid=False)

        for i, (tx, ty) in enumerate([(27, 20), (36, 20), (27, 25), (36, 25),
                                      (24, 23), (44, 23)]):
            self._add_point_obj(f"lamp{i}", sprites.lamp(True), tx, ty, 1, 1, solid=False)

        # workshop pad + props
        for y in range(15, 17):
            for x in range(39, 43):
                self.set_tile(x, y, PATH)
        self.add(Obj("prop", 39 * 16, 16 * 16 - 12, sprites.barrel(), w=1, h=1,
                     sort_y=16 * 16 + 4))
        self.add(Obj("prop", 42 * 16, 16 * 16 - 12, sprites.crate(), w=1, h=1,
                     sort_y=16 * 16 + 4))
        self.points["workshop"] = self.tile_center(41, 16)

        # town hall build site
        self.build_site = BuildSite(29, 13, 5, 4)
        site = Obj("buildsite", 29 * 16 - 2, 13 * 16 - 26, sprites.scaffold(0.0),
                   w=5, h=4, solid=True, sort_y=(13 + 4) * 16)
        self.objects.append(site)
        self.block(29, 13, 5, 4)
        self.points["buildsite"] = self.tile_center(31, 17)

        # farm points
        self.points["farm"] = self.tile_center(12, 28)
        self.points["pond"] = self.tile_center(45, 31)
        self.points["woods_west"] = self.tile_center(6, 36)
        self.points["woods_east"] = self.tile_center(57, 14)
        self.points["plaza"] = self.tile_center(31, 22)
        self.points["tavern_door"] = self.points["home_tavern"]
        self.points["market_front"] = self.tile_center(35, 28)
        self.points["road"] = self.tile_center(1, self.road_y)

        # fences around the farm
        for x in range(9, 15):
            self.add(Obj("fence", x * 16, 24 * 16 + 2, sprites.fence(), solid=False,
                         sort_y=24 * 16 + 16))
        for y in range(25, 28):
            self.add(Obj("fence", 9 * 16, y * 16 + 2, sprites.fence(), solid=False,
                         sort_y=y * 16 + 16))

        # nature
        self._scatter_trees()
        self._scatter_decor()

        # keep the road mouth clear for visitors
        for y in range(self.road_y - 1, self.road_y + 2):
            for x in range(0, 4):
                self.blocked[y][x] = False

    def _add_point_obj(self, name: str, sprite: pygame.Surface, tx: int, ty: int,
                       w: int, h: int, solid: bool = True, sort_off: int = 0) -> None:
        px = tx * 16 + (w * 16 - sprite.get_width()) // 2
        py = (ty + h) * 16 - sprite.get_height() + sort_off
        obj = Obj(name, px, py, sprite, w=w, h=h, solid=solid,
                  sort_y=(ty + h) * 16 + sort_off)
        self.add(obj)
        self.points.setdefault(name, self.tile_center(tx + w // 2, ty + h // 2))

    def _scatter_trees(self) -> None:
        rng = self.rng
        attempts = 0
        placed = 0
        while placed < 95 and attempts < 4000:
            attempts += 1
            tx = rng.randrange(1, W - 2)
            ty = rng.randrange(1, H - 2)
            edge = tx < 8 or tx > W - 9 or ty < 9 or ty > H - 8
            cluster = (tx < 18 and ty < 12) or (tx > 52 and ty < 24) or (tx < 16 and ty > 36)
            if not (edge or cluster) and rng.random() > 0.12:
                continue
            if not self.free_spot(tx, ty, 1):
                continue
            big = rng.random() < 0.6
            tree = sprites.tree(rng.randrange(0, 40), big)
            self.add(Obj("tree", tx * 16 + 8 - tree.get_width() // 2,
                         ty * 16 + 16 - tree.get_height(), tree, w=1, h=1,
                         sort_y=ty * 16 + 16))
            placed += 1

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

    # -- queries --------------------------------------------------------
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
