"""Pixel fonts and text helpers.

Silkscreen is used for body text (designed on an 8px grid, so 8/16/24 stay crisp),
Press Start 2P for the few places that want extra chunk.
"""
from __future__ import annotations

import pygame

from ..config import FONT_DIR
from .palette import P

_CACHE: dict[tuple[int, bool], pygame.font.Font] = {}
_PATH_CACHE: dict[int, bool] = {}


def clear_cache() -> None:
    """Drop cached Font objects (they die when the font module is quit)."""
    _CACHE.clear()
    _PATH_CACHE.clear()


def _font_path(size: int) -> str | None:
    if size >= 16:
        p = FONT_DIR / "PressStart2P-Regular.ttf"
    else:
        p = FONT_DIR / "Silkscreen-Regular.ttf"
    return str(p) if p.exists() else None


def get_font(size: int = 16, chunky: bool = False) -> pygame.font.Font:
    """chunky=True forces Press Start 2P even at small sizes."""
    key = (size, chunky)
    if key in _CACHE:
        return _CACHE[key]
    path = None
    if chunky:
        p = FONT_DIR / "PressStart2P-Regular.ttf"
        path = str(p) if p.exists() else None
    else:
        p = FONT_DIR / "Silkscreen-Regular.ttf"
        path = str(p) if p.exists() else None
    if path:
        f = pygame.font.Font(path, size)
    else:
        f = pygame.font.SysFont("consolas", max(8, size))
    _CACHE[key] = f
    return f


def render(text: str, size: int = 16, color=P["ui_text"], outline=None,
           chunky: bool = False) -> pygame.Surface:
    font = get_font(size, chunky)
    base = font.render(text, False, color)
    if not outline:
        return base
    pad = max(1, size // 8)
    w, h = base.get_size()
    surf = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)
    shadow = font.render(text, False, outline)
    for dx, dy in ((-pad, 0), (pad, 0), (0, -pad), (0, pad), (-pad, -pad), (pad, pad)):
        surf.blit(shadow, (pad + dx, pad + dy))
    surf.blit(base, (pad, pad))
    return surf


def draw_text(target: pygame.Surface, text: str, pos, size: int = 16,
              color=P["ui_text"], outline=None, chunky: bool = False,
              anchor: str = "topleft") -> pygame.Rect:
    surf = render(text, size, color, outline, chunky)
    rect = surf.get_rect(**{anchor: pos})
    target.blit(surf, rect)
    return rect


def wrap(text: str, size: int = 16, width: int = 300, chunky: bool = False) -> list[str]:
    font = get_font(size, chunky)
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        if font.size(trial)[0] <= width or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_wrapped(target: pygame.Surface, text: str, pos, width: int,
                 size: int = 16, color=P["ui_text"], outline=None,
                 line_gap: int = 2, max_lines: int = 99) -> int:
    x, y = pos
    font = get_font(size)
    line_h = font.get_height() + line_gap
    lines = wrap(text, size, width)[:max_lines]
    for i, line in enumerate(lines):
        draw_text(target, line, (x, y + i * line_h), size, color, outline)
    return len(lines) * line_h


def text_height(size: int = 16) -> int:
    return get_font(size).get_height()
