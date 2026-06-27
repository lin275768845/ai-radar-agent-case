from datetime import date
import logging

import httpx
import pytest

from ai_radar_agent.dates import window_for_date
from ai_radar_agent.fetchers import tavily_search
from ai_radar_agent.fetchers.tavily_search import TavilyFetcher, TavilyAuthError, TavilyConnectivityError, TavilyRateLimitError


def test_tavily_date_bounds_use_next_day_boundary():
    window = window_for_date(date(2026, 6, 1), "Asia/Shanghai")

    start_date, end_date = TavilyFetcher._date_bounds(window)

    assert start_date == "2026-06-01"
    assert end_date == "2026-06-02"


def test_tavily_search_sends_clean_query_and_date_params(monkeypatch):
    sent = {}

    class FakeClient:
        def __init__(self, timeout):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, json, headers):
            sent["url"] = url
            sent["json"] = json
            sent["headers"] = headers
            return httpx.Response(200, json={"results": []})

    monkeypatch.setattr(tavily_search.httpx, "Client", FakeClient)
    window = window_for_date(date(2026, 6, 1), "Asia/Shanghai")

    response = TavilyFetcher("tvly-test", max_results=10)._search_once("OpenAI model release", window)

    assert response == {"results": []}
    assert sent["json"]["query"] == "OpenAI model release"
    assert "after:" not in sent["json"]["query"]
    assert "before:" not in sent["json"]["query"]
    assert sent["json"]["start_date"] == "2026-06-01"
    assert sent["json"]["end_date"] == "2026-06-02"
    assert sent["json"]["max_results"] == 5


def test_tavily_http_400_logs_response_body(monkeypatch, caplog):
    calls = {"count": 0}

    class FakeClient:
        def __init__(self, timeout):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, json, headers):
            calls["count"] += 1
            return httpx.Response(400, json={"detail": {"error": "invalid date"}})

    monkeypatch.setattr(tavily_search.httpx, "Client", FakeClient)
    window = window_for_date(date(2026, 6, 1), "Asia/Shanghai")

    with caplog.at_level(logging.WARNING):
        items = TavilyFetcher("tvly-test").search_queries(
            queries=["OpenAI model release"],
            window=window,
            region_hint="overseas",
            source_basket="overseas_official",
        )

    assert items == []
    assert calls["count"] == 1
    assert "status_code=400" in caplog.text
    assert "invalid date" in caplog.text


def test_tavily_429_retries(monkeypatch):
    calls = {"count": 0}

    class FakeClient:
        def __init__(self, timeout):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, json, headers):
            calls["count"] += 1
            return httpx.Response(429, json={"error": "rate limited"})

    monkeypatch.setattr(tavily_search.httpx, "Client", FakeClient)
    window = window_for_date(date(2026, 6, 1), "Asia/Shanghai")

    with pytest.raises(TavilyRateLimitError):
        TavilyFetcher("tvly-test")._search_once("OpenAI model release", window)

    assert calls["count"] == 2


def test_connect_timeout_threshold_stops_following_queries(monkeypatch):
    calls = {"count": 0}

    class FakeClient:
        def __init__(self, timeout):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, json, headers):
            calls["count"] += 1
            raise httpx.ConnectTimeout("cannot connect")

    monkeypatch.setattr(tavily_search.httpx, "Client", FakeClient)
    window = window_for_date(date(2026, 6, 1), "Asia/Shanghai")
    fetcher = TavilyFetcher("tvly-test", max_consecutive_connect_failures=2)

    items = fetcher.search_queries(
        ["q1", "q2", "q3"],
        window=window,
        region_hint="overseas",
        source_basket="test",
    )

    assert items == []
    assert fetcher.status == "skipped_after_consecutive_failures"
    assert fetcher.failed_count == 2
    assert calls["count"] == 4


def test_401_stops_tavily_without_retry(monkeypatch):
    calls = {"count": 0}

    class FakeClient:
        def __init__(self, timeout):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, json, headers):
            calls["count"] += 1
            return httpx.Response(401, json={"error": "bad key"})

    monkeypatch.setattr(tavily_search.httpx, "Client", FakeClient)
    window = window_for_date(date(2026, 6, 1), "Asia/Shanghai")
    fetcher = TavilyFetcher("tvly-test")

    items = fetcher.search_queries(
        ["q1", "q2"],
        window=window,
        region_hint="overseas",
        source_basket="test",
    )

    assert items == []
    assert fetcher.status == "auth_failed"
    assert calls["count"] == 1
