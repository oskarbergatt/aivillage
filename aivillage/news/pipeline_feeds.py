"""Extracted methods for NewsService."""
from __future__ import annotations

from .pipeline_shared import (
    Dispatch,
    DispatchCallback,
    SOURCES,
    _fetch_feed,
    datetime,
    prompts,
    threading,
    time,
)


class FeedPipelineMixin:
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

    def fetch_once(self) -> int:
        if not self.enabled or self.fetching:
            return 0
        self.fetching = True
        added = 0
        ok = 0
        errors = 0
        try:
            sources = [src for src in SOURCES if self._source_active(src.name)]
            futures = [self._pool.submit(_fetch_feed, src) for src in sources]
            for future in futures:
                try:
                    src, items, err = future.result(timeout=25)
                except Exception as exc:
                    errors += 1
                    self.last_error = str(exc)[:120]
                    continue
                if err:
                    errors += 1
                    self._record_source(src.name, False)
                    continue
                ok += 1
                self._record_source(src.name, True)
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

    def _source_active(self, name: str) -> bool:
        if name in self.muted:
            return False
        return time.time() >= self.next_try.get(name, 0.0)

    def _record_source(self, name: str, success: bool) -> None:
        if success:
            self.failures.pop(name, None)
            self.next_try.pop(name, None)
            return
        count = self.failures.get(name, 0) + 1
        self.failures[name] = count
        if count >= self.mute_after:
            self.muted.add(name)
            self.next_try.pop(name, None)
            return
        delay = min(self.backoff_max, self.backoff_base * (2 ** (count - 1)))
        self.next_try[name] = time.time() + delay

    def feed_health(self) -> list[dict]:
        now = time.time()
        out = []
        for src in SOURCES:
            out.append({
                "name": src.name,
                "lang": src.lang,
                "category": src.category,
                "failures": self.failures.get(src.name, 0),
                "muted": src.name in self.muted,
                "retry_in": max(0, int(self.next_try.get(src.name, now) - now)),
            })
        return out

    def retry_feeds(self) -> None:
        """Clear all backoff/mute state and fetch soon."""
        self.muted.clear()
        self.failures.clear()
        self.next_try.clear()
        self.wake(force=True)

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

