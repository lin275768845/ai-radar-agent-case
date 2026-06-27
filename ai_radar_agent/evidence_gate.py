from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable
from urllib.parse import urlsplit

from .models import EvidenceItem, TimeWindow
from .source_quality import (
    SourceQualityConfig,
    apply_source_quality,
    load_source_quality_config,
    source_quality_counts,
)

logger = logging.getLogger(__name__)

SearchFn = Callable[[str, TimeWindow, int], list[EvidenceItem]]

OLD_REPEAT_MARKERS = ("回顾", "盘点", "一文看懂", "周报", "月报", "汇总", "昨日", "上周", "此前", "前延")
NEW_SIGNAL_MARKERS = (
    "上线",
    "推出",
    "开放",
    "官宣",
    "公告",
    "披露",
    "新增",
    "新价格",
    "降价",
    "涨价",
    "调用量",
    "token",
    "营收",
    "收入",
    "arr",
    "付费",
    "用户",
    "日活",
    "月活",
    "融资",
    "财报",
    "api",
)
CORE_SOURCE_TIERS = {"S1", "S2", "S3"}

ENTITY_DOMAINS = {
    "OpenAI": ["openai.com"],
    "Anthropic": ["anthropic.com"],
    "NVIDIA": ["nvidia.com", "blogs.nvidia.com"],
    "Microsoft": ["microsoft.com"],
    "Meta": ["meta.com", "about.fb.com"],
    "Amazon": ["amazon.com", "aws.amazon.com"],
    "阿里": ["aliyun.com", "qwenlm.github.io"],
    "腾讯": ["cloud.tencent.com", "tencent.com"],
    "字节": ["volcengine.com"],
    "DeepSeek": ["deepseek.com"],
    "月之暗面": ["moonshot.cn"],
    "MiniMax": ["minimax.io"],
}


@dataclass
class DroppedEvidence:
    title: str
    url: str
    source: str
    reason: str
    source_tier: str = ""
    date_status: str = ""

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass
class EvidenceGateAudit:
    date: str
    raw_evidence_count: int = 0
    filtered_evidence_count: int = 0
    dropped_count: int = 0
    primary_sources_count: int = 0
    official_sources_count: int = 0
    authoritative_media_count: int = 0
    aggregator_sources_count: int = 0
    dropped_old_repeated_count: int = 0
    dropped_out_of_window_count: int = 0
    dropped_low_source_fit_count: int = 0
    primary_source_enrichment_attempted: bool = False
    primary_source_enrichment_added_count: int = 0
    primary_source_missing_count: int = 0
    evidence_gate_relaxed: bool = False
    event_history_enabled: bool = True
    event_history_repeated_count: int = 0
    warnings: list[str] = field(default_factory=list)
    dropped: list[DroppedEvidence] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["dropped"] = [item.to_dict() for item in self.dropped]
        return data


@dataclass
class EvidenceGateResult:
    filtered: list[EvidenceItem]
    dropped: list[DroppedEvidence]
    audit: EvidenceGateAudit


def run_evidence_gate(
    items: list[EvidenceItem],
    window: TimeWindow,
    *,
    source_quality_path: Path | None = None,
    event_history_path: Path | None = None,
    event_history_enabled: bool = True,
    event_history_lookback_days: int = 7,
    primary_source_enrichment_enabled: bool = False,
    primary_source_max_queries: int = 8,
    primary_source_max_results_per_query: int = 3,
    primary_source_search: SearchFn | None = None,
    min_filtered_items: int = 10,
    max_items: int = 80,
) -> EvidenceGateResult:
    config = load_source_quality_config(source_quality_path)
    audit = EvidenceGateAudit(
        date=window.date_str,
        raw_evidence_count=len(items),
        event_history_enabled=event_history_enabled,
    )
    history = load_event_history(event_history_path, window.target_date, event_history_lookback_days) if event_history_enabled else {}
    scored = [apply_source_quality(item, config) for item in items]
    for item in scored:
        _classify_date(item, window, history, audit)
        _mark_source_core_eligibility(item)
    if primary_source_enrichment_enabled and primary_source_search:
        added = enrich_primary_sources(
            scored,
            window,
            config=config,
            search_fn=primary_source_search,
            max_queries=primary_source_max_queries,
            max_results_per_query=primary_source_max_results_per_query,
            audit=audit,
        )
        for item in added:
            _classify_date(item, window, history, audit)
            _mark_source_core_eligibility(item)
        scored.extend(added)
    elif primary_source_enrichment_enabled:
        audit.primary_source_enrichment_attempted = True
        audit.warnings.append("primary source enrichment skipped: no search function")

    filtered: list[EvidenceItem] = []
    relaxed_candidates: list[EvidenceItem] = []
    dropped: list[DroppedEvidence] = []
    seen_keys: set[str] = set()
    for item in scored:
        key = _dedupe_key(item)
        if key in seen_keys:
            _drop(item, "duplicate", dropped, audit)
            continue
        seen_keys.add(key)
        if item.source_fit == "low":
            reason = "aggregator" if item.source_tier == "S5" else "low_source_fit"
            _drop(item, reason, dropped, audit)
            continue
        if item.date_status == "old_repeated":
            _drop(item, "old_repeated", dropped, audit)
            continue
        if item.date_status == "out_of_window":
            _drop(item, "out_of_window", dropped, audit)
            continue
        if item.date_status == "unknown" and not item.is_primary_source:
            item.not_core_eligible = True
            relaxed_candidates.append(item)
            continue
        filtered.append(item)

    if len(filtered) < min_filtered_items:
        for item in relaxed_candidates:
            if len(filtered) >= min_filtered_items:
                break
            filtered.append(item)
            audit.evidence_gate_relaxed = True

    filtered = filtered[:max_items]
    counts = source_quality_counts(filtered)
    audit.filtered_evidence_count = len(filtered)
    audit.dropped_count = len(dropped)
    audit.dropped = dropped
    audit.primary_sources_count = counts["primary_sources_count"]
    audit.official_sources_count = counts["official_sources_count"]
    audit.authoritative_media_count = counts["authoritative_media_count"]
    audit.aggregator_sources_count = counts["aggregator_sources_count"]
    return EvidenceGateResult(filtered=filtered, dropped=dropped, audit=audit)


def enrich_primary_sources(
    items: list[EvidenceItem],
    window: TimeWindow,
    *,
    config: SourceQualityConfig,
    search_fn: SearchFn,
    max_queries: int,
    max_results_per_query: int,
    audit: EvidenceGateAudit,
) -> list[EvidenceItem]:
    audit.primary_source_enrichment_attempted = True
    output: list[EvidenceItem] = []
    queries_used = 0
    searched_entities: set[str] = set()
    for item in items:
        if queries_used >= max_queries:
            break
        if item.source_fit == "low" or item.date_status in {"old_repeated", "out_of_window"}:
            continue
        entity = _first_entity(item.title, item.content)
        if not entity or entity in searched_entities:
            continue
        searched_entities.add(entity)
        for domain in ENTITY_DOMAINS.get(entity, [])[:2]:
            if queries_used >= max_queries:
                break
            query = f'site:{domain} {entity} AI {window.date_str}'
            queries_used += 1
            try:
                results = search_fn(query, window, max_results_per_query)
            except Exception as exc:  # noqa: BLE001
                audit.warnings.append(f"primary source enrichment failed for {entity}: {str(exc)[:120]}")
                continue
            official = [apply_source_quality(result, config) for result in results if _host_matches(result.url, domain)]
            if not official:
                audit.primary_source_missing_count += 1
                continue
            for result in official:
                result.is_primary_source = True
                result.source_tier = "S1"
                result.source_fit = "high"
                result.source_quality_score = max(result.source_quality_score, 95)
                result.source_quality_reason = "official source enrichment"
                output.append(result)
                audit.primary_source_enrichment_added_count += 1
                if len(output) >= max_queries * max_results_per_query:
                    return output
    return output


def render_dropped_markdown(audit: EvidenceGateAudit) -> str:
    reason_counts: dict[str, int] = {
        "old_repeated": 0,
        "out_of_window": 0,
        "low_source_fit": 0,
        "aggregator": 0,
        "duplicate": 0,
        "no_date": 0,
        "other": 0,
    }
    for item in audit.dropped:
        reason = item.reason if item.reason in reason_counts else "other"
        reason_counts[reason] += 1
    rows = sorted(audit.dropped, key=_dropped_sort_key)[:50]
    lines = [
        "# Evidence Dropped",
        "",
        f"- date: {audit.date}",
        f"- dropped_count: {audit.dropped_count}",
        "",
        "## Reason distribution",
        "",
        "| reason | count |",
        "|---|---:|",
    ]
    for reason, count in reason_counts.items():
        lines.append(f"| {reason} | {count} |")
    lines.extend(
        [
            "",
            "## Dropped evidence sample",
            "",
            "| title | source | source_tier | date_status | reason | url |",
            "|---|---|---|---|---|---|",
        ]
    )
    for item in rows:
        lines.append(
            f"| {_cell(item.title)} | {_cell(item.source)} | {_cell(item.source_tier)} | "
            f"{_cell(item.date_status)} | {_cell(item.reason)} | {_cell(item.url, limit=None)} |"
        )
    lines.append("")
    return "\n".join(lines)


def update_event_history(path: Path, window: TimeWindow, brief: dict[str, object]) -> None:
    rows = []
    for side in ("domestic_top", "overseas_top"):
        value = brief.get(side)
        if not isinstance(value, list):
            continue
        for item in value:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or item.get("card_title") or "").strip()
            if not title:
                continue
            urls = []
            sources = item.get("sources")
            if isinstance(sources, list):
                for source in sources:
                    if isinstance(source, dict) and source.get("url"):
                        urls.append(str(source["url"]))
            rows.append(
                {
                    "event_id": event_id_for_title(title, urls[0] if urls else ""),
                    "title": title,
                    "entities": extract_entities(title),
                    "first_seen_date": window.date_str,
                    "last_seen_date": window.date_str,
                    "source_urls": urls[:5],
                    "status": "reported",
                }
            )
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_event_history(path: Path | None, target_date: date, lookback_days: int) -> dict[str, dict[str, object]]:
    if not path or not path.exists():
        return {}
    start = target_date - timedelta(days=lookback_days)
    output: dict[str, dict[str, object]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        event_id = str(row.get("event_id") or "")
        last_seen = str(row.get("last_seen_date") or row.get("first_seen_date") or "")
        try:
            last_seen_date = date.fromisoformat(last_seen)
        except ValueError:
            continue
        if event_id and start <= last_seen_date < target_date:
            output[event_id] = row
    return output


def event_id_for_title(title: str, url: str = "") -> str:
    slug = re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", "_", title.lower()).strip("_")[:80]
    host = urlsplit(url).netloc.lower()
    return f"{slug}_{host}" if host else slug


def extract_entities(text: str) -> list[str]:
    return [entity for entity in ENTITY_DOMAINS if entity.lower() in text.lower()]


def _classify_date(
    item: EvidenceItem,
    window: TimeWindow,
    history: dict[str, dict[str, object]],
    audit: EvidenceGateAudit,
) -> None:
    text = f"{item.title} {item.content}".lower()
    has_new_signal = any(marker.lower() in text for marker in NEW_SIGNAL_MARKERS)
    has_old_marker = any(marker.lower() in text for marker in OLD_REPEAT_MARKERS)
    explicit_event_date = _explicit_event_date(item, window)
    if explicit_event_date:
        item.event_date = explicit_event_date.isoformat()
    published = _parse_datetime(item.published_at, window)
    item.report_date = window.date_str
    if published:
        local = published.astimezone(window.start.tzinfo)
        item.published_at = local.isoformat()
        item.signal_date = local.date().isoformat()
        if explicit_event_date and explicit_event_date < window.target_date:
            item.date_status = "old_repeated"
            item.not_core_eligible = True
            item.date_reason = f"explicit event_date {explicit_event_date.isoformat()} before target date"
        elif explicit_event_date and explicit_event_date > window.target_date:
            item.date_status = "out_of_window"
            item.not_core_eligible = True
            item.date_reason = f"explicit event_date {explicit_event_date.isoformat()} after target date"
        elif window.start <= local <= window.end:
            item.date_status = "old_repeated" if has_old_marker and not has_new_signal else "in_window"
            item.date_reason = "published_at within target date"
        elif has_new_signal:
            item.date_status = "new_signal"
            item.not_core_eligible = False
            item.date_reason = "outside published_at but contains new signal marker"
        else:
            item.date_status = "out_of_window"
            item.not_core_eligible = True
            item.date_reason = "published_at outside target date"
    elif has_old_marker and not has_new_signal:
        item.date_status = "old_repeated"
        item.not_core_eligible = True
        item.date_reason = "old/review marker without new signal"
    else:
        item.date_status = "unknown"
        item.not_core_eligible = not item.is_primary_source
        item.date_reason = "published_at missing or unparsable"

    event_id = event_id_for_title(item.title, item.url)
    history_row = history.get(event_id)
    if history_row and item.date_status != "new_signal":
        if has_new_signal:
            item.date_status = "new_signal"
            item.not_core_eligible = False
            item.date_reason = "event seen in history but has new signal marker"
            return
        urls = {str(url) for url in history_row.get("source_urls", []) if isinstance(url, str)}
        is_new_good_source = item.source_tier in {"S1", "S2"} and item.url and item.url not in urls
        if not (has_new_signal or is_new_good_source):
            item.date_status = "old_repeated"
            item.not_core_eligible = True
            item.date_reason = "event seen in history without new signal"
            audit.event_history_repeated_count += 1


def _explicit_event_date(item: EvidenceItem, window: TimeWindow) -> date | None:
    parsed = _parse_explicit_date_value(item.event_date, window)
    if parsed:
        return parsed
    text = f"{item.title} {item.content}"
    return _extract_action_date_from_text(text, window)


def _parse_explicit_date_value(value: str, window: TimeWindow) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _extract_action_date_from_text(text: str, window: TimeWindow) -> date | None:
    action_markers = tuple(dict.fromkeys(NEW_SIGNAL_MARKERS + ("发布", "宣布", "启动", "完成", "收购", "签署")))
    for match in re.finditer(r"(?P<month>\d{1,2})\s*月\s*(?P<day>\d{1,2})\s*日", text):
        start, end = match.span()
        context = text[max(0, start - 30) : min(len(text), end + 90)]
        if not any(marker.lower() in context.lower() for marker in action_markers):
            continue
        try:
            explicit = date(window.target_date.year, int(match.group("month")), int(match.group("day")))
        except ValueError:
            continue
        if explicit > window.target_date + timedelta(days=180):
            explicit = date(window.target_date.year - 1, explicit.month, explicit.day)
        return explicit
    return None


def _mark_source_core_eligibility(item: EvidenceItem) -> None:
    if item.source_tier and item.source_tier not in CORE_SOURCE_TIERS:
        item.not_core_eligible = True


def _drop(item: EvidenceItem, reason: str, dropped: list[DroppedEvidence], audit: EvidenceGateAudit) -> None:
    if reason == "old_repeated":
        audit.dropped_old_repeated_count += 1
    elif reason == "out_of_window":
        audit.dropped_out_of_window_count += 1
    elif reason in {"low_source_fit", "aggregator"}:
        audit.dropped_low_source_fit_count += 1
    dropped.append(
        DroppedEvidence(
            title=item.title,
            url=item.url,
            source=item.source,
            reason=reason,
            source_tier=item.source_tier,
            date_status=item.date_status,
        )
    )


def _parse_datetime(value: str, window: TimeWindow) -> datetime | None:
    if not value:
        return None
    raw = value.strip()
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=window.start.tzinfo)
    return parsed


def _dedupe_key(item: EvidenceItem) -> str:
    return (item.url.split("?")[0].rstrip("/").lower() or event_id_for_title(item.title)).strip()


def _first_entity(title: str, content: str) -> str:
    entities = extract_entities(f"{title} {content}")
    return entities[0] if entities else ""


def _host_matches(url: str, domain: str) -> bool:
    host = urlsplit(url).netloc.lower()
    return host == domain or host.endswith(f".{domain}")


def _dropped_sort_key(item: DroppedEvidence) -> tuple[int, str]:
    reason_rank = {
        "old_repeated": 0,
        "out_of_window": 1,
        "aggregator": 2,
        "low_source_fit": 3,
        "duplicate": 4,
    }
    tier_rank = {"S1": 0, "S2": 1, "S3": 2, "S4": 3, "S5": 4}
    return (reason_rank.get(item.reason, 9), tier_rank.get(item.source_tier, 9), item.title)


def _cell(value: str, *, limit: int | None = 300) -> str:
    text = " ".join(str(value or "").replace("|", "\\|").split())
    return text if limit is None else text[:limit]
