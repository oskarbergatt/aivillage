"""World camera: integer zoom, panning, screen<->world conversion."""
from __future__ import annotations

import pygame


class Camera:
    MIN_ZOOM = 2
    MAX_ZOOM = 5

    def __init__(self, world_w: int, world_h: int, zoom: int = 3,
                 view: tuple[int, int] = (1440, 810)):
        self.world_w = world_w
        self.world_h = world_h
        self.zoom = max(self.MIN_ZOOM, min(self.MAX_ZOOM, int(zoom)))
        self.view_w, self.view_h = view
        self.x = 0.0
        self.y = 0.0
        self.center_on(world_w / 2, world_h / 2)

    # -- geometry --------------------------------------------------------
    @property
    def view_world_w(self) -> float:
        return self.view_w / self.zoom

    @property
    def view_world_h(self) -> float:
        return self.view_h / self.zoom

    def set_view(self, w: int, h: int) -> None:
        self.view_w, self.view_h = max(320, w), max(240, h)
        self.clamp()

    def center_on(self, wx: float, wy: float) -> None:
        self.x = wx - self.view_world_w / 2
        self.y = wy - self.view_world_h / 2
        self.clamp()

    def clamp(self) -> None:
        if self.view_world_w >= self.world_w:
            self.x = (self.world_w - self.view_world_w) / 2
        else:
            self.x = max(0.0, min(self.world_w - self.view_world_w, self.x))
        if self.view_world_h >= self.world_h:
            self.y = (self.world_h - self.view_world_h) / 2
        else:
            self.y = max(0.0, min(self.world_h - self.view_world_h, self.y))

    def world_to_screen(self, wx: float, wy: float) -> tuple[int, int]:
        return (int((wx - self.x) * self.zoom), int((wy - self.y) * self.zoom))

    def screen_to_world(self, sx: float, sy: float) -> tuple[float, float]:
        return (sx / self.zoom + self.x, sy / self.zoom + self.y)

    def visible_rect(self, pad: int = 64) -> pygame.Rect:
        return pygame.Rect(int(self.x) - pad, int(self.y) - pad,
                           int(self.view_world_w) + pad * 2,
                           int(self.view_world_h) + pad * 2)

    # -- movement --------------------------------------------------------
    def pan_screen(self, dx: float, dy: float) -> None:
        self.x -= dx / self.zoom
        self.y -= dy / self.zoom
        self.clamp()

    def nudge(self, dx: float, dy: float) -> None:
        """dx/dy in world pixels."""
        self.x += dx
        self.y += dy
        self.clamp()

    def zoom_at(self, sx: float, sy: float, delta: int) -> None:
        wx, wy = self.screen_to_world(sx, sy)
        new_zoom = max(self.MIN_ZOOM, min(self.MAX_ZOOM, self.zoom + delta))
        if new_zoom == self.zoom:
            return
        self.zoom = new_zoom
        self.x = wx - sx / self.zoom
        self.y = wy - sy / self.zoom
        self.clamp()

    def soft_follow(self, wx: float, wy: float, dt: float) -> None:
        """Keep a point inside a comfortable centre box, easing toward it."""
        left = self.x + self.view_world_w * 0.30
        right = self.x + self.view_world_w * 0.70
        top = self.y + self.view_world_h * 0.28
        bottom = self.y + self.view_world_h * 0.72
        tx = self.x + self.view_world_w / 2
        ty = self.y + self.view_world_h / 2
        if wx < left:
            tx = wx - self.view_world_w * 0.20
        elif wx > right:
            tx = wx + self.view_world_w * 0.20
        if wy < top:
            ty = wy - self.view_world_h * 0.20
        elif wy > bottom:
            ty = wy + self.view_world_h * 0.20
        target_x = tx - self.view_world_w / 2
        target_y = ty - self.view_world_h / 2
        ease = min(1.0, dt * 3.0)
        self.x += (target_x - self.x) * ease
        self.y += (target_y - self.y) * ease
        self.clamp()
