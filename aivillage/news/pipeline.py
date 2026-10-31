"""Public facade and controller composition."""
from __future__ import annotations

from .pipeline_shared import (
    Alert,
    Callable,
    Dispatch,
    DispatchCallback,
    HEADERS,
    MAX_PER_FEED,
    NewsItem,
    NewsStore,
    SOURCES,
    Source,
    ThreadPoolExecutor,
    _fetch_feed,
    clean,
    clip,
    datetime,
    feedparser,
    guess_tone,
    is_distress,
    item_id,
    prompts,
    requests,
    threading,
    time,
)

from .pipeline_feeds import FeedPipelineMixin
from .pipeline_dispatch import DispatchPipelineMixin


class NewsService(FeedPipelineMixin, DispatchPipelineMixin):
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

        # Per-source health.  A feed that fails repeatedly is backed off
        # exponentially and then muted; a manual wake or the settings panel
        # can bring it back.
        self.failures: dict[str, int] = {}
        self.muted: set[str] = set()
        self.next_try: dict[str, float] = {}
        self.mute_after = max(2, int(config.get("news.mute_after_failures", 5)))
        self.backoff_base = max(60, int(config.get("news.backoff_base_s", 300)))
        self.backoff_max = max(self.backoff_base,
                               int(config.get("news.backoff_max_s", 21600)))

        self._pending = False
        self._pending_item: NewsItem | None = None
        self._last_source = ""
        self._mem_cache: dict[tuple[str, str], Dispatch] = {}
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._pool = ThreadPoolExecutor(max_workers=7, thread_name_prefix="feed")
