import logging
import time
from datetime import datetime, timedelta
from typing import Optional

import feedparser
from newspaper import Article

logger = logging.getLogger(__name__)

SITES_RSS: dict[str, str] = {
    "adweek": "https://www.adweek.com/feed/",
    "adage": "https://adage.com/section/marketing-news/rss",
    "digiday": "https://digiday.com/feed/",
    "marketingweek": "https://www.marketingweek.com/feed/",
    "campaignlive": "https://www.campaignlive.co.uk/rss/",
    "warc": "https://www.warc.com/rss",
    "wuv": "https://www.wuv.de/rss/",
    "horizont": "https://www.horizont.net/rss/",
}

DEFAULT_KEYWORDS = [
    "advertising", "marketing", "campaign", "brand", "creative",
    "agency", "digital", "social media", "AI", "programmatic",
]


def _is_relevant(title: str, content: str, keywords: list[str]) -> bool:
    text = (title + " " + content).lower()
    return any(k.lower() in text for k in keywords)


def _relevance_score(title: str, content: str, keywords: list[str]) -> float:
    text = (title + " " + content).lower()
    matches = sum(1 for k in keywords if k.lower() in text)
    return matches / max(len(keywords), 1)


def collect_from_rss(
    name: str,
    rss_url: str,
    keywords: list[str],
    lookback_days: int = 7,
) -> list[dict]:
    logger.info(f"Collecting from {name}")
    items: list[dict] = []
    cutoff = datetime.utcnow() - timedelta(days=lookback_days)

    try:
        feed = feedparser.parse(rss_url)
    except Exception as e:
        logger.warning(f"RSS parse failed for {name}: {e}")
        return items

    for entry in feed.entries:
        link = entry.get("link")
        if not link:
            continue

        pub = datetime.utcnow()
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                pub = datetime.fromtimestamp(time.mktime(entry.published_parsed))
            except Exception:
                pass

        if pub < cutoff:
            continue

        try:
            art = Article(link)
            art.download()
            art.parse()
            content = art.text.strip()
            title = (art.title or entry.get("title", "")).strip()

            if len(content) < 100:
                continue
            if not _is_relevant(title, content, keywords):
                continue

            items.append({
                "source": name,
                "title": title,
                "url": link,
                "content": content,
                "published_at": pub,
                "score": _relevance_score(title, content, keywords),
            })
        except Exception as e:
            logger.debug(f"Failed to parse {link}: {e}")

    logger.info(f"{name}: {len(items)} relevant articles")
    return items


def collect_all(
    keywords: Optional[list[str]] = None,
    sources: Optional[list[str]] = None,
    lookback_days: int = 7,
) -> list[dict]:
    """Collect from all (or selected) sources, sorted by relevance × recency."""
    kws = keywords or DEFAULT_KEYWORDS
    feeds = {k: v for k, v in SITES_RSS.items() if not sources or k in sources}

    all_items: list[dict] = []
    seen_urls: set[str] = set()

    for name, url in feeds.items():
        items = collect_from_rss(name, url, kws, lookback_days)
        for item in items:
            if item["url"] not in seen_urls:
                seen_urls.add(item["url"])
                all_items.append(item)

    # Sort: relevance score desc, then recency desc
    all_items.sort(
        key=lambda x: (x["score"], x["published_at"].timestamp()),
        reverse=True,
    )
    return all_items
