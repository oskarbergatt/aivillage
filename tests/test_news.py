"""News filters, storage and dispatch selection."""
from __future__ import annotations

from aivillage.news.filters import clean, clip, guess_tone, is_distress
from aivillage.news.store import NewsItem, NewsStore, item_id


def test_clean_strips_markup_and_entities():
    raw = "<p>Fish &amp; chips</p>\n\n  in   town "
    assert clean(raw) == "Fish & chips in town"


def test_clip_keeps_words_intact():
    text = "one two three four five six"
    out = clip(text, 14)
    assert out.endswith("…")
    assert len(out) <= 15
    assert not out[:-1].endswith(" ")


def test_distress_detects_real_violence():
    assert is_distress("Three killed in storm")
    assert is_distress("Überschwemmung: mehrere Tote")
    assert is_distress("Shooting at a school")


def test_distress_allows_ordinary_words():
    # word boundaries: these must not trip the filter
    assert not is_distress("Deadline extended for tax returns")
    assert not is_distress("Total rainfall reaches a record")
    assert not is_distress("Skilled workers wanted")
    assert not is_distress("New study on software testing")


def test_tone_guessing():
    assert guess_tone("Scientists discover a new species") == "good"
    assert guess_tone("A mysterious shipwreck appears") == "strange"
    assert guess_tone("Council meets on Tuesday") == "neutral"


def _items() -> list[NewsItem]:
    return [
        NewsItem(id="a", source="BBC", title="A", summary="", url="u1",
                 lang="en", category="world"),
        NewsItem(id="b", source="BBC", title="B", summary="", url="u2",
                 lang="en", category="science"),
        NewsItem(id="c", source="DW", title="C", summary="", url="u3",
                 lang="de", category="world"),
    ]


def test_store_roundtrip_and_choose(tmp_path):
    store = NewsStore(tmp_path / "news.db")
    assert store.save_items(_items()) == 3
    assert store.count() == 3
    assert store.count_unused() == 3
    weights = {"world": 1.0, "science": 0.0}
    pick = store.choose_item(weights, "en", avoid_source="BBC")
    assert pick is not None
    assert pick.source != "BBC"
    store.mark_used(pick.id)
    assert store.count_unused() == 2
    assert store.item_by_id("a").title == "A"

    store.save_dispatch("a", "de", "Eine Kunde", "good", "trade")
    assert store.cached_dispatch("a", "de") == ("Eine Kunde", "good", "trade")
    store.log_visit("a", "de", "Eine Kunde", "good", "30 Oct")
    visits = store.recent_visits(5)
    assert visits and visits[0][0] == "a"
    store.close()


def test_store_ignores_duplicate_ids(tmp_path):
    store = NewsStore(tmp_path / "news.db")
    assert store.save_items(_items()) == 3
    assert store.save_items(_items()) == 0
    assert store.count() == 3
    store.close()


def test_item_id_is_stable():
    assert item_id("https://x", "Title") == item_id("https://x", "Title")
    assert item_id("https://x", "Title") != item_id("https://x", "Other")
