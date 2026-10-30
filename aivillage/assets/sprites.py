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


# ───────────────────────────── ground tiles ─────────────────────────────

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


# ───────────────────────────── nature props ─────────────────────────────

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


# ───────────────────────────── houses ─────────────────────────────

def house(w_tiles: int = 5, h_tiles: int = 4, roof_key: str = "roof_red",
          wall: tuple[int, int, int] = P["plank"], seed: int = 0,
          shop_sign: bool = False) -> tuple[pygame.Surface, pygame.Surface]:
    """Return (day, night) surfaces. Origin is the top-left of the sprite;
    the footprint occupies the lower w_tiles*16 x h_tiles*16."""
    rng = random.Random(8000 + seed)
    w = w_tiles * TILE + 16
    h = h_tiles * TILE + 40
    body_top = 32
    body = pygame.Rect(8, body_top, w_tiles * TILE, h_tiles * TILE)
    s = surf(w, h)
    roof = P[roof_key]
    roof_d = P.get(roof_key + "_d", shade(roof, 0.3))

    # ground shadow
    pygame.draw.ellipse(s, (0, 0, 0, 60), (6, h - 10, w - 12, 12))
    # walls
    pygame.draw.rect(s, wall, body)
    for y in range(body.top + 2, body.bottom, 6):
        hline(s, y, body.left + 1, body.right - 2, shade(wall, 0.18))
    dither(s, body, shade(wall, 0.10), 0.10, rng)
    dither(s, body, shade(wall, -0.12), 0.06, rng)
    pygame.draw.rect(s, P["wood_d"], (body.left, body.bottom - 4, body.width, 4))
    pygame.draw.rect(s, P["wood_d"], (body.left, body.top, body.width, 2))
    # corner beams
    pygame.draw.rect(s, P["wood_d"], (body.left, body.top, 3, body.height))
    pygame.draw.rect(s, P["wood_d"], (body.right - 3, body.top, 3, body.height))

    # roof (trapezoid)
    top_y = 4
    roof_h = body_top - top_y + 6
    pygame.draw.polygon(s, roof_d, [(2, body_top + 4), (w - 2, body_top + 4),
                                    (w - 14, top_y), (14, top_y)])
    pygame.draw.polygon(s, roof, [(5, body_top + 2), (w - 5, body_top + 2),
                                  (w - 16, top_y + 3), (16, top_y + 3)])
    for i, y in enumerate(range(top_y + 4, body_top + 1, 4)):
        pygame.draw.line(s, roof_d, (10 + i, y), (w - 12, y))
        for x in range(8 + (i % 2) * 4, w - 8, 8):
            s.set_at((x, y - 1), shade(roof, -0.2))
    pygame.draw.line(s, shade(roof, 0.25), (16, top_y + 3), (w - 16, top_y + 3))
    # eaves
    pygame.draw.rect(s, roof_d, (0, body_top + 2, w, 4))

    # chimney
    cx = w - 26 if seed % 2 == 0 else 20
    pygame.draw.rect(s, P["stone_d"], (cx, top_y - 6, 10, 18))
    pygame.draw.rect(s, P["stone"], (cx + 1, top_y - 5, 8, 16))
    for yy in range(top_y - 4, top_y + 12, 4):
        hline(s, yy, cx + 1, cx + 8, P["stone_d"])

    # door
    dx = body.left + body.width // 2 - 7
    door = pygame.Rect(dx, body.bottom - 20, 14, 20)
    pygame.draw.rect(s, P["wood_d"], door)
    pygame.draw.rect(s, P["wood"], (door.x + 1, door.y + 2, door.width - 2, door.height - 2))
    pygame.draw.line(s, P["wood_d"], (door.centerx, door.y + 2), (door.centerx, door.bottom))
    pygame.draw.rect(s, P["ui_accent"], (door.right - 4, door.centery, 2, 2))
    pygame.draw.rect(s, P["stone_l"], (door.x - 2, door.bottom - 2, door.width + 4, 2))
    # windows
    win_rects = []
    if body.width >= 70:
        win_rects = [pygame.Rect(body.left + 10, body.top + 10, 12, 11),
                     pygame.Rect(body.right - 24, body.top + 10, 12, 11)]
    else:
        win_rects = [pygame.Rect(body.left + 12, body.top + 12, 11, 10)]
    for wr in win_rects:
        pygame.draw.rect(s, P["wood_d"], wr.inflate(2, 2))
        pygame.draw.rect(s, P["window_d"], wr)
        pygame.draw.line(s, P["wood_d"], (wr.centerx, wr.top), (wr.centerx, wr.bottom))
        pygame.draw.line(s, P["wood_d"], (wr.left, wr.centery), (wr.right, wr.centery))
    # hanging sign for shops
    if shop_sign:
        sx = body.right - 6
        pygame.draw.rect(s, P["wood_d"], (sx, body.top + 22, 2, 8))
        pygame.draw.rect(s, P["green"] if "green" in P else P["leaf"], (sx - 8, body.top + 30, 16, 10))
        pygame.draw.rect(s, P["cream"], (sx - 7, body.top + 31, 14, 8))
        pygame.draw.rect(s, P["wood_d"], (sx - 8, body.top + 30, 16, 10), 1)

    night = s.copy()
    for wr in win_rects:
        pygame.draw.rect(night, P["window"], wr)
        pygame.draw.line(night, P["wood_d"], (wr.centerx, wr.top), (wr.centerx, wr.bottom))
        pygame.draw.line(night, P["wood_d"], (wr.left, wr.centery), (wr.right, wr.centery))
    pygame.draw.rect(night, P["window_d"], (door.x + 1, door.y + 2, door.width - 2, 3))
    return s, night


# ───────────────────────────── villagers ─────────────────────────────

@lru_cache(maxsize=512)
def villager(skin: int, hair: int, cloth: int, hair_style: str, hat: str,
             version: int, facing: int, frame: int, apron: bool = False,
             beard: bool = False) -> pygame.Surface:
    """14x22 villager sprite, feet on the bottom row."""
    skin_c = SKIN[skin % len(SKIN)]
    hair_c = HAIR[hair % len(HAIR)]
    shirt, shirt_d, pants, accent = CLOTH[cloth % len(CLOTH)]
    s = surf(14, 22)

    step = [0, 1, 0, -1][frame % 4]
    bob = 0 if frame % 2 == 0 else 1

    # legs
    ly = 16 + bob
    pygame.draw.rect(s, pants, (3, ly, 4, 5 - abs(step)))
    pygame.draw.rect(s, pants, (7, ly, 4, 5 - abs(step)))
    if step > 0:
        pygame.draw.rect(s, shade(pants, 0.2), (2, ly + 3, 4, 3))
    if step < 0:
        pygame.draw.rect(s, shade(pants, 0.2), (8, ly + 3, 4, 3))
    # shoes
    pygame.draw.rect(s, P["ink_soft"], (2 if step > 0 else 3, 20, 4, 2))
    pygame.draw.rect(s, P["ink_soft"], (8 if step < 0 else 7, 20, 4, 2))

    # torso
    ty = 9 + bob
    pygame.draw.rect(s, shirt, (3, ty, 9, 8))
    pygame.draw.rect(s, shirt_d, (3, ty + 6, 9, 2))
    if apron:
        pygame.draw.rect(s, accent, (4, ty + 3, 7, 6))
        pygame.draw.rect(s, shade(accent, 0.15), (4, ty + 3, 7, 1))
    pygame.draw.rect(s, accent, (3, ty + 5, 9, 1))

    # arms
    arm_off = 1 if frame % 2 else 0
    pygame.draw.rect(s, shirt_d, (1, ty + 1 + arm_off, 2, 5))
    pygame.draw.rect(s, shirt_d, (12, ty + 1 - arm_off, 2, 5))
    pygame.draw.rect(s, skin_c, (1, ty + 6 + arm_off, 2, 2))
    pygame.draw.rect(s, skin_c, (12, ty + 6 - arm_off, 2, 2))

    # head
    hy = 2 + bob
    pygame.draw.rect(s, skin_c, (3, hy, 9, 8))
    pygame.draw.rect(s, shade(skin_c, 0.12), (3, hy + 6, 9, 2))

    # hair
    if hair_style != "bald":
        pygame.draw.rect(s, hair_c, (3, hy - 1, 9, 3))
        if hair_style == "short":
            pygame.draw.rect(s, hair_c, (2, hy, 1, 3))
            pygame.draw.rect(s, hair_c, (12, hy, 1, 3))
        elif hair_style == "long":
            pygame.draw.rect(s, hair_c, (2, hy, 2, 6))
            pygame.draw.rect(s, hair_c, (11, hy, 2, 6))
        elif hair_style == "bun":
            pygame.draw.rect(s, hair_c, (6, hy - 3, 4, 2))
            pygame.draw.rect(s, hair_c, (2, hy, 1, 3))
            pygame.draw.rect(s, hair_c, (12, hy, 1, 3))
        elif hair_style == "wild":
            for x in range(2, 13, 2):
                s.fill(hair_c, (x, hy - 2, 1, 2))
            pygame.draw.rect(s, hair_c, (2, hy, 1, 4))
            pygame.draw.rect(s, hair_c, (12, hy, 1, 4))
    if facing == FACING_UP:
        pygame.draw.rect(s, hair_c, (3, hy, 9, 5))

    # face
    if facing != FACING_UP:
        eye_color = P["ink"]
        if facing == FACING_DOWN:
            s.fill(eye_color, (5, hy + 3, 1, 2))
            s.fill(eye_color, (9, hy + 3, 1, 2))
        elif facing == FACING_LEFT:
            s.fill(eye_color, (4, hy + 3, 1, 2))
            s.fill(skin_c, (10, hy + 4, 1, 1))
        else:
            s.fill(eye_color, (9, hy + 3, 1, 2))
            s.fill(skin_c, (3, hy + 4, 1, 1))
        if beard and facing == FACING_DOWN:
            pygame.draw.rect(s, hair_c, (4, hy + 5, 7, 2))

    # hats
    if hat == "straw":
        pygame.draw.rect(s, HAT_COLORS[0], (1, hy - 2, 13, 2))
        pygame.draw.rect(s, shade(HAT_COLORS[0], 0.2), (4, hy - 5, 7, 3))
    elif hat == "cap":
        pygame.draw.rect(s, HAT_COLORS[2], (3, hy - 2, 9, 3))
        pygame.draw.rect(s, shade(HAT_COLORS[2], 0.2), (3, hy + 1, 9, 1))
    elif hat == "hood":
        pygame.draw.rect(s, shirt_d, (2, hy - 2, 11, 4))
        pygame.draw.rect(s, shade(shirt_d, 0.15), (4, hy - 1, 7, 2))
    return s


def villager_with_tool(sprite: pygame.Surface, tool: str) -> pygame.Surface:
    """Overlay a simple tool sprite next to a villager."""
    out = sprite.copy()
    if tool == "hammer":
        pygame.draw.rect(out, P["wood"], (12, 8, 2, 9))
        pygame.draw.rect(out, P["stone_l"], (10, 6, 5, 4))
    elif tool == "hoe":
        pygame.draw.rect(out, P["wood"], (12, 4, 2, 13))
        pygame.draw.rect(out, P["stone_l"], (10, 3, 5, 2))
    elif tool == "rod":
        pygame.draw.line(out, P["wood_l"], (12, 6), (15, 1))
        pygame.draw.line(out, P["cream"], (15, 1), (15, 6))
        pygame.draw.circle(out, P["ui_accent"], (15, 7), 1)
    elif tool == "can":
        pygame.draw.rect(out, P["stone_l"], (10, 12, 5, 4))
        pygame.draw.rect(out, P["stone_d"], (14, 11, 2, 2))
    elif tool == "brush":
        pygame.draw.rect(out, P["wood"], (12, 6, 2, 9))
        pygame.draw.rect(out, (216, 122, 142), (11, 4, 4, 3))
    elif tool == "basket":
        pygame.draw.ellipse(out, P["wood"], (9, 12, 7, 5))
        pygame.draw.ellipse(out, P["wood_d"], (9, 12, 7, 5), 1)
    return out


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
