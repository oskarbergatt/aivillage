"""Public facade and controller composition."""
from __future__ import annotations

from .map_shared import (
    BuildSite,
    CropPlot,
    GRASS,
    H,
    Obj,
    P,
    PATH,
    PLAZA,
    SAND,
    SOIL,
    TILE,
    W,
    WATER,
    make_house_obj,
    math,
    pygame,
    random,
    sprites,
)

from .map_geometry import MapGeometryMixin
from .map_landmarks import MapLandmarksMixin
from .map_queries import MapQueriesMixin


class World(MapGeometryMixin, MapLandmarksMixin, MapQueriesMixin):
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
