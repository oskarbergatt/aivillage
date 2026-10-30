"""SQLite store for headlines and adapted dispatches."""
from __future__ import annotations

import hashlib
import sqlite3
import threading
import time
from dataclasses import dataclass

from ..config import DATA_DIR

DB_PATH = DATA_DIR / "news.db"


@dataclass
class NewsItem:
    id: str
    source: str
    title: str
    summary: str
    url: str
    lang: str
    category: str
    published: str = ""
    tone: str = "neutral"


class NewsStore:
    def __init__(self, path=DB_PATH):
        self.path = path
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.execute("""CREATE TABLE IF NOT EXISTS items (
            id TEXT PRIMARY KEY, source TEXT, title TEXT, summary TEXT, url TEXT,
            lang TEXT, category TEXT, published TEXT, fetched REAL, used INTEGER DEFAULT 0,
            tone TEXT)""")
        self._conn.execute("""CREATE TABLE IF NOT EXISTS dispatches (
            item_id TEXT, lang TEXT, headline TEXT, tone TEXT, topic TEXT,
            created REAL, PRIMARY KEY (item_id, lang))""")
        self._conn.execute("""CREATE TABLE IF NOT EXISTS visits (
            id INTEGER PRIMARY KEY AUTOINCREMENT, item_id TEXT, lang TEXT,
            tour TEXT, tone TEXT, day TEXT, created REAL)""")
        self._conn.commit()

    # -- items ----------------------------------------------------------
    def save_items(self, items: list[NewsItem]) -> int:
        """Insert new items; returns how many rows were actually new."""
        added = 0
        with self._lock:
            for it in items:
                try:
                    cur = self._conn.execute(
                        "INSERT OR IGNORE INTO items (id, source, title, summary, url, lang,"
                        " category, published, fetched, used, tone) VALUES (?,?,?,?,?,?,?,?,?,0,?)",
                        (it.id, it.source, it.title, it.summary, it.url, it.lang,
                         it.category, it.published, time.time(), it.tone))
                    if cur.rowcount > 0:
                        added += 1
                except Exception:
                    continue
            self._conn.commit()
        return added

    def choose_item(self, weights: dict[str, float], lang: str,
                    avoid_source: str = "") -> NewsItem | None:
        """Weighted category pick, preferring the active language."""
        import random
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, source, title, summary, url, lang, category, published, tone "
                "FROM items WHERE used = 0 AND tone != 'distress'").fetchall()
        if not rows:
            return None
        items = [NewsItem(*r) for r in rows]
        # prefer active language but allow the other one as a fallback
        preferred = [i for i in items if i.lang == lang] or items
        weights = {k: v for k, v in weights.items() if v > 0}
        categories = list(weights.keys())
        rng = random.Random()
        for _ in range(12):
            cat = rng.choices(categories, weights=[weights[c] for c in categories])[0]
            pool = [i for i in preferred if i.category == cat and i.source != avoid_source]
            if not pool:
                pool = [i for i in preferred if i.source != avoid_source]
            if pool:
                return rng.choice(pool)
        if preferred and preferred[0].source == avoid_source:
            others = [i for i in items if i.source != avoid_source]
            if others:
                return rng.choice(others)
        return preferred[0] if preferred else None

    def mark_used(self, item_id: str) -> None:
        with self._lock:
            self._conn.execute("UPDATE items SET used = 1 WHERE id = ?", (item_id,))
            self._conn.commit()

    def prune(self, days: int = 30) -> None:
        cutoff = time.time() - days * 86400
        with self._lock:
            self._conn.execute("DELETE FROM items WHERE fetched < ?", (cutoff,))
            self._conn.commit()

    def count(self) -> int:
        with self._lock:
            return self._conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]

    def count_unused(self) -> int:
        with self._lock:
            return self._conn.execute(
                "SELECT COUNT(*) FROM items WHERE used = 0").fetchone()[0]

    # -- dispatches -----------------------------------------------------
    def cached_dispatch(self, item_id: str, lang: str) -> tuple[str, str, str] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT headline, tone, topic FROM dispatches WHERE item_id=? AND lang=?",
                (item_id, lang)).fetchone()
        return tuple(row) if row else None

    def save_dispatch(self, item_id: str, lang: str, headline: str, tone: str,
                      topic: str) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO dispatches (item_id, lang, headline, tone, topic,"
                " created) VALUES (?,?,?,?,?,?)",
                (item_id, lang, headline, tone, topic, time.time()))
            self._conn.commit()

    def log_visit(self, item_id: str, lang: str, text: str, tone: str, day: str) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO visits (item_id, lang, tour, tone, day, created)"
                " VALUES (?,?,?,?,?,?)",
                (item_id, lang, text, tone, day, time.time()))
            self._conn.commit()

    def recent_visits(self, limit: int = 12) -> list[tuple]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT item_id, lang, tour, tone, day, created FROM visits"
                " ORDER BY created DESC LIMIT ?", (limit,)).fetchall()
        return rows

    def item_by_id(self, item_id: str) -> NewsItem | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT id, source, title, summary, url, lang, category, published, tone"
                " FROM items WHERE id = ?", (item_id,)).fetchone()
        return NewsItem(*row) if row else None

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass


def item_id(url: str, title: str) -> str:
    return hashlib.sha1(f"{url}|{title}".encode("utf-8", "ignore")).hexdigest()[:16]
