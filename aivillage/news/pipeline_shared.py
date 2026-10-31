"""The news pipeline.

Fetch → clean → filter → store → choose → retell (LLM) → dispatch.

Fetching happens on its own thread; the render loop only ever reads cached
results. Retelling is delegated to the LLM client, whose callbacks arrive on
the main thread via ``poll()``.
"""
from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Callable

import feedparser
import requests

from ..agents.visitor import Dispatch
from ..llm import prompts
from .alerts import Alert
from .filters import clean, clip, guess_tone, is_distress
from .sources import SOURCES, Source
from .store import NewsItem, NewsStore, item_id

HEADERS = {"User-Agent": "aivillage/0.1 (local village simulation)"}
MAX_PER_FEED = 22
DispatchCallback = Callable[[Dispatch | None], None]


def _fetch_feed(src: Source) -> tuple[Source, list[NewsItem], str]:
    """Returns the source, parsed items and an error string ('' on success)."""
    try:
        r = requests.get(src.url, timeout=9, headers=HEADERS)
        r.raise_for_status()
        parsed = feedparser.parse(r.content)
        items: list[NewsItem] = []
        for entry in parsed.entries[:MAX_PER_FEED]:
            title = clean(entry.get("title", ""))
            if not title:
                continue
            summary = clean(entry.get("summary") or entry.get("description") or "")
            if is_distress(title, summary):
                continue
            link = str(entry.get("link", "") or "")
            items.append(NewsItem(
                id=item_id(link, title),
                source=src.name,
                title=clip(title, 180),
                summary=clip(summary, 400),
                url=link,
                lang=src.lang,
                category=src.category,
                published=str(entry.get("published", "") or ""),
                tone=guess_tone(title, summary),
            ))
        if not items:
            return src, [], "no usable entries"
        return src, items, ""
    except Exception as exc:
        return src, [], str(exc)[:120]


