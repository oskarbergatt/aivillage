"""The village palette. Every colour in the game comes from here."""
from __future__ import annotations

from typing import Iterable

RGB = tuple[int, int, int]

P: dict[str, RGB] = {
    # greens
    "grass": (92, 148, 82),
    "grass_d": (72, 124, 68),
    "grass_l": (118, 172, 96),
    "grass_y": (150, 172, 88),
    "leaf": (66, 118, 72),
    "leaf_d": (46, 88, 58),
    "leaf_l": (96, 150, 88),
    # earth
    "dirt": (146, 112, 74),
    "dirt_d": (116, 88, 58),
    "dirt_l": (170, 136, 94),
    "soil": (94, 68, 48),
    "soil_d": (72, 52, 38),
    "sand": (198, 178, 128),
    "stone": (138, 138, 142),
    "stone_d": (104, 104, 112),
    "stone_l": (172, 172, 176),
    "slate": (84, 86, 98),
    # water
    "water": (58, 112, 158),
    "water_d": (42, 88, 132),
    "water_l": (96, 158, 196),
    "foam": (198, 224, 236),
    # wood
    "wood": (128, 92, 60),
    "wood_d": (96, 68, 44),
    "wood_l": (158, 118, 78),
    "plank": (144, 106, 70),
    # roofs
    "roof_red": (158, 74, 62),
    "roof_red_d": (124, 54, 46),
    "roof_blue": (78, 98, 138),
    "roof_blue_d": (58, 74, 108),
    "roof_green": (86, 118, 84),
    "roof_green_d": (64, 92, 66),
    "roof_ochre": (176, 134, 66),
    "roof_ochre_d": (140, 102, 48),
    "roof_plum": (108, 76, 108),
    "roof_plum_d": (84, 56, 84),
    # light / sky
    "window": (250, 214, 138),
    "window_d": (206, 166, 96),
    "white": (240, 238, 228),
    "cream": (226, 214, 188),
    "ink": (32, 28, 40),
    "ink_soft": (58, 52, 68),
    "shadow": (34, 30, 46, 90),
    # ui
    "ui_bg": (30, 28, 42),
    "ui_bg2": (44, 40, 58),
    "ui_line": (92, 84, 110),
    "ui_text": (232, 226, 208),
    "ui_dim": (154, 146, 168),
    "ui_accent": (240, 196, 108),
    "ui_good": (140, 196, 122),
    "ui_warn": (226, 158, 88),
    "ui_bad": (208, 106, 106),
    "ui_cool": (122, 172, 208),
}

# villager cloth palettes: (shirt, shirt dark, trousers, accent)
CLOTH: list[tuple[RGB, RGB, RGB, RGB]] = [
    ((196, 92, 72), (156, 68, 54), (74, 70, 96), (236, 198, 128)),   # rust
    ((92, 142, 176), (68, 110, 142), (78, 72, 62), (226, 214, 180)),  # blue
    ((150, 128, 186), (118, 98, 152), (62, 62, 84), (232, 210, 236)), # lilac
    ((214, 178, 104), (176, 142, 78), (86, 74, 54), (120, 84, 52)),   # wheat
    ((110, 158, 116), (84, 128, 92), (68, 66, 58), (214, 226, 190)),  # moss
    ((176, 118, 88), (140, 90, 66), (70, 72, 88), (228, 200, 160)),   # clay
    ((96, 118, 132), (72, 92, 106), (54, 58, 70), (198, 214, 220)),   # slate
    ((132, 108, 148), (102, 82, 118), (60, 54, 74), (206, 190, 230)), # dusk
]

SKIN: list[RGB] = [
    (238, 198, 160),
    (214, 166, 124),
    (186, 132, 94),
    (150, 102, 70),
    (108, 72, 52),
]

HAIR: list[RGB] = [
    (66, 50, 44),
    (110, 76, 48),
    (156, 112, 62),
    (208, 176, 120),
    (72, 72, 84),
    (140, 62, 48),
]

HAT_COLORS: list[RGB] = [
    (196, 168, 96),
    (120, 96, 70),
    (86, 96, 112),
    (156, 92, 74),
]


def mix(a: RGB, b: RGB, t: float) -> RGB:
    t = max(0.0, min(1.0, t))
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )


def shade(c: RGB, amount: float) -> RGB:
    return mix(c, (0, 0, 0), amount) if amount > 0 else mix(c, (255, 255, 255), -amount)


def lerp_list(stops: Iterable[tuple[float, RGB]], t: float) -> RGB:
    stops = list(stops)
    t = max(0.0, min(1.0, t))
    for i in range(len(stops) - 1):
        t0, c0 = stops[i]
        t1, c1 = stops[i + 1]
        if t0 <= t <= t1:
            local = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)
            return mix(c0, c1, local)
    return stops[-1][1]
