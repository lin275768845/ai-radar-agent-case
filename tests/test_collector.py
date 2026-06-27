from datetime import date

from ai_radar_agent.collector import collect_evidence_with_audit
from ai_radar_agent.config import Settings
from ai_radar_agent.dates import window_for_date
from ai_radar_agent.models import EvidenceItem, RecallAudit
from ai_radar_agent.utils import evidence_to_markdown


def _sources(tmp_path, search_queries: list[str] | None = None):
    queries = search_queries or ["q1", "q2", "q3"]
    source_yaml = "\n".join(f"      - {query}" for query in queries)
    path = tmp_path / "sources.yaml"
    path.write_text(
        "rss:\n"
        "  - name: Test\n"
        "    url: https://example.com/rss\n"
        "search_baskets:\n"
        "  - name: domestic\n"
        "    region: domestic\n"
        "    queries:\n"
        f"{source_yaml}\n",
        encoding="utf-8",
    )
    return path


def test_search_providers_rss_bocha_calls_rss_and_bocha_not_tavily(monkeypatch, tmp_path):
    settings = Settings(SEARCH_PROVIDERS="rss,bocha", BOCHA_API_KEY="bocha-test")
    settings.sources_path = _sources(tmp_path)
    calls = {"rss": 0, "bocha": 0}

    monkeypatch.setattr(
        "ai_radar_agent.collector.fetch_rss_feeds",
        lambda feeds, window, source_basket: calls.__setitem__("rss", calls["rss"] + 1)
        or [EvidenceItem(title="RSS event", url="https://example.com/rss", content="summary", source_type="rss")],
    )

    class FakeBocha:
        def __init__(self, *args, **kwargs):
            self.max_queries = kwargs["max_queries"]
            self.queries_used = 0
            self.results_count = 0
            self.failed_count = 0
            self.status = "ok"
            self.error_summary = ""

        def search_queries(self, queries, window, region_hint, source_basket):
            calls["bocha"] += 1
            self.queries_used += min(len(queries), self.max_queries - self.queries_used)
            self.results_count += 1
            return [
                EvidenceItem(
                    title="Bocha event",
                    url="https://example.com/bocha",
                    content="summary",
                    provider="bocha",
                    source_type="bocha",
                )
            ]

    monkeypatch.setattr("ai_radar_agent.collector.BochaFetcher", FakeBocha)
    monkeypatch.setattr(
        "ai_radar_agent.collector.TavilyFetcher",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("Tavily should not be called")),
    )

    evidence, audit = collect_evidence_with_audit(settings, window_for_date(date(2026, 6, 1), "Asia/Shanghai"))

    assert calls == {"rss": 1, "bocha": 1}
    assert [item.provider or item.source_type for item in evidence] == ["rss", "bocha"]
    assert audit.rss_item_count == 1
    assert audit.bocha_item_count == 1
    assert audit.tavily_status == "disabled_by_search_providers"


def test_bocha_missing_key_skips_provider_and_continues(monkeypatch, tmp_path):
    settings = Settings(SEARCH_PROVIDERS="rss,bocha", BOCHA_API_KEY="")
    settings.sources_path = _sources(tmp_path)
    monkeypatch.setattr(
        "ai_radar_agent.collector.fetch_rss_feeds",
        lambda feeds, window, source_basket: [
            EvidenceItem(title="RSS event", url="https://example.com/rss", content="summary", source_type="rss")
        ],
    )
    monkeypatch.setattr(
        "ai_radar_agent.collector.BochaFetcher",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("Bocha should not be called")),
    )

    evidence, audit = collect_evidence_with_audit(settings, window_for_date(date(2026, 6, 1), "Asia/Shanghai"))

    assert len(evidence) == 1
    assert audit.bocha_status == "missing_api_key"
    assert audit.rss_fallback_used is True


def test_tavily_default_disabled_even_when_provider_listed(monkeypatch, tmp_path):
    settings = Settings(SEARCH_PROVIDERS="rss,tavily", TAVILY_API_KEY="tvly-test")
    settings.sources_path = _sources(tmp_path)
    monkeypatch.setattr("ai_radar_agent.collector.fetch_rss_feeds", lambda feeds, window, source_basket: [])
    monkeypatch.setattr(
        "ai_radar_agent.collector.TavilyFetcher",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("Tavily should not be called")),
    )

    evidence, audit = collect_evidence_with_audit(settings, window_for_date(date(2026, 6, 1), "Asia/Shanghai"))

    assert evidence == []
    assert audit.tavily_status == "disabled_by_env"


def test_tavily_enabled_respects_max_queries(monkeypatch, tmp_path):
    settings = Settings(
        SEARCH_PROVIDERS="rss,tavily",
        TAVILY_ENABLED=True,
        TAVILY_API_KEY="tvly-test",
        TAVILY_MAX_QUERIES=2,
    )
    settings.sources_path = _sources(tmp_path, ["q1", "q2", "q3", "q4"])
    monkeypatch.setattr("ai_radar_agent.collector.fetch_rss_feeds", lambda feeds, window, source_basket: [])
    seen = {}

    class FakeTavily:
        def __init__(self, *args, **kwargs):
            self.max_queries = kwargs["max_queries"]
            self.queries_used = 0
            self.results_count = 0
            self.failed_count = 0
            self.status = "ok"
            self.error_summary = ""
            seen["max_queries"] = self.max_queries

        def search_queries(self, queries, window, region_hint, source_basket):
            used = min(len(queries), self.max_queries - self.queries_used)
            self.queries_used += used
            self.results_count += used
            return [
                EvidenceItem(title=f"Tavily {idx}", url=f"https://example.com/t{idx}", content="summary")
                for idx in range(used)
            ]

    monkeypatch.setattr("ai_radar_agent.collector.TavilyFetcher", FakeTavily)

    evidence, audit = collect_evidence_with_audit(settings, window_for_date(date(2026, 6, 1), "Asia/Shanghai"))

    assert seen["max_queries"] == 2
    assert len(evidence) == 2
    assert audit.provider_queries_used["tavily"] == 2


def test_total_query_budget_limits_providers(monkeypatch, tmp_path):
    settings = Settings(
        SEARCH_PROVIDERS="rss,bocha,tavily",
        BOCHA_API_KEY="bocha-test",
        TAVILY_ENABLED=True,
        TAVILY_API_KEY="tvly-test",
        MAX_SEARCH_QUERIES_PER_RUN=3,
        BOCHA_MAX_QUERIES=20,
    )
    settings.sources_path = _sources(tmp_path, ["q1", "q2", "q3", "q4", "q5"])
    monkeypatch.setattr("ai_radar_agent.collector.fetch_rss_feeds", lambda feeds, window, source_basket: [])

    class FakeBocha:
        def __init__(self, *args, **kwargs):
            self.max_queries = kwargs["max_queries"]
            self.queries_used = 0
            self.results_count = 0
            self.failed_count = 0
            self.status = "ok"
            self.error_summary = ""

        def search_queries(self, queries, window, region_hint, source_basket):
            self.queries_used = min(len(queries), self.max_queries)
            self.results_count = self.queries_used
            return [
                EvidenceItem(title=f"Bocha {idx}", url=f"https://example.com/b{idx}", content="summary")
                for idx in range(self.queries_used)
            ]

    monkeypatch.setattr("ai_radar_agent.collector.BochaFetcher", FakeBocha)
    monkeypatch.setattr(
        "ai_radar_agent.collector.TavilyFetcher",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("Tavily should not be called")),
    )

    evidence, audit = collect_evidence_with_audit(settings, window_for_date(date(2026, 6, 1), "Asia/Shanghai"))

    assert len(evidence) == 3
    assert audit.search_queries_used == 3
    assert audit.provider_queries_used["bocha"] == 3
    assert audit.tavily_status == "query_budget_exhausted"


def test_search_providers_order_controls_query_budget(monkeypatch, tmp_path):
    settings = Settings(
        SEARCH_PROVIDERS="rss,tavily,bocha",
        BOCHA_API_KEY="bocha-test",
        TAVILY_ENABLED=True,
        TAVILY_API_KEY="tvly-test",
        MAX_SEARCH_QUERIES_PER_RUN=2,
        TAVILY_MAX_QUERIES=8,
    )
    settings.sources_path = _sources(tmp_path, ["q1", "q2", "q3"])
    monkeypatch.setattr("ai_radar_agent.collector.fetch_rss_feeds", lambda feeds, window, source_basket: [])

    class FakeTavily:
        def __init__(self, *args, **kwargs):
            self.max_queries = kwargs["max_queries"]
            self.queries_used = 0
            self.results_count = 0
            self.failed_count = 0
            self.status = "ok"
            self.error_summary = ""

        def search_queries(self, queries, window, region_hint, source_basket):
            self.queries_used = min(len(queries), self.max_queries)
            self.results_count = self.queries_used
            return [
                EvidenceItem(title=f"Tavily {idx}", url=f"https://example.com/t{idx}", content="summary")
                for idx in range(self.queries_used)
            ]

    monkeypatch.setattr("ai_radar_agent.collector.TavilyFetcher", FakeTavily)
    monkeypatch.setattr(
        "ai_radar_agent.collector.BochaFetcher",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("Bocha should not be called")),
    )

    evidence, audit = collect_evidence_with_audit(settings, window_for_date(date(2026, 6, 1), "Asia/Shanghai"))

    assert len(evidence) == 2
    assert audit.search_queries_used == 2
    assert audit.provider_queries_used["tavily"] == 2
    assert audit.bocha_status == "query_budget_exhausted"


def test_evidence_markdown_includes_provider_audit():
    evidence, recall_audit = [EvidenceItem(title="A", url="https://example.com", content="B")], RecallAudit(
        target_date="2026-06-01",
        target_window="window",
        rss_item_count=1,
        bocha_item_count=2,
        tavily_item_count=3,
        total_evidence_count=6,
        failed_source_count=0,
        tavily_status="ok",
        bocha_status="ok",
        search_providers_used="rss,bocha,tavily",
        search_query_budget=30,
        search_queries_used=5,
        provider_queries_used={"bocha": 2, "tavily": 3},
        provider_results_count={"rss": 1, "bocha": 2, "tavily": 3},
    )

    md = evidence_to_markdown(evidence, recall_audit)

    assert md.startswith("## 召回审计")
    assert "target_date: 2026-06-01" in md
    assert "Bocha item count: 2" in md
    assert "Tavily item count: 3" in md
    assert "### Provider audit" in md
    assert "| rss | true | ok | 0 | 1 | 1 |  |" in md
    assert "| bocha | false | ok | 2 | 2 | 2 |  |" in md
    assert "| tavily | true | ok | 3 | 3 | 3 |  |" in md
