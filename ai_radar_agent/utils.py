from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Iterable

from .models import EvidenceItem, RecallAudit


def setup_logging(verbose: bool = False) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    logging.getLogger("ai_radar_agent").setLevel(logging.DEBUG if verbose else logging.INFO)
    for noisy_logger in ("openai", "openai._base_client", "httpx", "httpcore", "urllib3"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def safe_filename(value: str) -> str:
    value = re.sub(r"[^\w\-.\u4e00-\u9fff]+", "_", value, flags=re.UNICODE)
    return value.strip("_")


def dedupe_evidence(items: Iterable[EvidenceItem]) -> list[EvidenceItem]:
    seen: set[str] = set()
    output: list[EvidenceItem] = []
    for item in items:
        key = item.key()
        if not key or key in seen:
            continue
        seen.add(key)
        output.append(item)
    return output


def evidence_to_markdown(
    items: list[EvidenceItem],
    audit: RecallAudit | None = None,
    gate_audit: Any | None = None,
    *,
    include_dropped: bool = False,
    core_eligible_only: bool = False,
    not_core_only: bool = False,
) -> str:
    lines = []
    if gate_audit:
        lines.extend(_evidence_gate_section(gate_audit, include_dropped=include_dropped))
    if audit:
        lines.extend(
            [
                "## 召回审计",
                "",
                f"- target_date: {audit.target_date}",
                f"- target window: {audit.target_window}",
                f"- RSS item count: {audit.rss_item_count}",
                f"- Bocha item count: {audit.bocha_item_count}",
                f"- Tavily item count: {audit.tavily_item_count}",
                f"- total evidence count: {audit.total_evidence_count}",
                f"- failed source count: {audit.failed_source_count}",
                f"- search_providers_used: {audit.search_providers_used}",
                f"- search_query_budget: {audit.search_query_budget}",
                f"- search_queries_used: {audit.search_queries_used}",
                f"- tavily_enabled: {audit.tavily_enabled}",
                f"- tavily_status: {audit.tavily_status}",
                f"- tavily_error_summary: {audit.tavily_error_summary[:300]}",
                f"- rss_fallback_used: {audit.rss_fallback_used}",
                "",
            ]
        )
        lines.extend(_provider_audit_table(audit))
        if audit.rss_sources:
            lines.extend(
                [
                    "### RSS per-source audit",
                    "",
                    "| name | status | count | error | url |",
                    "| --- | --- | ---: | --- | --- |",
                ]
            )
            for source in audit.rss_sources:
                lines.append(
                    f"| {_md_cell(source.name)} | {source.status} | {source.count} | "
                    f"{_md_cell(source.error_summary[:120])} | {_md_cell(source.url)} |"
                )
            lines.append("")
        if audit.bocha_item_count == 0 and audit.tavily_item_count == 0 and audit.rss_item_count > 0:
            if audit.tavily_status == "disabled_by_env":
                lines.extend(["Tavily disabled by TAVILY_ENABLED=false; running with RSS-only evidence.", ""])
            elif audit.tavily_status == "missing_api_key":
                lines.extend(["TAVILY_API_KEY missing; running with RSS-only evidence.", ""])
            elif audit.tavily_status in {"connectivity_failed", "skipped_after_consecutive_failures"}:
                lines.extend(["Tavily connectivity degraded; running with RSS-only evidence.", ""])
            else:
                lines.extend(["Search providers returned 0 non-RSS items; running with RSS-only evidence.", ""])
        lines.extend(
            [
                "## 证据列表",
                "",
            ]
        )
    skipped_not_core = 0
    for idx, item in enumerate(items, start=1):
        if core_eligible_only and item.not_core_eligible:
            skipped_not_core += 1
            continue
        if not_core_only and not item.not_core_eligible:
            continue
        content = " ".join((item.content or "").split())[:1200]
        evidence_id = f"E{idx}"
        lines.append(
            f"[{evidence_id}] 标题：{item.title}\n"
            f"来源：{item.source or item.source_type}｜地区提示：{item.region_hint}｜篮子：{item.source_basket}\n"
            f"source_tier：{item.source_tier or 'unknown'}｜source_fit：{item.source_fit or 'unknown'}"
            f"｜primary_source：{_bool(bool(item.is_primary_source))}\n"
            f"date_status：{item.date_status or 'unknown'}｜not_core_eligible：{_bool(bool(item.not_core_eligible))}"
            f"｜date_reason：{item.date_reason or ''}\n"
            f"时间：{item.published_at or '未知'}\n"
            f"URL：{item.url}\n"
            f"摘要：{content}\n"
        )
    if core_eligible_only and skipped_not_core:
        lines.append(f"\n已从主报告 LLM 输入排除 not_core_eligible 证据：{skipped_not_core} 条。")
    return "\n".join(lines)


def _evidence_gate_section(gate_audit: Any, *, include_dropped: bool) -> list[str]:
    def get(name: str, default: object = "") -> object:
        if isinstance(gate_audit, dict):
            return gate_audit.get(name, default)
        return getattr(gate_audit, name, default)

    metrics = [
        "raw_evidence_count",
        "filtered_evidence_count",
        "dropped_count",
        "primary_sources_count",
        "official_sources_count",
        "authoritative_media_count",
        "aggregator_sources_count",
        "dropped_old_repeated_count",
        "dropped_out_of_window_count",
        "dropped_low_source_fit_count",
        "primary_source_enrichment_attempted",
        "primary_source_enrichment_added_count",
        "evidence_gate_relaxed",
        "event_history_enabled",
        "event_history_repeated_count",
    ]
    lines = [
        "## Evidence Gate 审计",
        "",
        "| metric | value |",
        "|---|---|",
    ]
    for metric in metrics:
        lines.append(f"| {metric} | {_md_cell(str(get(metric, '')))} |")
    lines.append("")
    if include_dropped:
        dropped = get("dropped", [])
        lines.extend(
            [
                "### Dropped evidence",
                "",
                "| title | source | source_tier | date_status | reason | url |",
                "|---|---|---|---|---|---|",
            ]
        )
        for item in (dropped or [])[:50]:
            if hasattr(item, "to_dict"):
                row = item.to_dict()
            elif isinstance(item, dict):
                row = item
            else:
                row = {}
            lines.append(
                f"| {_md_cell(str(row.get('title', ''))[:300])} | {_md_cell(str(row.get('source', ''))[:120])} | "
                f"{_md_cell(str(row.get('source_tier', ''))[:40])} | {_md_cell(str(row.get('date_status', ''))[:80])} | "
                f"{_md_cell(str(row.get('reason', ''))[:120])} | {_md_cell(str(row.get('url', '')))} |"
            )
        lines.append("")
    return lines


def _md_cell(value: str) -> str:
    return " ".join(str(value or "").replace("|", "\\|").split())


def _provider_audit_table(audit: RecallAudit) -> list[str]:
    rows = {entry.provider: entry for entry in audit.provider_audits or []}
    lines = [
        "### Provider audit",
        "",
        "| provider | enabled | status | queries_used | results_count | evidence_count | error_summary |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for provider in ["rss", "bocha", "tavily"]:
        entry = rows.get(provider)
        if entry is None:
            enabled = {
                "rss": True,
                "bocha": audit.bocha_enabled,
                "tavily": audit.tavily_enabled,
            }.get(provider, False)
            status = {
                "rss": "ok" if audit.rss_item_count else "not_run",
                "bocha": audit.bocha_status,
                "tavily": audit.tavily_status,
            }.get(provider, "not_run")
            queries_used = (audit.provider_queries_used or {}).get(provider, 0)
            results_count = (audit.provider_results_count or {}).get(provider, 0)
            evidence_count = {
                "rss": audit.rss_item_count,
                "bocha": audit.bocha_item_count,
                "tavily": audit.tavily_item_count,
            }.get(provider, 0)
            error_summary = {
                "bocha": audit.bocha_error_summary,
                "tavily": audit.tavily_error_summary,
            }.get(provider, "")
        else:
            enabled = entry.enabled
            status = entry.status
            queries_used = entry.queries_used
            results_count = entry.results_count
            evidence_count = entry.evidence_count
            error_summary = entry.error_summary
        lines.append(
            f"| {provider} | {_bool(enabled)} | {_md_cell(status)} | {queries_used} | "
            f"{results_count} | {evidence_count} | {_md_cell(error_summary[:160])} |"
        )
    lines.append("")
    return lines


def _bool(value: bool) -> str:
    return "true" if value else "false"


def save_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
