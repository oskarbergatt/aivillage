"""Procedural sprite drawing routines."""
from __future__ import annotations
import math
import random
from functools import lru_cache
import pygame
from .palette import CLOTH, HAIR, HAT_COLORS, P, SKIN, mix, shade
from .sprite_common import TILE, FACING_DOWN, FACING_LEFT, FACING_RIGHT, FACING_UP, surf, dither, hline


@lru_cache(maxsize=256)
def tile_grass(variant: int = 0, tint: tuple[int, int, int] | None = None) -> pygame.Surface:
    rng = random.Random(1000 + variant)
    s = surf(TILE, TILE)
    base = tint or P["grass"]
    s.fill(base)
    dither(s, (0, 0, TILE, TILE), P["grass_d"], 0.16, rng)
    dither(s, (0, 0, TILE, TILE), P["grass_l"], 0.10, rng)
    for _ in range(3):
        x = rng.randrange(1, TILE - 1)
        y = rng.randrange(2, TILE - 1)
        s.set_at((x, y), P["grass_l"])
        s.set_at((x, y - 1), P["grass_l"])
    if variant in (5, 11):
        for _ in range(2):
            x, y = rng.randrange(2, TILE - 2), rng.randrange(3, TILE - 3)
            s.set_at((x, y), (232, 210, 120))
            s.set_at((x + 1, y), (214, 158, 96))
    return s

@lru_cache(maxsize=128)
def tile_path(variant: int = 0) -> pygame.Surface:
    rng = random.Random(2000 + variant)
    s = surf(TILE, TILE)
    s.fill(P["dirt"])
    dither(s, (0, 0, TILE, TILE), P["dirt_d"], 0.22, rng)
    dither(s, (0, 0, TILE, TILE), P["dirt_l"], 0.14, rng)
    for _ in range(2):
        x, y = rng.randrange(1, TILE - 2), rng.randrange(1, TILE - 2)
        s.fill(P["stone_d"], (x, y, 2, 1))
    return s

@lru_cache(maxsize=128)
def tile_plaza(variant: int = 0) -> pygame.Surface:
    rng = random.Random(3000 + variant)
    s = surf(TILE, TILE)
    s.fill(P["stone"])
    for yy in range(0, TILE, 8):
        for xx in range(0, TILE, 8):
            c = mix(P["stone"], P["stone_l"] if (xx + yy) % 16 == 0 else P["stone_d"], 0.35)
            s.fill(c, (xx, yy, 8, 8))
            pygame.draw.rect(s, P["stone_d"], (xx, yy, 8, 8), 1)
    dither(s, (0, 0, TILE, TILE), P["stone_d"], 0.12, rng)
    return s

@lru_cache(maxsize=64)
def tile_soil(variant: int = 0) -> pygame.Surface:
    rng = random.Random(4000 + variant)
    s = surf(TILE, TILE)
    s.fill(P["soil"])
    for y in range(2, TILE, 5):
        hline(s, y, 1, TILE - 1, P["soil_d"])
        hline(s, y + 1, 1, TILE - 1, mix(P["soil"], P["dirt_d"], 0.4))
    dither(s, (0, 0, TILE, TILE), P["dirt_d"], 0.10, rng)
    return s

@lru_cache(maxsize=16)
def tile_water(frame: int = 0) -> pygame.Surface:
    rng = random.Random(5000)
    s = surf(TILE, TILE)
    s.fill(P["water"])
    dither(s, (0, 0, TILE, TILE), P["water_d"], 0.20, rng)
    off = (frame * 4) % 8
    for y in range(0, TILE, 8):
        for x in range(-8, TILE, 8):
            pygame.draw.line(s, P["water_l"], (x + off, y + 3), (x + off + 4, y + 3))
            pygame.draw.line(s, P["water_l"], (x + off + 2, y + 4), (x + off + 5, y + 4))
    return s

@lru_cache(maxsize=64)
def tile_sand(variant: int = 0) -> pygame.Surface:
    rng = random.Random(6000 + variant)
    s = surf(TILE, TILE)
    s.fill(P["sand"])
    dither(s, (0, 0, TILE, TILE), mix(P["sand"], P["dirt_l"], 0.5), 0.14, rng)
    dither(s, (0, 0, TILE, TILE), P["cream"], 0.08, rng)
    return s

@lru_cache(maxsize=64)
def tree(seed: int = 0, big: bool = True) -> pygame.Surface:
    rng = random.Random(7000 + seed)
    w = 44 if big else 32
    h = 56 if big else 40
    s = surf(w, h)
    cx = w // 2
    pygame.draw.rect(s, P["wood_d"], (cx - 3, h - 18, 6, 18))
    pygame.draw.rect(s, P["wood"], (cx - 2, h - 18, 3, 18))
    blobs = [
        (cx, 20, 16 if big else 12),
        (cx - 10, 26, 12 if big else 9),
        (cx + 10, 25, 12 if big else 9),
        (cx, 31, 13 if big else 10),
    ]
    for bx, by, r in blobs:
        pygame.draw.circle(s, P["leaf_d"], (bx, by + 2), r)
    for bx, by, r in blobs:
        pygame.draw.circle(s, P["leaf"], (bx, by), r - 1)
    for _ in range(int(w * h * 0.06)):
        a = rng.random() * math.tau
        rad = rng.random() * (14 if big else 10)
        x = int(cx + math.cos(a) * rad)
        y = int(20 + math.sin(a) * rad * 0.8)
        if 0 <= x < w and 0 <= y < h:
            s.set_at((x, y), P["leaf_l"] if rng.random() < 0.6 else P["leaf_d"])
    return s

@lru_cache(maxsize=32)
def bush(seed: int = 0) -> pygame.Surface:
    rng = random.Random(7100 + seed)
    s = surf(22, 16)
    pygame.draw.ellipse(s, P["leaf_d"], (0, 5, 22, 11))
    pygame.draw.ellipse(s, P["leaf"], (1, 4, 20, 10))
    dither(s, (2, 4, 18, 9), P["leaf_l"], 0.18, rng)
    return s

@lru_cache(maxsize=32)
def rock(seed: int = 0) -> pygame.Surface:
    rng = random.Random(7200 + seed)
    s = surf(18, 12)
    pygame.draw.ellipse(s, P["stone_d"], (1, 4, 16, 8))
    pygame.draw.ellipse(s, P["stone"], (2, 3, 13, 7))
    dither(s, (3, 3, 11, 6), P["stone_l"], 0.25, rng)
    return s

@lru_cache(maxsize=8)
def flower_patch(seed: int = 0) -> pygame.Surface:
    rng = random.Random(7300 + seed)
    s = surf(TILE, TILE)
    colors = [(232, 120, 140), (244, 214, 120), (200, 160, 236), (240, 168, 110)]
    for _ in range(6):
        x, y = rng.randrange(2, 14), rng.randrange(3, 14)
        s.fill(P["grass_d"], (x, y + 1, 1, 2))
        s.set_at((x, y), rng.choice(colors))
    return s

@lru_cache(maxsize=8)
def fence() -> pygame.Surface:
    s = surf(16, 16)
    pygame.draw.rect(s, P["wood_d"], (1, 4, 2, 12))
    pygame.draw.rect(s, P["wood"], (1, 4, 1, 12))
    pygame.draw.rect(s, P["wood_d"], (11, 4, 2, 12))
    pygame.draw.rect(s, P["wood"], (11, 4, 1, 12))
    pygame.draw.rect(s, P["wood_l"], (0, 6, 16, 2))
    pygame.draw.rect(s, P["wood"], (0, 11, 16, 2))
    return s

@lru_cache(maxsize=8)
def sheep(seed: int = 0) -> pygame.Surface:
    """A small woolly sheep, facing right."""
    rng = random.Random(7500 + seed)
    s = surf(20, 16)
    pygame.draw.ellipse(s, P["shadow"], (1, 11, 18, 4))
    pygame.draw.rect(s, P["ink_soft"], (4, 10, 2, 5))
    pygame.draw.rect(s, P["ink_soft"], (13, 10, 2, 5))
    pygame.draw.ellipse(s, P["cream"], (1, 3, 16, 10))
    dither(s, (2, 4, 14, 8), P["white"], 0.28, rng)
    dither(s, (2, 4, 14, 8), P["ui_dim"], 0.08, rng)
    pygame.draw.ellipse(s, P["ink_soft"], (13, 4, 6, 6))
    pygame.draw.rect(s, P["ink_soft"], (12, 3, 2, 3))
    pygame.draw.rect(s, P["cream"], (11, 1, 3, 2))
    s.set_at((16, 6), P["white"])
    return s

@lru_cache(maxsize=8)
def beehive() -> pygame.Surface:
    """A straw skep on a wooden stand, with a few bees around it."""
    s = surf(16, 20)
    pygame.draw.ellipse(s, P["shadow"], (1, 16, 14, 4))
    pygame.draw.rect(s, P["wood_d"], (3, 15, 2, 4))
    pygame.draw.rect(s, P["wood_d"], (11, 15, 2, 4))
    pygame.draw.rect(s, P["wood"], (2, 12, 12, 3))
    pygame.draw.ellipse(s, (198, 158, 84), (2, 2, 12, 12))
    pygame.draw.ellipse(s, (176, 134, 66), (2, 8, 12, 6))
    for y in (5, 8, 11):
        pygame.draw.arc(s, P["wood_d"], (3, y - 1, 10, 5), 0.15, 2.9, 1)
    pygame.draw.rect(s, P["ink_soft"], (6, 8, 4, 3))
    pygame.draw.rect(s, P["wood_d"], (1, 14, 14, 1))
    for x, y in ((13, 3), (15, 6), (1, 5)):
        s.set_at((x, y), P["window_d"])
    return s

@lru_cache(maxsize=8)
def log_pile() -> pygame.Surface:
    """Stacked cordwood: three logs on the bottom, two on top."""
    s = surf(24, 16)
    pygame.draw.ellipse(s, P["shadow"], (1, 12, 22, 4))
    logs = [(2, 9), (9, 9), (16, 9), (5, 4), (12, 4)]
    for i, (x, y) in enumerate(logs):
        pygame.draw.rect(s, P["wood_d"], (x - 1, y, 8, 7), border_radius=3)
        pygame.draw.ellipse(s, P["wood"], (x, y + 1, 7, 6))
        pygame.draw.ellipse(s, P["wood_l"], (x + 1, y + 2, 4, 3))
        pygame.draw.ellipse(s, P["wood_d"], (x + 2, y + 3, 2, 2))
    return s

@lru_cache(maxsize=32)
def boulder(seed: int = 0) -> pygame.Surface:
    """A chunky quarry stone with a chipped face."""
    rng = random.Random(7800 + seed)
    s = surf(22, 16)
    pygame.draw.ellipse(s, P["shadow"], (1, 11, 20, 5))
    pygame.draw.polygon(s, P["slate"], [(2, 13), (1, 8), (5, 3), (15, 2),
                                        (20, 7), (19, 13)])
    pygame.draw.polygon(s, P["stone"], [(3, 12), (2, 8), (6, 4), (14, 3),
                                        (18, 7), (17, 12)])
    dither(s, (5, 5, 11, 7), P["stone_l"], 0.30, rng)
    pygame.draw.line(s, P["stone_d"], (10, 4), (9, 9))
    pygame.draw.line(s, P["stone_d"], (9, 9), (13, 11))
    return s
