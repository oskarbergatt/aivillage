"""Extracted methods for UI."""
from __future__ import annotations

from .ui_shared import (
    ADULT_JOBS,
    JOBS,
    P,
    _truncate,
    draw_text,
    draw_wrapped,
    pygame,
    render,
    time,
)


class DialogsMixin:
    def _chat(self, screen, app, w, h) -> None:
        t = self.i18n.t
        chat = app.chat
        width = min(1000, w - 48)
        height = 268
        rect = pygame.Rect((w - width) // 2, h - height - 48, width, height)
        self._panel(screen, rect, fill=(32, 28, 42))
        agent = app.agent_by_key.get(chat.target or "")
        name = agent.name if agent else "—"
        draw_text(screen, f"{t('ui.you')} · {name}", (rect.x + 16, rect.y + 10), 16,
                  P["ui_accent"], chunky=True)
        self._button(screen, pygame.Rect(rect.right - 38, rect.y + 8, 24, 24),
                     "x", "close_chat")

        body = pygame.Rect(rect.x + 16, rect.y + 40, rect.w - 32, height - 100)
        pygame.draw.rect(screen, (24, 22, 34), body)
        pygame.draw.rect(screen, P["ui_line"], body, 1)
        y = body.y + 8
        lines = chat.lines[-7:]
        for speaker, text in lines:
            prefix = t("ui.you") if speaker == "you" else (agent.name.split()[0]
                                                             if agent else t("ui.them"))
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
                     t("ui.send"), "send", active=bool(chat.input.strip()),
                     enabled=bool(chat.input.strip()) and not chat.pending)
        draw_text(screen, t("ui.chat_controls"), (rect.right - 16, rect.y + 12),
                  8, P["ui_dim"], anchor="topright")

    def _setup(self, screen, app, w, h) -> None:
        t = self.i18n.t
        rect = pygame.Rect(16, h - 34 - 208, 620, 198)
        self._panel(screen, rect, fill=(38, 26, 34), border=(126, 78, 82))
        draw_text(screen, t("ui.no_llm"), (rect.x + 16, rect.y + 12), 16,
                  P["ui_bad"], chunky=True)
        y = rect.y + 40
        y += draw_wrapped(screen, t("ui.no_llm_hint"), (rect.x + 16, y),
                          rect.w - 140, 16, P["ui_text"], max_lines=3)
        lines = [t(key) for key in (
            "setup.example_ollama", "setup.example_openai",
            "setup.example_claude", "setup.example_codex")]
        for i, line in enumerate(lines):
            draw_text(screen, line, (rect.x + 16, y + 4 + i * 20), 16, P["ui_dim"])
        self._button(screen, pygame.Rect(rect.right - 112, rect.y + 40, 96, 28),
                      t("ui.retry"), "llm_retry")
        self._button(screen, pygame.Rect(rect.right - 112, rect.y + 76, 96, 28),
                     t("setup.open"), "provider_open")
        self._button(screen, pygame.Rect(rect.right - 38, rect.y + 8, 24, 24),
                     "x", "close_setup")

    def _jobs(self, screen, app, w, h) -> None:
        t = self.i18n.t
        shade = pygame.Surface((w, h), pygame.SRCALPHA)
        shade.fill((8, 8, 14, 190))
        screen.blit(shade, (0, 0))
        width = min(780, w - 60)
        height = min(560, h - 60)
        rect = pygame.Rect((w - width) // 2, (h - height) // 2, width, height)
        self._panel(screen, rect, fill=(28, 25, 38), border=P["ui_line"])
        draw_text(screen, t("ui.jobs"), (rect.x + 20, rect.y + 14), 16,
                  P["ui_accent"], chunky=True)
        draw_text(screen, t("ui.jobs_hint"), (rect.x + 20, rect.y + 38), 8,
                  P["ui_dim"])
        self._button(screen, pygame.Rect(rect.right - 44, rect.y + 10, 30, 30),
                     "x", "close_jobs")

        body = pygame.Rect(rect.x + 20, rect.y + 62, rect.w - 40, rect.h - 82)
        keys = list(ADULT_JOBS) + ["child"]
        rows = (len(keys) + 1) // 2
        colw = body.w // 2
        rowh = max(24, min(34, body.h // max(1, rows)))
        selected = app.selected_agent()
        for idx, key in enumerate(keys):
            col = idx // rows
            row = idx % rows
            x = body.x + col * colw
            y = body.y + row * rowh
            job = JOBS[key]
            active = selected is not None and selected.persona.job == key
            dream = (selected is not None and selected.persona.is_child
                     and selected.persona.dream_job == key)
            colour = (P["ui_accent"] if active else
                      (P["ui_cool"] if dream else P["ui_text"]))
            draw_text(screen, t(f"job.{key}"), (x, y), 16, colour)
            if key == "child":
                holders = [a.name.split()[0] for a in app.agents
                           if a.persona.is_child]
            else:
                holders = [a.name.split()[0] for a in app.agents
                           if not a.persona.is_child and a.persona.job == key]
            detail = ", ".join(holders) if holders else t("ui.job_open")
            draw_text(screen, _truncate(detail, 8, colw - 200), (x + 148, y + 4),
                      8, P["ui_dim"])
            if job.resource and not job.child:
                gain = (t("ui.progress") if job.resource == "progress"
                        else f"+{job.amount:g} {t('ui.' + job.resource)}")
                draw_text(screen, gain, (x + colw - 14, y + 4), 8, P["ui_dim"],
                          anchor="topright")

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
        draw_text(screen, f"{app.clock.date_text()} · "
                  f"{t('ui.day_count', day=app.day_number)}",
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
            draw_text(screen, t("ui.recent_dispatches", count=len(visits)),
                      (rect.x + 20, vy), 8, P["ui_dim"])

    def action_at(self, pos) -> str | None:
        for action, rect in reversed(list(self.hits.items())):
            if rect.collidepoint(pos):
                return action
        return None

    def scroll(self, dy: int) -> None:
        delta = -1 if dy > 0 else 1
        self.chronicle_scroll = max(0, self.chronicle_scroll + delta)

