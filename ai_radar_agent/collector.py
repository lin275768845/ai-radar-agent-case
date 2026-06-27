from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from .config import Settings
from .fetchers.bocha_search import BochaFetcher
from .fetchers.rss import fetch_rss_feeds
from .fetchers.tavily_search import TavilyFetcher
from .models import EvidenceItem, ProviderAudit, RecallAudit, TimeWindow
from .utils import dedupe_evidence

logger = logging.getLogger(__name__)


def load_sources(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def collect_evidence_with_audit(settings: Settings, window: TimeWindow) -> tuple[list[EvidenceItem], RecallAudit]:
    sources = load_sources(settings.sources_path)
    all_items: list[EvidenceItem] = []
    audit = RecallAudit(target_date=window.date_str, target_window=window.display_range)
    providers = _search_providers(settings)
    audit.search_providers_used = ",".join(providers)
    audit.search_query_budget = settings.max_search_queries_per_run
    audit.provider_queries_used = {}
    audit.provider_results_count = {}
    audit.provider_audits = []
    remaining_queries = settings.max_search_queries_per_run

    rss_feeds = sources.get("rss", [])
    rss_items: list[EvidenceItem] = []
    rss_enabled = "rss" in providers
    if rss_enabled and rss_feeds:
        try:
            rss_result = fetch_rss_feeds(rss_feeds, window, source_basket="rss_official_media")
            if isinstance(rss_result, tuple):
                rss_items, audit.rss_sources = rss_result
            else:
                rss_items = rss_result
                audit.rss_sources = []
        except Exception as exc:  # noqa: BLE001
            logger.warning("RSS fetch failed; continuing with other sources: %s", exc)
            rss_items = []
            audit.rss_sources = []
            audit.failed_source_count += 1
        audit.rss_item_count = len(rss_items)
        audit.failed_source_count += sum(1 for source in audit.rss_sources or [] if source.status in {"failed", "timeout"})
        all_items.extend(rss_items)
    elif not rss_enabled:
        audit.rss_sources = []
    audit.provider_audits.append(
        ProviderAudit(
            provider="rss",
            enabled=rss_enabled,
            status="ok" if rss_enabled else "disabled_by_search_providers",
            queries_used=0,
            results_count=len(rss_items),
            evidence_count=len(rss_items),
            error_summary="",
        )
    )

    bocha_items: list[EvidenceItem] = []
    tavily_items: list[EvidenceItem] = []
    search_baskets = sources.get("search_baskets", [])
    for provider in (provider for provider in providers if provider != "rss"):
        if provider == "bocha":
            audit.bocha_enabled = True
            if not settings.bocha_api_key:
                audit.bocha_status = "missing_api_key"
                audit.bocha_error_summary = "BOCHA_API_KEY missing; skipping Bocha."
                logger.warning("BOCHA_API_KEY missing; skipping Bocha.")
            elif remaining_queries <= 0:
                audit.bocha_status = "query_budget_exhausted"
                audit.bocha_error_summary = "MAX_SEARCH_QUERIES_PER_RUN exhausted before Bocha."
            else:
                max_queries = min(settings.bocha_max_queries, remaining_queries)
                fetcher = BochaFetcher(
                    settings.bocha_api_key,
                    base_url=settings.bocha_base_url,
                    max_results=settings.bocha_max_results_per_query,
                    connect_timeout=settings.bocha_connect_timeout,
                    read_timeout=settings.bocha_read_timeout,
                    max_queries=max_queries,
                )
                bocha_items = _run_search_fetcher(fetcher, search_baskets, window)
                bocha_items = bocha_items[: settings.max_search_results_per_provider]
                audit.bocha_status = fetcher.status
                audit.bocha_error_summary = fetcher.error_summary
                audit.failed_source_count += fetcher.failed_count
                remaining_queries -= fetcher.queries_used
                audit.search_queries_used += fetcher.queries_used
                audit.provider_queries_used["bocha"] = fetcher.queries_used
                audit.provider_results_count["bocha"] = fetcher.results_count
                all_items.extend(bocha_items)
            audit.bocha_item_count = len(bocha_items)
            audit.provider_audits.append(
                ProviderAudit(
                    provider="bocha",
                    enabled=True,
                    status=audit.bocha_status,
                    queries_used=audit.provider_queries_used.get("bocha", 0),
                    results_count=audit.provider_results_count.get("bocha", 0),
                    evidence_count=len(bocha_items),
                    error_summary=audit.bocha_error_summary[:300],
                )
            )
        elif provider == "tavily":
            audit.tavily_enabled = bool(settings.tavily_enabled)
            if not settings.tavily_enabled:
                audit.tavily_status = "disabled_by_env"
                audit.tavily_error_summary = "Tavily disabled by TAVILY_ENABLED=false."
                logger.warning("Tavily disabled by TAVILY_ENABLED=false.")
            elif not settings.tavily_api_key:
                audit.tavily_enabled = False
                audit.tavily_status = "missing_api_key"
                audit.tavily_error_summary = "TAVILY_API_KEY missing; skipping Tavily."
                logger.warning("TAVILY_API_KEY missing; skipping Tavily.")
            elif remaining_queries <= 0:
                audit.tavily_status = "query_budget_exhausted"
                audit.tavily_error_summary = "MAX_SEARCH_QUERIES_PER_RUN exhausted before Tavily."
            else:
                max_queries = min(settings.tavily_max_queries, remaining_queries)
                fetcher = TavilyFetcher(
                    settings.tavily_api_key,
                    max_results=settings.tavily_max_results_per_query,
                    connect_timeout=settings.tavily_connect_timeout,
                    read_timeout=settings.tavily_read_timeout,
                    max_queries=max_queries,
                    max_consecutive_connect_failures=settings.tavily_max_consecutive_connect_failures,
                )
                tavily_items = _run_search_fetcher(fetcher, search_baskets, window)
                tavily_items = tavily_items[: settings.max_search_results_per_provider]
                if not tavily_items:
                    logger.warning("Tavily returned 0 items; continuing with other evidence.")
                audit.tavily_item_count = len(tavily_items)
                audit.failed_source_count += fetcher.failed_count
                audit.tavily_status = fetcher.status
                audit.tavily_error_summary = fetcher.error_summary
                remaining_queries -= fetcher.queries_used
                audit.search_queries_used += fetcher.queries_used
                audit.provider_queries_used["tavily"] = fetcher.queries_used
                audit.provider_results_count["tavily"] = fetcher.results_count
                all_items.extend(tavily_items)
            audit.provider_audits.append(
                ProviderAudit(
                    provider="tavily",
                    enabled=audit.tavily_enabled,
                    status=audit.tavily_status,
                    queries_used=audit.provider_queries_used.get("tavily", 0),
                    results_count=audit.provider_results_count.get("tavily", 0),
                    evidence_count=len(tavily_items),
                    error_summary=audit.tavily_error_summary[:300],
                )
            )

    if "bocha" not in providers:
        audit.bocha_status = "disabled_by_search_providers"
        audit.bocha_error_summary = "Bocha disabled by SEARCH_PROVIDERS."
        audit.provider_audits.append(
            ProviderAudit(
                provider="bocha",
                enabled=False,
                status=audit.bocha_status,
                error_summary=audit.bocha_error_summary[:300],
            )
        )
    if "tavily" not in providers:
        audit.tavily_status = "disabled_by_search_providers"
        audit.tavily_error_summary = "Tavily disabled by SEARCH_PROVIDERS."
        audit.provider_audits.append(
            ProviderAudit(
                provider="tavily",
                enabled=False,
                status=audit.tavily_status,
                error_summary=audit.tavily_error_summary[:300],
            )
        )
    audit.provider_queries_used.setdefault("rss", 0)
    audit.provider_results_count.setdefault("rss", len(rss_items))
    audit.provider_queries_used.setdefault("bocha", 0)
    audit.provider_results_count.setdefault("bocha", 0)
    audit.provider_queries_used.setdefault("tavily", 0)
    audit.provider_results_count.setdefault("tavily", 0)
    audit.rss_fallback_used = len(rss_items) > 0 and len(bocha_items) == 0 and len(tavily_items) == 0

    deduped = dedupe_evidence(all_items)
    # Simple ordering: keep search/RSS order but cap context to avoid context overflow.
    evidence = deduped[: settings.max_evidence_items]
    audit.total_evidence_count = len(evidence)
    return evidence, audit


def collect_evidence(settings: Settings, window: TimeWindow) -> list[EvidenceItem]:
    evidence, _ = collect_evidence_with_audit(settings, window)
    return evidence


def _search_providers(settings: Settings) -> list[str]:
    raw = settings.search_providers or "rss,bocha"
    providers = []
    for item in raw.split(","):
        provider = item.strip().lower()
        if provider in {"rss", "bocha", "tavily"} and provider not in providers:
            providers.append(provider)
    providers = providers or ["rss", "bocha"]
    if "rss" not in providers:
        providers.insert(0, "rss")
    if settings.bocha_enabled and "bocha" not in providers:
        providers.append("bocha")
    return providers


def _run_search_fetcher(fetcher: Any, baskets: list[dict[str, Any]], window: TimeWindow) -> list[EvidenceItem]:
    items: list[EvidenceItem] = []
    for basket in baskets:
        items.extend(
            fetcher.search_queries(
                queries=basket.get("queries", []),
                window=window,
                region_hint=basket.get("region", "unknown"),
                source_basket=basket.get("name", "unknown"),
            )
        )
        if getattr(fetcher, "queries_used", 0) >= getattr(fetcher, "max_queries", 0):
            break
    return items
