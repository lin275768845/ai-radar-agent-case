from __future__ import annotations

import json
import logging
import re
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .models import EvidenceItem

logger = logging.getLogger(__name__)

MAX_P2_TOP_EVENTS_PER_REGION = 2
CORE_SOURCE_TIERS = {"S1", "S2", "S3"}

COMMON_TITLE_WORDS = (
    "发布",
    "上线",
    "推出",
    "宣布",
    "正式",
    "计划",
    "报告",
    "消息",
    "传闻",
    "价格",
    "升级",
    "完成",
    "突破",
    "创纪录",
    "超预期",
)

OLD_REPEAT_MARKERS = ("回顾", "盘点", "一文看懂", "周报", "月报", "汇总", "昨日", "上周", "此前", "前延", "前延回看", "转载", "媒体转载")

NEW_SIGNAL_MARKERS = (
    "官方发布",
    "正式上线",
    "开始收费",
    "价格调整",
    "降价",
    "涨价",
    "调用量",
    "token",
    "mau",
    "dau",
    "arr",
    "收入",
    "付费用户",
    "企业客户",
    "融资",
    "ipo",
    "sec",
    "财报",
    "业绩会",
    "榜单",
    "排名",
    "api",
    "open beta",
    "ga",
    "generally available",
    "launched",
    "released",
    "pricing",
    "revenue",
    "customers",
    "users",
)

STRONG_NEW_SIGNAL_MARKERS = (
    "今日",
    "最新",
    "当日",
    "刚刚",
    "正式上线",
    "正式发布",
    "正式商用",
    "官方披露",
    "官方宣布",
    "首次披露",
    "新增",
    "新价格",
    "新调用量",
    "开始收费",
    "新融资",
    "新一轮融资",
    "付费用户",
    "企业客户",
    "open beta",
    "ga",
    "generally available",
)

KNOWN_ENTITIES = (
    "OpenAI",
    "Anthropic",
    "NVIDIA",
    "Microsoft",
    "Meta",
    "Amazon",
    "Alphabet",
    "Google",
    "Google Cloud",
    "GCP",
    "ChatGPT",
    "Lovable",
    "CrowdStrike",
    "TSMC",
    "DeepSeek",
    "Qwen",
    "Kimi",
    "Coze",
    "Codex",
    "Copilot",
    "WhatsApp",
    "阿里",
    "阿里云",
    "千问",
    "腾讯",
    "腾讯云",
    "字节",
    "火山引擎",
    "豆包",
    "扣子",
    "月之暗面",
    "MiniMax",
    "智谱",
    "支付宝",
    "飞书",
    "企业微信",
)

SEMANTIC_FACET_MARKERS = {
    "paid_subscription": ("付费版", "付费订阅", "专业版", "开始收费", "subscription"),
    "mau_drop": ("mau", "月活", "首降", "首次下滑", "环比下降", "用户流失"),
    "price_cut": ("降价", "下调", "大幅下调", "价格调整", "最高降", "价格战", "price cut"),
    "api_pricing": ("api价格", "api 价格", "调用价", "模型调用价", "定价", "价格战", "pricing"),
    "api_usage": ("调用量", "token", "tokens", "消耗量", "使用量"),
    "api_billing_incident": ("退款", "计费", "账单", "赠金", "故障", "billing", "refund", "credit"),
    "agent_platform": ("agent", "智能体", "扣子", "coze", "skill"),
    "third_party_open": ("第三方", "开放", "入驻", "生态"),
    "agent_collaboration": ("多人", "多agent", "协作", "workflow", "工作流"),
    "local_agent": ("本地agent", "本地 agent", "ai pc", "desktop", "pc"),
    "model_release": ("模型", "发布", "上线", "qwen", "deepseek", "claude", "gpt", "kimi"),
    "ai_payment": ("ai支付", "ai 支付", "支付", "下单", "交易闭环", "钱包"),
    "maas_revenue": ("maas", "营收", "收入", "seedance", "视频模型", "视频生成"),
    "funding_ipo": ("融资", "ipo", "sec", "估值", "上市"),
    "enterprise_adoption": ("企业客户", "客户", "部署", "商用", "adoption"),
    "data_center_capex": ("数据中心", "capex", "算力", "电力", "gw"),
    "ai_funding": ("融资", "raise", "funding", "850亿", "85b"),
    "memory_system": ("dreaming", "记忆系统", "memory"),
    "cloud_contract": ("google cloud", "gcp", "合同", "签约", "多年", "5倍", "usage"),
    "warehouse_robot": ("proteus", "仓库机器人", "warehouse robot"),
    "earnings_arr": ("q1", "arr", "业绩", "营收", "收入", "revenue", "crowdstrike"),
    "personal_ai_agent": ("hatch", "个人ai代理", "personal ai agent", "business agent"),
}

SPECIFIC_SEMANTIC_FACETS = {
    "paid_subscription",
    "mau_drop",
    "price_cut",
    "api_pricing",
    "api_usage",
    "api_billing_incident",
    "third_party_open",
    "agent_collaboration",
    "ai_payment",
    "maas_revenue",
    "funding_ipo",
    "enterprise_adoption",
    "data_center_capex",
    "ai_funding",
    "memory_system",
    "cloud_contract",
    "warehouse_robot",
    "earnings_arr",
    "personal_ai_agent",
}

SINGLE_STRONG_SEMANTIC_FACETS = {
    "ai_payment",
    "maas_revenue",
    "funding_ipo",
    "ai_funding",
    "memory_system",
    "cloud_contract",
    "warehouse_robot",
    "earnings_arr",
    "personal_ai_agent",
}

ENTITY_ALIASES = {
    "gcp": "Google",
    "google cloud": "Google",
    "谷歌云": "Google",
    "alphabet": "Alphabet",
    "chatgpt": "ChatGPT",
    "lovable": "Lovable",
    "crowdstrike": "CrowdStrike",
    "tsmc": "TSMC",
    "台积电": "TSMC",
    "亚马逊": "Amazon",
    "英伟达": "NVIDIA",
    "微软": "Microsoft",
    "蚂蚁": "支付宝",
}

TITLE_ALIASES = (
    ("google cloud", "gcp"),
    ("谷歌云", "gcp"),
    ("ai agent", "agent"),
    ("ai代理", "agent"),
    ("ai支付", "支付"),
    ("ai 支付", "支付"),
    ("dreaming", "dreaming"),
    ("q1", "q1"),
    ("850亿美元", "850亿"),
    ("85b", "850亿"),
    ("使用量扩大5倍", "5倍"),
    ("使用量提升5倍", "5倍"),
    ("签署多年合同", "签约"),
    ("多年合同", "签约"),
    ("完成融资", "融资"),
    ("融资创纪录", "融资"),
    ("arr创历史新高", "arr"),
    ("业绩超预期", "业绩"),
)


@dataclass
class HistoryEvent:
    date: str
    event_id: str
    region: str
    title: str
    normalized_title: str
    entities: list[str] = field(default_factory=list)
    priority: str = ""
    source_urls: list[str] = field(default_factory=list)
    source_labels: list[str] = field(default_factory=list)
    summary: str = ""
    doc_url: str = ""
    created_at: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HistoryEvent":
        title = str(data.get("title") or "").strip()
        region = str(data.get("region") or "unknown").strip() or "unknown"
        entities = _string_list(data.get("entities")) or extract_entities(title)
        return cls(
            date=str(data.get("date") or data.get("last_seen_date") or data.get("first_seen_date") or ""),
            event_id=str(data.get("event_id") or make_event_id(region, title, entities)),
            region=region,
            title=title,
            normalized_title=str(data.get("normalized_title") or normalize_event_title(title)),
            entities=entities,
            priority=str(data.get("priority") or ""),
            source_urls=_string_list(data.get("source_urls")),
            source_labels=_string_list(data.get("source_labels")),
            summary=str(data.get("summary") or "")[:240],
            doc_url=str(data.get("doc_url") or ""),
            created_at=str(data.get("created_at") or ""),
        )

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass
class HistoryMatchResult:
    matched: bool = False
    matched_event_id: str = ""
    matched_title: str = ""
    matched_date: str = ""
    similarity: float = 0.0
    match_reason: str = ""
    is_old_repeated: bool = False
    new_signal_detected: bool = False
    repeat_allowed: bool = False
    action: str = ""
    candidate_title: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass
class EventHistoryMatchAudit:
    date: str
    lookback_days: int
    filter_mode: str = "mark"
    history_events_loaded: int = 0
    matched_candidates_count: int = 0
    old_repeated_count: int = 0
    new_signal_repeat_count: int = 0
    dropped_from_core_count: int = 0
    observe_only_count: int = 0
    pre_llm_dropped_count: int = 0
    matches: list[HistoryMatchResult] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "date": self.date,
            "lookback_days": self.lookback_days,
            "filter_mode": self.filter_mode,
            "history_events_loaded": self.history_events_loaded,
            "matched_candidates_count": self.matched_candidates_count,
            "old_repeated_count": self.old_repeated_count,
            "new_signal_repeat_count": self.new_signal_repeat_count,
            "matches": [
                {
                    "candidate_title": item.candidate_title,
                    "matched_title": item.matched_title,
                    "matched_date": item.matched_date,
                    "similarity": round(item.similarity, 3),
                    "is_old_repeated": item.is_old_repeated,
                    "new_signal_detected": item.new_signal_detected,
                    "action": item.action,
                    "matched_event_id": item.matched_event_id,
                    "match_reason": item.match_reason,
                }
                for item in self.matches
            ],
            "dropped_from_core_count": self.dropped_from_core_count,
            "observe_only_count": self.observe_only_count,
            "pre_llm_dropped_count": self.pre_llm_dropped_count,
            "warnings": self.warnings,
        }

    def to_summary_dict(self) -> dict[str, object]:
        return {
            "event_history_events_loaded": self.history_events_loaded,
            "event_history_filter_mode": self.filter_mode,
            "event_history_matches_count": self.matched_candidates_count,
            "event_history_old_repeated_count": self.old_repeated_count,
            "event_history_new_signal_count": self.new_signal_repeat_count,
            "event_history_dropped_from_core_count": self.dropped_from_core_count,
            "event_history_observe_only_count": self.observe_only_count,
            "event_history_pre_llm_dropped_count": self.pre_llm_dropped_count,
        }


@dataclass
class FinalTopDedupeAudit:
    date: str
    lookback_days: int
    history_events_loaded: int = 0
    matches_count: int = 0
    dropped_count: int = 0
    new_signal_count: int = 0
    p2_capped_count: int = 0
    llm_audit_attempted: bool = False
    llm_audit_succeeded: bool = False
    llm_audit_failed: bool = False
    llm_audit_decisions_count: int = 0
    llm_audit_dropped_count: int = 0
    llm_audit_rejected_count: int = 0
    llm_audit_error: str = ""
    cleared_core_judgments_count: int = 0
    cleared_watch_signals_count: int = 0
    p2_capped_titles: list[str] = field(default_factory=list)
    llm_audit_dropped_titles: list[str] = field(default_factory=list)
    dropped_titles: list[str] = field(default_factory=list)
    matches: list[HistoryMatchResult] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "date": self.date,
            "lookback_days": self.lookback_days,
            "history_events_loaded": self.history_events_loaded,
            "matches_count": self.matches_count,
            "dropped_count": self.dropped_count,
            "new_signal_count": self.new_signal_count,
            "p2_capped_count": self.p2_capped_count,
            "llm_audit_attempted": self.llm_audit_attempted,
            "llm_audit_succeeded": self.llm_audit_succeeded,
            "llm_audit_failed": self.llm_audit_failed,
            "llm_audit_decisions_count": self.llm_audit_decisions_count,
            "llm_audit_dropped_count": self.llm_audit_dropped_count,
            "llm_audit_rejected_count": self.llm_audit_rejected_count,
            "llm_audit_error": self.llm_audit_error,
            "llm_audit_dropped_titles": self.llm_audit_dropped_titles,
            "p2_capped_titles": self.p2_capped_titles,
            "cleared_core_judgments_count": self.cleared_core_judgments_count,
            "cleared_watch_signals_count": self.cleared_watch_signals_count,
            "dropped_titles": self.dropped_titles,
            "matches": [
                {
                    "candidate_title": item.candidate_title,
                    "matched_title": item.matched_title,
                    "matched_date": item.matched_date,
                    "similarity": round(item.similarity, 3),
                    "new_signal_detected": item.new_signal_detected,
                    "action": item.action,
                    "matched_event_id": item.matched_event_id,
                    "match_reason": item.match_reason,
                }
                for item in self.matches
            ],
            "warnings": self.warnings,
        }

    def to_summary_dict(self) -> dict[str, object]:
        return {
            "final_top_dedupe_matches_count": self.matches_count,
            "final_top_dedupe_dropped_count": self.dropped_count,
            "final_top_dedupe_new_signal_count": self.new_signal_count,
            "final_top_p2_capped_count": self.p2_capped_count,
            "final_top_p2_capped_titles_sample": ", ".join(self.p2_capped_titles[:5]),
            "final_top_llm_audit_attempted": self.llm_audit_attempted,
            "final_top_llm_audit_succeeded": self.llm_audit_succeeded,
            "final_top_llm_audit_failed": self.llm_audit_failed,
            "final_top_llm_audit_decisions_count": self.llm_audit_decisions_count,
            "final_top_llm_audit_dropped_count": self.llm_audit_dropped_count,
            "final_top_llm_audit_rejected_count": self.llm_audit_rejected_count,
            "final_top_llm_audit_error": self.llm_audit_error,
            "final_top_llm_audit_dropped_titles_sample": ", ".join(self.llm_audit_dropped_titles[:5]),
            "final_top_dedupe_cleared_core_judgments_count": self.cleared_core_judgments_count,
            "final_top_dedupe_cleared_watch_signals_count": self.cleared_watch_signals_count,
            "final_top_dedupe_dropped_titles_sample": ", ".join(self.dropped_titles[:5]),
        }


def load_recent_event_history(path: Path, target_date: date, lookback_days: int) -> list[HistoryEvent]:
    if not path.exists():
        return []
    start = target_date - timedelta(days=lookback_days)
    events: list[HistoryEvent] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception as exc:  # noqa: BLE001
        logger.warning("event history read failed: %s", str(exc)[:200])
        return []
    for line in lines:
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        event = HistoryEvent.from_dict(data)
        try:
            event_date = date.fromisoformat(event.date)
        except ValueError:
            continue
        if start <= event_date < target_date:
            events.append(event)
    return dedupe_history_events(events)


def append_event_history(path: Path, target_date: date | str, brief_json: dict[str, object], doc_url: str = "") -> None:
    date_str = target_date.isoformat() if isinstance(target_date, date) else str(target_date)
    existing_keys = _existing_history_keys(path)
    rows: list[HistoryEvent] = []
    for region, key in (("domestic", "domestic_top"), ("overseas", "overseas_top")):
        items = brief_json.get(key)
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            card_title = str(item.get("card_title") or "").strip()
            if title and _is_empty_event_title(title):
                continue
            if card_title and _is_empty_event_title(card_title):
                continue
            if not title and not card_title:
                continue
            title = title or card_title
            entities = extract_entities(title)
            event_id = make_event_id(region, title, entities)
            dedupe_key = f"{date_str}:{event_id}"
            if dedupe_key in existing_keys:
                continue
            source_urls, source_labels = _sources_from_item(item)
            rows.append(
                HistoryEvent(
                    date=date_str,
                    event_id=event_id,
                    region=region,
                    title=title,
                    normalized_title=normalize_event_title(title),
                    entities=entities,
                    priority=str(item.get("priority") or ""),
                    source_urls=source_urls[:5],
                    source_labels=source_labels[:5],
                    summary=str(item.get("card_why") or item.get("why") or "")[:240],
                    doc_url=doc_url or str(brief_json.get("doc_url") or ""),
                    created_at=datetime.now(timezone.utc).isoformat(),
                )
            )
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row.to_dict(), ensure_ascii=False) + "\n")


def normalize_event_title(title: str) -> str:
    text = _canonical_text(str(title or "").lower())
    for word in COMMON_TITLE_WORDS:
        text = text.replace(word.lower(), " ")
    text = re.sub(r"[^\w\u4e00-\u9fff]+", " ", text, flags=re.UNICODE)
    return " ".join(text.split())


def make_event_id(region: str, title: str, entities: list[str] | None = None) -> str:
    entity_slug = "_".join(_slug(entity) for entity in (entities or [])[:2] if entity) or "unknown"
    title_slug = _slug(normalize_event_title(title))[:72] or "untitled"
    return f"{_slug(region or 'unknown')}_{entity_slug}_{title_slug}"


def dedupe_history_events(events: list[HistoryEvent]) -> list[HistoryEvent]:
    seen: set[str] = set()
    output: list[HistoryEvent] = []
    for event in sorted(events, key=lambda item: (item.date, item.event_id)):
        key = f"{event.date}:{event.event_id}"
        if key in seen:
            continue
        seen.add(key)
        output.append(event)
    return output


def select_history_context_events(
    history_events: list[HistoryEvent],
    audit: EventHistoryMatchAudit,
    *,
    max_events: int = 30,
) -> list[HistoryEvent]:
    by_id = {event.event_id: event for event in history_events}
    selected: list[HistoryEvent] = []
    seen: set[str] = set()

    for match in audit.matches:
        event = by_id.get(match.matched_event_id) or _find_history_event(history_events, match)
        if event and event.event_id not in seen:
            selected.append(event)
            seen.add(event.event_id)
        if len(selected) >= max_events:
            return selected

    remaining = [event for event in history_events if event.event_id not in seen]
    remaining.sort(key=_history_context_sort_key)
    for event in remaining:
        selected.append(event)
        if len(selected) >= max_events:
            break
    return selected


def match_recent_history(
    candidate_event: EvidenceItem | dict[str, object],
    history_events: list[HistoryEvent],
    *,
    strict_new_signal: bool = False,
) -> HistoryMatchResult:
    title = _candidate_text(candidate_event, "title")
    content = _candidate_text(candidate_event, "content")
    candidate_entities = extract_entities(f"{title} {content}")
    candidate_title_entities = extract_entities(title)
    candidate_domains = _candidate_domains(candidate_event)
    best: tuple[float, HistoryEvent, str] | None = None
    for event in history_events:
        similarity, reason = _history_similarity(
            title,
            content,
            candidate_entities,
            candidate_title_entities,
            candidate_domains,
            event,
        )
        if best is None or similarity > best[0]:
            best = (similarity, event, reason)
    if best is None or best[0] < 0.55:
        return HistoryMatchResult(matched=False, candidate_title=title)
    similarity, event, reason = best
    signal_text = f"{title} {content} {_candidate_text(candidate_event, 'source')} {_candidate_text(candidate_event, 'url')}"
    new_signal = detect_final_top_new_signal(signal_text) if strict_new_signal else detect_new_signal(signal_text)
    old_repeated = not new_signal
    return HistoryMatchResult(
        matched=True,
        matched_event_id=event.event_id,
        matched_title=event.title,
        matched_date=event.date,
        similarity=similarity,
        match_reason=reason,
        is_old_repeated=old_repeated,
        new_signal_detected=new_signal,
        repeat_allowed=new_signal,
        action="allow_new_signal" if new_signal else "drop_core",
        candidate_title=title,
    )


def dedupe_final_top_events(
    brief: dict[str, object],
    history_events: list[HistoryEvent],
    *,
    target_date: str,
    lookback_days: int,
) -> tuple[dict[str, object], FinalTopDedupeAudit]:
    audit = FinalTopDedupeAudit(
        date=target_date,
        lookback_days=lookback_days,
        history_events_loaded=len(history_events),
    )
    output = deepcopy(brief)
    if not history_events:
        _cap_final_p2_items(output, audit)
        _update_brief_top_counts(output)
        return output, audit

    for region, key in (("domestic", "domestic_top"), ("overseas", "overseas_top")):
        items = output.get(key)
        if not isinstance(items, list):
            continue
        kept: list[object] = []
        for item in items:
            if not isinstance(item, dict):
                kept.append(item)
                continue
            if _is_empty_event_title(str(item.get("title") or item.get("card_title") or "")):
                kept.append(item)
                continue
            candidate = _brief_item_candidate(item, region)
            match = match_recent_history(candidate, history_events, strict_new_signal=True)
            if not match.matched:
                kept.append(item)
                continue
            audit.matches.append(match)
            audit.matches_count += 1
            if match.new_signal_detected:
                audit.new_signal_count += 1
                kept.append(item)
                continue
            audit.dropped_count += 1
            title = str(item.get("title") or item.get("card_title") or "").strip()
            if title:
                audit.dropped_titles.append(title)
        output[key] = kept
    _cap_final_p2_items(output, audit)
    _update_brief_top_counts(output)
    _filter_top_dependent_bullets(output, audit)
    return output, audit


def apply_final_top_llm_decisions(
    brief: dict[str, object],
    decisions: list[dict[str, object]],
    audit: FinalTopDedupeAudit,
) -> tuple[dict[str, object], FinalTopDedupeAudit]:
    output = deepcopy(brief)
    indexed = _indexed_top_items(output)
    if not indexed:
        return output, audit

    ids_to_drop: set[str] = set()
    for decision in decisions:
        audit.llm_audit_decisions_count += 1
        item_id = str(decision.get("id") or "").strip()
        action = str(decision.get("action") or "").strip().lower()
        confidence = str(decision.get("confidence") or "").strip().lower()
        duplicate_of = str(decision.get("duplicate_of") or "").strip()
        new_signal = _truthy(decision.get("new_signal"))
        if (
            item_id in indexed
            and action == "drop"
            and confidence == "high"
            and duplicate_of
            and not new_signal
        ):
            ids_to_drop.add(item_id)
        else:
            audit.llm_audit_rejected_count += 1

    if not ids_to_drop:
        _update_brief_top_counts(output)
        return output, audit
    if len(ids_to_drop) >= len(indexed):
        audit.llm_audit_rejected_count += len(ids_to_drop)
        audit.warnings.append("llm_audit_drop_all_rejected")
        _update_brief_top_counts(output)
        return output, audit

    for key in ("domestic_top", "overseas_top"):
        items = output.get(key)
        if not isinstance(items, list):
            continue
        kept: list[object] = []
        for index, item in enumerate(items, 1):
            item_id = f"{key.removesuffix('_top')}_{index}"
            if item_id in ids_to_drop and isinstance(item, dict):
                title = str(item.get("title") or item.get("card_title") or "").strip()
                if title:
                    audit.dropped_titles.append(title)
                    audit.llm_audit_dropped_titles.append(title)
                audit.dropped_count += 1
                audit.llm_audit_dropped_count += 1
                continue
            kept.append(item)
        output[key] = kept

    _update_brief_top_counts(output)
    _filter_top_dependent_bullets(output, audit)
    return output, audit


def mark_history_matches(
    evidence: list[EvidenceItem],
    history_events: list[HistoryEvent],
    *,
    target_date: str,
    lookback_days: int,
) -> EventHistoryMatchAudit:
    audit = EventHistoryMatchAudit(
        date=target_date,
        lookback_days=lookback_days,
        history_events_loaded=len(history_events),
    )
    if not history_events:
        return audit
    for item in evidence:
        match = match_recent_history(item, history_events)
        if not match.matched:
            continue
        audit.matches.append(match)
        if match.new_signal_detected:
            audit.new_signal_repeat_count += 1
            item.date_status = "new_signal"
            source_core_eligible = not item.source_tier or item.source_tier in CORE_SOURCE_TIERS
            item.date_reason = f"matched recent Top event {match.matched_date}; allowed by new signal"
            item.not_core_eligible = not source_core_eligible
            if not source_core_eligible:
                item.date_reason = (
                    f"matched recent Top event {match.matched_date}; new signal kept as evidence but source tier not core eligible"
                )
        else:
            audit.old_repeated_count += 1
            audit.dropped_from_core_count += 1
            audit.observe_only_count += 1
            item.date_status = "old_repeated"
            item.date_reason = f"matched recent Top event {match.matched_date}; no new signal"
            item.not_core_eligible = True
    audit.matched_candidates_count = len(audit.matches)
    return audit


def render_event_history_context(history_events: list[HistoryEvent], audit: EventHistoryMatchAudit) -> str:
    lines = [
        "# Event History Context",
        "",
        f"- date: {audit.date}",
        f"- lookback_days: {audit.lookback_days}",
        f"- history_events_loaded: {audit.history_events_loaded}",
        f"- matched_candidates_count: {audit.matched_candidates_count}",
        f"- old_repeated_count: {audit.old_repeated_count}",
        f"- new_signal_repeat_count: {audit.new_signal_repeat_count}",
        "",
        "## Recent Top Events",
        "",
        "| date | region | priority | title | summary |",
        "|---|---|---|---|---|",
    ]
    for event in select_history_context_events(history_events, audit, max_events=30):
        lines.append(
            f"| {_cell(event.date)} | {_cell(event.region)} | {_cell(event.priority)} | "
            f"{_cell(event.title)} | {_cell(event.summary)} |"
        )
    lines.extend(
        [
            "",
            "## Matched Current Evidence",
            "",
            "| candidate | matched_date | matched_title | similarity | action |",
            "|---|---|---|---:|---|",
        ]
    )
    for match in audit.matches:
        lines.append(
            f"| {_cell(match.candidate_title)} | {_cell(match.matched_date)} | {_cell(match.matched_title)} | "
            f"{match.similarity:.2f} | {_cell(match.action)} |"
        )
    lines.append("")
    return "\n".join(lines)


def build_history_prompt_context(history_events: list[HistoryEvent], audit: EventHistoryMatchAudit, *, max_events: int = 30) -> str:
    if not history_events:
        return ""
    lines = [
        f"## 最近{audit.lookback_days}日已入选Top事件（历史去重参考，不是新证据）",
        "",
        "下面只列结构化历史摘要，请不要重复写已报道事件；只有今天出现官方披露、新数据、新价格、新上线、新采用度信号时，才可重新纳入核心事件，并在判断中说明新增信号。",
        "",
    ]
    for event in select_history_context_events(history_events, audit, max_events=max_events):
        summary = f"｜{event.summary}" if event.summary else ""
        lines.append(f"- {event.date}｜{event.region}｜{event.priority}｜{event.title}{summary}")
    if audit.matches:
        lines.extend(["", "### 今日证据命中历史事件", ""])
        for match in audit.matches[:20]:
            lines.append(
                f"- {match.candidate_title} -> {match.matched_date} {match.matched_title}；"
                f"action={match.action}；new_signal={str(match.new_signal_detected).lower()}"
            )
    return "\n".join(lines)


def detect_new_signal(text: str) -> bool:
    raw = str(text or "")
    lowered = raw.lower()
    if any(marker.lower() in lowered for marker in OLD_REPEAT_MARKERS) and not any(
        marker.lower() in lowered for marker in STRONG_NEW_SIGNAL_MARKERS
    ):
        return False
    return any(marker.lower() in lowered for marker in NEW_SIGNAL_MARKERS)


def detect_final_top_new_signal(text: str) -> bool:
    raw = str(text or "")
    lowered = raw.lower()
    if any(marker.lower() in lowered for marker in OLD_REPEAT_MARKERS) and not any(
        marker.lower() in lowered for marker in STRONG_NEW_SIGNAL_MARKERS
    ):
        return False
    strong_hits = [marker for marker in STRONG_NEW_SIGNAL_MARKERS if marker.lower() in lowered]
    if any(marker in strong_hits for marker in ("今日", "最新", "当日", "刚刚", "官方披露", "官方宣布", "首次披露", "新一轮融资")):
        return True
    data_signal_pattern = (
        r"(新增|最新|当日|今日|正式|官方).{0,20}"
        r"(\d+(?:\.\d+)?\s*(?:%|亿|万|token|tokens|mau|dau|arr|用户|客户|收入|调用量|价格|美元|人民币|元))"
    )
    if re.search(data_signal_pattern, lowered, flags=re.I):
        return True
    if len(strong_hits) >= 2:
        return True
    return False


def extract_entities(text: str) -> list[str]:
    lowered = str(text or "").lower()
    found: list[str] = []
    for marker, canonical in ENTITY_ALIASES.items():
        if marker in lowered and canonical not in found:
            found.append(canonical)
    for entity in KNOWN_ENTITIES:
        canonical = ENTITY_ALIASES.get(entity.lower(), entity)
        if entity.lower() in lowered and canonical not in found:
            found.append(canonical)
    return found


def _history_similarity(
    title: str,
    candidate_content: str,
    candidate_entities: list[str],
    candidate_title_entities: list[str],
    candidate_domains: set[str],
    event: HistoryEvent,
) -> tuple[float, str]:
    title_score = _jaccard(_tokens(title), _tokens(event.title))
    normalized_score = _jaccard(set(normalize_event_title(title).split()), set(event.normalized_title.split()))
    entity_score = _jaccard(set(entity.lower() for entity in candidate_entities), set(entity.lower() for entity in event.entities))
    title_entity_score = _jaccard(
        set(entity.lower() for entity in candidate_title_entities),
        set(entity.lower() for entity in event.entities),
    )
    history_domains = {_domain(url) for url in event.source_urls if url}
    domain_score = 1.0 if candidate_domains and candidate_domains.intersection(history_domains) else 0.0
    score = max(title_score, normalized_score) * 0.75 + entity_score * 0.2 + domain_score * 0.05
    semantic_score, semantic_reason = _semantic_similarity(
        title,
        candidate_content,
        candidate_entities,
        event,
        max(title_score, normalized_score),
        entity_score,
        title_entity_score,
        domain_score,
    )
    if semantic_score > score:
        score = semantic_score
        reason = semantic_reason
    elif entity_score > 0 and _has_paid_mau_signal(f"{title} {candidate_content}") and _has_paid_mau_signal(f"{event.title} {event.summary}"):
        score = max(score, 0.75)
        reason = "entity_and_paid_mau_signal"
    elif max(title_score, normalized_score) >= 0.75:
        reason = "title_overlap_high"
    elif entity_score > 0 and max(title_score, normalized_score) >= 0.45:
        reason = "entity_and_title_overlap"
    elif domain_score > 0 and max(title_score, normalized_score) >= 0.45:
        reason = "domain_and_title_overlap"
    else:
        reason = "weak_overlap"
    return min(score, 1.0), reason


def _semantic_similarity(
    title: str,
    candidate_content: str,
    candidate_entities: list[str],
    event: HistoryEvent,
    title_overlap: float,
    entity_score: float,
    title_entity_score: float,
    domain_score: float,
) -> tuple[float, str]:
    candidate_text = f"{title} {candidate_content}"
    history_text = f"{event.title} {event.summary}"
    candidate_title_facets = _semantic_facets(title)
    candidate_facets = _semantic_facets(candidate_text)
    history_facets = _semantic_facets(history_text)
    shared_facets = candidate_facets & history_facets
    shared_title_facets = candidate_title_facets & history_facets
    shared_specific = shared_facets & SPECIFIC_SEMANTIC_FACETS
    numeric_overlap = _numeric_overlap(candidate_text, history_text)

    if title_entity_score > 0 and _has_paid_mau_signal(candidate_text) and _has_paid_mau_signal(history_text):
        return 0.8, "entity_and_paid_mau_signal"
    if title_entity_score > 0 and shared_specific and numeric_overlap:
        return min(0.8 + len(shared_specific) * 0.02, 0.9), "entity_numeric_semantic_overlap"
    if title_entity_score > 0 and {"price_cut", "api_pricing"}.issubset(shared_facets) and (
        "price_cut" in candidate_title_facets or "api_pricing" in candidate_title_facets
    ):
        return 0.78, "entity_and_api_price_signal"
    if title_entity_score > 0 and len(shared_facets) >= 2 and shared_specific and shared_title_facets:
        return min(0.76 + len(shared_specific) * 0.02, 0.88), "entity_and_semantic_facets"
    if title_entity_score > 0 and shared_title_facets & SINGLE_STRONG_SEMANTIC_FACETS:
        return 0.72, "entity_and_semantic_facets"
    if title_entity_score > 0 and shared_specific and title_overlap >= 0.32:
        return 0.62, "entity_and_semantic_overlap"
    if shared_specific and numeric_overlap and title_overlap >= 0.42:
        return min(0.72 + len(shared_specific) * 0.02, 0.84), "numeric_semantic_overlap"
    if domain_score > 0 and len(shared_specific) >= 2 and title_overlap >= 0.35:
        return 0.58, "domain_and_semantic_facets"
    return 0.0, "weak_semantic_overlap"


def _semantic_facets(text: str) -> set[str]:
    lowered = _canonical_text(str(text or "").lower())
    facets: set[str] = set()
    for facet, markers in SEMANTIC_FACET_MARKERS.items():
        if any(marker.lower() in lowered for marker in markers):
            facets.add(facet)
    return facets


def _canonical_text(text: str) -> str:
    value = str(text or "").lower()
    for old, new in TITLE_ALIASES:
        value = value.replace(old, new)
    return value


def _numeric_tokens(text: str) -> set[str]:
    value = _canonical_text(str(text or "").lower())
    return set(re.findall(r"(?:q[1-4])|(?:\d+(?:\.\d+)?\s*(?:亿|万|%|美元|元|倍|b|m|arr|mau|dau))", value, flags=re.I))


def _numeric_overlap(left: str, right: str) -> bool:
    return bool(_numeric_tokens(left) & _numeric_tokens(right))


def _has_paid_mau_signal(text: str) -> bool:
    value = str(text or "").lower()
    has_paid = any(marker in value for marker in ("付费版", "付费订阅", "专业版", "开始收费"))
    has_mau_drop = (
        "mau" in value
        or "月活" in value
        or "首降" in value
        or "首次下滑" in value
        or ("首次" in value and "下滑" in value)
    )
    return has_paid and has_mau_drop


def _find_history_event(history_events: list[HistoryEvent], match: HistoryMatchResult) -> HistoryEvent | None:
    for event in history_events:
        if event.date == match.matched_date and event.title == match.matched_title:
            return event
    for event in history_events:
        if event.title == match.matched_title:
            return event
    return None


def _history_context_sort_key(event: HistoryEvent) -> tuple[int, int, str]:
    try:
        date_rank = -date.fromisoformat(event.date).toordinal()
    except ValueError:
        date_rank = -date.min.toordinal()
    return (date_rank, _priority_rank(event.priority), event.event_id)


def _priority_rank(priority: str) -> int:
    text = str(priority or "").upper()
    if "P1" in text:
        return 0
    if "P2" in text:
        return 1
    if "观察" in text or "OBSERVE" in text:
        return 2
    return 3


def _tokens(value: str) -> set[str]:
    normalized = normalize_event_title(value)
    tokens: set[str] = set()
    for part in re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]", normalized, flags=re.I):
        part = part.lower()
        if part and part not in COMMON_TITLE_WORDS:
            tokens.add(part)
    return tokens


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _candidate_text(candidate: EvidenceItem | dict[str, object], key: str) -> str:
    if isinstance(candidate, EvidenceItem):
        return str(getattr(candidate, key, "") or "")
    return str(candidate.get(key) or "")


def _candidate_domains(candidate: EvidenceItem | dict[str, object]) -> set[str]:
    urls = [_candidate_text(candidate, "url")]
    sources = candidate.get("sources") if isinstance(candidate, dict) else None
    if isinstance(sources, list):
        for source in sources:
            if isinstance(source, dict):
                urls.append(str(source.get("url") or ""))
    return {_domain(url) for url in urls if _domain(url)}


def _brief_item_candidate(item: dict[str, object], region: str) -> dict[str, object]:
    title = str(item.get("title") or item.get("card_title") or "")
    content_parts = [
        str(item.get("card_title") or ""),
        str(item.get("why") or ""),
        str(item.get("card_why") or ""),
        str(item.get("priority") or ""),
        region,
    ]
    return {
        "title": title,
        "content": " ".join(part for part in content_parts if part),
        "sources": item.get("sources") if isinstance(item.get("sources"), list) else [],
    }


def _update_brief_top_counts(brief: dict[str, object]) -> None:
    domestic_count = len(brief.get("domestic_top") or []) if isinstance(brief.get("domestic_top"), list) else 0
    overseas_count = len(brief.get("overseas_top") or []) if isinstance(brief.get("overseas_top"), list) else 0
    total_count = domestic_count + overseas_count
    for key, value in (
        ("brief_domestic_items_count", domestic_count),
        ("brief_overseas_items_count", overseas_count),
        ("brief_final_domestic_items_count", domestic_count),
        ("brief_final_overseas_items_count", overseas_count),
        ("brief_actual_domestic_items_count", domestic_count),
        ("brief_actual_overseas_items_count", overseas_count),
        ("brief_items_count", total_count),
    ):
        brief[key] = value


def _cap_final_p2_items(brief: dict[str, object], audit: FinalTopDedupeAudit) -> None:
    for key in ("domestic_top", "overseas_top"):
        items = brief.get(key)
        if not isinstance(items, list):
            continue
        kept: list[object] = []
        p2_count = 0
        for item in items:
            if not isinstance(item, dict) or _priority_rank(str(item.get("priority") or "")) != 1:
                kept.append(item)
                continue
            if p2_count < MAX_P2_TOP_EVENTS_PER_REGION:
                p2_count += 1
                kept.append(item)
                continue
            audit.p2_capped_count += 1
            title = str(item.get("title") or item.get("card_title") or "").strip()
            if title:
                audit.p2_capped_titles.append(title)
        brief[key] = kept


def _indexed_top_items(brief: dict[str, object]) -> dict[str, dict[str, object]]:
    indexed: dict[str, dict[str, object]] = {}
    for key in ("domestic_top", "overseas_top"):
        items = brief.get(key)
        if not isinstance(items, list):
            continue
        region = key.removesuffix("_top")
        for index, item in enumerate(items, 1):
            if isinstance(item, dict):
                indexed[f"{region}_{index}"] = item
    return indexed


def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value or "").strip().lower() in {"true", "1", "yes", "y"}


def _filter_top_dependent_bullets(brief: dict[str, object], audit: FinalTopDedupeAudit) -> None:
    if audit.dropped_count <= 0:
        return
    remaining_top_texts = _remaining_top_texts(brief)

    core_judgments = brief.get("core_judgments")
    watch_signals = brief.get("watch_signals")

    if not remaining_top_texts:
        audit.cleared_core_judgments_count = len(core_judgments) if isinstance(core_judgments, list) else 0
        audit.cleared_watch_signals_count = len(watch_signals) if isinstance(watch_signals, list) else 0
        for key in ("core_judgments", "watch_signals", "core_judgments_card", "watch_signals_card"):
            if isinstance(brief.get(key), list):
                brief[key] = []
    else:
        removed_top_texts = _removed_top_texts(audit)
        audit.cleared_core_judgments_count = _filter_bullet_pair_by_removed_top(
            brief,
            "core_judgments",
            "core_judgments_card",
            removed_top_texts,
        )
        audit.cleared_core_judgments_count += _filter_bullet_pair_by_remaining_top(
            brief,
            "core_judgments",
            "core_judgments_card",
            remaining_top_texts,
        )
        audit.cleared_watch_signals_count = _filter_bullet_pair_by_removed_top(
            brief,
            "watch_signals",
            "watch_signals_card",
            removed_top_texts,
        )
        _ensure_core_judgments_from_remaining_top(brief)

    if audit.cleared_core_judgments_count or audit.cleared_watch_signals_count:
        audit.warnings.append("cleared_top_dependent_bullets_after_final_top_dedupe")

    brief["brief_core_judgments_count"] = len(brief.get("core_judgments") or []) if isinstance(brief.get("core_judgments"), list) else 0
    brief["brief_watch_signals_count"] = len(brief.get("watch_signals") or []) if isinstance(brief.get("watch_signals"), list) else 0
    if isinstance(brief.get("core_judgments_card"), list):
        brief["brief_core_judgments_card_count"] = len(brief.get("core_judgments_card") or [])
    if isinstance(brief.get("watch_signals_card"), list):
        brief["brief_watch_signals_card_count"] = len(brief.get("watch_signals_card") or [])


def _ensure_core_judgments_from_remaining_top(brief: dict[str, object]) -> None:
    core_judgments = brief.get("core_judgments")
    if isinstance(core_judgments, list) and core_judgments:
        return
    items = _remaining_top_items(brief)
    if not items:
        return
    full: list[str] = []
    cards: list[str] = []
    for item in items[:3]:
        title = str(item.get("title") or item.get("card_title") or "").strip()
        why = str(item.get("why") or item.get("card_why") or "").strip()
        card_why = str(item.get("card_why") or why).strip()
        if title and why:
            full.append(f"{title}：{why}")
            cards.append(f"{title}：{card_why}" if card_why else f"{title}进入最终 Top。")
        elif title:
            full.append(f"{title}进入最终 Top。")
            cards.append(f"{title}进入最终 Top。")
    if full:
        brief["core_judgments"] = full
        brief["core_judgments_card"] = cards


def _remaining_top_items(brief: dict[str, object]) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    for key in ("domestic_top", "overseas_top"):
        items = brief.get(key)
        if not isinstance(items, list):
            continue
        output.extend(item for item in items if isinstance(item, dict))
    return output


def _filter_bullet_pair_by_remaining_top(
    brief: dict[str, object],
    full_key: str,
    card_key: str,
    remaining_top_texts: list[str],
) -> int:
    full_items = brief.get(full_key)
    card_items = brief.get(card_key)
    if not isinstance(full_items, list) or not remaining_top_texts:
        return 0

    kept_full: list[object] = []
    kept_cards: list[object] = []
    removed = 0
    for index, item in enumerate(full_items):
        card_item = card_items[index] if isinstance(card_items, list) and index < len(card_items) else None
        text = f"{_bullet_text(item)} {_bullet_text(card_item)}".strip()
        if _bullet_matches_top_text(text, remaining_top_texts):
            kept_full.append(item)
            if isinstance(card_items, list) and index < len(card_items):
                kept_cards.append(card_item)
            continue
        removed += 1

    brief[full_key] = kept_full
    if isinstance(card_items, list):
        brief[card_key] = kept_cards
    return removed


def _remaining_top_texts(brief: dict[str, object]) -> list[str]:
    texts: list[str] = []
    for key in ("domestic_top", "overseas_top"):
        items = brief.get(key)
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, dict):
                text = " ".join(
                    str(item.get(field) or "")
                    for field in ("title", "card_title", "why", "card_why")
                    if item.get(field)
                ).strip()
                if text:
                    texts.append(text)
    return texts


def _removed_top_texts(audit: FinalTopDedupeAudit) -> list[str]:
    texts: list[str] = []
    for title in [*audit.dropped_titles, *audit.llm_audit_dropped_titles]:
        text = str(title or "").strip()
        if text and text not in texts:
            texts.append(text)
    return texts


def _filter_bullet_pair_by_removed_top(
    brief: dict[str, object],
    full_key: str,
    card_key: str,
    removed_top_texts: list[str],
) -> int:
    full_items = brief.get(full_key)
    card_items = brief.get(card_key)
    if not isinstance(full_items, list) or not removed_top_texts:
        return 0

    kept_full: list[object] = []
    kept_cards: list[object] = []
    removed = 0
    for index, item in enumerate(full_items):
        card_item = card_items[index] if isinstance(card_items, list) and index < len(card_items) else None
        text = f"{_bullet_text(item)} {_bullet_text(card_item)}".strip()
        if _bullet_matches_top_text(text, removed_top_texts):
            removed += 1
            continue
        kept_full.append(item)
        if isinstance(card_items, list) and index < len(card_items):
            kept_cards.append(card_item)

    brief[full_key] = kept_full
    if isinstance(card_items, list):
        brief[card_key] = kept_cards
    return removed


def _bullet_text(item: object) -> str:
    if isinstance(item, dict):
        return " ".join(str(item.get(key) or "") for key in ("card", "full", "title", "text") if item.get(key)).strip()
    return str(item or "").strip()


def _bullet_matches_top_text(text: str, top_texts: list[str]) -> bool:
    if not str(text or "").strip():
        return False
    bullet_tokens = _tokens(text)
    bullet_entities = {entity.lower() for entity in extract_entities(text)}
    bullet_facets = _semantic_facets(text)
    bullet_numbers = _numeric_tokens(text)
    for top_text in top_texts:
        top_tokens = _tokens(top_text)
        token_score = _jaccard(bullet_tokens, top_tokens)
        top_entities = {entity.lower() for entity in extract_entities(top_text)}
        entity_overlap = bool(bullet_entities & top_entities)
        facet_overlap = bool(bullet_facets & _semantic_facets(top_text))
        number_overlap = bool(bullet_numbers & _numeric_tokens(top_text))
        if token_score >= 0.32:
            return True
        if entity_overlap and token_score >= 0.2:
            return True
        if entity_overlap and facet_overlap and token_score >= 0.12:
            return True
        if entity_overlap and number_overlap:
            return True
    return False


def _domain(url: str) -> str:
    return urlsplit(str(url or "")).netloc.lower().removeprefix("www.")


def _sources_from_item(item: dict[str, object]) -> tuple[list[str], list[str]]:
    urls: list[str] = []
    labels: list[str] = []
    sources = item.get("sources")
    if isinstance(sources, list):
        for source in sources:
            if not isinstance(source, dict):
                continue
            url = str(source.get("url") or "").strip()
            label = str(source.get("label") or source.get("title") or source.get("source") or "").strip()
            if url:
                urls.append(url)
            if label:
                labels.append(label)
    return urls, labels


def _existing_history_keys(path: Path) -> set[str]:
    if not path.exists():
        return set()
    keys: set[str] = set()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:  # noqa: BLE001
        return set()
    for line in lines:
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        event = HistoryEvent.from_dict(data)
        if event.date and event.event_id:
            keys.add(f"{event.date}:{event.event_id}")
    return keys


def _is_empty_event_title(title: str) -> bool:
    text = str(title or "").strip()
    if not text:
        return True
    compact = re.sub(r"\s+", "", text)
    if re.fullmatch(r"[一二三四五六七八九十]+[、.．]?(核心解读|核心判断|观察信号|今日总览|逐条深度解读)", compact):
        return True
    return (
        "今日无强核心事件" in text
        or re.search(r"无(国内|海外)?强?核心事件", compact) is not None
        or re.search(r"(国内|海外)无强?核心事件", compact) is not None
        or re.search(r"无.{0,12}(国内|海外)?.{0,6}核心事件", compact) is not None
        or re.search(r"未发现.{0,20}(国内|海外)?.{0,8}核心事件", compact) is not None
        or re.search(r"无.{0,16}核心.{0,8}事件", compact) is not None
        or "不强行凑数" in text
        or "详见完整日报" in text
        or text in {"—", "-", "–", "--", "无", "无。", "N/A", "n/a", "NA", "na", "None", "none"}
    )


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _slug(value: str) -> str:
    return re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", "_", str(value or "").lower()).strip("_")


def _cell(value: str) -> str:
    return " ".join(str(value or "").replace("|", "\\|").split())[:300]
