"""Help window: controls, the latest change and village working hours."""
from __future__ import annotations

from .ui_shared import (
    P,
    draw_text,
    draw_wrapped,
    get_font,
    pygame,
    wrap,
)


CONTROLS = (
    "help.controls_pan",
    "help.controls_talk",
    "help.controls_time",
    "help.controls_misc",
    "help.controls_extra",
)

WORK = (
    "help.work_day",
    "help.work_night",
    "help.work_kid",
    "help.work_market",
    "help.work_note",
)


def _section_height(t, heading: str, body: tuple[str, ...], size: int,
                    width: int) -> int:
    height = 24
    line_h = get_font(size).get_height() + 2
    for key in body:
        height += len(wrap(t(key), size, width)) * line_h + 2
    return height + 12


def _draw_section(screen, t, pos, heading: str, body: tuple[str, ...],
                  size: int, width: int) -> int:
    x, y = pos
    draw_text(screen, t(heading), (x, y), 16, P["ui_accent"], chunky=True)
    y += 24
    for key in body:
        y += draw_wrapped(screen, t(key), (x, y), width, size, P["ui_text"]) + 2
    return y + 12


def draw_help(ui, screen, app, w: int, h: int) -> None:
    t = app.i18n.t
    shade = pygame.Surface((w, h), pygame.SRCALPHA)
    shade.fill((8, 8, 14, 210))
    screen.blit(shade, (0, 0))

    width = min(980, w - 48)
    height = min(620, h - 48)
    rect = pygame.Rect((w - width) // 2, (h - height) // 2, width, height)
    ui._panel(screen, rect, fill=(28, 25, 38), border=P["ui_accent"])

    draw_text(screen, t("help.title"), (rect.x + 24, rect.y + 16), 24,
              P["ui_accent"], chunky=True)
    draw_text(screen, t("help.subtitle"), (rect.x + 24, rect.y + 52), 8,
              P["ui_dim"])
    ui._button(screen, pygame.Rect(rect.right - 44, rect.y + 12, 30, 30),
               "x", "close_help")

    x = rect.x + 24
    inner = rect.w - 48
    y = rect.y + 76
    pygame.draw.line(screen, P["ui_line"], (x, y), (rect.right - 24, y))
    y += 14

    top = y
    body_size = 16
    needed = (
        _section_height(t, "help.controls_title", CONTROLS, 8, inner)
        + _section_height(t, "help.update_title", ("help.update_body",),
                          body_size, inner)
        + _section_height(t, "help.work_title", WORK, body_size, inner)
    )
    if needed > rect.bottom - top - 20:
        body_size = 8

    y = _draw_section(screen, t, (x, y), "help.controls_title", CONTROLS, 8,
                      inner)
    y = _draw_section(screen, t, (x, y), "help.update_title",
                      ("help.update_body",), body_size, inner)
    _draw_section(screen, t, (x, y), "help.work_title", WORK, body_size, inner)
