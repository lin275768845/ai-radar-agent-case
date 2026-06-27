from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal


@dataclass(frozen=True)
class TimeWindow:
    """A complete Beijing/Shanghai natural day window."""

    target_date: date
    start: datetime
    end: datetime
    timezone: str

    @property
    def date_str(self) -> str:
        return self.target_date.isoformat()

    @property
    def zh_date(self) -> str:
        return self.target_date.strftime("%Y年%m月%d日")

    @property
    def display_range(self) -> str:
        return f"{self.start:%Y-%m-%d %H:%M:%S %Z} – {self.end:%Y-%m-%d %H:%M:%S %Z}"


@dataclass
class EvidenceItem:
    title: str
    url: str
    content: str
    source: str = ""
    published_at: str = ""
    provider: str = ""
    retrieved_at: str = ""
    region_hint: Literal["domestic", "overseas", "global", "unknown"] = "unknown"
    source_basket: str = "unknown"
    source_type: str = "search"
    event_date: str = ""
    report_date: str = ""
    signal_date: str = ""
    date_status: str = ""
    date_reason: str = ""
    not_core_eligible: bool = False
    source_tier: str = ""
    source_fit: str = ""
    source_quality_score: int = 0
    is_primary_source: bool = False
    source_quality_reason: str = ""

    def key(self) -> str:
        normalized_url = self.url.split("?")[0].rstrip("/").lower()
        normalized_title = " ".join(self.title.lower().split())
        return normalized_url or normalized_title


@dataclass
class RssSourceAudit:
    name: str
    url: str
    status: str
    count: int = 0
    error_summary: str = ""

    def to_dict(self) -> dict[str, int | str]:
        return {
            "name": self.name,
            "url": self.url,
            "status": self.status,
            "count": self.count,
            "error_summary": self.error_summary,
        }


@dataclass
class ProviderAudit:
    provider: str
    enabled: bool
    status: str = "ok"
    queries_used: int = 0
    results_count: int = 0
    evidence_count: int = 0
    error_summary: str = ""

    def to_dict(self) -> dict[str, bool | int | str]:
        return {
            "provider": self.provider,
            "enabled": self.enabled,
            "status": self.status,
            "queries_used": self.queries_used,
            "results_count": self.results_count,
            "evidence_count": self.evidence_count,
            "error_summary": self.error_summary,
        }


@dataclass
class RecallAudit:
    target_date: str
    target_window: str
    rss_item_count: int = 0
    tavily_item_count: int = 0
    total_evidence_count: int = 0
    failed_source_count: int = 0
    tavily_enabled: bool = True
    tavily_status: str = "ok"
    tavily_error_summary: str = ""
    rss_fallback_used: bool = False
    rss_sources: list[RssSourceAudit] | None = None
    bocha_item_count: int = 0
    bocha_enabled: bool = False
    bocha_status: str = "disabled"
    bocha_error_summary: str = ""
    search_providers_used: str = ""
    search_query_budget: int = 0
    search_queries_used: int = 0
    provider_queries_used: dict[str, int] | None = None
    provider_results_count: dict[str, int] | None = None
    provider_audits: list[ProviderAudit] | None = None

    def to_dict(self) -> dict[str, bool | int | str | dict[str, int] | list[dict[str, bool | int | str]]]:
        return {
            "target_date": self.target_date,
            "target_window": self.target_window,
            "rss_item_count": self.rss_item_count,
            "tavily_item_count": self.tavily_item_count,
            "total_evidence_count": self.total_evidence_count,
            "failed_source_count": self.failed_source_count,
            "tavily_enabled": self.tavily_enabled,
            "tavily_status": self.tavily_status,
            "tavily_error_summary": self.tavily_error_summary,
            "rss_fallback_used": self.rss_fallback_used,
            "rss_sources": [source.to_dict() for source in self.rss_sources or []],
            "bocha_item_count": self.bocha_item_count,
            "bocha_enabled": self.bocha_enabled,
            "bocha_status": self.bocha_status,
            "bocha_error_summary": self.bocha_error_summary,
            "search_providers_used": self.search_providers_used,
            "search_query_budget": self.search_query_budget,
            "search_queries_used": self.search_queries_used,
            "provider_queries_used": self.provider_queries_used or {},
            "provider_results_count": self.provider_results_count or {},
            "provider_audits": [provider.to_dict() for provider in self.provider_audits or []],
        }
