from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from difflib import SequenceMatcher
from urllib.parse import urlsplit, urlunsplit

from .models import EvidenceItem, TimeWindow


@dataclass
class TopEventAuditItem:
    title: str
    region: str
    priority: str
    source_tiers: list[str] = field(default_factory=list)
    source_fit: str = "unknown"
    date_status: str = "unknown"
    is_primary_source_present: bool = False
    source_urls: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass
class TopEventAudit:
    date: str
    top_events_count: int = 0
    top_events_with_primary_source_count: int = 0
    top_events_with_s1_source_count: int = 0
    top_events_with_s1_or_s2_source_count: int = 0
    top_events_with_s1_s2_or_s3_source_count: int = 0
    top_events_with_low_source_count: int = 0
    top_events_out_of_window_count: int = 0
    top_events_old_repeated_count: int = 0
    top_events_new_signal_count: int = 0
    events: list[TopEventAuditItem] = field(default_factory=list)

    @property
    def warnings_count(self) -> int:
        return sum(len(item.warnings) for item in self.events)

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["events"] = [item.to_dict() for item in self.events]
        data["top_event_audit_warnings_count"] = self.warnings_count
        return data


def audit_top_events(brief: dict[str, object], evidence: list[EvidenceItem], window: TimeWindow) -> TopEventAudit:
    evidence_by_url = {_normalize_url(item.url): item for item in evidence if item.url}
    audit = TopEventAudit(date=window.date_str)
    for region, key in (("domestic", "domestic_top"), ("overseas", "overseas_top")):
        value = brief.get(key)
        if not isinstance(value, list):
            continue
        for raw_item in value:
            if not isinstance(raw_item, dict):
                continue
            title = str(raw_item.get("title") or raw_item.get("card_title") or "").strip()
            if not title:
                continue
            matched = _matched_evidence(raw_item, title, evidence_by_url, evidence)
            item = _audit_item(title, region, str(raw_item.get("priority") or ""), matched)
            audit.events.append(item)
    _finalize_counts(audit)
    return audit


def _audit_item(title: str, region: str, priority: str, matched: list[EvidenceItem]) -> TopEventAuditItem:
    source_urls = _unique([item.url for item in matched if item.url])
    tiers = _unique([item.source_tier or "unknown" for item in matched if item.source_tier])
    source_fit = _combined_source_fit(matched)
    date_status = _combined_date_status(matched)
    item = TopEventAuditItem(
        title=title,
        region=region,
        priority=priority,
        source_tiers=tiers,
        source_fit=source_fit,
        date_status=date_status,
        is_primary_source_present=any(bool(item.is_primary_source) for item in matched),
        source_urls=source_urls,
    )
    if source_fit == "low":
        item.warnings.append("source_fit=low")
    if date_status in {"old_repeated", "out_of_window"}:
        item.warnings.append(f"date_status={date_status}")
    if not any(tier in {"S1", "S2", "S3"} for tier in tiers):
        item.warnings.append("missing S1/S2/S3 source")
    return item


def _matched_evidence(
    raw_item: dict[str, object],
    title: str,
    evidence_by_url: dict[str, EvidenceItem],
    evidence: list[EvidenceItem],
) -> list[EvidenceItem]:
    matched: list[EvidenceItem] = []
    sources = raw_item.get("sources")
    if isinstance(sources, list):
        for source in sources:
            if not isinstance(source, dict):
                continue
            url = str(source.get("url") or "")
            item = evidence_by_url.get(_normalize_url(url))
            if item:
                matched.append(item)
    if matched:
        return _dedupe_items(matched)
    scored = []
    for item in evidence:
        ratio = _title_similarity(title, item.title)
        if ratio >= 0.74:
            scored.append((ratio, item))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _ratio, item in scored[:2]]


def _finalize_counts(audit: TopEventAudit) -> None:
    audit.top_events_count = len(audit.events)
    audit.top_events_with_primary_source_count = sum(1 for item in audit.events if item.is_primary_source_present)
    audit.top_events_with_s1_source_count = sum(1 for item in audit.events if "S1" in item.source_tiers)
    audit.top_events_with_s1_or_s2_source_count = sum(
        1 for item in audit.events if any(tier in {"S1", "S2"} for tier in item.source_tiers)
    )
    audit.top_events_with_s1_s2_or_s3_source_count = sum(
        1 for item in audit.events if any(tier in {"S1", "S2", "S3"} for tier in item.source_tiers)
    )
    audit.top_events_with_low_source_count = sum(1 for item in audit.events if item.source_fit == "low")
    audit.top_events_out_of_window_count = sum(1 for item in audit.events if item.date_status == "out_of_window")
    audit.top_events_old_repeated_count = sum(1 for item in audit.events if item.date_status == "old_repeated")
    audit.top_events_new_signal_count = sum(1 for item in audit.events if item.date_status == "new_signal")


def _combined_source_fit(items: list[EvidenceItem]) -> str:
    fits = {item.source_fit for item in items if item.source_fit}
    if "low" in fits:
        return "low"
    if "high" in fits:
        return "high"
    if "medium" in fits:
        return "medium"
    return "unknown"


def _combined_date_status(items: list[EvidenceItem]) -> str:
    statuses = {item.date_status for item in items if item.date_status}
    for status in ("old_repeated", "out_of_window", "new_signal", "in_window", "unknown"):
        if status in statuses:
            return status
    return "unknown"


def _title_similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, _normalize_title(left), _normalize_title(right)).ratio()


def _normalize_title(value: str) -> str:
    return re.sub(r"[\W_]+", "", str(value or "").lower(), flags=re.UNICODE)


def _normalize_url(value: str) -> str:
    parsed = urlsplit(str(value or ""))
    host = parsed.netloc.lower().removeprefix("www.")
    path = parsed.path.rstrip("/")
    return urlunsplit((parsed.scheme.lower(), host, path, "", ""))


def _dedupe_items(items: list[EvidenceItem]) -> list[EvidenceItem]:
    seen: set[str] = set()
    output: list[EvidenceItem] = []
    for item in items:
        key = _normalize_url(item.url) or _normalize_title(item.title)
        if key in seen:
            continue
        seen.add(key)
        output.append(item)
    return output


def _unique(values: list[str]) -> list[str]:
    output: list[str] = []
    for value in values:
        if value and value not in output:
            output.append(value)
    return output
