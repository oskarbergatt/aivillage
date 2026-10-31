"""Extracted methods for NewsService."""
from __future__ import annotations

from .pipeline_shared import (
    Alert,
    Dispatch,
    DispatchCallback,
    NewsItem,
    datetime,
    prompts,
    threading,
)


class DispatchPipelineMixin:
    def request_alert(self, alert: Alert, lang: str,
                      callback: DispatchCallback) -> bool:
        """Retell an official DWD warning as a courier bulletin (LLM only)."""
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
            callback(Dispatch(
                headline=headline,
                tone=str(data.get("tone", "bad") or "bad"),
                topic=str(data.get("topic", "weather") or "weather"),
                original=alert.headline,
                source="DWD · Bright Sky",
                url=alert.url,
                day=datetime.now().strftime("%d %b"),
            ))

        self.llm.submit(
            "alert",
            prompts.alert_system(lang),
            prompts.alert_user(alert.headline, alert.description, alert.instruction,
                               alert.severity, lang),
            done,
            max_tokens=240,
            temperature=0.75,
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
            "muted": len(self.muted),
            "failing": len(self.failures),
        }

    def wake(self, force: bool = False) -> None:
        """Force a refresh soon (called when the player asks for a traveller)."""
        if force:
            self.muted.clear()
            self.next_try.clear()
        if not self.fetching:
            threading.Thread(target=self.fetch_once, daemon=True).start()

