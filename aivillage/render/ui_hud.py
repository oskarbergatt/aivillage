"""Extracted methods for UI."""
from __future__ import annotations

from .provider_setup import draw_provider_setup
from .ambient_model import draw_ambient_model
from .gateway_setup import draw_gateway_setup
from .help import draw_help

from .ui_shared import (
    P,
    TITLE,
    _truncate,
    draw_settings,
    draw_text,
    get_font,
    pygame,
)


class HudMixin:
    def _panel(self, screen, rect, fill=P["ui_bg"], border=P["ui_line"],
               shadow: bool = True) -> None:
        if shadow:
            pygame.draw.rect(screen, (10, 9, 16), rect.move(3, 3))
        pygame.draw.rect(screen, fill, rect)
        pygame.draw.rect(screen, border, rect, 1)
        pygame.draw.rect(screen, P["ui_bg2"], (rect.x + 1, rect.y + 1,
                                               rect.w - 2, 2))

    def _button(self, screen, rect, label: str, action: str,
                active: bool = False, enabled: bool = True, size: int = 16) -> None:
        hover = enabled and rect.collidepoint(self._mouse)
        if not enabled:
            fill, fg = (34, 32, 44), (98, 92, 110)
        elif active:
            fill, fg = (92, 78, 42), P["ui_accent"]
        elif hover:
            fill, fg = (64, 58, 78), P["ui_text"]
        else:
            fill, fg = P["ui_bg2"], P["ui_dim"]
        pygame.draw.rect(screen, fill, rect)
        pygame.draw.rect(screen, P["ui_line"] if enabled else (58, 52, 68), rect, 1)
        draw_text(screen, label, rect.center, size, fg, anchor="center")
        if enabled:
            self.hits[action] = rect

    def _bar(self, screen, rect, value: float, colour, label: str = "",
             size: int = 16) -> None:
        pygame.draw.rect(screen, (26, 24, 36), rect)
        fill = rect.copy()
        fill.w = int(rect.w * max(0.0, min(1.0, value)))
        if fill.w > 0:
            pygame.draw.rect(screen, colour, fill)
        pygame.draw.rect(screen, P["ui_line"], rect, 1)
        if label:
            draw_text(screen, label, (rect.x, rect.centery - 1), size,
                      P["ui_text"], anchor="midleft")

    def _chip(self, screen, pos, label: str, colour, value: str,
              size: int = 16) -> int:
        x, y = pos
        pygame.draw.rect(screen, colour, (x, y + 3, 9, 9))
        draw_text(screen, value, (x + 15, y), size, P["ui_text"])
        width = 15 + get_font(size).size(value)[0] + 18
        if label:
            draw_text(screen, label, (x + 15 + get_font(size).size(value)[0] + 6, y),
                      size, P["ui_dim"])
            width += 6 + get_font(size).size(label)[0]
        return width

    def draw(self, screen, app, dt: float) -> None:
        self.hits = {}
        self._mouse = pygame.mouse.get_pos()
        self._pulse += dt
        w, h = screen.get_size()
        self._top_left(screen, app, w, h)
        self._top_right(screen, app, w, h)
        self._bottom(screen, app, w, h)
        if app.selected is not None:
            self._inspector(screen, app, w, h)
        if getattr(app, "dispatch_card", None) is not None:
            self._dispatch(screen, app, w, h)
        if app.chat.active:
            self._chat(screen, app, w, h)
        if not app.llm.available and not app.setup_dismissed:
            self._setup(screen, app, w, h)
        self._toasts(screen, app, w, h)
        if app.show_chronicle:
            self._chronicle(screen, app, w, h)
        if getattr(app, "show_jobs", False):
            self._jobs(screen, app, w, h)
        if app.show_settings:
            self.hits = {}
            draw_settings(self, screen, app, w, h)
        if app.show_provider_setup:
            self.hits = {}
            draw_provider_setup(self, screen, app, w, h)
        if app.show_ambient_model:
            self.hits = {}
            draw_ambient_model(self, screen, app, w, h)
        if app.show_gateway:
            self.hits = {}
            draw_gateway_setup(self, screen, app, w, h)
        if app.show_help:
            self.hits = {}
            draw_help(self, screen, app, w, h)

    def _top_left(self, screen, app, w, h) -> None:
        t = self.i18n.t
        rect = pygame.Rect(16, 16, 478, 164)
        self._panel(screen, rect)
        draw_text(screen, TITLE, (rect.x + 14, rect.y + 10), 16, P["ui_accent"],
                  chunky=True)
        badge = "LIVE" if app.clock.is_live else (
            t("ui.paused") if app.clock.paused else f"{app.clock.sim_speed}x")
        badge_colour = P["ui_good"] if app.clock.is_live else (
            P["ui_warn"] if app.clock.paused else P["ui_cool"])
        bw = get_font(8).size(badge)[0] + 18
        pygame.draw.rect(screen, (24, 30, 26), (rect.right - bw - 12, rect.y + 10,
                                                bw, 20))
        pygame.draw.rect(screen, badge_colour, (rect.right - bw - 12, rect.y + 10,
                                                bw, 20), 1)
        draw_text(screen, badge, (rect.right - bw - 3, rect.y + 20), 8,
                  badge_colour, anchor="midright")

        draw_text(screen, app.clock.clock_text(), (rect.x + 14, rect.y + 38), 24,
                  P["ui_text"])
        draw_text(screen, app.clock.date_text(), (rect.x + 130, rect.y + 42), 16,
                  P["ui_dim"])
        draw_text(screen, t(f"weekday.{app.clock.weekday()}"), (rect.x + 130, rect.y + 62),
                  16, P["ui_dim"])
        draw_text(screen, t(f"season.{app.clock.season()}"), (rect.x + 14, rect.y + 74),
                  16, P["ui_accent"])

        weather = app.weather
        line = f"{t('weather.' + weather.condition)} · {weather.temp_c:.0f}°C"
        draw_text(screen, line, (rect.x + 14, rect.y + 94), 16, P["ui_text"])
        if weather.wind > 0:
            draw_text(screen, f"{weather.wind:.0f} km/h", (rect.x + 250, rect.y + 94),
                      16, P["ui_dim"])
        loc = app.locations.location
        draw_text(screen, _truncate(loc.label, 16, rect.w - 28),
                  (rect.x + 14, rect.y + 112), 16, P["ui_dim"])
        src = "live" if weather.source == "live" else (
            t("ui.offline_weather"))
        draw_text(screen, src, (rect.right - 14, rect.y + 112), 8,
                  P["ui_dim"], anchor="topright")

        x = rect.x + 14
        y = rect.y + 134
        for key, colour, value in (
                ("wood", P["wood_l"], app.stats["wood"]),
                ("stone", P["stone_l"], app.stats["stone"]),
                ("food", P["ui_good"], app.stats["food"]),
                ("coin", P["ui_accent"], app.stats["coin"])):
            chip_w = 9 + 22 + get_font(16).size(str(int(value)))[0] + \
                get_font(16).size(t(f"ui.{key}"))[0] + 14
            if x + chip_w > rect.right - 10:
                break
            x += self._chip(screen, (x, y), t(f"ui.{key}"), colour, str(int(value)))
            x += 8

    def _top_right(self, screen, app, w, h) -> None:
        t = self.i18n.t
        width = 430
        rect = pygame.Rect(w - width - 16, 16, width, 164)
        self._panel(screen, rect)

        model = app.llm.label
        colour = P["ui_good"] if app.llm.available else P["ui_bad"]
        draw_text(screen, _truncate(model, 16, rect.w - 28),
                  (rect.x + 14, rect.y + 8), 16, colour)

        status = app.news.status()
        news_line = (f"{status['feeds_ok']}/{status['feeds_total']} feeds · "
                     f"{status['unused']} unread")
        if status["pending"]:
            news_line = "retelling a dispatch…"
        draw_text(screen, _truncate(news_line, 16, 250), (rect.x + 14, rect.y + 28),
                  16, P["ui_dim"])
        draw_text(screen, t("ui.language") + ": " + app.i18n.language.upper(),
                  (rect.right - 14, rect.y + 28), 16, P["ui_dim"],
                  anchor="topright")

        row1 = pygame.Rect(rect.x + 12, rect.y + 52, rect.w - 24, 26)
        labels = [("||" if not app.clock.paused else ">", "pause"),
                  ("1x", "speed:2"), ("2x", "speed:2"), ("4x", "speed:4"),
                  ("8x", "speed:8"), (t("ui.live"), "live")]
        actions = ["pause", "speed:1", "speed:2", "speed:4", "speed:8", "live"]
        widths = [38, 46, 50, 50, 50, 92]
        x = row1.x
        for (label, _), action, bw in zip(labels, actions, widths):
            active = False
            if action == "pause":
                active = app.clock.paused
            elif action == "live":
                active = app.clock.is_live
            elif action.startswith("speed:"):
                n = int(action.split(":")[1])
                active = (not app.clock.live) and app.clock.sim_speed == n
            r = pygame.Rect(x, row1.y, bw, row1.h)
            self._button(screen, r, label, action, active=active)
            x += bw + 6

        row2 = pygame.Rect(rect.x + 12, rect.y + 86, rect.w - 24, 26)
        x = row2.x
        talk_agent = app.selected_agent()
        buttons = [
            ("EN" if app.i18n.language == "de" else "DE", 56, "lang", False, True),
            ("UNMUTE" if app.voice.muted else "MUTE", 76, "mute",
             app.voice.muted, True),
            ("C", 46, "chronicle", app.show_chronicle, True),
            ("S", 46, "save", False, True),
            ("V", 46, "visitor", False, True),
            ("J", 46, "jobs", getattr(app, "show_jobs", False), True),
            ("R", 46, "self", app.self_pending is not None,
             talk_agent is not None and app.llm.available),
        ]
        for label, bw, action, active, enabled in buttons:
            self._button(screen, pygame.Rect(x, row2.y, bw, row2.h), label,
                         action, active=active, enabled=enabled)
            x += bw + 5
        draw_text(screen, _truncate(app.voice.label(), 8, 46),
                  (rect.right - 14, row1.y + 9), 8, P["ui_dim"],
                  anchor="topright")
        draw_text(screen, _truncate(app.llm.cost_text(), 8, 200),
                  (rect.right - 14, rect.y + 150), 8, P["ui_dim"], anchor="topright")

        if app.world.build_site is not None:
            prog = app.world.build_site.progress
            draw_text(screen, f"Town hall {int(prog * 100)}%",
                      (rect.x + 14, rect.y + 124), 16, P["ui_dim"])
            self._bar(screen, pygame.Rect(rect.x + 150, rect.y + 130, rect.w - 170, 9),
                      prog, P["ui_cool"])
        else:
            draw_text(screen, t("ui.new_village"),
                      (rect.x + 14, rect.y + 124), 16, P["ui_dim"])

