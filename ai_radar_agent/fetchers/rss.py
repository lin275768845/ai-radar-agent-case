from __future__ import annotations

import logging
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any

import feedparser
import httpx

from ..models import EvidenceItem, RssSourceAudit, TimeWindow

logger = logging.getLogger(__name__)


def _entry_datetime(entry: dict[str, Any]) -> datetime | None:
    for key in ("published", "updated", "created"):
        value = entry.get(key)
        if not value:
            continue
        try:
            dt = parsedate_to_datetime(value)
            return dt if dt.tzinfo else dt.replace(tzinfo=window_tz_fallback())
        except Exception:  # noqa: BLE001
            continue
    return None


def window_tz_fallback():
    # feedparser dates without tz are rare; keep deterministic local fallback.
    from zoneinfo import ZoneInfo

    return ZoneInfo("Asia/Shanghai")


def fetch_rss_feeds(
    feeds: list[dict[str, str]], window: TimeWindow, source_basket: str
) -> tuple[list[EvidenceItem], list[RssSourceAudit]]:
    items: list[EvidenceItem] = []
    audits: list[RssSourceAudit] = []
    for feed in feeds:
        name = feed.get("name", "RSS")
        url = feed.get("url", "")
        region_hint = feed.get("region", "unknown")
        if not url:
            continue
        logger.info("Fetching RSS [%s] %s", name, url)
        try:
            response_text = _fetch_rss_text(url)
            parsed = feedparser.parse(response_text)
        except httpx.TimeoutException as exc:
            logger.warning("RSS source timed out: name=%s url=%s error=%s", name, url, exc)
            audits.append(RssSourceAudit(name=name, url=url, status="timeout", error_summary=str(exc)[:300]))
            continue
        except Exception as exc:  # noqa: BLE001
            logger.warning("RSS source failed: name=%s url=%s error=%s", name, url, exc)
            audits.append(RssSourceAudit(name=name, url=url, status="failed", error_summary=str(exc)[:300]))
            continue
        count_before = len(items)
        for entry in parsed.entries:
            dt = _entry_datetime(entry)
            # RSS is supplementary. If date is missing, keep it but force the LLM to classify date口径.
            if dt and not (window.start <= dt.astimezone(window.start.tzinfo) <= window.end):
                continue
            title = entry.get("title", "")
            link = entry.get("link", "")
            summary = entry.get("summary", "") or entry.get("description", "")
            items.append(
                EvidenceItem(
                    title=title,
                    url=link,
                    content=summary,
                    source=name,
                    published_at=dt.isoformat() if dt else entry.get("published", ""),
                    region_hint=region_hint,  # type: ignore[arg-type]
                    source_basket=source_basket,
                    source_type="rss",
                )
            )
        count = len(items) - count_before
        audits.append(RssSourceAudit(name=name, url=url, status="ok" if count else "empty", count=count))
    return items, audits


def _fetch_rss_text(url: str) -> str:
    timeout = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.text
