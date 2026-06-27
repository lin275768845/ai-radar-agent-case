from datetime import date

import httpx
import pytest

from ai_radar_agent.dates import window_for_date
from ai_radar_agent.fetchers import bocha_search
from ai_radar_agent.fetchers.bocha_search import BochaBadRequestError, BochaFetcher, BochaRateLimitError, BochaServerError


def test_bocha_result_maps_to_evidence_item(monkeypatch):
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
            return httpx.Response(
                200,
                json={
                    "data": {
                        "webPages": {
                            "value": [
                                {
                                    "name": "国产模型发布",
                                    "url": "https://example.com/news",
                                    "summary": "发布摘要",
                                    "siteName": "Example",
                                    "datePublished": "2026-06-01T10:00:00+08:00",
                                }
                            ]
                        }
                    }
                },
            )

    monkeypatch.setattr(bocha_search.httpx, "Client", FakeClient)
    window = window_for_date(date(2026, 6, 1), "Asia/Shanghai")

    items = BochaFetcher("bocha-test", base_url="https://api.bochaai.com", max_results=5).search_queries(
        ["国产大模型 发布"],
        window=window,
        region_hint="domestic",
        source_basket="domestic",
    )

    assert sent["url"] == "https://api.bochaai.com/v1/web-search"
    assert sent["json"]["query"] == "国产大模型 发布"
    assert "after:" not in sent["json"]["query"]
    assert "before:" not in sent["json"]["query"]
    assert "2026年06月01日" not in sent["json"]["query"]
    assert sent["json"]["freshness"] == "2026-06-01..2026-06-01"
    assert sent["json"]["count"] == 5
    assert items[0].title == "国产模型发布"
    assert items[0].url == "https://example.com/news"
    assert items[0].provider == "bocha"
    assert items[0].source_type == "bocha"
    assert items[0].source == "Example"
    assert items[0].published_at == "2026-06-01T10:00:00+08:00"


def test_bocha_400_does_not_retry(monkeypatch):
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
            return httpx.Response(400, json={"error": "bad request"})

    monkeypatch.setattr(bocha_search.httpx, "Client", FakeClient)
    window = window_for_date(date(2026, 6, 1), "Asia/Shanghai")

    with pytest.raises(BochaBadRequestError):
        BochaFetcher("bocha-test")._search_once("AI 发布", window)

    assert calls["count"] == 1


@pytest.mark.parametrize(
    ("status_code", "error_type"),
    [(429, BochaRateLimitError), (500, BochaServerError)],
)
def test_bocha_429_and_5xx_retry_once(monkeypatch, status_code, error_type):
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
            return httpx.Response(status_code, json={"error": "temporary"})

    monkeypatch.setattr(bocha_search.httpx, "Client", FakeClient)
    monkeypatch.setattr(bocha_search.time, "sleep", lambda seconds: None)
    window = window_for_date(date(2026, 6, 1), "Asia/Shanghai")

    with pytest.raises(error_type):
        BochaFetcher("bocha-test")._search_once("AI 发布", window)

    assert calls["count"] == 2
