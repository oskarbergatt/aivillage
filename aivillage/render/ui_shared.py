"""Native-resolution pixel UI: HUD, inspector, chat, chronicle, dispatch card."""
from __future__ import annotations

import math
import time

import pygame

from ..assets.font import draw_text, draw_wrapped, get_font, render, wrap
from ..assets.palette import P
from ..agents.jobs import ADULT_JOBS, JOBS
from ..agents.needs import clamp
from .settings import draw_settings

TITLE = "aivillage"


def _truncate(text: str, size: int, width: int) -> str:
    font = get_font(size)
    if font.size(text)[0] <= width:
        return text
    out = text
    while out and font.size(out + "…")[0] > width:
        out = out[:-1]
    return (out.rstrip() + "…") if out else "…"


