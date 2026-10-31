"""Procedural art sanity: everything draws, at the right size, without assets."""
from __future__ import annotations

import pygame

from aivillage.assets import sprites
from aivillage.assets.font import get_font, render, wrap
from aivillage.assets.palette import P


def test_tiles_are_square_and_opaque():
    tiles = [sprites.tile_grass(3), sprites.tile_path(2), sprites.tile_plaza(1),
             sprites.tile_water(0), sprites.tile_sand(2), sprites.tile_soil(1)]
    for tile in tiles:
        assert tile.get_size() == (16, 16)
        assert tile.get_at((8, 8))[3] == 255


def test_villager_frames_differ_and_have_alpha():
    a = sprites.villager(0, 1, 2, "short", "straw", 3, 1, 0, apron=True)
    b = sprites.villager(0, 1, 2, "short", "straw", 3, 1, 1, apron=True)
    assert a.get_size() == b.get_size()
    assert pygame.image.tostring(a, "RGBA") != pygame.image.tostring(b, "RGBA")
    assert a.get_at((0, 0))[3] == 0


def test_tool_variants_render():
    base = sprites.villager(1, 2, 3, "bun", "", 4, 2, 0, apron=True)
    for tool in ("hoe", "hammer", "basket", "rod", "brush",
                 "staff", "axe", "pick", "smoker"):
        out = sprites.villager_with_tool(base, tool)
        assert out.get_width() >= base.get_width()


def test_portrait_scales():
    portrait = sprites.portrait(2, 3, 4, "long", "hood", 5, 96)
    assert portrait.get_size() == (96, 96)
    assert portrait.get_at((0, 0))[3] == 0


def test_house_has_day_and_night_versions():
    day, night = sprites.house(w_tiles=5, h_tiles=4, roof_key="roof_red", seed=3)
    assert day.get_size() == night.get_size()
    assert day.get_width() > 64
    assert pygame.image.tostring(day, "RGB") != pygame.image.tostring(night, "RGB")


def test_scaffold_grows():
    a = sprites.scaffold(0.0)
    b = sprites.scaffold(0.9)
    assert a.get_size() == b.get_size()
    assert pygame.image.tostring(a, "RGBA") != pygame.image.tostring(b, "RGBA")


def test_fonts_render_and_stay_inside_a_panel():
    for size in (8, 16, 24):
        surf = render("Rostock, Germany", size, P["ui_text"])
        assert surf.get_width() > 0 and surf.get_height() > 0
    font = get_font(16)
    assert font.size("Bram Tock")[0] < 478


def test_wrap_never_exceeds_width():
    text = ("The council met beside the well and argued about the bridge for "
            "most of the afternoon, which is longer than the bridge took to build.")
    lines = wrap(text, 16, 300)
    font = get_font(16)
    assert len(lines) > 1
    for line in lines:
        assert font.size(line)[0] <= 320, line


def test_glow_and_lights():
    glow = sprites.glow(64, (255, 200, 120))
    assert glow.get_size() == (128, 128)
    assert glow.get_at((64, 64))[3] > 0
    assert glow.get_at((0, 0))[3] == 0


def test_all_world_sprites_exist():
    expected = ("well", "bell_post", "market_stall", "bench", "lamp", "barrel",
                "crate", "fence", "tree", "flower_patch", "rock", "bush",
                "crop", "sheep", "beehive", "log_pile", "boulder")
    for name in expected:
        assert hasattr(sprites, name), name
