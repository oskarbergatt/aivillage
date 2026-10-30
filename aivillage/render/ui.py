"""Native-resolution pixel UI: HUD, inspector, chat, chronicle, dispatch card."""
from __future__ import annotations

import math
import time

import pygame

from ..assets.font import draw_text, draw_wrapped, get_font, render, wrap
from ..assets.palette import P
from ..agents.needs import clamp

TITLE = "aivillage"


def _truncate(text: str, size: int, width: int) -> str:
    font = get_font(size)
    if font.size(text)[0] <= width:
        return text
    out = text
    while out and font.size(out + "…")[0] > width:
        out = out[:-1]
    return (out.rstrip() + "…") if out else "…"


class UI:
    def __init__(self, i18n):
        self.i18n = i18n
        self.hits: dict[str, pygame.Rect] = {}
        self.chronicle_scroll = 0
        self._mouse = (0, 0)
        self._pulse = 0.0

    # -- primitives ------------------------------------------------------
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

    # -- main ------------------------------------------------------------
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

    # -- HUD -------------------------------------------------------------
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
        self._button(screen, pygame.Rect(x, row2.y, 56, row2.h),
                     "EN" if app.i18n.language == "de" else "DE", "lang")
        x += 62
        self._button(screen, pygame.Rect(x, row2.y, 74, row2.h),
                     "UNMUTE" if app.voice.muted else "MUTE", "mute",
                     active=app.voice.muted)
        x += 80
        self._button(screen, pygame.Rect(x, row2.y, 54, row2.h), "C", "chronicle")
        x += 60
        self._button(screen, pygame.Rect(x, row2.y, 54, row2.h), "S", "save")
        x += 60
        self._button(screen, pygame.Rect(x, row2.y, 62, row2.h), "V", "visitor")
        draw_text(screen, _truncate(app.voice.label(), 16, 120),
                  (rect.right - 14, row2.y + 5), 16, P["ui_dim"], anchor="topright")

        if app.world.build_site is not None:
            prog = app.world.build_site.progress
            draw_text(screen, f"Town hall {int(prog * 100)}%",
                      (rect.x + 14, rect.y + 124), 16, P["ui_dim"])
            self._bar(screen, pygame.Rect(rect.x + 150, rect.y + 130, rect.w - 170, 9),
                      prog, P["ui_cool"])
        else:
            draw_text(screen, t("ui.new_village"),
                      (rect.x + 14, rect.y + 124), 16, P["ui_dim"])

    # -- bottom hint -----------------------------------------------------
    def _bottom(self, screen, app, w, h) -> None:
        if app.chat.active:
            return
        bar = pygame.Rect(0, h - 34, w, 34)
        pygame.draw.rect(screen, (20, 18, 28), bar)
        pygame.draw.line(screen, P["ui_line"], (0, bar.y), (w, bar.y))
        hint = self.i18n.t("ui.hint_pan") + " · T talk · C chronicle · V traveller · " + \
            self.i18n.t("ui.select_lang")
        draw_text(screen, hint, (16, bar.y + 9), 16, P["ui_dim"])

    # -- inspector -------------------------------------------------------
    def _inspector(self, screen, app, w, h) -> None:
        sel = app.selected
        if isinstance(sel, dict):
            return
        width = 392
        top = 192
        rect = pygame.Rect(w - width - 16, top, width, h - top - 52)
        self._panel(screen, rect)
        if hasattr(sel, "persona"):
            self._inspector_agent(screen, app, rect, sel)
        else:
            self._inspector_visitor(screen, app, rect, sel)

    def _inspector_agent(self, screen, app, rect, agent) -> None:
        t = self.i18n.t
        from ..assets import sprites
        p = agent.persona
        portrait = sprites.portrait(p.look.skin, p.look.hair, p.look.cloth,
                                   p.look.hair_style, p.look.hat, p.look.version, 96)
        pr = pygame.Rect(rect.x + 14, rect.y + 14, 96, 96)
        pygame.draw.rect(screen, P["ui_bg2"], pr.inflate(4, 4))
        screen.blit(portrait, pr)
        pygame.draw.rect(screen, P["ui_line"], pr.inflate(4, 4), 1)
        draw_text(screen, p.name, (rect.x + 122, rect.y + 14), 16, P["ui_text"],
                  chunky=True)
        draw_text(screen, t(f"job.{p.job}"), (rect.x + 122, rect.y + 38), 16,
                  P["ui_accent"])
        state = agent.state if agent.state else "idle"
        draw_text(screen, t(f"state.{state}"), (rect.x + 122, rect.y + 58), 16,
                  P["ui_dim"])
        draw_text(screen, f"Day {app.day_number}", (rect.x + 122, rect.y + 78),
                  16, P["ui_dim"])

        y = rect.y + 122
        pygame.draw.line(screen, P["ui_line"], (rect.x + 14, y),
                         (rect.right - 14, y))
        y += 10
        draw_text(screen, t("ui.task"), (rect.x + 14, y), 16, P["ui_dim"])
        task = agent.task_name or t("ui.idle")
        y += 20
        y += draw_wrapped(screen, task, (rect.x + 14, y), rect.w - 28, 16,
                          P["ui_text"], max_lines=2)
        y += 8

        draw_text(screen, t("ui.needs"), (rect.x + 14, y), 16, P["ui_dim"])
        y += 20
        needs = [("hunger", agent.needs.hunger, P["ui_warn"]),
                 ("energy", agent.needs.energy, P["ui_cool"]),
                 ("social", agent.needs.social, P["ui_good"]),
                 ("fun", agent.needs.fun, P["ui_accent"])]
        for key, value, colour in needs:
            draw_text(screen, t(f"ui.{key}"), (rect.x + 14, y), 16, P["ui_dim"])
            self._bar(screen, pygame.Rect(rect.x + 108, y + 4, rect.w - 166, 10),
                      value / 100.0, colour)
            draw_text(screen, str(int(value)), (rect.right - 16, y), 16,
                      P["ui_text"], anchor="topright")
            y += 22
        y += 4

        draw_text(screen, t("ui.traits"), (rect.x + 14, y), 16, P["ui_dim"])
        y += 20
        traits = list(p.traits.items())
        for key, value in traits:
            draw_text(screen, _truncate(t(f"ui.{key}"), 16, 108),
                      (rect.x + 14, y), 16, P["ui_dim"])
            self._bar(screen, pygame.Rect(rect.x + 130, y + 4, 128, 8), value,
                      P["ui_cool"] if value > 0.6 else P["ui_line"])
            y += 18
        y += 4

        draw_text(screen, t("ui.relationships"), (rect.x + 14, y), 16, P["ui_dim"])
        y += 20
        rels = sorted(((k, v) for k, v in agent.memory.affinity.items()),
                      key=lambda kv: -abs(kv[1]))[:2]
        if not rels:
            draw_text(screen, "—", (rect.x + 14, y), 16, P["ui_dim"])
            y += 20
        for key, value in rels:
            other = app.agent_by_key.get(key)
            name = other.name if other else key
            draw_text(screen, _truncate(f"{name} · {agent.memory.relation_word(key)}",
                                        16, rect.w - 28),
                      (rect.x + 14, y), 16, P["ui_good"] if value > 0 else P["ui_warn"])
            y += 20
        y += 4

        draw_text(screen, t("ui.memories"), (rect.x + 14, y), 16, P["ui_dim"])
        y += 20
        for line in agent.memory.recent(2):
            y += draw_wrapped(screen, "· " + line, (rect.x + 14, y), rect.w - 28,
                              16, P["ui_dim"], max_lines=2) + 4

        if app.llm.available:
            btn = pygame.Rect(rect.x + 14, rect.bottom - 40, rect.w - 28, 28)
            self._button(screen, btn, t("ui.chat_hint", name=p.name), "talk",
                         active=True, size=16)
        else:
            draw_text(screen, t("ui.no_llm"), (rect.centerx, rect.bottom - 26), 16,
                      P["ui_bad"], anchor="center")

    def _inspector_visitor(self, screen, app, rect, visitor) -> None:
        t = self.i18n.t
        from ..assets import sprites
        portrait = sprites.portrait(visitor.skin, visitor.hair, visitor.cloth,
                                   visitor.hair_style, visitor.hat, visitor.version, 96)
        pr = pygame.Rect(rect.x + 14, rect.y + 14, 96, 96)
        pygame.draw.rect(screen, P["ui_bg2"], pr.inflate(4, 4))
        screen.blit(portrait, pr)
        pygame.draw.rect(screen, P["ui_line"], pr.inflate(4, 4), 1)
        draw_text(screen, visitor.name, (rect.x + 122, rect.y + 14), 16,
                  P["ui_text"], chunky=True)
        draw_text(screen, visitor.trade, (rect.x + 122, rect.y + 38), 16,
                  P["ui_cool"])
        draw_text(screen, t("ui.news_from") + " " + visitor.origin,
                  (rect.x + 122, rect.y + 58), 16, P["ui_dim"])
        draw_text(screen, t("ui." + visitor.state) if t("ui." + visitor.state)
                  != "ui." + visitor.state else visitor.state,
                  (rect.x + 122, rect.y + 78), 16, P["ui_dim"])
        y = rect.y + 128
        pygame.draw.line(screen, P["ui_line"], (rect.x + 14, y), (rect.right - 14, y))
        y += 12
        if visitor.dispatch:
            d = visitor.dispatch
            draw_text(screen, t("ui.dispatch"), (rect.x + 14, y), 16, P["ui_dim"])
            y += 22
            y += draw_wrapped(screen, d.headline, (rect.x + 14, y), rect.w - 28,
                              16, P["ui_text"], max_lines=4)
            y += 10
            draw_text(screen, t("ui.real_headline"), (rect.x + 14, y), 16,
                      P["ui_dim"])
            y += 20
            y += draw_wrapped(screen, d.original or "—", (rect.x + 14, y),
                              rect.w - 28, 16, P["ui_dim"], max_lines=3)
            y += 8
            draw_text(screen, f"— {d.source}", (rect.x + 14, y), 16, P["ui_dim"])
        else:
            draw_text(screen, t("ui.no_news"), (rect.x + 14, y), 16, P["ui_dim"])

    # -- dispatch card ---------------------------------------------------
    def _dispatch(self, screen, app, w, h) -> None:
        t = self.i18n.t
        visitor = app.dispatch_card
        d = visitor.dispatch
        if not d:
            return
        rect = pygame.Rect(16, h - 34 - 200, 620, 190)
        self._panel(screen, rect, fill=(34, 30, 44))
        draw_text(screen, t("ui.dispatch"), (rect.x + 14, rect.y + 10), 16,
                  P["ui_cool"])
        draw_text(screen, f"{visitor.name} · {visitor.trade}", (rect.x + 110,
                                                               rect.y + 10),
                  16, P["ui_text"])
        self._button(screen, pygame.Rect(rect.right - 38, rect.y + 8, 24, 24),
                     "x", "close_dispatch")
        y = rect.y + 40
        y += draw_wrapped(screen, d.headline, (rect.x + 14, y), rect.w - 28, 16,
                          P["ui_text"], max_lines=3)
        y += 8
        pygame.draw.line(screen, P["ui_line"], (rect.x + 14, y), (rect.right - 14, y))
        y += 8
        draw_text(screen, t("ui.real_headline"), (rect.x + 14, y), 16, P["ui_dim"])
        y += 18
        y += draw_wrapped(screen, d.original or "—", (rect.x + 14, y), rect.w - 28,
                          16, P["ui_dim"], max_lines=2)
        draw_text(screen, f"— {d.source}", (rect.right - 14, y + 2), 16,
                  P["ui_dim"], anchor="topright")

    # -- chat ------------------------------------------------------------
    def _chat(self, screen, app, w, h) -> None:
        t = self.i18n.t
        chat = app.chat
        width = min(1000, w - 48)
        height = 268
        rect = pygame.Rect((w - width) // 2, h - height - 48, width, height)
        self._panel(screen, rect, fill=(32, 28, 42))
        agent = app.agent_by_key.get(chat.target or "")
        name = agent.name if agent else "—"
        draw_text(screen, f"You · {name}", (rect.x + 16, rect.y + 10), 16,
                  P["ui_accent"], chunky=True)
        self._button(screen, pygame.Rect(rect.right - 38, rect.y + 8, 24, 24),
                     "x", "close_chat")

        body = pygame.Rect(rect.x + 16, rect.y + 40, rect.w - 32, height - 100)
        pygame.draw.rect(screen, (24, 22, 34), body)
        pygame.draw.rect(screen, P["ui_line"], body, 1)
        y = body.y + 8
        lines = chat.lines[-7:]
        for speaker, text in lines:
            prefix = "you" if speaker == "you" else (agent.name.split()[0]
                                                     if agent else "them")
            colour = P["ui_cool"] if speaker == "you" else P["ui_text"]
            draw_text(screen, prefix, (body.x + 10, y), 16, P["ui_dim"])
            used = draw_wrapped(screen, text, (body.x + 86, y), body.w - 100, 16,
                                colour, max_lines=3)
            y += max(20, used) + 2
            if y > body.bottom - 22:
                break
        if chat.pending:
            dots = "*" * (1 + int(self._pulse * 3) % 3)
            draw_text(screen, dots, (body.right - 14, body.bottom - 22), 16,
                      P["ui_accent"], anchor="topright")
        elif not chat.lines:
            draw_text(screen, t("ui.chat_placeholder"), (body.centerx, body.centery),
                      16, P["ui_dim"], anchor="center")

        field = pygame.Rect(rect.x + 16, rect.bottom - 48, rect.w - 100, 34)
        pygame.draw.rect(screen, (22, 20, 30), field)
        pygame.draw.rect(screen, P["ui_accent"] if chat.active else P["ui_line"],
                         field, 1)
        shown = chat.input
        if chat.active and int(time.time() * 2) % 2 == 0:
            shown += "|"
        draw_text(screen, _truncate(shown or t("ui.chat_placeholder"), 16,
                                    field.w - 20),
                  (field.x + 10, field.centery), 16,
                  P["ui_text"] if chat.input else P["ui_dim"], anchor="midleft")
        self._button(screen, pygame.Rect(field.right + 8, field.y, 70, 34),
                     "SEND", "send", active=bool(chat.input.strip()),
                     enabled=bool(chat.input.strip()) and not chat.pending)
        draw_text(screen, "Enter send · Esc close", (rect.right - 16, rect.y + 12),
                  8, P["ui_dim"], anchor="topright")

    # -- setup -----------------------------------------------------------
    def _setup(self, screen, app, w, h) -> None:
        t = self.i18n.t
        rect = pygame.Rect(16, h - 34 - 166, 560, 156)
        self._panel(screen, rect, fill=(38, 26, 34), border=(126, 78, 82))
        draw_text(screen, t("ui.no_llm"), (rect.x + 16, rect.y + 12), 16,
                  P["ui_bad"], chunky=True)
        y = rect.y + 40
        y += draw_wrapped(screen, t("ui.no_llm_hint"), (rect.x + 16, y),
                          rect.w - 140, 16, P["ui_text"], max_lines=3)
        draw_text(screen, "Ollama:  ollama run llama3.2", (rect.x + 16, y + 4),
                  16, P["ui_dim"])
        draw_text(screen, "OpenAI:  OPENAI_API_KEY=... in .env", (rect.x + 16,
                                                                  y + 24),
                  16, P["ui_dim"])
        self._button(screen, pygame.Rect(rect.right - 112, rect.y + 40, 96, 28),
                     "RETRY", "llm_retry")
        self._button(screen, pygame.Rect(rect.right - 38, rect.y + 8, 24, 24),
                     "x", "close_setup")

    # -- toasts ----------------------------------------------------------
    def _toasts(self, screen, app, w, h) -> None:
        y = 196
        for text, ttl in list(app.toasts)[-3:]:
            alpha = 1.0 if ttl > 1.2 else max(0.0, ttl / 1.2)
            surf = render(text, 16, P["ui_text"])
            width = min(w - 40, surf.get_width() + 34)
            rect = pygame.Rect((w - width) // 2, y, width, 34)
            panel = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
            panel.fill((28, 24, 38, int(232 * alpha)))
            pygame.draw.rect(panel, (*P["ui_accent"], int(220 * alpha)), panel.get_rect(), 1)
            screen.blit(panel, rect.topleft)
            draw_text(screen, _truncate(text, 16, width - 28),
                      (rect.centerx, rect.centery), 16,
                      (*P["ui_text"],) if alpha >= 1 else P["ui_text"], anchor="center")
            y += 40

    # -- chronicle -------------------------------------------------------
    def _chronicle(self, screen, app, w, h) -> None:
        t = self.i18n.t
        shade = pygame.Surface((w, h), pygame.SRCALPHA)
        shade.fill((8, 8, 14, 190))
        screen.blit(shade, (0, 0))
        rect = pygame.Rect((w - min(1020, w - 60)) // 2,
                           (h - min(680, h - 60)) // 2,
                           min(1020, w - 60), min(680, h - 60))
        self._panel(screen, rect, fill=(28, 25, 38), border=P["ui_line"])
        draw_text(screen, t("ui.chronicle"), (rect.x + 20, rect.y + 14), 16,
                  P["ui_accent"], chunky=True)
        draw_text(screen, f"{app.clock.date_text()} · Day {app.day_number}",
                  (rect.x + 190, rect.y + 18), 16, P["ui_dim"])
        self._button(screen, pygame.Rect(rect.right - 44, rect.y + 10, 30, 30),
                     "x", "close_chronicle")

        body = pygame.Rect(rect.x + 20, rect.y + 56, rect.w - 40, rect.h - 76)
        clip = screen.get_clip()
        screen.set_clip(body)
        y = body.y + 4
        diary = app.diaries.get(app.current_day_key)
        if diary:
            draw_text(screen, t("ui.diary"), (body.x, y), 16, P["ui_accent"])
            y += 20
            y += draw_wrapped(screen, diary, (body.x, y), body.w - 20, 16,
                              P["ui_text"], max_lines=5) + 10
            pygame.draw.line(screen, P["ui_line"], (body.x, y),
                             (body.right - 10, y))
            y += 10

        entries = list(reversed(app.chronicle))
        if not entries:
            draw_text(screen, "—", (body.centerx, body.y + 40), 16, P["ui_dim"],
                      anchor="center")
        start = max(0, self.chronicle_scroll)
        for entry in entries[start:start + 16]:
            head = f"{entry.get('day', '')} {entry.get('time', '')}".strip()
            draw_text(screen, head, (body.x, y), 16, P["ui_dim"])
            used = draw_wrapped(screen, entry.get("text", ""),
                                (body.x + 130, y), body.w - 150, 16,
                                P["ui_text"], max_lines=3)
            y += max(22, used) + 4
        screen.set_clip(clip)

        visits = app.news.recent_visits(6)
        if visits:
            vy = rect.bottom - 30
            draw_text(screen, f"{len(visits)} recent dispatches · scroll to read",
                      (rect.x + 20, vy), 8, P["ui_dim"])

    # -- input -----------------------------------------------------------
    def action_at(self, pos) -> str | None:
        for action, rect in reversed(list(self.hits.items())):
            if rect.collidepoint(pos):
                return action
        return None

    def scroll(self, dy: int) -> None:
        delta = -1 if dy > 0 else 1
        self.chronicle_scroll = max(0, self.chronicle_scroll + delta)
