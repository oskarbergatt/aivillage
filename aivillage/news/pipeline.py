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


class NewsService:
    def __init__(self, config, llm, i18n, db_path=None):
        self.config = config
        self.llm = llm
        self.i18n = i18n
        self.store = NewsStore(db_path) if db_path is not None else NewsStore()
        self.enabled = bool(config.get("news.enabled", True))
        self.weights: dict[str, float] = dict(config.get("news.weights", {}))
        self.tone_pref = str(config.get("news.tone", "neutral"))
        self.poll_minutes = max(10, int(config.get("news.poll_minutes", 40)))

        self.feeds_ok = 0
        self.feeds_total = len(SOURCES)
        self.last_fetch = 0.0
        self.fetching = False
        self.last_error = ""
        self.added_total = 0

        self._pending = False
        self._pending_item: NewsItem | None = None
        self._last_source = ""
        self._mem_cache: dict[tuple[str, str], Dispatch] = {}
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._pool = ThreadPoolExecutor(max_workers=7, thread_name_prefix="feed")

    # -- lifecycle -------------------------------------------------------
    def start(self) -> None:
        if not self.enabled or self._thread is not None:
            return
        self._thread = threading.Thread(target=self._loop, daemon=True, name="news")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._pool.shutdown(wait=False, cancel_futures=True)
        self.store.close()

    def _loop(self) -> None:
        while not self._stop.is_set():
            self.fetch_once()
            self._stop.wait(self.poll_minutes * 60)

    # -- fetching --------------------------------------------------------
    def fetch_once(self) -> int:
        if not self.enabled or self.fetching:
            return 0
        self.fetching = True
        added = 0
        ok = 0
        errors = 0
        try:
            futures = [self._pool.submit(_fetch_feed, src) for src in SOURCES]
            for future in futures:
                try:
                    src, items, err = future.result(timeout=25)
                except Exception as exc:
                    errors += 1
                    self.last_error = str(exc)[:120]
                    continue
                if err:
                    errors += 1
                    continue
                ok += 1
                added += self.store.save_items(items)
            self.feeds_ok = ok
            self.last_fetch = time.time()
            self.added_total += added
            if errors and not ok:
                self.last_error = "all feeds unreachable"
            elif ok:
                self.last_error = ""
            self.store.prune(21)
        finally:
            self.fetching = False
        return added

    # -- choosing & retelling --------------------------------------------
    def _weights(self, lang: str) -> dict[str, float]:
        w = dict(self.weights)
        if not w:
            w = {"world": 0.4, "odd": 0.15, "science": 0.15,
                 "tech": 0.1, "sport": 0.1, "local": 0.1}
        if self.tone_pref == "strange_only":
            w = {"odd": 0.5, "science": 0.2, "tech": 0.1, "world": 0.1, "local": 0.1}
        elif self.tone_pref == "wholesome":
            w["world"] = max(0.05, w.get("world", 0.3) * 0.7)
            w["odd"] = w.get("odd", 0.15) + 0.05
            w["science"] = w.get("science", 0.15) + 0.03
        if lang == "de":
            w["local"] = w.get("local", 0.1) + 0.08
        return w

    def request_dispatch(self, lang: str, callback: DispatchCallback) -> bool:
        """Ask for one village retelling. callback(None) on failure."""
        if not self.enabled:
            return False
        if self._pending:
            return False
        if not self.llm.available:
            return False
        item = self.store.choose_item(self._weights(lang), lang,
                                      avoid_source=self._last_source)
        if item is None:
            # nothing fetched yet — try once in the background for next time
            if not self.fetching and (time.time() - self.last_fetch) > 120:
                threading.Thread(target=self.fetch_once, daemon=True).start()
            return False

        cached = self._mem_cache.get((item.id, lang))
        if cached is None:
            row = self.store.cached_dispatch(item.id, lang)
            if row:
                cached = self._make_dispatch(item, row[0], row[1], row[2])
                self._mem_cache[(item.id, lang)] = cached
        if cached is not None:
            self._finish(item, cached, callback)
            return True

        self._pending = True
        self._pending_item = item

        def done(data: dict | None, error: str) -> None:
            self._pending = False
            self._pending_item = None
            if error or not data:
                callback(None)
                return
            headline = str(data.get("headline", "")).strip()
            if not headline:
                callback(None)
                return
            tone = str(data.get("tone", item.tone) or "neutral")
            topic = str(data.get("topic", item.category) or item.category)
            self.store.save_dispatch(item.id, lang, headline, tone, topic)
            dispatch = self._make_dispatch(item, headline, tone, topic)
            self._mem_cache[(item.id, lang)] = dispatch
            self._finish(item, dispatch, callback)

        self.llm.submit(
            "dispatch",
            prompts.dispatch_system(lang),
            prompts.dispatch_user(item.title, item.summary, item.source, lang),
            done,
            max_tokens=240,
            temperature=0.8,
        )
        return True

    def request_rumour(self, lang: str, visitor_name: str, trade: str,
                       origin: str, context: dict,
                       callback: DispatchCallback) -> bool:
        """A traveller with no fresh headline still carries a rumour (LLM)."""
        if not self.llm.available:
            return False

        def done(data: dict | None, error: str) -> None:
            if error or not data:
                callback(None)
                return
            headline = str(data.get("headline", "")).strip()
            if not headline:
                callback(None)
                return
            dispatch = Dispatch(
                headline=headline,
                tone=str(data.get("tone", "neutral")),
                topic=str(data.get("topic", "people")),
                original="",
                source="the road",
                day=datetime.now().strftime("%d %b"),
            )
            callback(dispatch)

        self.llm.submit(
            "rumour",
            prompts.rumour_system(lang),
            prompts.rumour_user(visitor_name, trade, origin, context),
            done,
            max_tokens=240,
            temperature=1.0,
        )
        return True

    def _make_dispatch(self, item: NewsItem, headline: str, tone: str,
                       topic: str) -> Dispatch:
        return Dispatch(
            headline=headline,
            tone=tone,
            topic=topic,
            original=item.title,
            source=item.source,
            url=item.url,
            item_id=item.id,
            day=datetime.now().strftime("%d %b"),
        )

    def _finish(self, item: NewsItem, dispatch: Dispatch,
                callback: DispatchCallback) -> None:
        self.store.mark_used(item.id)
        self._last_source = item.source
        callback(dispatch)

    # -- records ---------------------------------------------------------
    def record_visit(self, dispatch: Dispatch, spoken: str, day: str) -> None:
        if not dispatch.item_id:
            return
        self.store.log_visit(dispatch.item_id, self.i18n.language, spoken,
                             dispatch.tone, day)

    def recent_visits(self, limit: int = 14) -> list[tuple]:
        return self.store.recent_visits(limit)

    def status(self) -> dict:
        return {
            "feeds_ok": self.feeds_ok,
            "feeds_total": self.feeds_total,
            "items": self.store.count(),
            "unused": self.store.count_unused(),
            "last_fetch": self.last_fetch,
            "fetching": self.fetching,
            "error": self.last_error,
            "pending": self._pending,
        }

    def wake(self) -> None:
        """Force a refresh soon (called when the player asks for a traveller)."""
        if not self.fetching:
            threading.Thread(target=self.fetch_once, daemon=True).start()
