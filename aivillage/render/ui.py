"""Public facade and controller composition."""
from __future__ import annotations

from .ui_shared import (
    ADULT_JOBS,
    JOBS,
    P,
    TITLE,
    _truncate,
    clamp,
    draw_settings,
    draw_text,
    draw_wrapped,
    get_font,
    math,
    pygame,
    render,
    time,
    wrap,
)

from .ui_hud import HudMixin
from .ui_inspector import InspectorMixin
from .ui_dialogs import DialogsMixin


class UI(HudMixin, InspectorMixin, DialogsMixin):
    def __init__(self, i18n):
        self.i18n = i18n
        self.hits: dict[str, pygame.Rect] = {}
        self.chronicle_scroll = 0
        self._mouse = (0, 0)
        self._pulse = 0.0
