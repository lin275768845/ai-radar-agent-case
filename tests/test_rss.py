from datetime import date

import httpx

from ai_radar_agent.dates import window_for_date
from ai_radar_agent.fetchers import rss
from ai_radar_agent.utils import evidence_to_markdown


RSS_XML = """<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <title>Test</title>
    <item>
      <title>Event</title>
      <link>https://example.com/a</link>
      <description>Summary</description>
      <pubDate>Mon, 01 Jun 2026 08:00:00 +0800</pubDate>
    </item>
  </channel>
</rss>
"""


def test_rss_single_source_timeout_does_not_block_other_sources(monkeypatch):
    calls = []

    def fake_fetch(url):
        calls.append(url)
        if "slow" in url:
            raise httpx.ReadTimeout("timeout")
        return RSS_XML

    monkeypatch.setattr(rss, "_fetch_rss_text", fake_fetch)
    window = window_for_date(date(2026, 6, 1), "Asia/Shanghai")

    items, audit = rss.fetch_rss_feeds(
        [
            {"name": "Slow", "url": "https://example.com/slow.xml"},
            {"name": "Fast", "url": "https://example.com/fast.xml"},
        ],
        window,
        source_basket="rss",
    )

    assert len(items) == 1
    assert calls == ["https://example.com/slow.xml", "https://example.com/fast.xml"]
    assert audit[0].status == "timeout"
    assert audit[1].status == "ok"
    assert audit[1].count == 1


def test_evidence_markdown_includes_rss_per_source_audit():
    from ai_radar_agent.models import RecallAudit, RssSourceAudit

    audit = RecallAudit(
        target_date="2026-06-01",
        target_window="window",
        rss_item_count=1,
        rss_sources=[
            RssSourceAudit(name="A", url="https://example.com/a.xml", status="ok", count=1),
            RssSourceAudit(name="B", url="https://example.com/b.xml", status="timeout", error_summary="timeout"),
        ],
    )

    md = evidence_to_markdown([], audit)

    assert "RSS per-source audit" in md
    assert "| A | ok | 1 |" in md
    assert "| B | timeout | 0 | timeout |" in md
