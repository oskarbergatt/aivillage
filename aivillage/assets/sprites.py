"""Procedural pixel art.

Every sprite is generated at runtime from palette colours and small drawing
routines, so the game ships with no image assets at all.
"""
from __future__ import annotations

import math
import random
from functools import lru_cache

import pygame

from .palette import CLOTH, HAIR, HAT_COLORS, P, SKIN, mix, shade

TILE = 16

FACING_DOWN, FACING_LEFT, FACING_RIGHT, FACING_UP = 0, 1, 2, 3



from .sprite_common import surf, dither, hline
from .sprite_terrain import (
    tile_grass,
    tile_path,
    tile_plaza,
    tile_soil,
    tile_water,
    tile_sand,
    tree,
    bush,
    rock,
    flower_patch,
    fence,
    sheep,
    beehive,
    log_pile,
    boulder,
)
from .sprite_props import (
    lamp,
    bench,
    well,
    market_stall,
    crop,
    windmill,
    bell_post,
    crate,
    barrel,
    scaffold,
)
from .sprite_characters import (
    house,
    villager,
    villager_with_tool,
)
from .sprite_lighting import (
    portrait,
    light_radius,
    glow,
)
