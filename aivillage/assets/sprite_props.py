"""Procedural sprite drawing routines."""
from __future__ import annotations
import math
import random
from functools import lru_cache
import pygame
from .palette import CLOTH, HAIR, HAT_COLORS, P, SKIN, mix, shade
from .sprite_common import TILE, FACING_DOWN, FACING_LEFT, FACING_RIGHT, FACING_UP, surf, dither, hline


@lru_cache(maxsize=8)
def lamp(on: bool = True) -> pygame.Surface:
    s = surf(16, 34)
    pygame.draw.rect(s, P["ink_soft"], (7, 8, 2, 26))
    pygame.draw.rect(s, P["stone_d"], (5, 30, 6, 4))
    pygame.draw.rect(s, P["wood_d"], (4, 6, 8, 2))
    pygame.draw.rect(s, P["window"] if on else P["stone_d"], (5, 1, 6, 6))
    pygame.draw.rect(s, P["ink_soft"], (5, 1, 6, 6), 1)
    if on:
        pygame.draw.rect(s, P["window_d"], (6, 3, 4, 3))
    return s

@lru_cache(maxsize=8)
def bench() -> pygame.Surface:
    s = surf(22, 12)
    pygame.draw.rect(s, P["wood_d"], (0, 4, 22, 3))
    pygame.draw.rect(s, P["wood"], (0, 3, 22, 2))
    pygame.draw.rect(s, P["wood_d"], (2, 7, 2, 5))
    pygame.draw.rect(s, P["wood_d"], (18, 7, 2, 5))
    return s

@lru_cache(maxsize=8)
def well() -> pygame.Surface:
    s = surf(30, 30)
    pygame.draw.ellipse(s, P["stone_d"], (3, 18, 24, 10))
    pygame.draw.ellipse(s, P["stone"], (4, 17, 22, 8))
    pygame.draw.ellipse(s, (26, 34, 52), (7, 18, 16, 5))
    pygame.draw.rect(s, P["wood_d"], (5, 4, 3, 16))
    pygame.draw.rect(s, P["wood_d"], (22, 4, 3, 16))
    pygame.draw.rect(s, P["roof_red_d"], (2, 2, 26, 4))
    pygame.draw.rect(s, P["roof_red"], (4, 0, 22, 3))
    pygame.draw.rect(s, P["wood"], (15, 8, 1, 8))
    pygame.draw.rect(s, P["wood_l"], (13, 15, 5, 4))
    return s

@lru_cache(maxsize=8)
def market_stall() -> pygame.Surface:
    s = surf(40, 34)
    pygame.draw.rect(s, P["wood_d"], (2, 26, 36, 4))
    pygame.draw.rect(s, P["wood"], (3, 20, 34, 6))
    pygame.draw.rect(s, P["wood_d"], (4, 8, 3, 22))
    pygame.draw.rect(s, P["wood_d"], (33, 8, 3, 22))
    for i in range(0, 36, 8):
        pygame.draw.rect(s, P["roof_red"] if (i // 8) % 2 == 0 else P["cream"], (3 + i, 4, 8, 7))
    pygame.draw.rect(s, P["roof_red_d"], (2, 10, 38, 2))
    pygame.draw.rect(s, P["roof_red_d"], (2, 2, 38, 2))
    pygame.draw.rect(s, (176, 92, 62), (8, 15, 5, 5))
    pygame.draw.rect(s, (214, 160, 74), (17, 16, 6, 4))
    pygame.draw.rect(s, (140, 168, 96), (28, 15, 5, 5))
    return s

@lru_cache(maxsize=32)
def crop(stage: int = 0) -> pygame.Surface:
    s = surf(TILE, TILE)
    rng = random.Random(7600 + stage)
    if stage == 0:
        for x in (4, 9, 13):
            s.fill(P["leaf_d"], (x, 12, 1, 3))
        return s
    grow = [(4, 10), (8, 8), (12, 9)]
    for x, y in grow:
        height = {1: 4, 2: 7, 3: 8}[stage]
        s.fill(P["leaf_d"], (x, y + (8 - height), 1, height))
        s.fill(P["leaf_l"], (x - 1, y + (8 - height), 1, 2))
        s.fill(P["leaf"], (x + 1, y + (8 - height) + 2, 1, 2))
        if stage == 3:
            s.fill((224, 146, 78) if rng.random() < 0.5 else (196, 92, 72), (x - 1, y - 1, 3, 3))
    return s

@lru_cache(maxsize=4)
def windmill() -> pygame.Surface:
    """A small windmill: stone base, wooden sails, 3x4 tiles."""
    s = surf(54, 72)
    rng = random.Random(771)
    pygame.draw.rect(s, P["stone_d"], (14, 38, 26, 32))
    pygame.draw.rect(s, P["stone"], (16, 40, 22, 28))
    dither(s, (17, 41, 20, 26), P["stone_l"], 0.25, rng)
    pygame.draw.polygon(s, P["plank"], [(18, 12), (36, 12), (41, 42), (13, 42)])
    for y in range(16, 42, 5):
        pygame.draw.line(s, P["wood_d"], (17, y), (37, y))
    pygame.draw.rect(s, P["wood_d"], (15, 10, 24, 5))
    pygame.draw.polygon(s, P["roof_red_d"], [(12, 12), (42, 12), (27, 2)])
    pygame.draw.polygon(s, P["roof_red"], [(15, 11), (39, 11), (27, 4)])
    pygame.draw.rect(s, P["wood_d"], (23, 52, 8, 18))
    pygame.draw.rect(s, P["window"], (22, 27, 4, 5))
    pygame.draw.rect(s, P["window_d"], (28, 27, 4, 5))
    cx, cy = 27, 22
    for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
        for step in range(4, 22, 4):
            x = cx + dx * step
            y = cy + dy * step
            w = 7 if dx else 5
            h = 5 if dy else 7
            pygame.draw.rect(s, P["wood_d"], (x - w // 2, y - h // 2, w, h))
            pygame.draw.rect(s, P["cream"], (x - w // 2 + 1, y - h // 2 + 1,
                                             max(1, w - 2), max(1, h - 2)))
    pygame.draw.circle(s, P["wood_d"], (cx, cy), 3)
    return s

@lru_cache(maxsize=8)
def bell_post() -> pygame.Surface:
    s = surf(20, 34)
    pygame.draw.rect(s, P["wood_d"], (8, 6, 4, 28))
    pygame.draw.rect(s, P["wood"], (9, 6, 2, 28))
    pygame.draw.rect(s, P["wood_d"], (2, 2, 16, 3))
    pygame.draw.polygon(s, (198, 158, 84), [(9, 5), (15, 5), (17, 15), (7, 15)])
    pygame.draw.rect(s, (160, 120, 60), (6, 15, 12, 2))
    pygame.draw.rect(s, P["ink_soft"], (10, 17, 2, 2))
    return s

@lru_cache(maxsize=8)
def crate() -> pygame.Surface:
    s = surf(12, 12)
    pygame.draw.rect(s, P["wood_d"], (0, 0, 12, 12))
    pygame.draw.rect(s, P["wood"], (1, 1, 10, 10))
    pygame.draw.line(s, P["wood_d"], (1, 1), (10, 10))
    pygame.draw.line(s, P["wood_d"], (10, 1), (1, 10))
    return s

@lru_cache(maxsize=8)
def barrel() -> pygame.Surface:
    s = surf(12, 14)
    pygame.draw.rect(s, P["wood_d"], (1, 1, 10, 13), border_radius=2)
    pygame.draw.rect(s, P["wood"], (2, 2, 8, 11), border_radius=2)
    pygame.draw.rect(s, P["stone_d"], (1, 4, 10, 1))
    pygame.draw.rect(s, P["stone_d"], (1, 10, 10, 1))
    return s

@lru_cache(maxsize=8)
def scaffold(progress: float = 0.0) -> pygame.Surface:
    """Town hall under construction, 5x4 tiles + roof headroom."""
    s = surf(84, 88)
    rng = random.Random(9001)
    base_y = 88
    # scaffold frame
    for x in (4, 40, 76):
        pygame.draw.rect(s, P["wood_d"], (x, 20, 3, base_y - 20))
    for y in (28, 48, 68):
        pygame.draw.rect(s, P["wood_d"], (4, y, 76, 2))
    # stone foundation
    pygame.draw.rect(s, P["stone_d"], (6, base_y - 14, 72, 14))
    dither(s, (8, base_y - 12, 68, 10), P["stone"], 0.5, rng)
    walls = int(progress * 6)
    if walls > 0:
        wall_h = 6 + walls * 9
        pygame.draw.rect(s, P["plank"], (10, base_y - 18 - wall_h, 64, wall_h))
        for y in range(base_y - 18 - wall_h, base_y - 18, 5):
            hline(s, y, 10, 73, P["wood_d"])
        dither(s, (10, base_y - 18 - wall_h, 64, wall_h), P["wood_l"], 0.10, rng)
    if progress >= 1.0:
        pygame.draw.rect(s, P["roof_blue_d"], (4, 30, 76, 8))
        pygame.draw.rect(s, P["roof_blue"], (8, 24, 68, 8))
        pygame.draw.rect(s, P["cream"], (34, 56, 16, 22))
        pygame.draw.rect(s, P["wood_d"], (34, 56, 16, 22), 2)
        pygame.draw.rect(s, P["window"], (12, 44, 10, 10))
        pygame.draw.rect(s, P["window"], (62, 44, 10, 10))
    return s
