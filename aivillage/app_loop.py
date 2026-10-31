"""Extracted methods for VillageApp."""
from __future__ import annotations

from .app_shared import (
    pygame,
    time,
    traceback,
)


class VillageLoopMixin:
    def _mouse_up(self, e) -> None:
        if e.button != 1 or not self._press_world:
            return
        self._press_world = False
        if self._dragging:
            self._dragging = False
            return
        picked = self._pick(e.pos)
        self.selected = picked
        self.follow_selected = picked is not None
        if picked is not None:
            self.sfx.play("select")

    def _events(self) -> None:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                self.running = False
            elif e.type == pygame.VIDEORESIZE:
                w = max(960, e.w)
                h = max(600, e.h)
                self.screen = pygame.display.set_mode((w, h), pygame.RESIZABLE)
                self.camera.set_view(w, h)
                self.renderer.invalidate()
            elif e.type == pygame.KEYDOWN:
                self._key(e)
            elif e.type == pygame.MOUSEWHEEL:
                if self.show_provider_setup or self.show_settings:
                    continue
                if self.show_chronicle:
                    self.ui.scroll(e.y)
                else:
                    self.camera.zoom_at(*pygame.mouse.get_pos(), e.y)
                    self.renderer.invalidate()
                    self.follow_selected = False
            elif e.type == pygame.MOUSEBUTTONDOWN:
                self._mouse_down(e)
            elif e.type == pygame.MOUSEBUTTONUP:
                self._mouse_up(e)
            elif e.type == pygame.MOUSEMOTION:
                if self._press_world and e.buttons[0]:
                    dx = e.pos[0] - self._drag_last[0]
                    dy = e.pos[1] - self._drag_last[1]
                    if abs(dx) + abs(dy) > 3:
                        self._dragging = True
                        self.follow_selected = False
                        self.camera.pan_screen(dx, dy)
                    self._drag_last = e.pos

        keys = pygame.key.get_pressed()
        if (not self.chat.active and not self.show_chronicle and not self.show_jobs
                and not self.show_settings and not self.show_provider_setup):
            step = 260.0 * (1 / 60.0)
            dx = (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - \
                 (keys[pygame.K_a] or keys[pygame.K_LEFT])
            dy = (keys[pygame.K_s] or keys[pygame.K_DOWN]) - \
                 (keys[pygame.K_w] or keys[pygame.K_UP])
            if dx or dy:
                self.follow_selected = False
                self.camera.nudge(dx * step, dy * step)

    def run(self) -> None:
        self._start_services()
        last = time.perf_counter()
        while self.running:
            now = time.perf_counter()
            frame_dt = min(0.12, max(0.0001, now - last))
            last = now
            self._events()
            self._update(frame_dt)
            self._draw(frame_dt)
            self.pyclock.tick(60)

            elapsed = time.time() - self._started_at
            if self._autoshot and not self._shot_done and elapsed >= self._shot_at:
                self._shot_done = True
                try:
                    pygame.image.save(self.screen, self._autoshot)
                except Exception:
                    traceback.print_exc()
            if self._autoquit and elapsed >= self._autoquit:
                self.running = False
        self.shutdown()

    def shutdown(self) -> None:
        try:
            self.autosave()
        except Exception:
            pass
        try:
            self.news.stop()
        except Exception:
            pass
        self.alerts.stop()
        try:
            self.weather_service.stop()
        except Exception:
            pass
        try:
            self._close_social_tracks()
            self.voice.shutdown()
        except Exception:
            pass
        try:
            self.llm.stop()
        except Exception:
            pass
        pygame.quit()

