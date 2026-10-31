"""Procedural sprite drawing routines."""
from __future__ import annotations
import math
import random
from functools import lru_cache
import pygame
from .palette import CLOTH, HAIR, HAT_COLORS, P, SKIN, mix, shade
from .sprite_common import TILE, FACING_DOWN, FACING_LEFT, FACING_RIGHT, FACING_UP, surf, dither, hline


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
    elif tool == "staff":
        pygame.draw.line(out, P["wood"], (12, 3), (12, 15))
        pygame.draw.arc(out, P["wood_l"], (8, 0, 9, 8), 0.2, 3.0, 2)
    elif tool == "axe":
        pygame.draw.rect(out, P["wood"], (12, 5, 2, 11))
        pygame.draw.polygon(out, P["stone_l"],
                            [(10, 3), (16, 4), (15, 8), (10, 7)])
        pygame.draw.line(out, P["stone_d"], (10, 7), (15, 8))
    elif tool == "pick":
        pygame.draw.rect(out, P["wood"], (12, 4, 2, 12))
        pygame.draw.line(out, P["stone_l"], (8, 4), (17, 6), 2)
        pygame.draw.line(out, P["stone_d"], (8, 5), (17, 7))
    elif tool == "smoker":
        pygame.draw.rect(out, P["stone_d"], (10, 10, 6, 6))
        pygame.draw.rect(out, P["stone"], (10, 10, 5, 5))
        pygame.draw.rect(out, P["stone_l"], (12, 8, 2, 2))
        pygame.draw.circle(out, P["ui_dim"], (13, 6), 1)
        pygame.draw.circle(out, P["ui_dim"], (15, 4), 1)
    return out
