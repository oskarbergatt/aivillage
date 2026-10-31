"""World rendering: tiles, depth-sorted props and villagers, light, weather."""
from __future__ import annotations

import math
import random
import time

import pygame

from ..assets import sprites
from ..assets.font import get_font, render, wrap
from ..assets.palette import P, mix
from .camera import Camera

TILE = 16


class Renderer:
    def __init__(self, world, camera: Camera, i18n):
        self.world = world
        self.camera = camera
        self.i18n = i18n
        self._scaled: dict[tuple[int, int], pygame.Surface] = {}
        self._keep: dict[tuple[int, int], pygame.Surface] = {}
        self._overlay: pygame.Surface | None = None
        self._fog: pygame.Surface | None = None
        self._glow_big: pygame.Surface | None = None
        self._glow_small: pygame.Surface | None = None
        self._rain: list[list[float]] = []
        self._snow: list[list[float]] = []
        self._flash = 0.0
        self._rng = random.Random(4242)
        self._last_condition = ""
        self._dots = 0.0

    # -- scaling cache ---------------------------------------------------
    def _scaled_sprite(self, surf: pygame.Surface,
                       factor: float = 1.0) -> pygame.Surface:
        key = (id(surf), self.camera.zoom, round(factor, 3))
        cached = self._scaled.get(key)
        if cached is not None:
            return cached
        scaled = pygame.transform.scale(
            surf, (max(1, int(surf.get_width() * self.camera.zoom * factor)),
                   max(1, int(surf.get_height() * self.camera.zoom * factor))))
        self._scaled[key] = scaled
        self._keep[key] = surf
        return scaled

    def invalidate(self) -> None:
        self._scaled.clear()
        self._keep.clear()

    # -- main draw -------------------------------------------------------
    def draw(self, screen: pygame.Surface, clock, weather, agents, visitors,
             selected, dt: float, night_override: bool | None = None) -> None:
        screen.fill((18, 24, 22))
        cam = self.camera
        vis = cam.visible_rect()
        x0 = max(0, vis.left // TILE)
        y0 = max(0, vis.top // TILE)
        x1 = min(self.world.W - 1, vis.right // TILE)
        y1 = min(self.world.H - 1, vis.bottom // TILE)
        water_frame = int(time.time() * 2.2) % 2

        # ---- ground
        for ty in range(y0, y1 + 1):
            for tx in range(x0, x1 + 1):
                surf = self.world.tile_surface(tx, ty, water_frame)
                img = self._scaled_sprite(surf)
                sx, sy = cam.world_to_screen(tx * TILE, ty * TILE)
                screen.blit(img, (sx, sy))

        # ---- crops
        for plot in self.world.plots:
            if not (x0 <= plot.tx <= x1 and y0 <= plot.ty <= y1):
                continue
            img = self._scaled_sprite(sprites.crop(min(3, plot.stage)))
            sx, sy = cam.world_to_screen(plot.tx * TILE, plot.ty * TILE)
            screen.blit(img, (sx, sy))

        night = night_override if night_override is not None else clock.daylight() < 0.34
        drawables: list[tuple[float, int, object]] = []
        for obj in self.world.objects:
            if not (x0 - 2 <= (obj.x // TILE) <= x1 + 3 and
                    y0 - 4 <= (obj.y // TILE) <= y1 + 3):
                continue
            drawables.append((obj.bottom, 0, obj))
        for agent in agents:
            drawables.append((agent.y, 1, agent))
        for visitor in visitors:
            if visitor.state != "gone":
                drawables.append((visitor.y, 2, visitor))
        drawables.sort(key=lambda d: (d[0], d[1]))

        for _, kind, ent in drawables:
            if kind == 0:
                self._draw_object(screen, ent, night)
            elif kind == 1:
                self._draw_agent(screen, ent, selected)
            else:
                self._draw_visitor(screen, ent, selected)

        # ---- light
        daylight = 0.0 if night_override else clock.daylight()
        self._draw_light(screen, clock, daylight, night)

        # ---- weather
        if weather.condition != self._last_condition:
            self._reset_particles(weather.condition, screen.get_size())
            self._last_condition = weather.condition
        self._draw_weather(screen, weather, dt)

        # ---- speech bubbles (above everything, below UI)
        for agent in agents:
            if agent.bubble:
                sx, sy = cam.world_to_screen(agent.x, agent.y)
                self._draw_bubble(screen, agent.bubble.text, (sx, sy),
                                  agent.bubble.color, agent.bubble.pending,
                                  agent.bubble.kind)
        for visitor in visitors:
            if visitor.bubble_timer > 0 and visitor.bubble_text and visitor.state != "gone":
                sx, sy = cam.world_to_screen(visitor.x, visitor.y)
                self._draw_bubble(screen, visitor.bubble_text, (sx, sy),
                                  (236, 224, 200), False, "dispatch")

    # -- entities --------------------------------------------------------
    def _draw_object(self, screen, obj, night: bool) -> None:
        img = self._scaled_sprite(obj.image(night))
        sx, sy = self.camera.world_to_screen(obj.x, obj.y)
        screen.blit(img, (sx, sy))

    def _shadow(self, screen, sx: int, sy: int, w: int) -> None:
        rect = pygame.Rect(sx - w // 2, sy - max(2, w // 8), w, max(3, w // 5))
        pygame.draw.ellipse(screen, (58, 86, 60), rect)

    def _draw_agent(self, screen, agent, selected) -> None:
        zoom = self.camera.zoom
        factor = 0.72 if getattr(agent.persona, "is_child", False) else 1.0
        sprite = self._scaled_sprite(agent.sprite(), factor)
        sx, sy = self.camera.world_to_screen(agent.x, agent.y)
        self._shadow(screen, sx, sy, max(7, int(12 * zoom * factor)))
        screen.blit(sprite, (sx - sprite.get_width() // 2,
                             sy - sprite.get_height() + 2))
        if selected is agent:
            pulse = 0.5 + 0.5 * math.sin(time.time() * 5)
            r = int((8 + pulse * 2) * zoom * factor)
            pygame.draw.circle(screen, P["ui_accent"], (sx, sy - 2), r, 2)
            self._name_tag(screen, agent.name, sx, sy - sprite.get_height() - 6,
                           P["ui_accent"])

    def _draw_visitor(self, screen, visitor, selected) -> None:
        zoom = self.camera.zoom
        sprite = self._scaled_sprite(visitor.sprite())
        sx, sy = self.camera.world_to_screen(visitor.x, visitor.y)
        self._shadow(screen, sx, sy, max(10, 12 * zoom))
        screen.blit(sprite, (sx - sprite.get_width() // 2,
                             sy - sprite.get_height() + 2))
        if selected is visitor:
            pulse = 0.5 + 0.5 * math.sin(time.time() * 5)
            r = int((9 + pulse * 2) * zoom)
            pygame.draw.circle(screen, P["ui_cool"], (sx, sy - 2), r, 2)
        self._name_tag(screen, visitor.name, sx, sy - sprite.get_height() - 6,
                       P["ui_cool"])

    def _name_tag(self, screen, text: str, cx: int, y: int, colour) -> None:
        surf = render(text, 16, colour, P["ink"])
        rect = surf.get_rect(midbottom=(cx, y))
        screen.blit(surf, rect)

    # -- light -----------------------------------------------------------
    def _draw_light(self, screen, clock, daylight: float, night: bool) -> None:
        size = screen.get_size()
        if self._overlay is None or self._overlay.get_size() != size:
            self._overlay = pygame.Surface(size, pygame.SRCALPHA)
        phase = clock.phase()
        if night:
            base = (8, 12, 34)
            alpha = 150
        elif phase == "dusk":
            base = (52, 26, 44)
            alpha = int(52 + (1 - daylight) * 44)
        elif phase == "dawn":
            base = (58, 44, 58)
            alpha = int(46 + (1 - daylight) * 44)
        else:
            base = (18, 28, 46)
            alpha = int(max(0.0, (0.72 - daylight)) * 120)
        if alpha <= 2:
            return
        self._overlay.fill((*base, min(190, alpha)))
        screen.blit(self._overlay, (0, 0))

        if alpha < 45:
            return
        if self._glow_big is None:
            self._glow_big = sprites.glow(105, (255, 208, 132))
            self._glow_small = sprites.glow(46, (255, 196, 116))
        vis = self.camera.visible_rect(-64)
        strength = min(1.0, alpha / 120.0)

        def add_glow(surf, sx, sy):
            surf.set_alpha(int(210 * strength))
            screen.blit(surf, (sx - surf.get_width() // 2,
                               sy - surf.get_height() // 2),
                        special_flags=pygame.BLEND_RGBA_ADD)

        for obj in self.world.objects:
            if obj.kind == "lamp":
                if not vis.collidepoint(obj.x, obj.y):
                    continue
                sx, sy = self.camera.world_to_screen(obj.x + 8, obj.y + 4)
                add_glow(self._glow_big, sx, sy)
            elif obj.kind == "house" and night:
                if not vis.collidepoint(obj.x, obj.y):
                    continue
                sx, sy = self.camera.world_to_screen(obj.x + 20, obj.y + 44)
                add_glow(self._glow_small, sx, sy)
                sx2, sy2 = self.camera.world_to_screen(obj.x + 64, obj.y + 44)
                add_glow(self._glow_small, sx2, sy2)
        # warm pools around the plaza lamps at night
        if night:
            for name in ("well", "market"):
                pt = self.world.points.get(name)
                if pt and vis.collidepoint(*pt):
                    sx, sy = self.camera.world_to_screen(*pt)
                    add_glow(self._glow_small, sx, sy)

    # -- weather ---------------------------------------------------------
    def _reset_particles(self, condition: str, size: tuple[int, int]) -> None:
        w, h = size
        self._rain.clear()
        self._snow.clear()
        if condition in ("rain", "showers", "storm", "drizzle"):
            count = 150 if condition == "drizzle" else 260
            for _ in range(count):
                self._rain.append([self._rng.uniform(0, w), self._rng.uniform(0, h),
                                   self._rng.uniform(520, 820),
                                   self._rng.uniform(7, 16)])
        elif condition == "snow":
            for _ in range(190):
                self._snow.append([self._rng.uniform(0, w), self._rng.uniform(0, h),
                                   self._rng.uniform(28, 62),
                                   self._rng.uniform(0, math.tau)])

    def _draw_weather(self, screen, weather, dt: float) -> None:
        w, h = screen.get_size()
        if not self._rain and not self._snow:
            # still allow a fog layer on a freshly resized window
            if weather.condition != "fog":
                return
        if self._rain:
            wind = max(-2.0, min(2.0, weather.wind / 14.0))
            for drop in self._rain:
                drop[1] += drop[2] * dt
                drop[0] += drop[2] * dt * wind * 0.35
                if drop[1] > h:
                    drop[1] = -12
                    drop[0] = self._rng.uniform(-40, w)
                if drop[0] > w + 20:
                    drop[0] = -20
                elif drop[0] < -20:
                    drop[0] = w + 20
                pygame.draw.line(screen, (168, 196, 220),
                                 (drop[0], drop[1]),
                                 (drop[0] - wind * 5, drop[1] + drop[3]), 1)
        if self._snow:
            for flake in self._snow:
                flake[3] += dt * 1.4
                flake[1] += flake[2] * dt
                flake[0] += math.sin(flake[3]) * 14 * dt
                if flake[1] > h:
                    flake[1] = -6
                    flake[0] = self._rng.uniform(0, w)
                if flake[0] < -8:
                    flake[0] = w + 8
                elif flake[0] > w + 8:
                    flake[0] = -8
                pygame.draw.circle(screen, (232, 238, 244),
                                   (int(flake[0]), int(flake[1])), 2)
        if weather.condition == "fog":
            if self._fog is None or self._fog.get_size() != (w, h):
                self._fog = pygame.Surface((w, h), pygame.SRCALPHA)
            self._fog.fill((214, 218, 216, 34))
            t = time.time() * 9
            for i in range(4):
                y = int((t * (8 + i * 3) + i * h / 4) % (h + 200)) - 100
                band = pygame.Rect(0, y, w, 120)
                pygame.draw.rect(self._fog, (228, 230, 226, 22), band)
            screen.blit(self._fog, (0, 0))
        if weather.condition == "storm":
            if self._flash > 0:
                self._flash = max(0.0, self._flash - dt * 3.4)
                alpha = int(self._flash * 90)
                if alpha > 0:
                    flash = pygame.Surface((w, h), pygame.SRCALPHA)
                    flash.fill((210, 220, 255, alpha))
                    screen.blit(flash, (0, 0))
            elif self._rng.random() < dt * 0.16:
                self._flash = 1.0

    # -- bubbles ---------------------------------------------------------
    def _draw_bubble(self, screen, text: str, anchor: tuple[int, int],
                     colour=(240, 232, 210), pending: bool = False,
                     kind: str = "speech") -> None:
        size = 16
        font = get_font(size)
        max_w = 300 if screen.get_width() > 1000 else 220
        if pending:
            dots = "." * (1 + int(self._dots) % 3)
            lines = [dots]
        else:
            lines = wrap(text, size, max_w)[:5]
        if not lines:
            return
        line_h = font.get_height() + 3
        width = max(font.size(line)[0] for line in lines) + 18
        height = line_h * len(lines) + 12
        ax, ay = anchor
        x = max(8, min(screen.get_width() - width - 8, ax - width // 2))
        y = ay - height - 26
        flipped = False
        if y < 8:
            y = ay + 28
            flipped = True
        rect = pygame.Rect(x, y, width, height)
        shadow = rect.move(2, 2)
        pygame.draw.rect(screen, (16, 14, 24), shadow)
        pygame.draw.rect(screen, P["ui_bg"], rect)
        border = P["ui_cool"] if kind == "dispatch" else P["ui_line"]
        pygame.draw.rect(screen, border, rect, 1)
        pygame.draw.rect(screen, P["ui_bg2"], (rect.x + 2, rect.y + 2, rect.w - 4, 2))
        tail_x = max(rect.x + 12, min(rect.right - 12, ax))
        if flipped:
            pygame.draw.polygon(screen, border,
                                [(tail_x - 5, rect.top), (tail_x + 5, rect.top),
                                 (ax, rect.top - 9)])
        else:
            pygame.draw.polygon(screen, border,
                                [(tail_x - 5, rect.bottom - 1),
                                 (tail_x + 5, rect.bottom - 1),
                                 (ax, rect.bottom + 9)])
        for i, line in enumerate(lines):
            img = render(line, size, colour)
            screen.blit(img, (rect.x + 9, rect.y + 7 + i * line_h))
        if pending:
            self._dots += 0.12
