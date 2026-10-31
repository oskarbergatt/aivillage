"""Extracted methods for World."""
from __future__ import annotations

from .map_shared import (
    BuildSite,
    CropPlot,
    GRASS,
    H,
    Obj,
    PATH,
    PLAZA,
    SAND,
    SOIL,
    W,
    WATER,
    make_house_obj,
    pygame,
    sprites,
)


class MapLandmarksMixin:
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
            # v0.3 arrivals
            ("june", 6, 14, 4, 3, "roof_ochre", True),
            ("fen", 51, 8, 4, 3, "roof_blue", False),
            ("mira", 6, 33, 4, 3, "roof_plum", True),
            ("tobin", 34, 38, 4, 3, "roof_red", True),
            # v0.4 resource trades
            ("maude", 57, 9, 4, 3, "roof_green", False),
            ("ivo", 57, 17, 4, 3, "roof_ochre", False),
            ("greta", 53, 41, 4, 3, "roof_plum", False),
            ("corin", 8, 39, 4, 3, "roof_blue", False),
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
        self._add_point_obj("mill", sprites.windmill(), 52, 14, 3, 4)

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
        self.points["school"] = self.tile_center(30, 21)
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

        # -- v0.4 resource work sites ------------------------------------
        # East lane: both east houses and the apiary/pasture open onto it.
        self.carve_path(59, 12, 62, 12)
        self.carve_path(62, 12, 62, 27)
        self.carve_path(59, 20, 62, 20)
        self.carve_path(62, 20, 62, 22)
        self.carve_path(62, 22, 59, 22)
        self.carve_path(62, 27, 59, 27)

        self.points["pasture"] = self.tile_center(59, 27)
        self.points["apiary"] = self.tile_center(59, 22)

        # A fenced pasture with sheep; the fence and sheep stay non-solid so
        # the shepherd can walk to the middle of her flock.
        for x in range(55, 63):
            for y in (26, 29):
                self.add(Obj("fence", x * 16, y * 16 + 2, sprites.fence(),
                             solid=False, sort_y=y * 16 + 16))
        for y in range(27, 29):
            for x in (55, 62):
                self.add(Obj("fence", x * 16, y * 16 + 2, sprites.fence(),
                             solid=False, sort_y=y * 16 + 16))
        for i, (tx, ty) in enumerate([(57, 27), (61, 28), (58, 28), (60, 28)]):
            ewe = sprites.sheep(i)
            self.add(Obj("sheep", tx * 16 - 2, ty * 16 + 16 - ewe.get_height(),
                         ewe, solid=False, sort_y=ty * 16 + 16))

        # Hives around the apiary point. Solid, but the work point is clear.
        for tx, ty in ((57, 21), (61, 21), (57, 23), (61, 23)):
            hive = sprites.beehive()
            self.add(Obj("beehive", tx * 16 + 2, ty * 16 + 16 - hive.get_height(),
                         hive, solid=True, sort_y=ty * 16 + 16))

        # South woodlot, with stacked cordwood beside the splitting ground.
        self.carve_path(55, 44, 60, 44)
        self.carve_path(60, 44, 60, 42)
        self.points["woodlot"] = self.tile_center(60, 42)
        for i, (tx, ty) in enumerate([(62, 41), (61, 44)]):
            pile = sprites.log_pile()
            self.add(Obj("logs", tx * 16 - 4, ty * 16 + 16 - pile.get_height(),
                         pile, solid=True, sort_y=ty * 16 + 16))

        # West quarry, ringed by boulders with a short barrow track.
        self.carve_path(10, 42, 4, 42)
        self.carve_path(4, 42, 4, 44)
        self.points["quarry"] = self.tile_center(4, 42)
        for i, (tx, ty) in enumerate([(1, 41), (2, 44), (6, 44), (3, 39),
                                      (5, 40)]):
            stone = sprites.boulder(i)
            self.add(Obj("boulder", tx * 16 - 3, ty * 16 + 16 - stone.get_height(),
                         stone, solid=True, sort_y=ty * 16 + 16))

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

