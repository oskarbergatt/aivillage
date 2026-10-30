"""Verified keyless news feeds.

Everything in this list answered HTTP 200 with parseable entries when tested.
Add your own at the bottom; the pipeline handles failures gracefully.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Source:
    name: str
    url: str
    lang: str          # en | de
    category: str      # world | local | tech | science | odd | sport
    weight: float = 1.0


SOURCES: list[Source] = [
    # world — english
    Source("BBC World", "https://feeds.bbci.co.uk/news/world/rss.xml", "en", "world"),
    Source("The Guardian", "https://www.theguardian.com/world/rss", "en", "world"),
    Source("Guardian UK", "https://www.theguardian.com/uk/rss", "en", "world"),
    Source("NPR", "https://feeds.npr.org/1001/rss.xml", "en", "world"),
    Source("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml", "en", "world"),
    Source("DW English", "https://rss.dw.com/rdf/rss-en-world", "en", "world"),
    Source("France 24", "https://www.france24.com/en/rss", "en", "world"),
    Source("Euronews", "https://www.euronews.com/rss?level=theme&name=news", "en", "world"),
    Source("CBC World", "https://www.cbc.ca/webfeed/rss/rss-world", "en", "world"),
    Source("ABC Australia", "https://www.abc.net.au/news/feed/51120/rss.xml", "en", "world"),
    Source("UN News", "https://news.un.org/feed/subscribe/en/news/all/rss.xml", "en", "world"),
    Source("Sky News", "https://feeds.skynews.com/feeds/rss/world.xml", "en", "world"),
    # world — german
    Source("Tagesschau", "https://www.tagesschau.de/xml/rss2/", "de", "world"),
    Source("ZDF heute", "https://www.zdf.de/rss/zdf/nachrichten", "de", "world"),
    Source("Deutschlandfunk", "https://www.deutschlandfunk.de/nachrichten-100.rss", "de", "world"),
    Source("Spiegel", "https://www.spiegel.de/schlagzeilen/index.rss", "de", "world"),
    Source("Zeit Online", "https://newsfeed.zeit.de/index", "de", "world"),
    Source("taz", "https://taz.de/!p4608;rss/", "de", "world"),
    # tech
    Source("Hacker News", "https://hnrss.org/frontpage", "en", "tech"),
    Source("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index", "en", "tech"),
    Source("Heise", "https://www.heise.de/rss/heise-atom.xml", "de", "tech"),
    Source("The Verge", "https://www.theverge.com/rss/index.xml", "en", "tech"),
    # science
    Source("NASA", "https://www.nasa.gov/feed/", "en", "science"),
    Source("Nature", "https://www.nature.com/nature.rss", "en", "science"),
    Source("Phys.org", "https://phys.org/rss-feed/", "en", "science"),
    Source("ScienceDaily", "https://www.sciencedaily.com/rss/all.xml", "en", "science"),
    # oddities
    Source("Atlas Obscura", "https://www.atlasobscura.com/feeds/latest", "en", "odd"),
    # sport
    Source("BBC Sport", "https://feeds.bbci.co.uk/sport/rss.xml", "en", "sport"),
    Source("ESPN", "https://www.espn.com/espn/rss/news", "en", "sport"),
]

# Sources that replied 403 / 404 / no RSS when tested, kept here as notes:
#   AP News       403
#   Ostsee-Zeitung 403
#   NDR MV        no usable RSS
#   SVZ           no RSS
