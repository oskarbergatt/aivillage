"""A* on the tile grid, plus path smoothing helpers."""
from __future__ import annotations

import heapq
import math
from typing import Iterable

Point = tuple[int, int]


def heuristic(a: Point, b: Point) -> float:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def astar(start: Point, goal: Point, walkable, max_nodes: int = 9000) -> list[Point]:
    """4-directional A*. `walkable` is a callable (tx, ty) -> bool."""
    if start == goal:
        return [start]
    if not walkable(*goal):
        # find the closest walkable neighbour so clicks near walls still work
        best, best_d = None, 1e9
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                p = (goal[0] + dx, goal[1] + dy)
                if walkable(*p):
                    d = abs(dx) + abs(dy)
                    if d < best_d:
                        best, best_d = p, d
        if best is None:
            return []
        goal = best

    open_heap: list[tuple[float, int, Point]] = []
    counter = 0
    heapq.heappush(open_heap, (heuristic(start, goal), counter, start))
    came: dict[Point, Point | None] = {start: None}
    cost: dict[Point, float] = {start: 0.0}
    visited = 0

    while open_heap:
        _, _, current = heapq.heappop(open_heap)
        visited += 1
        if current == goal:
            path = [current]
            while came.get(path[-1]) is not None:
                path.append(came[path[-1]])  # type: ignore[arg-type]
            path.reverse()
            return path
        if visited > max_nodes:
            break
        cx, cy = current
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nxt = (cx + dx, cy + dy)
            if not walkable(*nxt):
                continue
            step = 1.0
            new_cost = cost[current] + step
            if new_cost < cost.get(nxt, 1e9):
                cost[nxt] = new_cost
                counter += 1
                heapq.heappush(open_heap, (new_cost + heuristic(nxt, goal), counter, nxt))
                came[nxt] = current
    return []


def nearest_walkable(tx: int, ty: int, walkable, radius: int = 6) -> Point | None:
    if walkable(tx, ty):
        return (tx, ty)
    for r in range(1, radius + 1):
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                if abs(dx) != r and abs(dy) != r:
                    continue
                if walkable(tx + dx, ty + dy):
                    return (tx + dx, ty + dy)
    return None


def smooth(path: list[Point]) -> list[Point]:
    """Drop collinear points to keep movement tidy."""
    if len(path) < 3:
        return path
    out = [path[0]]
    for i in range(1, len(path) - 1):
        px, py = out[-1]
        cx, cy = path[i]
        nx, ny = path[i + 1]
        if (cx - px, cy - py) == (nx - cx, ny - cy):
            continue
        out.append(path[i])
    out.append(path[-1])
    return out


def path_length(path: Iterable[Point]) -> float:
    pts = list(path)
    return sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))
