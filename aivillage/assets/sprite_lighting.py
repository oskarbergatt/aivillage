"""Procedural sprite drawing routines."""
from __future__ import annotations
import math
import random
from functools import lru_cache
import pygame
from .palette import CLOTH, HAIR, HAT_COLORS, P, SKIN, mix, shade
from .sprite_common import TILE, FACING_DOWN, FACING_LEFT, FACING_RIGHT, FACING_UP, surf, dither, hline
from .sprite_characters import villager


@lru_cache(maxsize=64)
def portrait(skin: int, hair: int, cloth: int, hair_style: str, hat: str,
             version: int, size: int = 64) -> pygame.Surface:
    base = villager(skin, hair, cloth, hair_style, hat, version, FACING_DOWN, 0)
    head = base.subsurface(pygame.Rect(1, 0, 12, 12)).copy()
    return pygame.transform.scale(head, (size, size))

def light_radius(radius: int, color=(255, 214, 140), strength: int = 210,
                 falloff: float = 2.2) -> pygame.Surface:
    """Radial alpha gradient used by the lighting pass."""
    size = radius * 2
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    for y in range(size):
        for x in range(size):
            d = math.hypot(x - radius, y - radius) / radius
            if d >= 1:
                continue
            a = int(strength * (1 - d) ** falloff)
            if a > 0:
                s.set_at((x, y), (*color, a))
    return s

@lru_cache(maxsize=16)
def glow(radius: int = 40, color=(255, 214, 140)) -> pygame.Surface:
    return light_radius(radius, color, 200, 2.0)
