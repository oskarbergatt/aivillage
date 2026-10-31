"""Extracted methods for UI."""
from __future__ import annotations

from .ui_shared import (
    P,
    _truncate,
    draw_text,
    draw_wrapped,
    pygame,
)


class InspectorMixin:
    def _bottom(self, screen, app, w, h) -> None:
        if app.chat.active:
            return
        bar = pygame.Rect(0, h - 34, w, 34)
        pygame.draw.rect(screen, (20, 18, 28), bar)
        pygame.draw.line(screen, P["ui_line"], (0, bar.y), (w, bar.y))
        hint = self.i18n.t("ui.hint_pan") + " · T talk · J jobs · C chronicle · F3 settings · F10 photo"
        draw_text(screen, hint, (16, bar.y + 9), 16, P["ui_dim"])

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
        role = t(f"job.{p.job}")
        if p.age:
            role += " · " + t("ui.age", age=p.age)
        if p.is_child and p.dream_job:
            role += " · " + t("ui.dream", job=t(f"job.{p.dream_job}"))
        draw_text(screen, _truncate(role, 16, rect.right - rect.x - 136),
                  (rect.x + 122, rect.y + 38), 16, P["ui_accent"])
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
        if p.ambition:
            draw_text(screen, t("ui.ambition"), (rect.x + 14, y), 16, P["ui_dim"])
            draw_text(screen, _truncate(p.ambition, 16, rect.w - 132),
                      (rect.x + 110, y), 16, P["ui_accent"])
            y += 20

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
        for line in agent.memory.recent(1):
            y += draw_wrapped(screen, "· " + line, (rect.x + 14, y), rect.w - 28,
                              16, P["ui_dim"], max_lines=1) + 4

        if app.llm.available:
            full = rect.w - 28
            chat_w = int(full * 0.56)
            gap = 8
            chat_btn = pygame.Rect(rect.x + 14, rect.bottom - 40, chat_w, 28)
            self_btn = pygame.Rect(chat_btn.right + gap, rect.bottom - 40,
                                   full - chat_w - gap, 28)
            self._button(screen, chat_btn, t("ui.chat_short"), "talk",
                         active=True, size=16)
            self._button(screen, self_btn, t("ui.self_short"), "self",
                         active=getattr(app, "self_pending", None) == agent.key,
                         size=16)
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

