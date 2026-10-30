"""Distress filtering: keep the village cosy without making the news fake."""
from __future__ import annotations

import html
import re

# Graphic violence, death counts, abuse, terrorism. Deliberately blunt.
DISTRESS_EN = {
    "killed", "kill", "dead", "death", "deaths", "dies", "died", "murder",
    "murdered", "shooting", "shot dead", "massacre", "gore", "corpse", "body found",
    "beheaded", "rape", "raped", "abuse", "suicide", "terror", "terrorist",
    "hostage", "genocide", "fatal", "bomb", "bombing", "airstrike", "war crime",
    "torture", "mass grave", "school shooting", "stabbed", "militant", "atrocity",
}
DISTRESS_DE = {
    "getötet", "tötete", "tot", "tote", "toten", "mord", "ermordet", "erschossen",
    "absturz", "leiche", "leichen", "vergewaltigt", "missbraucht", "missbrauch",
    "selbstmord", "terror", "terrorist", "geisel", "massaker", "völkermord",
    "bombe", "bombenanschlag", "kriegsverbrechen", "folter", "tödlich", "unglück",
    "amoklauf", "erstochen", "verletzte",
}

# Things that make a story feel upbeat vs strange for the village retelling.
GOOD_WORDS = {"festival", "record", "discover", "discovery", "celebrates", "wins",
              "won", "rescue", "rescued", "reopens", "saved", "first", "new species",
              "breakthrough", "milestone", "harvest", "surplus", "funding", "prize"}
STRANGE_WORDS = {"strange", "weird", "unusual", "mystery", "mysterious", "odd",
                 "bizarre", "ghost", "haunted", "ancient", "lost", "secret",
                 "unexplained", "fossil", "volcano", "meteor", "shipwreck"}

TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")


def _word_hit(word: str, blob: str) -> bool:
    # word-boundary match: "dead" must not fire on "deadline", nor "tot" on "total"
    return re.search(rf"(?<!\w){re.escape(word)}(?!\w)", blob) is not None


def clean(text: str) -> str:
    text = html.unescape(text or "")
    text = TAG_RE.sub(" ", text)
    return SPACE_RE.sub(" ", text).strip()


def is_distress(title: str, summary: str = "") -> bool:
    blob = f"{title} {summary}".lower()
    for words in (DISTRESS_EN, DISTRESS_DE):
        for w in words:
            if _word_hit(w, blob):
                return True
    return False


def guess_tone(title: str, summary: str = "") -> str:
    blob = f"{title} {summary}".lower()
    if any(w in blob for w in GOOD_WORDS):
        return "good"
    if any(w in blob for w in STRANGE_WORDS):
        return "strange"
    return "neutral"


def clip(text: str, limit: int = 220) -> str:
    text = clean(text)
    if len(text) <= limit:
        return text
    cut = text[:limit]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut + "…"
