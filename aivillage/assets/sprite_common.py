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



def surf(w: int, h: int) -> pygame.Surface:
    return pygame.Surface((max(1, w), max(1, h)), pygame.SRCALPHA)

def dither(s: pygame.Surface, rect, color, density: float, rng: random.Random) -> None:
    x, y, w, h = rect
    for yy in range(y, y + h):
        for xx in range(x, x + w):
            if 0 <= xx < s.get_width() and 0 <= yy < s.get_height() and rng.random() < density:
                s.set_at((xx, yy), color)

def hline(s: pygame.Surface, y: int, x0: int, x1: int, color) -> None:
    pygame.draw.line(s, color, (x0, y), (x1, y))
