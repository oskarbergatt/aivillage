"""World generation, pathfinding and crop logic."""
from __future__ import annotations

import random

from aivillage.world.mapgen import H, W, World
from aivillage.world.pathfinding import astar, nearest_walkable, smooth


def test_world_dimensions_match_grid():
    world = World(1234)
    assert world.W == W
    assert world.H == H
    assert len(world.tiles) == H
    assert all(len(row) == W for row in world.tiles)


def test_landmarks_are_walkable_or_reachable():
    world = World(1234)
    needed = ("plaza", "farm", "pond", "workshop", "market_front", "road",
              "tavern_door", "woods_west", "woods_east", "buildsite",
              "school", "mill", "pasture", "apiary", "woodlot", "quarry")
    for name in needed:
        assert name in world.points, name
        px, py = world.points[name]
        tx, ty = px // 16, py // 16
        spot = nearest_walkable(tx, ty, world.is_walkable, radius=4)
        assert spot is not None, f"{name} has no walkable ground near it"


def test_every_home_has_a_door_point():
    world = World(1234)
    for name in ("pip", "orin", "marrow", "bram", "wisp", "hazel", "sable",
                 "nim", "tavern", "june", "fen", "mira", "tobin",
                 "maude", "ivo", "greta", "corin"):
        point = world.points.get(f"home_{name}")
        assert point is not None
        assert world.is_walkable(point[0] // 16, point[1] // 16)


def test_paths_connect_the_village():
    world = World(1234)
    start = world.points["road"]
    start_t = (start[0] // 16, start[1] // 16)
    for name in ("plaza", "farm", "wood_spot"):
        point = world.points.get(name if name != "wood_spot" else "woods_west")
        goal = (point[0] // 16, point[1] // 16)
        path = astar(start_t, goal, world.is_walkable)
        assert path, f"no path from road to {name}"
        assert path[0] == start_t
        assert path[-1] == goal or world.is_walkable(*goal)


def test_path_through_water_is_impossible():
    world = World(1234)
    assert not world.is_walkable(50, 34)
    lake_edge = (48, 34)
    if world.is_walkable(*lake_edge):
        path = astar((31, 22), (50, 34), world.is_walkable)
        assert (50, 34) not in path


def test_smooth_keeps_endpoints():
    path = [(0, 0), (1, 0), (2, 0), (2, 1), (2, 2)]
    out = smooth(path)
    assert out[0] == (0, 0)
    assert out[-1] == (2, 2)
    assert len(out) < len(path)


def test_crop_growth_and_harvest_cycle():
    world = World(1234)
    plot = world.plots[0]
    plot.stage = 0
    plot.growth = 0.0
    plot.watered = 0.0
    for _ in range(12):
        plot.watered = 1.5
        plot.advance(4.0, raining=False)
    assert plot.ripe
    assert plot.stage == 3


def test_build_site_completes_once():
    world = World(1234)
    site = world.build_site
    assert site is not None
    assert not site.contribute(0.5)
    assert site.progress == 0.5
    assert site.contribute(0.6)
    assert site.progress == 1.0
    assert not site.contribute(1.0)


def test_completed_town_hall_has_a_distinct_roof_and_facade():
    from aivillage.assets import sprites
    from aivillage.assets.palette import P

    scaffold = sprites.scaffold(0.0)
    hall = sprites.scaffold(1.0)
    assert hall.get_size() == scaffold.get_size()
    assert hall.get_at((42, 8))[:3] == P["roof_blue_d"]
    assert hall.get_at((42, 42))[:3] == P["cream"]
    assert hall.get_at((42, 8)).a > scaffold.get_at((42, 8)).a


def test_random_walkable_stays_on_ground():
    world = World(1234)
    rng = random.Random(3)
    for _ in range(50):
        tx, ty = world.random_walkable(rng, 31, 22, 8)
        assert world.is_walkable(tx, ty)
