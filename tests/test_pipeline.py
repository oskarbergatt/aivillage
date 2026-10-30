"""News service: selection, LLM retelling, caching, visitor integration."""
from __future__ import annotations

import time

from aivillage.agents.visitor import Dispatch, Visitor
from aivillage.llm.client import LLMClient
from aivillage.news.filters import clip
from aivillage.news.pipeline import NewsService
from aivillage.news.store import NewsItem

ITEMS = [
    NewsItem(id="n1", source="Test World", title="New bridge opens across the river",
             summary="The council finished the bridge after two years of work.",
             url="https://example.test/1", lang="en", category="world"),
    NewsItem(id="n2", source="Test Science", title="Researchers map an ancient forest",
             summary="A survey found trees older than expected.",
             url="https://example.test/2", lang="en", category="science"),
    NewsItem(id="n3", source="Test Odd", title="A strange light appears over the hills",
             summary="Villagers report a light that moves against the wind.",
             url="https://example.test/3", lang="en", category="odd"),
]


def _service(app, tmp_path):
    service = NewsService(app.config, app.llm, app.i18n, db_path=tmp_path / "news.db")
    service.enabled = True
    # Never reach out to the real feeds from a test: pretend we fetched just now.
    service.last_fetch = time.time()
    service.store.save_items(ITEMS)
    return service


def _poll(app, service, seconds=4.0):
    end = time.time() + seconds
    while time.time() < end:
        app.llm.poll()
        time.sleep(0.02)


def test_dispatch_is_retold_and_cached(app, tmp_path):
    service = _service(app, tmp_path)
    got = []
    assert service.request_dispatch("en", got.append)
    _poll(app, service)
    assert got and isinstance(got[0], Dispatch)
    dispatch = got[0]
    assert dispatch.headline
    assert dispatch.source in {i.source for i in ITEMS}
    assert dispatch.original in {i.title for i in ITEMS}
    assert dispatch.item_id

    # A second request for the same item+language is served from cache and
    # returns synchronously (the callback runs before request_dispatch ends).
    same = []
    service._last_source = ""
    service.store._conn.execute("UPDATE items SET used = 0 WHERE id = ?",
                                (dispatch.item_id,))
    service.store._conn.execute("UPDATE items SET used = 1 WHERE id != ?",
                                (dispatch.item_id,))
    service.store._conn.commit()
    assert service.request_dispatch("en", same.append)
    assert same and same[0].headline == dispatch.headline
    service.store.close()


def test_dispatch_skips_distress_and_marks_items_used(app, tmp_path):
    service = _service(app, tmp_path)
    got = []
    for _ in range(6):
        service.request_dispatch("en", got.append)
        _poll(app, service, 2.0)
    assert got
    assert service.store.count_unused() < len(ITEMS)
    assert service.store.recent_visits(1) == []


def test_rumour_when_no_news(app, tmp_path):
    service = _service(app, tmp_path)
    got = []
    assert service.request_rumour("en", "Tilda Vell", "salt merchant",
                                  "the fog coast", {"time": "10:00"}, got.append)
    _poll(app, service)
    assert got and got[0].headline
    assert got[0].source == "the road"


def test_status_shape(app, tmp_path):
    service = _service(app, tmp_path)
    status = service.status()
    for key in ("feeds_ok", "feeds_total", "items", "unused", "last_fetch",
                "fetching", "error", "pending"):
        assert key in status
    assert status["items"] == len(ITEMS)


def test_visitor_is_admitted_from_the_real_pipeline(app, tmp_path):
    service = _service(app, tmp_path)
    app.news = service
    app.visitors_today = 0
    app.social_timer = 1e9
    assert app.spawn_visitor(force=True)
    assert app.visitor_pending
    end = time.time() + 5
    while time.time() < end and not app.visitors:
        app._update(0.05)
        time.sleep(0.02)
    assert app.visitors, "no traveller was admitted"
    visitor = app.visitors[0]
    assert visitor.dispatch is not None
    assert visitor.dispatch.headline
    end = time.time() + 90
    while time.time() < end and app.dispatch_card is None:
        app._update(0.2)
    assert app.dispatch_card is visitor
    service.store.close()


def test_clipping_helper_used_for_feeds():
    assert len(clip("x" * 500, 100)) <= 101
