from __future__ import annotations

import json
import logging
import re
from difflib import SequenceMatcher
from typing import Any
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit, urlunsplit

from openai import OpenAI

from .config import Settings
from .models import EvidenceItem, RecallAudit, TimeWindow

logger = logging.getLogger(__name__)

DAILY_MAX_CORE_EVENTS_PER_REGION = 6
MAX_TOP_EVENTS_PER_REGION = DAILY_MAX_CORE_EVENTS_PER_REGION
MAX_P2_TOP_EVENTS_PER_REGION = 2
CARD_TITLE_MAX_CHARS = 28
CARD_WHY_MAX_CHARS = 60
CARD_BULLET_MAX_CHARS = 56
BRIEF_WHY_MAX_CHARS = 500
BRIEF_BULLET_MAX_CHARS = 500
CARD_FIELD_FALLBACK_TEXT = "LLM返回超字数，请查看完整日报"
BAD_SOURCE_LABELS = {"tavily", "tavily.tavily", "rss", "rss.rss", "unknown", "unknown.unknown", "none", "none.none"}
KNOWN_ENTITY_TYPO_REPLACEMENTS = {
    "月之暗夜": "月之暗面",
    "Kim K2.7": "Kimi K2.7",
}
TOP_SOURCE_TIERS = {"S1", "S2", "S3"}
DOMAIN_LABELS = {
    "finance.sina.com.cn": "新浪财经",
    "sina.com.cn": "新浪",
    "wap.eastmoney.com": "东方财富",
    "eastmoney.com": "东方财富",
    "techcrunch.com": "TechCrunch",
    "theverge.com": "The Verge",
    "openai.com": "OpenAI",
    "anthropic.com": "Anthropic",
    "nvidia.com": "NVIDIA",
    "blogs.nvidia.com": "NVIDIA Blog",
    "microsoft.com": "Microsoft",
    "aws.amazon.com": "AWS",
    "aboutamazon.com": "Amazon",
    "reuters.com": "Reuters",
    "bloomberg.com": "Bloomberg",
    "theinformation.com": "The Information",
    "ft.com": "FT",
    "wsj.com": "WSJ",
    "github.com": "GitHub",
    "huggingface.co": "Hugging Face",
    "arxiv.org": "arXiv",
}


def _limit_text(value: Any, max_len: int) -> str:
    text = _normalize_known_entity_typos(str(value or "").strip())
    if len(text) <= max_len:
        return text
    clipped = text[:max_len].rstrip()
    clipped = _trim_incomplete_ascii_tail(clipped, text)
    return _append_truncation_marker(clipped, max_len)


def _limit_brief_why(value: Any) -> str:
    return _limit_text(value, BRIEF_WHY_MAX_CHARS)


def _normalize_known_entity_typos(value: str) -> str:
    text = str(value or "")
    for typo, replacement in KNOWN_ENTITY_TYPO_REPLACEMENTS.items():
        text = text.replace(typo, replacement)
    return text


def _append_truncation_marker(text: str, max_len: int) -> str:
    if max_len <= 0 or not text:
        return ""
    if text.endswith(("…", "。", "！", "？", ".", "!", "?")):
        return text[:max_len]
    if max_len == 1:
        return "…"
    return text[: max_len - 1].rstrip(" -_/.,，:：;；") + "…"


def _trim_incomplete_ascii_tail(clipped: str, original: str) -> str:
    next_char = original[len(clipped) : len(clipped) + 1]
    if next_char and re.match(r"[A-Za-z0-9+._-]", next_char) and re.search(r"[A-Za-z0-9]$", clipped):
        trimmed = re.sub(r"[A-Za-z0-9][A-Za-z0-9+._-]*$", "", clipped).rstrip(" -_/.,，:：;；")
        if len(trimmed) >= max(8, len(clipped) // 2):
            return trimmed
    if re.search(r"[\u4e00-\u9fff][A-Za-z]$", clipped):
        trimmed = clipped[:-1].rstrip(" -_/.,，:：;；")
        if len(trimmed) >= max(8, len(clipped) // 2):
            return trimmed
    return clipped


def sort_top_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    indexed = list(enumerate(items))
    indexed.sort(key=lambda row: (_priority_rank(row[1].get("priority")), row[0]))
    return [item for _idx, item in indexed]


def _normalize_card_bullets(raw_items: Any) -> tuple[list[str], list[str]]:
    full_items: list[str] = []
    card_items: list[str] = []
    for raw in raw_items if isinstance(raw_items, list) else []:
        if isinstance(raw, dict):
            full = _limit_text(raw.get("full") or raw.get("text") or raw.get("card"), BRIEF_BULLET_MAX_CHARS)
            card = _limit_text(raw.get("card") or full, 120)
        else:
            full = _limit_text(raw, BRIEF_BULLET_MAX_CHARS)
            card = full
        if not full:
            continue
        full_items.append(full)
        card_items.append(card)
        if len(full_items) >= 3:
            break
    return full_items, card_items


def _priority_rank(priority: Any) -> int:
    text = str(priority or "").upper()
    if "P1" in text:
        return 0
    if "P2" in text:
        return 1
    if "观察" in str(priority or "") or "OBSERVE" in text:
        return 2
    return 9


def _strip_json_fence(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned


def _clean_json_text(text: str) -> str:
    _parsed, _stage, cleaned = parse_brief_json_with_stage(text)
    return cleaned


def parse_brief_json_with_stage(text: str) -> tuple[dict[str, Any], str, str]:
    raw = text.strip()
    cleaned = re.sub(r",(\s*[}\]])", r"\1", _strip_json_fence(raw))
    first_error = ""

    for candidate_text, stage in ((raw, "raw_json_ok"), (cleaned, "extracted_json_ok")):
        try:
            parsed = json.loads(candidate_text)
        except json.JSONDecodeError as exc:
            first_error = first_error or str(exc)
            continue
        selected = _select_brief_object([parsed])
        if selected is not None:
            return selected, stage, candidate_text

    decoder = json.JSONDecoder()
    candidates: list[dict[str, Any]] = []
    for match in re.finditer(r"\{", cleaned):
        try:
            obj, end = decoder.raw_decode(cleaned[match.start() :])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            candidates.append(obj)
    selected = _select_brief_object(candidates)
    if selected is not None:
        return selected, "extracted_json_ok", json.dumps(selected, ensure_ascii=False)
    salvaged = salvage_brief_items_from_partial_json(cleaned)
    if _has_top_list(salvaged):
        return salvaged, "partial_json_salvaged", json.dumps(salvaged, ensure_ascii=False)
    if _mentions_brief_schema(raw):
        raise json.JSONDecodeError("parsed JSON does not contain domestic_top or overseas_top", cleaned, 0)
    raise json.JSONDecodeError(first_error or "No JSON object found", cleaned, 0)


URL_RE = re.compile(r"https?://[^\s)\]}>\"']+")


def parse_brief_json(text: str) -> dict[str, Any]:
    parsed, _stage, _cleaned = parse_brief_json_with_stage(text)
    return parsed


def salvage_brief_items_from_partial_json(text: str) -> dict[str, Any]:
    cleaned = _strip_json_fence(str(text or ""))
    output: dict[str, Any] = {}
    for key in ("domestic_top", "overseas_top"):
        items = _salvage_object_array(cleaned, key)
        if items:
            output[key] = items
    for key in ("core_judgments", "watch_signals"):
        values = _salvage_simple_array(cleaned, key)
        if values:
            output[key] = values
    return output


def _salvage_object_array(text: str, key: str) -> list[dict[str, Any]]:
    start = _array_start_for_key(text, key)
    if start < 0:
        return []
    decoder = json.JSONDecoder()
    items: list[dict[str, Any]] = []
    idx = start + 1
    while idx < len(text):
        char = text[idx]
        if char == "]":
            break
        if char != "{":
            idx += 1
            continue
        try:
            obj, end = decoder.raw_decode(text[idx:])
        except json.JSONDecodeError:
            break
        if isinstance(obj, dict):
            items.append(obj)
        idx += max(end, 1)
    return items


def _salvage_simple_array(text: str, key: str) -> list[Any]:
    start = _array_start_for_key(text, key)
    if start < 0:
        return []
    end = _matching_array_end(text, start)
    if end < 0:
        return []
    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def _array_start_for_key(text: str, key: str) -> int:
    match = re.search(rf'"{re.escape(key)}"\s*:\s*\[', text)
    return text.find("[", match.start()) if match else -1


def _matching_array_end(text: str, start: int) -> int:
    in_string = False
    escape = False
    depth = 0
    for idx in range(start, len(text)):
        char = text[idx]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                return idx
    return -1


def _select_brief_object(candidates: list[Any]) -> dict[str, Any] | None:
    dicts = [candidate for candidate in candidates if isinstance(candidate, dict)]
    for candidate in dicts:
        nested = _nested_brief_object(candidate)
        if nested is not None and _has_top_list(nested):
            return nested
        if _has_top_list(candidate):
            return candidate
    for candidate in dicts:
        nested = _nested_brief_object(candidate)
        if nested is not None:
            return nested
    return dicts[0] if len(dicts) == 1 and not _mentions_brief_schema(json.dumps(dicts[0], ensure_ascii=False)) else None


def _nested_brief_object(value: dict[str, Any]) -> dict[str, Any] | None:
    for key in ("brief", "data", "result", "output"):
        nested = value.get(key)
        if isinstance(nested, dict):
            return nested
    return None


def _has_top_list(value: dict[str, Any]) -> bool:
    return isinstance(value.get("domestic_top"), list) or isinstance(value.get("overseas_top"), list)


def _mentions_brief_schema(value: str) -> bool:
    return "domestic_top" in value or "overseas_top" in value


def fallback_brief(
    window: TimeWindow,
    audit: RecallAudit,
    doc_url: str = "",
    reason: str = "",
    *,
    raw_response: str = "",
    json_parse_error: str = "",
    repair_attempted: bool = False,
) -> dict[str, Any]:
    if reason:
        logger.warning("Brief generation fallback used: %s", reason)
    return {
        "date": window.date_str,
        "title": f"AI Radar｜{window.date_str}",
        "domestic_top": [],
        "overseas_top": [],
        "core_judgments": ["今日简报摘要未能稳定生成，请查看完整日报。"],
        "watch_signals": [],
        "core_judgments_card": ["今日简报摘要未能稳定生成，请查看完整日报。"],
        "watch_signals_card": [],
        "brief_core_judgments_count": 1,
        "brief_watch_signals_count": 0,
        "brief_core_judgments_dropped_non_top_count": 0,
        "brief_watch_signals_demoted_from_top_count": 0,
        "brief_watch_signals_demoted_from_top_examples": [],
        "doc_url": doc_url or "",
        "evidence_count": audit.total_evidence_count,
        "recall_summary": {
            "rss_count": audit.rss_item_count,
            "tavily_count": audit.tavily_item_count,
            "total_count": audit.total_evidence_count,
        },
        "brief_generation_status": "fallback",
        "brief_source_validation_warnings": [reason[:300]] if reason else [],
        "brief_error_summary": reason[:300],
        "brief_repair_attempted": repair_attempted,
        "brief_repair_succeeded": False,
        "brief_parse_stage": "fallback",
        "brief_raw_response_length": len(raw_response or ""),
        "brief_raw_response_summary": _redact_summary(raw_response),
        "brief_json_parse_error": json_parse_error[:300],
        "brief_normalization_error": "",
        "brief_source_resolution_status": "fallback",
        "brief_invalid_source_ids_count": 0,
        "brief_llm_domestic_items_count": 0,
        "brief_llm_overseas_items_count": 0,
        "brief_final_domestic_items_count": 0,
        "brief_final_overseas_items_count": 0,
        "brief_domestic_items_count_raw": 0,
        "brief_overseas_items_count_raw": 0,
        "brief_domestic_items_count_capped": 0,
        "brief_overseas_items_count_capped": 0,
        "brief_domestic_truncated": False,
        "brief_overseas_truncated": False,
        "brief_source_ids_requested_count": 0,
        "brief_source_ids_resolved_count": 0,
        "brief_source_ids_unresolved_count": 0,
        "brief_unresolved_source_ids_sample": [],
        "brief_sources_filled_by_matching_count": 0,
        "brief_empty_placeholder_removed_count": 0,
        "report_domestic_core_events_count": 0,
        "report_overseas_core_events_count": 0,
        "report_domestic_core_events_count_raw": 0,
        "report_overseas_core_events_count_raw": 0,
        "report_domestic_core_events_count_capped": 0,
        "report_overseas_core_events_count_capped": 0,
        "domestic_core_events_truncated": False,
        "overseas_core_events_truncated": False,
        "domestic_core_events_truncated_from": 0,
        "overseas_core_events_truncated_from": 0,
        "report_domestic_empty_reason": "",
        "report_overseas_empty_reason": "",
        "report_domestic_zero_core_conflict_resolved": "",
        "report_overseas_zero_core_conflict_resolved": "",
        "report_domestic_zero_core_explicit": False,
        "report_overseas_zero_core_explicit": False,
        "report_domestic_extraction_suspect": False,
        "report_overseas_extraction_suspect": False,
        "report_domestic_section_found": False,
        "report_overseas_section_found": False,
        "report_domestic_extraction_method": "none",
        "report_overseas_extraction_method": "none",
        "report_domestic_extracted_titles_sample": [],
        "report_overseas_extracted_titles_sample": [],
        "brief_count_mismatch": False,
        "brief_count_mismatch_type": "none",
        "brief_count_mismatch_handled": False,
        "brief_count_repair_attempted": False,
        "brief_count_repair_succeeded": False,
    }


def extract_core_events_from_report(report_md: str) -> dict[str, Any]:
    domestic = _extract_region_core_events(report_md, "domestic")
    overseas = _extract_region_core_events(report_md, "overseas")
    return {
        "domestic_core_events": domestic["events"],
        "overseas_core_events": overseas["events"],
        "domestic_core_events_raw_count": domestic["raw_count"],
        "overseas_core_events_raw_count": overseas["raw_count"],
        "domestic_core_events_capped_count": domestic["capped_count"],
        "overseas_core_events_capped_count": overseas["capped_count"],
        "domestic_core_events_truncated": domestic["truncated"],
        "overseas_core_events_truncated": overseas["truncated"],
        "domestic_core_events_truncated_from": domestic["raw_count"] if domestic["truncated"] else 0,
        "overseas_core_events_truncated_from": overseas["raw_count"] if overseas["truncated"] else 0,
        "domestic_zero_core_explicit": domestic["zero_core_explicit"],
        "overseas_zero_core_explicit": overseas["zero_core_explicit"],
        "domestic_zero_core_conflict_resolved": domestic["zero_core_conflict_resolved"],
        "overseas_zero_core_conflict_resolved": overseas["zero_core_conflict_resolved"],
        "domestic_extraction_suspect": domestic["extraction_suspect"],
        "overseas_extraction_suspect": overseas["extraction_suspect"],
        "domestic_section_found": domestic["section_found"],
        "overseas_section_found": overseas["section_found"],
        "domestic_extraction_method": domestic["extraction_method"],
        "overseas_extraction_method": overseas["extraction_method"],
        "domestic_extracted_titles_sample": domestic["titles_sample"],
        "overseas_extracted_titles_sample": overseas["titles_sample"],
    }


def _extract_core_judgments_from_report(report_md: str) -> list[str]:
    return _extract_report_bullets(
        report_md,
        (
            "今日核心判断",
            "本周核心判断",
            "本月核心判断",
            "核心判断",
        ),
    )


def _extract_watch_signals_from_report(report_md: str) -> list[str]:
    return _extract_report_bullets(report_md, ("观察信号",))


def _extract_report_bullets(report_md: str, markers: tuple[str, ...]) -> list[str]:
    section = _extract_named_section(report_md, markers)
    if not section:
        return []
    items: list[str] = []
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("|"):
            continue
        match = re.match(r"^(?:[-*+]\s+|\d+[.)、]\s+|[一二三四五六七八九十]+[、.]\s*)(.+)$", stripped)
        if not match:
            continue
        item = _clean_report_bullet(match.group(1))
        if item:
            items.append(_limit_text(item, 80))
        if len(items) == 3:
            break
    return items


def _extract_named_section(report_md: str, markers: tuple[str, ...]) -> str:
    lines = report_md.splitlines()
    start_idx = None
    start_level = 0
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue
        heading = re.sub(r"^#{1,6}\s*", "", stripped).strip()
        if _blocked_report_section_line(heading):
            continue
        heading_text = re.sub(r"^[一二三四五六七八九十\d]+[、.．]\s*", "", heading)
        normalized = re.sub(r"\s+", "", heading_text)
        if any(re.sub(r"\s+", "", marker) in normalized for marker in markers):
            start_idx = idx + 1
            start_level = len(stripped) - len(stripped.lstrip("#"))
            break
    if start_idx is None:
        return ""

    end_idx = len(lines)
    for idx in range(start_idx, len(lines)):
        stripped = lines[idx].strip()
        if _blocked_report_section_line(stripped):
            end_idx = idx
            break
        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            if level <= start_level:
                end_idx = idx
                break
    return "\n".join(lines[start_idx:end_idx]).strip()


def _blocked_report_section_line(value: str) -> bool:
    return any(marker in str(value or "") for marker in ("候选事件筛选表", "候选表", "输出前自我检查", "输出前自检", "自检清单", "来源索引", "附录"))


def _clean_report_bullet(value: str) -> str:
    text = re.sub(r"\[[^\]]+\]\(([^)]+)\)", r"\1", str(value or "")).strip()
    text = re.sub(r"<https?://[^>]+>", "", text)
    text = URL_RE.sub("", text)
    text = re.sub(r"^\*\*(.+?)\*\*\s*[:：]?\s*", r"\1：", text)
    text = text.strip(" -*_`：:；;，,。")
    if not text or _blocked_report_section_line(text) or _is_no_core_text(text):
        return ""
    return re.sub(r"\s+", " ", text)


def normalize_brief(
    raw: dict[str, Any],
    window: TimeWindow,
    audit: RecallAudit,
    doc_url: str = "",
    *,
    report_md: str = "",
    evidence: list[EvidenceItem] | None = None,
    generation_status: str = "ok",
    repair_attempted: bool = False,
    repair_succeeded: bool = False,
    raw_response: str = "",
    json_parse_error: str = "",
    parse_stage: str = "raw_json_ok",
    normalization_error: str = "",
    core_events: dict[str, list[dict[str, Any]]] | None = None,
    count_repair_attempted: bool = False,
    count_repair_succeeded: bool = False,
) -> dict[str, Any]:
    evidence_items = evidence or []
    records = _evidence_records(evidence_items)
    evidence_by_id = _evidence_map(records)
    allowed_urls = _allowed_source_urls(report_md, evidence_items)
    warnings: list[str] = []
    source_ids_requested_count = 0
    source_ids_resolved_count = 0
    unresolved_source_ids: list[str] = []
    sources_filled_by_matching_count = 0
    empty_placeholder_removed_count = 0
    source_quality_dropped_examples: list[str] = []
    region_reassigned_examples: list[str] = []

    def normalize_top(items: Any) -> list[dict[str, Any]]:
        nonlocal source_ids_requested_count, source_ids_resolved_count, sources_filled_by_matching_count, empty_placeholder_removed_count
        output = []
        for item in items if isinstance(items, list) else []:
            if not isinstance(item, dict):
                continue
            if _is_empty_placeholder_item(item):
                empty_placeholder_removed_count += 1
                continue
            source_ids = _source_id_values(item.get("source_ids"))
            source_ids_requested_count += len(source_ids)
            sources, resolved_count, unresolved_ids = _sources_from_ids(source_ids, evidence_by_id, warnings)
            source_ids_resolved_count += resolved_count
            unresolved_source_ids.extend(unresolved_ids)
            if not sources:
                sources = _normalize_sources(item.get("sources"), allowed_urls, warnings)
            original_sources = list(sources)
            sources = _filter_sources_for_item(item, sources, records, warnings)
            if not sources:
                matched_sources = _fallback_sources_for_item(item, records, allowed_urls)
                if matched_sources:
                    sources_filled_by_matching_count += len(matched_sources)
                    sources = matched_sources
                elif original_sources and not _source_query_is_specific(_source_query_for_item(item)):
                    sources = original_sources[:2]
            sources = _prefer_top_tier_sources(sources, records)
            output.append(
                {
                    "title": _limit_text(item.get("title"), 80),
                    "card_title": _limit_text(item.get("card_title") or item.get("title"), 40),
                    "why": _limit_brief_why(_clean_brief_why_value(item.get("why") or item.get("card_why"), item.get("title"))),
                    "card_why": _limit_text(
                        _clean_brief_why_value(item.get("card_why") or item.get("why"), item.get("title")),
                        120,
                    ),
                    "priority": _limit_text(item.get("priority"), 8) or "观察",
                    "sources": sources,
                }
            )
        return output

    domestic_top = normalize_top(raw.get("domestic_top"))
    overseas_top = normalize_top(raw.get("overseas_top"))
    llm_domestic_items_count = _llm_items_count(raw.get("domestic_top"))
    llm_overseas_items_count = _llm_items_count(raw.get("overseas_top"))
    domestic_core_events = (core_events or {}).get("domestic_core_events") or []
    overseas_core_events = (core_events or {}).get("overseas_core_events") or []
    if domestic_core_events:
        domestic_top = _align_items_to_core_events(domestic_top, domestic_core_events, records, allowed_urls, warnings)
    elif _force_empty_top(core_events or {}, "domestic"):
        domestic_top = []
    else:
        domestic_top = sort_top_items(domestic_top)
    if overseas_core_events:
        overseas_top = _align_items_to_core_events(overseas_top, overseas_core_events, records, allowed_urls, warnings)
    elif _force_empty_top(core_events or {}, "overseas"):
        overseas_top = []
    else:
        overseas_top = sort_top_items(overseas_top)
    domestic_top, domestic_quality_dropped, domestic_quality_dropped_items = _filter_top_items_by_source_quality(
        domestic_top,
        records,
        warnings,
    )
    overseas_top, overseas_quality_dropped, overseas_quality_dropped_items = _filter_top_items_by_source_quality(
        overseas_top,
        records,
        warnings,
    )
    domestic_top, overseas_top, region_reassigned_examples = _reassign_top_items_by_subject_region(
        domestic_top,
        overseas_top,
        warnings,
    )
    source_quality_dropped_examples.extend(domestic_quality_dropped[:3])
    source_quality_dropped_examples.extend(overseas_quality_dropped[:3])
    domestic_top_raw_count = len(domestic_top)
    overseas_top_raw_count = len(overseas_top)
    domestic_top = _cap_ranked_items(domestic_top)
    overseas_top = _cap_ranked_items(overseas_top)
    expected_domestic_count = _expected_final_top_count(domestic_core_events)
    expected_overseas_count = _expected_final_top_count(overseas_core_events)
    domestic_top_truncated = domestic_top_raw_count > len(domestic_top)
    overseas_top_truncated = overseas_top_raw_count > len(overseas_top)
    unresolved_count = len(unresolved_source_ids)
    mismatch_type = _count_mismatch_type(
        llm_domestic_items_count,
        llm_overseas_items_count,
        expected_domestic_count,
        expected_overseas_count,
        empty_placeholder_removed_count,
    )
    initial_count_mismatch = mismatch_type != "none"
    final_mismatch_type = _count_mismatch_type(
        len(domestic_top),
        len(overseas_top),
        expected_domestic_count,
        expected_overseas_count,
        0,
    )
    final_count_mismatch = final_mismatch_type != "none"
    mismatch_handled = _count_mismatch_handled(
        final_mismatch_type,
        count_repair_attempted=count_repair_attempted,
        domestic_final_count=len(domestic_top),
        overseas_final_count=len(overseas_top),
        expected_domestic_count=expected_domestic_count,
        expected_overseas_count=expected_overseas_count,
    )
    if initial_count_mismatch and not final_count_mismatch:
        mismatch_handled = True
    if (
        final_count_mismatch
        and region_reassigned_examples
        and len(domestic_top) + len(overseas_top) == expected_domestic_count + expected_overseas_count
    ):
        mismatch_handled = True

    if not normalization_error:
        normalization_error = _normalization_error(
            llm_domestic_items_count,
            llm_overseas_items_count,
            len(domestic_top),
            len(overseas_top),
            domestic_source_quality_dropped_count=len(domestic_quality_dropped),
            overseas_source_quality_dropped_count=len(overseas_quality_dropped),
            region_reassigned_count=len(region_reassigned_examples),
        )

    core_judgments, core_judgments_card = _normalize_card_bullets(raw.get("core_judgments"))
    watch_signals, watch_signals_card = _normalize_card_bullets(raw.get("watch_signals"))
    core_judgments_filled_from_report = False
    watch_signals_filled_from_report = False
    if not core_judgments:
        core_judgments = _extract_core_judgments_from_report(report_md)
        core_judgments_card = list(core_judgments)
        core_judgments_filled_from_report = bool(core_judgments)
    if not watch_signals:
        watch_signals = _extract_watch_signals_from_report(report_md)
        watch_signals_card = list(watch_signals)
        watch_signals_filled_from_report = bool(watch_signals)
    quality_dropped_titles = domestic_quality_dropped + overseas_quality_dropped
    quality_dropped_items = domestic_quality_dropped_items + overseas_quality_dropped_items
    if quality_dropped_titles:
        core_judgments, core_judgments_card = _drop_bullets_mentioning_titles(
            core_judgments,
            core_judgments_card,
            quality_dropped_titles,
        )
        watch_signals, watch_signals_card = _drop_bullets_mentioning_titles(
            watch_signals,
            watch_signals_card,
            quality_dropped_titles,
        )
        if not core_judgments:
            core_judgments = _core_judgments_from_final_top(domestic_top, overseas_top)
            core_judgments_card = list(core_judgments)
        watch_signals, watch_signals_card, watch_signals_demoted_examples = _demote_dropped_top_items_to_watch_signals(
            watch_signals,
            watch_signals_card,
            quality_dropped_items,
            domestic_top + overseas_top,
        )
    else:
        watch_signals_demoted_examples = []
    core_judgments, core_judgments_card, core_judgments_dropped_non_top = _filter_core_judgments_to_final_top(
        core_judgments,
        core_judgments_card,
        domestic_top,
        overseas_top,
    )
    if (domestic_top or overseas_top) and _has_truncated_bullet(core_judgments):
        warnings.append("replaced truncated core judgment from final top")
        core_judgments = _core_judgments_from_final_top(domestic_top, overseas_top)
        core_judgments_card = list(core_judgments)
    if core_judgments_dropped_non_top:
        warnings.append(f"dropped core judgment not tied to final top: {core_judgments_dropped_non_top}")
    brief = {
        "date": window.date_str,
        "title": f"AI Radar｜{window.date_str}",
        "domestic_top": domestic_top,
        "overseas_top": overseas_top,
        "core_judgments": core_judgments,
        "watch_signals": watch_signals,
        "core_judgments_card": core_judgments_card,
        "watch_signals_card": watch_signals_card,
        "brief_core_judgments_count": len(core_judgments),
        "brief_watch_signals_count": len(watch_signals),
        "brief_core_judgments_dropped_non_top_count": core_judgments_dropped_non_top,
        "brief_watch_signals_demoted_from_top_count": len(watch_signals_demoted_examples),
        "brief_watch_signals_demoted_from_top_examples": watch_signals_demoted_examples[:10],
        "core_judgments_filled_from_report": core_judgments_filled_from_report,
        "watch_signals_filled_from_report": watch_signals_filled_from_report,
        "doc_url": doc_url or _limit_text(raw.get("doc_url"), 500),
        "evidence_count": audit.total_evidence_count,
        "recall_summary": {
            "rss_count": audit.rss_item_count,
            "tavily_count": audit.tavily_item_count,
            "total_count": audit.total_evidence_count,
        },
        "brief_generation_status": generation_status,
        "brief_source_validation_warnings": warnings,
        "brief_error_summary": normalization_error[:300],
        "brief_repair_attempted": repair_attempted,
        "brief_repair_succeeded": repair_succeeded,
        "brief_parse_stage": parse_stage,
        "brief_raw_response_length": len(raw_response or ""),
        "brief_raw_response_summary": _redact_summary(raw_response),
        "brief_json_parse_error": json_parse_error[:300],
        "brief_normalization_error": normalization_error[:300],
        "brief_source_resolution_status": _source_resolution_status(
            domestic_top + overseas_top,
            source_ids_requested_count,
            source_ids_resolved_count,
            unresolved_count,
        ),
        "brief_invalid_source_ids_count": unresolved_count,
        "brief_llm_domestic_items_count": llm_domestic_items_count,
        "brief_llm_overseas_items_count": llm_overseas_items_count,
        "brief_final_domestic_items_count": len(domestic_top),
        "brief_final_overseas_items_count": len(overseas_top),
        "brief_domestic_items_count_raw": domestic_top_raw_count,
        "brief_overseas_items_count_raw": overseas_top_raw_count,
        "brief_domestic_items_count_capped": len(domestic_top),
        "brief_overseas_items_count_capped": len(overseas_top),
        "brief_domestic_truncated": domestic_top_truncated,
        "brief_overseas_truncated": overseas_top_truncated,
        "brief_source_ids_requested_count": source_ids_requested_count,
        "brief_source_ids_resolved_count": source_ids_resolved_count,
        "brief_source_ids_unresolved_count": unresolved_count,
        "brief_unresolved_source_ids_sample": unresolved_source_ids[:10],
        "brief_sources_filled_by_matching_count": sources_filled_by_matching_count,
        "brief_empty_placeholder_removed_count": empty_placeholder_removed_count,
        "brief_top_items_dropped_source_quality_count": len(domestic_quality_dropped) + len(overseas_quality_dropped),
        "brief_top_items_dropped_source_quality_examples": source_quality_dropped_examples[:10],
        "brief_top_items_region_reassigned_count": len(region_reassigned_examples),
        "brief_top_items_region_reassigned_examples": region_reassigned_examples[:10],
        "report_domestic_core_events_count": len(domestic_core_events),
        "report_overseas_core_events_count": len(overseas_core_events),
        "report_domestic_core_events_count_raw": int((core_events or {}).get("domestic_core_events_raw_count") or len(domestic_core_events)),
        "report_overseas_core_events_count_raw": int((core_events or {}).get("overseas_core_events_raw_count") or len(overseas_core_events)),
        "report_domestic_core_events_count_capped": int(
            (core_events or {}).get("domestic_core_events_capped_count") or len(domestic_core_events)
        ),
        "report_overseas_core_events_count_capped": int(
            (core_events or {}).get("overseas_core_events_capped_count") or len(overseas_core_events)
        ),
        "domestic_core_events_truncated": bool((core_events or {}).get("domestic_core_events_truncated", False)),
        "overseas_core_events_truncated": bool((core_events or {}).get("overseas_core_events_truncated", False)),
        "domestic_core_events_truncated_from": int((core_events or {}).get("domestic_core_events_truncated_from") or 0),
        "overseas_core_events_truncated_from": int((core_events or {}).get("overseas_core_events_truncated_from") or 0),
        "report_domestic_zero_core_explicit": bool((core_events or {}).get("domestic_zero_core_explicit", False)),
        "report_overseas_zero_core_explicit": bool((core_events or {}).get("overseas_zero_core_explicit", False)),
        "report_domestic_zero_core_conflict_resolved": str((core_events or {}).get("domestic_zero_core_conflict_resolved") or ""),
        "report_overseas_zero_core_conflict_resolved": str((core_events or {}).get("overseas_zero_core_conflict_resolved") or ""),
        "report_domestic_extraction_suspect": bool((core_events or {}).get("domestic_extraction_suspect", False)),
        "report_overseas_extraction_suspect": bool((core_events or {}).get("overseas_extraction_suspect", False)),
        "report_domestic_section_found": bool((core_events or {}).get("domestic_section_found", False)),
        "report_overseas_section_found": bool((core_events or {}).get("overseas_section_found", False)),
        "report_domestic_extraction_method": str((core_events or {}).get("domestic_extraction_method", "none")),
        "report_overseas_extraction_method": str((core_events or {}).get("overseas_extraction_method", "none")),
        "report_domestic_extracted_titles_sample": (core_events or {}).get("domestic_extracted_titles_sample", []),
        "report_overseas_extracted_titles_sample": (core_events or {}).get("overseas_extracted_titles_sample", []),
        "report_domestic_empty_reason": _empty_reason(core_events or {}, "domestic", domestic_core_events),
        "report_overseas_empty_reason": _empty_reason(core_events or {}, "overseas", overseas_core_events),
        "brief_count_mismatch": initial_count_mismatch,
        "brief_count_mismatch_initial": initial_count_mismatch,
        "brief_count_mismatch_final": final_count_mismatch,
        "brief_count_mismatch_type": mismatch_type,
        "brief_count_mismatch_handled": mismatch_handled,
        "brief_count_filled_from_core_events": bool(initial_count_mismatch and not final_count_mismatch and (domestic_core_events or overseas_core_events)),
        "brief_expected_domestic_items_count": expected_domestic_count,
        "brief_expected_overseas_items_count": expected_overseas_count,
        "brief_actual_domestic_items_count": len(domestic_top),
        "brief_actual_overseas_items_count": len(overseas_top),
        "brief_count_repair_attempted": count_repair_attempted,
        "brief_count_repair_succeeded": count_repair_succeeded,
    }
    return brief


def render_brief_markdown(brief: dict[str, Any]) -> str:
    lines = [f"# {brief['title']}", "", f"- Evidence: {brief['evidence_count']}"]
    if brief.get("doc_url"):
        lines.append(f"- 完整日报：{brief['doc_url']}")
    if brief.get("brief_generation_status") == "fallback":
        lines.extend(["", "今日简报摘要未能稳定生成，请查看完整日报。"])
        if brief.get("doc_url"):
            lines.append(f"全文：{brief['doc_url']}")
        return "\n".join(lines) + "\n"
    lines.extend(["", "## 国内 Top"])
    domestic_items = brief.get("domestic_top") or []
    if not domestic_items:
        lines.append("今日无强核心事件，不强行凑数。")
    for idx, item in enumerate(domestic_items, start=1):
        lines.append(f"{idx}. {item['title']}｜{item['priority']}")
        lines.append(f"   {item['why']}")
        source_text = _source_markdown(item.get("sources") or [])
        if source_text:
            lines.append(f"   来源：{source_text}")
    lines.extend(["", "## 海外 Top"])
    overseas_items = brief.get("overseas_top") or []
    if not overseas_items:
        lines.append("今日无强核心事件，不强行凑数。")
    for idx, item in enumerate(overseas_items, start=1):
        lines.append(f"{idx}. {item['title']}｜{item['priority']}")
        lines.append(f"   {item['why']}")
        source_text = _source_markdown(item.get("sources") or [])
        if source_text:
            lines.append(f"   来源：{source_text}")
    lines.extend(["", "## 核心判断"])
    for item in brief.get("core_judgments", []):
        lines.append(f"- {item}")
    lines.extend(["", "## 观察信号"])
    for item in brief.get("watch_signals", []):
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


class DeepSeekBriefGenerator:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = OpenAI(api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url)

    def generate(
        self,
        window: TimeWindow,
        report_md: str,
        audit: RecallAudit,
        doc_url: str = "",
        evidence: list[EvidenceItem] | None = None,
    ) -> dict[str, Any]:
        catalog = _evidence_catalog(report_md, evidence or [])
        core_events = extract_core_events_from_report(report_md)
        if _core_extraction_needs_fallback(core_events):
            core_events = self._fallback_extract_core_events(report_md, core_events)
        if bool(getattr(getattr(self, "settings", None), "brief_section_generation_enabled", False)):
            try:
                return self._generate_sectioned_brief(window, report_md, audit, doc_url, evidence, catalog, core_events)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Section-level brief generation failed, falling back to full brief JSON: %s", exc)
        prompt = self._prompt(window, report_md, audit, doc_url, catalog, core_events)
        raw_response = ""
        first_error = ""
        try:
            raw_response = self._call(prompt)
            parsed, parse_stage, _cleaned = parse_brief_json_with_stage(raw_response)
            brief = normalize_brief(
                _validated_brief_schema(parsed),
                window,
                audit,
                doc_url,
                report_md=report_md,
                evidence=evidence,
                generation_status="ok",
                raw_response=raw_response,
                parse_stage=parse_stage,
                core_events=core_events,
            )
            _raise_if_normalization_dropped_items(brief)
            if _brief_count_mismatch(brief):
                return self._repair_count_mismatch(
                    window,
                    audit,
                    doc_url,
                    report_md,
                    evidence,
                    core_events,
                    catalog,
                    raw_response,
                    parsed,
                    first_error,
                )
            return self._repair_card_fields(brief)
        except Exception as exc:  # noqa: BLE001
            first_error = str(exc)
            logger.warning("Brief JSON parse failed, retrying once: %s", exc)
        try:
            repair_prompt = self._repair_prompt(raw_response, first_error)
            repair_response = self._call(repair_prompt)
            parsed, _parse_stage, _cleaned = parse_brief_json_with_stage(repair_response)
            brief = normalize_brief(
                _validated_brief_schema(parsed),
                window,
                audit,
                doc_url,
                report_md=report_md,
                evidence=evidence,
                generation_status="repaired",
                repair_attempted=True,
                repair_succeeded=True,
                raw_response=repair_response,
                json_parse_error=first_error,
                parse_stage="repaired",
                core_events=core_events,
            )
            if _repair_payload_empty(parsed, core_events):
                brief["brief_repair_succeeded"] = False
                brief["brief_repair_empty_payload"] = True
                brief["brief_error_summary"] = "repair returned empty top lists; filled from report core events"
            else:
                brief["brief_repair_empty_payload"] = False
            _raise_if_normalization_dropped_items(brief)
            return self._repair_card_fields(brief)
        except Exception as exc:  # noqa: BLE001
            return fallback_brief(
                window,
                audit,
                doc_url,
                reason=f"repair failed: {exc}",
                raw_response=raw_response,
                json_parse_error=first_error,
                repair_attempted=True,
            )

    def _call(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.settings.deepseek_model,
            messages=[
                {"role": "system", "content": "你是日报简报编辑，只能基于用户提供的完整报告提炼 JSON。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=3500,
        )
        return response.choices[0].message.content or ""

    def _generate_sectioned_brief(
        self,
        window: TimeWindow,
        report_md: str,
        audit: RecallAudit,
        doc_url: str,
        evidence: list[EvidenceItem] | None,
        catalog: list[dict[str, str]],
        core_events: dict[str, list[dict[str, Any]]],
    ) -> dict[str, Any]:
        max_attempts = max(1, int(getattr(self.settings, "brief_section_repair_max_attempts", 3) or 3))
        self._section_attempts_count = 0
        domestic_response, domestic_top = self._call_top_section("domestic_top", window, report_md, catalog, core_events, max_attempts)
        overseas_response, overseas_top = self._call_top_section("overseas_top", window, report_md, catalog, core_events, max_attempts)
        bullets_response, bullets = self._call_bullet_sections(window, report_md, max_attempts)
        raw = {
            "domestic_top": domestic_top,
            "overseas_top": overseas_top,
            "core_judgments": bullets.get("core_judgments") or [],
            "watch_signals": bullets.get("watch_signals") or [],
        }
        raw_response = json.dumps(raw, ensure_ascii=False)
        brief = normalize_brief(
            _validated_brief_schema(raw),
            window,
            audit,
            doc_url,
            report_md=report_md,
            evidence=evidence,
            generation_status="ok",
            raw_response=raw_response,
            parse_stage="sectioned_json_ok",
            core_events=core_events,
        )
        brief.update(
            {
                "brief_section_generation_used": True,
                "brief_section_generation_status": "ok",
                "brief_section_generation_attempts_count": self._section_attempts_count,
                "brief_section_raw_response_length": len(domestic_response) + len(overseas_response) + len(bullets_response),
            }
        )
        _raise_if_normalization_dropped_items(brief)
        if _brief_count_mismatch(brief):
            return self._repair_count_mismatch(
                window,
                audit,
                doc_url,
                report_md,
                evidence,
                core_events,
                catalog,
                raw_response,
                raw,
                "",
            )
        return self._repair_card_fields(brief)

    def _call_top_section(
        self,
        key: str,
        window: TimeWindow,
        report_md: str,
        catalog: list[dict[str, str]],
        core_events: dict[str, list[dict[str, Any]]],
        max_attempts: int,
    ) -> tuple[str, list[dict[str, Any]]]:
        self._section_attempts_count = int(getattr(self, "_section_attempts_count", 0))
        last_response = ""
        prompt = self._top_section_prompt(key, window, report_md, catalog, core_events)
        for _attempt in range(max_attempts):
            self._section_attempts_count += 1
            last_response = self._call(prompt)
            parsed_ok, items = _parse_top_section_response(last_response, key)
            if parsed_ok:
                return last_response, items
        raise ValueError(f"{key} section generation failed")

    def _call_bullet_sections(self, window: TimeWindow, report_md: str, max_attempts: int) -> tuple[str, dict[str, Any]]:
        self._section_attempts_count = int(getattr(self, "_section_attempts_count", 0))
        last_response = ""
        prompt = self._bullet_section_prompt(window, report_md)
        for _attempt in range(max_attempts):
            self._section_attempts_count += 1
            last_response = self._call(prompt)
            parsed = _parse_bullet_section_response(last_response)
            if parsed:
                return last_response, parsed
        return last_response, {}

    def _repair_count_mismatch(
        self,
        window: TimeWindow,
        audit: RecallAudit,
        doc_url: str,
        report_md: str,
        evidence: list[EvidenceItem] | None,
        core_events: dict[str, list[dict[str, Any]]],
        catalog: list[dict[str, str]],
        raw_response: str,
        parsed: dict[str, Any],
        json_parse_error: str,
    ) -> dict[str, Any]:
        try:
            repair_response = self._call(self._count_repair_prompt(raw_response, core_events, catalog))
            repaired, _parse_stage, _cleaned = parse_brief_json_with_stage(repair_response)
            brief = normalize_brief(
                _validated_brief_schema(repaired),
                window,
                audit,
                doc_url,
                report_md=report_md,
                evidence=evidence,
                generation_status="repaired",
                repair_attempted=True,
                repair_succeeded=True,
                raw_response=repair_response,
                json_parse_error=json_parse_error,
                parse_stage="repaired",
                core_events=core_events,
                count_repair_attempted=True,
                count_repair_succeeded=True,
            )
            _raise_if_normalization_dropped_items(brief)
            return self._repair_card_fields(brief)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Brief count repair failed, using deterministic core-event fallback: %s", exc)
            brief = normalize_brief(
                _validated_brief_schema(parsed),
                window,
                audit,
                doc_url,
                report_md=report_md,
                evidence=evidence,
                generation_status="repaired",
                repair_attempted=False,
                repair_succeeded=False,
                raw_response=raw_response,
                json_parse_error=json_parse_error,
                parse_stage="repaired",
                core_events=core_events,
                count_repair_attempted=True,
                count_repair_succeeded=True,
            )
            return self._repair_card_fields(brief)

    def _repair_card_fields(self, brief: dict[str, Any]) -> dict[str, Any]:
        settings = getattr(self, "settings", None)
        max_attempts = max(0, int(getattr(settings, "brief_card_repair_max_attempts", 3) or 0))
        stats = {
            "brief_card_field_repair_attempted": False,
            "brief_card_field_repair_max_attempts": max_attempts,
            "brief_card_field_repair_attempts_count": 0,
            "brief_card_field_repair_succeeded_count": 0,
            "brief_card_field_repair_failed_count": 0,
            "brief_card_field_fallback_used_count": 0,
            "brief_card_field_fallback_reason": "",
            "brief_card_field_fallback_examples": [],
        }
        for issue in _card_field_issues(brief):
            stats["brief_card_field_repair_attempted"] = True
            for attempt in range(max_attempts):
                stats["brief_card_field_repair_attempts_count"] += 1
                try:
                    repaired = _parse_card_field_repair_response(self._call(self._card_field_repair_prompt(issue)))
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Brief card field repair failed on attempt %s: %s", attempt + 1, exc)
                    repaired = ""
                if _valid_card_value(repaired, int(issue["max_chars"])):
                    _set_card_field(issue, repaired)
                    stats["brief_card_field_repair_succeeded_count"] += 1
                    break
            else:
                _set_card_field(issue, _deterministic_card_field_fallback(issue))
                stats["brief_card_field_repair_failed_count"] += 1
                stats["brief_card_field_fallback_used_count"] += 1
                stats["brief_card_field_fallback_reason"] = "deterministic_truncate_after_llm_over_limit"
                examples = list(stats["brief_card_field_fallback_examples"])
                if len(examples) < 5:
                    examples.append(f"{issue['path']}: {str(issue['value'])[:60]}")
                stats["brief_card_field_fallback_examples"] = examples
        brief.update(stats)
        return brief

    @staticmethod
    def _card_field_repair_prompt(issue: dict[str, Any]) -> str:
        return f"""
请修复一个飞书卡片字段。只输出 JSON，不要 Markdown。

字段路径：{issue['path']}
字段类型：{issue['kind']}
最大长度：{issue['max_chars']} 个中文字符/中英混排字符
当前内容：{issue['value']}

要求：
1. 只压缩当前这一条，不要新增事实。
2. 必须是一句完整自然语言。
3. 不要使用省略号。
4. 不要输出 Markdown、编号、表格字段。
5. 长度必须小于等于 {issue['max_chars']}。

输出 schema：
{{"value": "修复后的短句"}}
"""

    @staticmethod
    def _top_section_prompt(
        key: str,
        window: TimeWindow,
        report_md: str,
        catalog: list[dict[str, str]],
        core_events: dict[str, list[dict[str, Any]]],
    ) -> str:
        region_name = "国内" if key == "domestic_top" else "海外"
        core_key = "domestic_core_events" if key == "domestic_top" else "overseas_core_events"
        return f"""
请只生成 brief.json 的 {key} 字段。只输出 JSON object，不要 Markdown。

输出 schema：
{{"{key}": [{{"title": "完整标题", "card_title": "不超过28字卡片标题", "why": "相对完整解释", "card_why": "不超过60字卡片短句", "priority": "P1/P2/观察", "source_ids": ["E1"]}}]}}

要求：
1. 只生成{region_name} Top，不要输出其他字段。
2. 必须基于正式核心事件清单；每个正式核心事件生成 1 条，每侧最多 6 条。
3. card_title 不超过 28 字；card_why 不超过 60 字。
4. card 字段必须是完整短句，不要省略号，不要半截词。
5. source_ids 只能来自 evidence catalog，每条最多 2 个；无法匹配则 []。
6. 日期：{window.date_str}

正式核心事件清单：
{json.dumps({core_key: (core_events or {}).get(core_key) or []}, ensure_ascii=False, indent=2)[:10000]}

Evidence catalog：
{json.dumps(catalog or [], ensure_ascii=False, indent=2)[:12000]}

完整日报：
{report_md[:16000]}
""".strip()

    @staticmethod
    def _bullet_section_prompt(window: TimeWindow, report_md: str) -> str:
        return f"""
请只生成 brief.json 的 core_judgments 和 watch_signals 字段。只输出 JSON object，不要 Markdown。

输出 schema：
{{
  "core_judgments": [{{"full": "完整判断", "card": "不超过56字卡片短句"}}],
  "watch_signals": [{{"full": "完整观察", "card": "不超过56字卡片短句"}}]
}}

要求：
1. core_judgments 最多 3 条；watch_signals 最多 3 条。
2. card 不超过 56 字，必须是完整短句，不要省略号，不要半截词。
3. 不得引入完整日报没有的事实。
4. 日期：{window.date_str}

完整日报：
{report_md[:14000]}
""".strip()

    def _fallback_extract_core_events(self, report_md: str, core_events: dict[str, Any]) -> dict[str, Any]:
        try:
            response = self._call(self._core_extractor_prompt(report_md, core_events))
            parsed, _stage, _cleaned = parse_brief_json_with_stage(response)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Core event LLM fallback extraction failed: %s", exc)
            return _mark_core_fallback_failed(core_events)
        updated = dict(core_events)
        for region in ("domestic", "overseas"):
            key = f"{region}_core_events"
            if not updated.get(f"{region}_extraction_suspect"):
                continue
            raw_events = _normalize_llm_core_events(parsed.get(key))
            events, raw_count, truncated = _cap_events(raw_events)
            if events:
                updated[key] = events
                updated[f"{region}_core_events_raw_count"] = raw_count
                updated[f"{region}_core_events_capped_count"] = len(events)
                updated[f"{region}_core_events_truncated"] = truncated
                updated[f"{region}_core_events_truncated_from"] = raw_count if truncated else 0
                updated[f"{region}_extraction_method"] = "llm_fallback"
                updated[f"{region}_extraction_suspect"] = False
                updated[f"{region}_extracted_titles_sample"] = [event["title"] for event in events[:5]]
            else:
                updated[f"{region}_extraction_method"] = "llm_fallback_failed"
        return updated

    @staticmethod
    def _prompt(
        window: TimeWindow,
        report_md: str,
        audit: RecallAudit,
        doc_url: str,
        catalog: list[dict[str, str]] | None = None,
        core_events: dict[str, list[dict[str, Any]]] | None = None,
    ) -> str:
        catalog_text = json.dumps(catalog or [], ensure_ascii=False, indent=2)
        core_events_text = json.dumps(core_events or {}, ensure_ascii=False, indent=2)
        return f"""
请从下面完整日报中提炼飞书群卡片用 brief.json。

硬性要求：
1. 只输出 JSON，不要 Markdown code fence。
2. 不得引入完整日报中没有的事实。
3. 每条摘要保持精炼，适合群推送阅读。
4. 你会收到完整日报中的正式核心事件清单；请为每个正式核心事件生成一条 brief item。
5. 不要为了凑数添加低质量事件；日报模式每侧最多 6 条，完整报告只有 1 条就输出 1 条，超过 6 条只输出优先级最高的 6 条。
6. core_judgments 最多 3 条，watch_signals 最多 3 条。
7. title / why / core_judgments.full / watch_signals.full 保留相对完整表达；飞书卡片只使用 card_title / card_why / card 字段。
8. card_title 不超过 28 字；card_why 不超过 60 字；core_judgments.card / watch_signals.card 不超过 56 字。
9. 所有 card 字段必须是完整短句，不要靠省略号，不要输出半截词。
10. priority 只使用 P1 / P2 / 观察，不引入 P3。
11. 如果没有国内或海外核心事件，写“今日无强核心事件，不强行凑数。”
12. 每条 domestic_top / overseas_top item 只输出 source_ids，不要输出 sources，不要输出 URL。
13. source_ids 必须来自下面 evidence catalog 的 id，每条最多 2 个；如果无法匹配，source_ids=[]。
14. source_ids 优先选择最直接证明该事件的来源：官方源优先，其次权威媒体，再其次第三方数据源；不要优先使用聚合页、搜索结果页或无关背景页。
15. domestic_top 条数必须等于 domestic_core_events 条数；overseas_top 条数必须等于 overseas_core_events 条数；不要只挑前三条，每侧最多 6 条。

必须使用这个 schema：
{{
  "date": "{window.date_str}",
  "title": "AI Radar｜{window.date_str}",
  "domestic_top": [{{"title": "完整标题", "card_title": "不超过28字卡片标题", "why": "相对完整解释", "card_why": "不超过60字卡片短句", "priority": "P1/P2/观察", "source_ids": ["E1", "E2"]}}],
  "overseas_top": [{{"title": "完整标题", "card_title": "不超过28字卡片标题", "why": "相对完整解释", "card_why": "不超过60字卡片短句", "priority": "P1/P2/观察", "source_ids": ["E3"]}}],
  "core_judgments": [{{"full": "完整判断", "card": "不超过56字卡片短句"}}],
  "watch_signals": [{{"full": "完整观察", "card": "不超过56字卡片短句"}}]
}}

Evidence catalog，必须只从这里选择 source_ids，不要复制 URL：
{catalog_text[:12000]}

正式核心事件清单，brief 条数必须与这里一致：
{core_events_text[:12000]}

完整日报：
{report_md[:20000]}
""".strip()

    @staticmethod
    def _repair_prompt(raw_response: str, parse_error: str) -> str:
        return f"""
请把下面内容修复成合法 JSON object。

要求：
1. 只修 JSON，不要重新生成事实。
2. 只输出 JSON，不要 Markdown code fence。
3. 保留 domestic_top / overseas_top / core_judgments / watch_signals。
4. Top item 使用 source_ids 数组，不要输出 URL。

解析错误：
{parse_error[:500]}

原始响应：
{raw_response[:6000]}
""".strip()

    @staticmethod
    def _count_repair_prompt(raw_response: str, core_events: dict[str, list[dict[str, Any]]], catalog: list[dict[str, str]]) -> str:
        return f"""
上一次 brief JSON 的 domestic_top / overseas_top 条数少于完整日报正式核心事件清单。

请只输出修复后的 JSON object，不要 Markdown code fence。

要求：
1. domestic_top 必须为 domestic_core_events 中每个事件各生成 1 条，每侧最多 6 条。
2. overseas_top 必须为 overseas_core_events 中每个事件各生成 1 条，每侧最多 6 条。
3. 不要只挑前三条，不要删除事件。
4. 每条 item 包含 title、why、priority、source_ids。
5. source_ids 只能来自 evidence catalog，每条最多 2 个；无法匹配则 []。

正式核心事件清单：
{json.dumps(core_events, ensure_ascii=False, indent=2)[:12000]}

Evidence catalog：
{json.dumps(catalog, ensure_ascii=False, indent=2)[:12000]}

上一次输出：
{raw_response[:6000]}
""".strip()

    @staticmethod
    def _core_extractor_prompt(report_md: str, core_events: dict[str, Any]) -> str:
        return f"""
请只从完整日报的“正式雷达”section 提取正式核心事件。

要求：
1. 不要从候选事件筛选表提取。
2. 不要从观察信号提取。
3. 如果正式雷达明确写无强核心事件，则输出空列表。
4. 不得编造报告中不存在的事件。
5. 只输出 JSON object，不要 Markdown code fence。

输出 schema：
{{
  "domestic_core_events": [
    {{"title": "...", "priority": "P1/P2/观察", "evidence_hint": "...", "source_urls": []}}
  ],
  "overseas_core_events": []
}}

当前 deterministic extraction metadata：
{json.dumps(_core_event_metadata(core_events), ensure_ascii=False, indent=2)[:4000]}

完整日报：
{report_md[:20000]}
""".strip()


def _allowed_source_urls(report_md: str, evidence: list[EvidenceItem]) -> set[str]:
    urls = {_normalize_url(item.url) for item in evidence if item.url}
    urls.update(_normalize_url(url) for url in URL_RE.findall(report_md or ""))
    return {url for url in urls if url}


def _extract_region_core_events(report_md: str, region: str) -> dict[str, Any]:
    info = _extract_radar_section_info(report_md, region)
    raw_events, method = _extract_core_events_from_section_with_method(info["section"])
    events, raw_count, truncated = _cap_events(raw_events)
    raw_zero_core_explicit = _zero_core_explicit(info["section"])
    zero_core_conflict_resolved = "events_found" if raw_zero_core_explicit and events else ""
    zero_core_explicit = bool(raw_zero_core_explicit and not events)
    extraction_suspect = bool(info["section_found"] and not zero_core_explicit and not events)
    if zero_core_explicit and not events:
        method = "none"
    return {
        "events": events,
        "raw_count": raw_count,
        "capped_count": len(events),
        "truncated": truncated,
        "section_found": info["section_found"],
        "zero_core_explicit": zero_core_explicit,
        "zero_core_conflict_resolved": zero_core_conflict_resolved,
        "extraction_suspect": extraction_suspect,
        "extraction_method": method,
        "titles_sample": [event["title"] for event in events[:5]],
        "section": info["section"],
    }


def _cap_events(events: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int, bool]:
    ranked = sort_top_items(events)
    raw_count = len(ranked)
    return ranked[:MAX_TOP_EVENTS_PER_REGION], raw_count, raw_count > MAX_TOP_EVENTS_PER_REGION


def _cap_ranked_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    p2_count = 0
    for item in sort_top_items(items):
        if len(output) >= MAX_TOP_EVENTS_PER_REGION:
            break
        if _priority_rank(item.get("priority")) == 1:
            if p2_count >= MAX_P2_TOP_EVENTS_PER_REGION:
                continue
            p2_count += 1
        output.append(item)
    return output


def _expected_final_top_count(core_events: list[dict[str, Any]]) -> int:
    if not core_events:
        return 0
    return len(_cap_ranked_items(core_events))


def _core_extraction_needs_fallback(core_events: dict[str, Any]) -> bool:
    return any(bool(core_events.get(f"{region}_extraction_suspect")) for region in ("domestic", "overseas"))


def _mark_core_fallback_failed(core_events: dict[str, Any]) -> dict[str, Any]:
    updated = dict(core_events)
    for region in ("domestic", "overseas"):
        if updated.get(f"{region}_extraction_suspect"):
            updated[f"{region}_extraction_method"] = "llm_fallback_failed"
    return updated


def _normalize_llm_core_events(items: Any) -> list[dict[str, Any]]:
    output = []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        title = _clean_event_title(str(item.get("title") or ""))
        if not title or _is_no_core_text(title):
            continue
        raw_block = str(item.get("raw_block") or item.get("evidence_hint") or title)
        source_urls = [str(url) for url in item.get("source_urls") or [] if str(url or "").startswith("http")]
        if not source_urls:
            source_urls = URL_RE.findall(raw_block)
        output.append(
            {
                "title": title,
                "priority": _priority_from_text(str(item.get("priority") or raw_block)),
                "level": _level_from_text(str(item.get("level") or raw_block)),
                "raw_block": raw_block,
                "source_urls": source_urls,
            }
        )
    return output


def _core_event_metadata(core_events: dict[str, Any]) -> dict[str, Any]:
    return {
        key: core_events.get(key)
        for key in (
            "domestic_section_found",
            "overseas_section_found",
            "domestic_zero_core_explicit",
            "overseas_zero_core_explicit",
            "domestic_extraction_suspect",
            "overseas_extraction_suspect",
            "domestic_extraction_method",
            "overseas_extraction_method",
        )
    }


def _extract_radar_section(report_md: str, region: str) -> str:
    return str(_extract_radar_section_info(report_md, region)["section"])


def _extract_radar_section_info(report_md: str, region: str) -> dict[str, Any]:
    starts = {
        "domestic": (
            "AI 前沿能力与应用雷达 - 国内版",
            "AI 前沿能力与应用雷达-国内版",
            "AI前沿能力与应用雷达-国内版",
            "国内版正式雷达",
            "国内 AI 前沿能力与应用雷达",
            "国内 AI 雷达",
            "国内正式雷达",
            "国内核心事件",
            "国内版",
        ),
        "overseas": (
            "AI 前沿能力与应用雷达 - 海外版",
            "AI 前沿能力与应用雷达-海外版",
            "AI前沿能力与应用雷达-海外版",
            "海外版正式雷达",
            "海外 AI 前沿能力与应用雷达",
            "海外 AI 雷达",
            "海外正式雷达",
            "海外核心事件",
            "海外版",
        ),
    }[region]
    stop_markers = (
        "国内候选事件筛选表",
        "海外候选事件筛选表",
        "输出前自我检查清单",
        "输出前自检",
        "附录",
        "来源索引",
    )
    lines = report_md.splitlines()
    start_idx = None
    start_level = 0
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("#") and _heading_matches_formal_radar(stripped, starts, region):
            start_idx = idx + 1
            start_level = len(stripped) - len(stripped.lstrip("#"))
            break
    if start_idx is None:
        return {"section": "", "section_found": False}
    end_idx = len(lines)
    for idx in range(start_idx, len(lines)):
        stripped = lines[idx].strip()
        if not stripped.startswith("#"):
            continue
        level = len(stripped) - len(stripped.lstrip("#"))
        if any(marker in stripped for marker in ("今日总览", "逐条深度解读")):
            continue
        if level <= start_level or any(marker in stripped for marker in stop_markers):
            end_idx = idx
            break
    return {"section": "\n".join(lines[start_idx:end_idx]).strip(), "section_found": True}


def _heading_matches_formal_radar(heading: str, markers: tuple[str, ...], region: str) -> bool:
    text = re.sub(r"^#{1,6}\s*", "", heading).strip()
    normalized = re.sub(r"\s+", "", text)
    if any(re.sub(r"\s+", "", marker) in normalized for marker in markers):
        if "候选" in text or "筛选" in text:
            return False
        return True
    if region == "domestic" and re.search(r"国内版【\d{4}年\d{1,2}月\d{1,2}日】", text):
        return True
    if region == "overseas" and re.search(r"海外版【\d{4}年\d{1,2}月\d{1,2}日】", text):
        return True
    return False


def _extract_core_events_from_section(section: str) -> list[dict[str, Any]]:
    events, _method = _extract_core_events_from_section_with_method(section)
    return events


def _extract_core_events_from_section_with_method(section: str) -> tuple[list[dict[str, Any]], str]:
    if not section:
        return [], "none"
    table_events = _extract_events_from_overview_table(section)
    if table_events:
        return _merge_table_events_with_deep_dive(table_events, _extract_events_from_deep_dive(section)), "table"
    deep_dive_events = _extract_events_from_deep_dive(section)
    if deep_dive_events:
        return deep_dive_events, "deep_dive"
    return [], "none"


def _merge_table_events_with_deep_dive(
    table_events: list[dict[str, Any]],
    deep_dive_events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not deep_dive_events:
        return table_events
    output = []
    used_deep: set[int] = set()
    for event in table_events:
        best_idx = None
        best_score = 0.0
        for idx, candidate in enumerate(deep_dive_events):
            if idx in used_deep:
                continue
            score = _match_score(str(event.get("title") or ""), str(candidate.get("title") or ""))
            if score > best_score:
                best_idx = idx
                best_score = score
        if best_idx is not None and best_score >= 0.18:
            used_deep.add(best_idx)
            deep_event = deep_dive_events[best_idx]
            merged = dict(event)
            merged["raw_block"] = deep_event.get("raw_block") or event.get("raw_block", "")
            merged["source_urls"] = deep_event.get("source_urls") or event.get("source_urls", [])
            if not merged.get("level"):
                merged["level"] = deep_event.get("level", "")
            output.append(merged)
        else:
            output.append(event)
    return output


def _extract_events_from_overview_table(section: str) -> list[dict[str, Any]]:
    lines = section.splitlines()
    events: list[dict[str, Any]] = []
    for idx, line in enumerate(lines):
        if "今日总览" not in line:
            continue
        table_lines = []
        for table_line in lines[idx + 1 :]:
            stripped = table_line.strip()
            if not stripped:
                if table_lines:
                    break
                continue
            if not stripped.startswith("|"):
                if table_lines:
                    break
                continue
            table_lines.append(stripped)
        events = _parse_markdown_table_events(table_lines)
        if events:
            return events
    return _parse_markdown_table_events([line.strip() for line in lines if line.strip().startswith("|")])


def _parse_markdown_table_events(table_lines: list[str]) -> list[dict[str, Any]]:
    rows = [_split_table_row(line) for line in table_lines if "|" in line]
    rows = [row for row in rows if row and not all(re.fullmatch(r":?-{2,}:?", cell.strip()) for cell in row)]
    if len(rows) < 2:
        return []
    header = rows[0]
    title_idx = _find_col(header, ("事件", "标题", "核心事件", "事项"))
    priority_idx = _find_col(header, ("优先级", "priority", "级别"))
    level_idx = _find_col(header, ("level", "层级", "等级"))
    if title_idx is None:
        title_idx = 0
    events = []
    for row in rows[1:]:
        if title_idx >= len(row):
            continue
        title = _clean_event_title(row[title_idx])
        if not title or _is_no_core_text(title):
            continue
        raw = " | ".join(row)
        events.append(
            {
                "title": title,
                "priority": _priority_from_text(row[priority_idx] if priority_idx is not None and priority_idx < len(row) else raw),
                "level": _level_from_text(row[level_idx] if level_idx is not None and level_idx < len(row) else raw),
                "raw_block": raw,
                "source_urls": URL_RE.findall(raw),
            }
        )
    return events


def _extract_events_from_deep_dive(section: str) -> list[dict[str, Any]]:
    lines = section.splitlines()
    start = None
    for idx, line in enumerate(lines):
        if "逐条深度解读" in line:
            start = idx + 1
            break
    if start is None:
        return []
    events = []
    current: dict[str, Any] | None = None
    for line in lines[start:]:
        stripped = line.strip()
        if not stripped:
            if current:
                current["raw_block"] = f"{current['raw_block']}\n"
            continue
        if any(marker in stripped for marker in ("观察信号", "自我检查", "附录", "来源索引")) and stripped.startswith("#"):
            break
        title = _deep_dive_title(stripped)
        if title:
            if current:
                current["source_urls"] = URL_RE.findall(current["raw_block"])
                events.append(current)
            current = {
                "title": title,
                "priority": _priority_from_text(stripped),
                "level": _level_from_text(stripped),
                "raw_block": stripped,
                "source_urls": URL_RE.findall(stripped),
            }
        elif current:
            current["raw_block"] = f"{current['raw_block']}\n{line}"
            if current["priority"] == "观察":
                current["priority"] = _priority_from_text(line)
            if not current["level"]:
                current["level"] = _level_from_text(line)
    if current:
        current["source_urls"] = URL_RE.findall(current["raw_block"])
        events.append(current)
    return [event for event in events if not _is_placeholder_core_event(event)]


def _split_table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _find_col(header: list[str], names: tuple[str, ...]) -> int | None:
    for idx, cell in enumerate(header):
        lowered = cell.lower()
        if any(name.lower() in lowered for name in names):
            return idx
    return None


def _deep_dive_title(line: str) -> str:
    text = re.sub(r"^#{1,6}\s*", "", line).strip()
    if re.match(r"^[-*]\s+", text):
        return ""
    blocked_heading_markers = ("今日总览", "逐条", "核心解读", "核心判断", "观察信号", "自我检查", "输出前")
    if re.match(r"^[一二三四五六七八九十]+[、.．]\s*", text) and any(marker in text for marker in blocked_heading_markers):
        return ""
    bold = re.match(r"^\*\*(?:标题[:：])?(.+?)\*\*\s*[:：]?", text)
    if bold:
        title = bold.group(1)
    else:
        label = re.match(r"^(?:标题|事件)[:：]\s*(.+)$", text)
        if label:
            title = label.group(1)
        else:
            numbered = re.match(r"^(?:\d+[\.\、\)]|[-*]\s*)\s*(.+)$", text)
            if numbered:
                title = numbered.group(1)
            elif line.lstrip().startswith("#") and not any(marker in text for marker in blocked_heading_markers):
                title = text
            else:
                return ""
    title = re.split(r"\s*[｜|]\s*|\s+-\s+|\s+—\s+|[:：]", title, maxsplit=1)[0]
    return _clean_event_title(title)


def _is_placeholder_core_event(event: dict[str, Any]) -> bool:
    title = str(event.get("title") or "").strip()
    raw_block = str(event.get("raw_block") or "")
    if not title or _is_no_core_text(title):
        return True
    if title in {"说明", "结论", "备注", "提示"} and _is_no_core_text(raw_block):
        return True
    return False


def _clean_event_title(value: str) -> str:
    text = re.sub(r"\[[^\]]+\]\(([^)]+)\)", "", str(value or "")).strip()
    text = re.sub(r"<[^>]+>", "", text)
    text = text.strip("*` _")
    return _limit_text(text, 80)


def _is_no_core_text(value: str) -> bool:
    text = str(value or "").strip()
    if text in {"—", "-", "–", "--", "无", "无。", "N/A", "n/a", "NA", "na", "None", "none"}:
        return True
    compact = re.sub(r"\s+", "", text)
    if (
        re.search(r"无(国内|海外)?强?核心事件", compact)
        or re.search(r"(国内|海外)无强?核心事件", compact)
        or re.search(r"无.{0,12}(国内|海外)?.{0,6}核心事件", compact)
        or re.search(r"未发现.{0,20}(国内|海外)?.{0,8}核心事件", compact)
        or re.search(r"未出现.{0,20}(结构性|入选|核心).{0,8}事件", compact)
        or re.search(r"(本日|今日|当日).{0,6}无.{0,8}事件.{0,8}入选.{0,8}(深度解读|正式雷达|最终Top|最终top)?", compact)
        or re.search(r"无.{0,8}事件.{0,8}入选.{0,8}(深度解读|正式雷达|最终Top|最终top)", compact)
        or re.search(r"(本日|今日|当日).{0,6}无.{0,8}(重大|核心|结构性).{0,8}事件", compact)
        or re.search(r"无.{0,16}核心.{0,8}事件", compact)
        or re.search(r"无.{0,8}重大.{0,8}事件", compact)
        or re.search(r"无.{0,20}(结构性|入选标准|符合条件).{0,8}事件", compact)
    ):
        return True
    return any(
        marker in text
        for marker in (
            "无强核心事件",
            "不强行凑数",
            "未出现符合筛选标准的结构性事件",
            "本日无重大事件",
            "今日无重大事件",
            "当日无重大事件",
            "无符合入选标准",
            "无符合条件",
            "无。",
            "无足够证据",
            "无 P1/P2",
            "无P1/P2",
            "本日无入选核心事件",
            "本日无事件入选",
            "今日无事件入选",
            "当日无事件入选",
            "详见完整日报",
        )
    )


def _is_empty_placeholder_item(item: dict[str, Any]) -> bool:
    title = str(item.get("title") or "")
    card_title = str(item.get("card_title") or "")
    why = str(item.get("why") or "")
    card_why = str(item.get("card_why") or "")
    return _is_no_core_text(title) or _is_no_core_text(card_title) or (
        title.strip() in {"—", "-", "–", "--"} and ("详见完整日报" in why or "详见完整日报" in card_why)
    ) or ("无强核心事件" in title and "不强行凑数" in why)


def _force_empty_top(core_events: dict[str, Any], region: str) -> bool:
    return bool(
        not core_events.get(f"{region}_core_events")
        and (core_events.get(f"{region}_zero_core_explicit") or core_events.get(f"{region}_extraction_suspect"))
    )


def _empty_reason(core_events: dict[str, Any], region: str, events: list[dict[str, Any]]) -> str:
    if events:
        return ""
    if core_events.get(f"{region}_zero_core_explicit"):
        return "zero_core_explicit"
    if core_events.get(f"{region}_extraction_suspect"):
        return "extraction_suspect_unresolved"
    if not core_events.get(f"{region}_section_found"):
        return "section_not_found"
    return ""


def _zero_core_explicit(section: str) -> bool:
    return _is_no_core_text(section)


def _priority_from_text(value: str) -> str:
    rank = _priority_rank(value)
    if rank == 0:
        return "P1"
    if rank == 1:
        return "P2"
    return "观察"


def _level_from_text(value: str) -> str:
    match = re.search(r"\bL\d+\b", str(value or ""), flags=re.IGNORECASE)
    return match.group(0).upper() if match else ""


def _evidence_records(evidence: list[EvidenceItem]) -> list[dict[str, str]]:
    records = []
    for idx, item in enumerate(evidence, start=1):
        evidence_id = _normalize_source_id(getattr(item, "id", "")) or f"E{idx}"
        raw_source = str(item.source or getattr(item, "source_name", "") or "").strip()
        source_name = _clean_source_label(raw_source, item.url, provider=item.source_type or "") or _domain(item.url)
        records.append(
            {
                "id": evidence_id,
                "title": _limit_text(item.title, 120),
                "source": _limit_text(source_name, 60),
                "url": item.url,
                "summary": _limit_text(item.content, 300),
                "region_hint": item.region_hint,
                "basket": item.source_basket,
                "source_type": item.source_type,
                "source_tier": item.source_tier,
                "source_fit": item.source_fit,
                "is_primary_source": "true" if item.is_primary_source else "false",
                "not_core_eligible": "true" if item.not_core_eligible else "false",
            }
        )
    return records


def _evidence_catalog(report_md: str, evidence: list[EvidenceItem], *, max_items: int = 40) -> list[dict[str, str]]:
    records = _evidence_records(evidence)
    report_text = report_md.lower()

    def score(record: dict[str, str]) -> tuple[int, int]:
        direct = int(bool(record["url"] and record["url"] in report_md) or bool(record["title"] and record["title"].lower() in report_text))
        authority = int(record["source_type"] in {"rss", "official"} or any(
            key in record["source"].lower() for key in ("openai", "google", "anthropic", "microsoft", "techcrunch", "the verge")
        ))
        return (direct, authority)

    indexed = list(enumerate(records))
    indexed.sort(key=lambda row: (*score(row[1]), -row[0]), reverse=True)
    return [
        {
            "id": record["id"],
            "title": record["title"],
            "source": record["source"],
            "url": record["url"],
            "summary": record["summary"],
            "region_hint": record["region_hint"],
            "basket": record["basket"],
        }
        for _idx, record in indexed[:max_items]
        if record["url"]
    ]


def _evidence_map(records: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    evidence_by_id: dict[str, dict[str, str]] = {}
    for idx, record in enumerate(records, start=1):
        for raw_id in (record.get("id"), f"E{idx}", str(idx), f"[{idx}]"):
            normalized_id = _normalize_source_id(raw_id)
            if normalized_id and normalized_id not in evidence_by_id:
                evidence_by_id[normalized_id] = record
    return evidence_by_id


def _normalize_source_id(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    text = text.strip("[](){}")
    text = re.sub(r"\s+", "", text)
    match = re.fullmatch(r"(?i)e?0*(\d+)", text)
    if not match:
        return ""
    return f"E{int(match.group(1))}"


def _source_id_values(source_ids: Any) -> list[str]:
    if not isinstance(source_ids, list):
        return []
    return [str(source_id or "").strip() for source_id in source_ids if str(source_id or "").strip()]


def _sources_from_ids(
    source_ids: list[str],
    evidence_by_id: dict[str, dict[str, str]],
    warnings: list[str],
) -> tuple[list[dict[str, str]], int, list[str]]:
    output: list[dict[str, str]] = []
    resolved_count = 0
    unresolved_ids: list[str] = []
    for raw_id in source_ids:
        evidence_id = _normalize_source_id(raw_id)
        if not evidence_id:
            unresolved_ids.append(raw_id)
            warnings.append(f"invalid source_id dropped: {raw_id}")
            continue
        record = evidence_by_id.get(evidence_id)
        if not record or not record.get("url"):
            unresolved_ids.append(raw_id)
            warnings.append(f"invalid source_id dropped: {raw_id}")
            continue
        resolved_count += 1
        if len(output) < 2:
            source = _source_from_record(record)
            if source:
                output.append(source)
    return output, resolved_count, unresolved_ids


def _source_from_record(record: dict[str, str]) -> dict[str, str] | None:
    url = str(record.get("url") or "")
    label = _clean_source_label(record.get("source"), url, provider=record.get("source_type"))
    if not label or _is_disallowed_source_url(url):
        return None
    return {
        "title": _limit_text(record.get("title"), 24),
        "url": url,
        "source": label,
        "evidence_id": str(record.get("id") or ""),
    }


def _normalize_sources(items: Any, allowed_urls: set[str], warnings: list[str] | None = None) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "").strip()
        normalized_url = _normalize_url(url)
        if not normalized_url or normalized_url not in allowed_urls:
            logger.warning("Dropping brief source URL not found in evidence/report: %s", url[:200])
            if warnings is not None:
                warnings.append(f"dropped source URL not found in evidence/report: {url[:200]}")
            continue
        label = _clean_source_label(
            item.get("source") or item.get("source_name") or item.get("title"),
            url,
            provider=item.get("provider") or item.get("source_type"),
        )
        if not label:
            continue
        output.append({"title": _limit_text(item.get("title"), 24), "url": url, "source": label, "evidence_id": _limit_text(item.get("evidence_id"), 80)})
        if len(output) == 2:
            break
    return output


def _filter_sources_for_item(
    item: dict[str, Any],
    sources: list[dict[str, str]],
    records: list[dict[str, str]],
    warnings: list[str],
) -> list[dict[str, str]]:
    if not sources:
        return []
    query = _source_query_for_item(item)
    if not _source_query_is_specific(query) and not _source_title_query_is_specific(item):
        return sources[:2]
    required_entities = _source_required_entity_tokens(item)
    allow_low_confidence_fill = not _event_specific_source_tokens(_match_tokens(query) - _WEAK_SOURCE_TOKENS)
    output: list[dict[str, str]] = []
    low_confidence_sources: list[dict[str, str]] = []
    for source in sources:
        record = _record_for_source(source, records)
        if _is_core_priority(item.get("priority")) and record and _record_not_core_eligible(record):
            warnings.append(f"dropped not-core-eligible source binding: {source.get('evidence_id') or source.get('url', '')}")
            continue
        if record:
            record_text = _record_match_text(record)
            title_score = _source_title_relevance_score(item, record_text)
            score = title_score if title_score is not None else _source_relevance_score(query, record_text, required_entities=required_entities)
        else:
            source_text = f"{source.get('title', '')} {source.get('source', '')} {source.get('url', '')}"
            title_score = _source_title_relevance_score(item, source_text)
            score = title_score if title_score is not None else _source_relevance_score(
                query,
                source_text,
                required_entities=required_entities,
            )
        if score < 0.2:
            warnings.append(f"dropped low-confidence source binding: {source.get('evidence_id') or source.get('url', '')}")
            low_confidence_sources.append(source)
            continue
        output.append(source)
        if len(output) == 2:
            break
    if allow_low_confidence_fill and output:
        for source in low_confidence_sources:
            if len(output) == 2:
                break
            output.append(source)
    return output


def _filter_top_items_by_source_quality(
    items: list[dict[str, Any]],
    records: list[dict[str, str]],
    warnings: list[str],
) -> tuple[list[dict[str, Any]], list[str], list[dict[str, Any]]]:
    output: list[dict[str, Any]] = []
    dropped: list[str] = []
    dropped_items: list[dict[str, Any]] = []
    for item in items:
        title = str(item.get("title") or "").strip()
        if not _is_core_priority(item.get("priority")):
            output.append(item)
            continue
        quality_state = _top_item_source_quality_state(item, records)
        if quality_state == "accepted" or quality_state == "unknown":
            output.append(item)
            continue
        dropped.append(title)
        dropped_items.append(item)
        warnings.append(f"dropped top event without S1/S2/S3 source: {title}")
    return output, dropped, dropped_items


def _demote_dropped_top_items_to_watch_signals(
    watch_signals: list[str],
    watch_cards: list[str],
    dropped_items: list[dict[str, Any]],
    final_top: list[dict[str, Any]],
) -> tuple[list[str], list[str], list[str]]:
    if not dropped_items or len(watch_signals) >= 3:
        return watch_signals, watch_cards, []
    output_signals = list(watch_signals)
    output_cards = list(watch_cards)
    demoted_examples: list[str] = []
    final_titles = [
        str(item.get("title") or item.get("card_title") or "").strip()
        for item in final_top
        if isinstance(item, dict) and str(item.get("title") or item.get("card_title") or "").strip()
    ]
    combined_existing = " ".join(output_signals + output_cards)
    for item in dropped_items:
        if len(output_signals) >= 3:
            break
        title = str(item.get("title") or item.get("card_title") or "").strip()
        if not title:
            continue
        if final_titles and _mentions_same_event_title(title, final_titles):
            continue
        if combined_existing and _mentions_any_title(combined_existing, [title]):
            continue
        why = _clean_brief_why_value(item.get("card_why") or item.get("why"), title)
        if why:
            full = f"【观察】{title}：{why}；来源未达核心事件标准，待 S1/S2/S3 强源确认。"
        else:
            full = f"【观察】{title}：来源未达核心事件标准，待 S1/S2/S3 强源确认。"
        card = f"{title}待强源确认。"
        output_signals.append(_limit_text(full, BRIEF_BULLET_MAX_CHARS))
        output_cards.append(_limit_text(card, 120))
        demoted_examples.append(title)
        combined_existing = f"{combined_existing} {full} {card}"
    return output_signals, output_cards, demoted_examples


def _mentions_same_event_title(title: str, candidate_titles: list[str]) -> bool:
    return any(
        _mentions_dropped_title(title, candidate_title) or _mentions_dropped_title(candidate_title, title)
        for candidate_title in candidate_titles
    )


def _reassign_top_items_by_subject_region(
    domestic_top: list[dict[str, Any]],
    overseas_top: list[dict[str, Any]],
    warnings: list[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    domestic_output: list[dict[str, Any]] = []
    overseas_output: list[dict[str, Any]] = []
    reassigned: list[str] = []
    for item in domestic_top:
        region = _subject_region_for_item(item)
        if region == "overseas":
            overseas_output.append(item)
            title = str(item.get("title") or "").strip()
            reassigned.append(f"{title} -> overseas")
            warnings.append(f"reassigned top event region by subject: {title} -> overseas")
        else:
            domestic_output.append(item)
    for item in overseas_top:
        region = _subject_region_for_item(item)
        if region == "domestic":
            domestic_output.append(item)
            title = str(item.get("title") or "").strip()
            reassigned.append(f"{title} -> domestic")
            warnings.append(f"reassigned top event region by subject: {title} -> domestic")
        else:
            overseas_output.append(item)
    return sort_top_items(domestic_output), sort_top_items(overseas_output), reassigned


def _subject_region_for_item(item: dict[str, Any]) -> str:
    title_text = " ".join(
        str(item.get(key) or "")
        for key in ("title", "card_title")
        if str(item.get(key) or "").strip()
    )
    body_text = " ".join(
        str(item.get(key) or "")
        for key in ("why", "card_why")
        if str(item.get(key) or "").strip()
    )
    source_title_text = " ".join(
        str(source.get("title") or "")
        for source in item.get("sources", [])
        if isinstance(source, dict) and str(source.get("title") or "").strip()
    )
    text = " ".join(value for value in (title_text, body_text, source_title_text) if value)
    domestic_idx = _first_subject_match(text, _DOMESTIC_SUBJECT_TOKENS)
    overseas_idx = _first_subject_match(text, _OVERSEAS_SUBJECT_TOKENS)
    if domestic_idx is None and overseas_idx is None:
        return ""
    if domestic_idx is None:
        return "overseas"
    if overseas_idx is None:
        return "domestic"
    return "domestic" if domestic_idx <= overseas_idx else "overseas"


def _first_subject_match(text: str, tokens: tuple[str, ...]) -> int | None:
    haystack = str(text or "")
    lower = haystack.lower()
    indexes: list[int] = []
    for token in tokens:
        needle = token.lower()
        if re.fullmatch(r"[a-z0-9_.+-]+", needle):
            match = re.search(rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])", lower)
            if match:
                indexes.append(match.start())
            continue
        idx = haystack.find(token)
        if idx >= 0:
            indexes.append(idx)
    return min(indexes) if indexes else None


def _top_item_source_quality_state(item: dict[str, Any], records: list[dict[str, str]]) -> str:
    if not records:
        return "unknown"
    sources = item.get("sources")
    if not isinstance(sources, list) or not sources:
        return "rejected"
    matched_records = []
    for source in sources:
        if not isinstance(source, dict):
            continue
        record = _record_for_source(source, records)
        if record:
            matched_records.append(record)
    if not matched_records:
        return "rejected"
    eligible_records = [
        record
        for record in matched_records
        if not _record_not_core_eligible(record) and str(record.get("source_tier") or "").upper() in TOP_SOURCE_TIERS
    ]
    if eligible_records:
        return "accepted"
    tiers = {str(record.get("source_tier") or "").upper() for record in matched_records if str(record.get("source_tier") or "").strip()}
    return "rejected" if tiers else "unknown"


def _drop_bullets_mentioning_titles(
    bullets: list[str],
    cards: list[str],
    dropped_titles: list[str],
) -> tuple[list[str], list[str]]:
    if not bullets or not dropped_titles:
        return bullets, cards
    kept_bullets: list[str] = []
    kept_cards: list[str] = []
    for idx, bullet in enumerate(bullets):
        card = cards[idx] if idx < len(cards) else bullet
        combined = f"{bullet} {card}"
        if _mentions_any_dropped_title(combined, dropped_titles):
            continue
        kept_bullets.append(bullet)
        kept_cards.append(card)
    return kept_bullets, kept_cards


def _mentions_any_dropped_title(text: str, titles: list[str]) -> bool:
    return any(_mentions_dropped_title(text, title) for title in titles)


def _mentions_dropped_title(text: str, title: str) -> bool:
    text_tokens = _match_tokens(text)
    normalized_text = _compact_title_text(text)
    title_tokens = _event_specific_source_tokens(_match_tokens(title) - _WEAK_SOURCE_TOKENS)
    if not title_tokens:
        return False
    title_entity_tokens = title_tokens & _source_entity_tokens()
    distinctive_tokens = title_tokens - _BROAD_ENTITY_SOURCE_TOKENS
    distinctive_overlap = distinctive_tokens & text_tokens
    if any(len(token) >= 4 and not re.search(r"[a-z0-9]", token) for token in distinctive_overlap):
        return True
    if title_entity_tokens and distinctive_overlap:
        return True
    if len(distinctive_overlap) >= 2:
        return True
    normalized_title = _compact_title_text(title)
    if normalized_title and len(normalized_title) >= 5 and normalized_title in normalized_text:
        return True
    if _has_compact_cjk_phrase_overlap(normalized_text, normalized_title):
        return True
    return False


def _mentions_any_title(text: str, titles: list[str]) -> bool:
    text_tokens = _match_tokens(text)
    normalized_text = _compact_title_text(text)
    for title in titles:
        title_tokens = _event_specific_source_tokens(_match_tokens(title) - _WEAK_SOURCE_TOKENS)
        strong_tokens = {token for token in title_tokens if len(token) >= 3 or re.search(r"[a-z0-9]", token)}
        if not strong_tokens:
            strong_tokens = title_tokens
        overlap = strong_tokens & text_tokens
        if any(re.search(r"[a-z0-9]", token) for token in overlap):
            return True
        if len(overlap) >= 2:
            return True
        normalized_title = _compact_title_text(title)
        if normalized_title and len(normalized_title) >= 5 and normalized_title in normalized_text:
            return True
        if _has_compact_cjk_phrase_overlap(normalized_text, normalized_title):
            return True
    return False


def _compact_title_text(value: str) -> str:
    return re.sub(r"[\s\-_—:：|｜，,。.!！?？（）()【】\\[\\]\"'“”‘’]+", "", str(value or "").lower())


def _has_compact_cjk_phrase_overlap(normalized_text: str, normalized_title: str) -> bool:
    if not normalized_text or not normalized_title:
        return False
    for chunk in re.findall(r"[\u4e00-\u9fff]{4,}", normalized_title):
        max_size = min(8, len(chunk))
        for size in range(max_size, 3, -1):
            for idx in range(0, len(chunk) - size + 1):
                phrase = chunk[idx : idx + size]
                if phrase in normalized_text:
                    return True
    return False


def _core_judgments_from_final_top(domestic_top: list[dict[str, Any]], overseas_top: list[dict[str, Any]]) -> list[str]:
    judgments: list[str] = []
    for item in (domestic_top + overseas_top)[:3]:
        title = _limit_text(item.get("title") or item.get("card_title"), 80)
        why = _limit_brief_why(item.get("why") or item.get("card_why"))
        if title and why:
            judgments.append(_limit_text(f"{title}：{why}", BRIEF_BULLET_MAX_CHARS))
        elif title:
            judgments.append(f"{title}进入最终 Top。")
    return judgments


def _has_truncated_bullet(items: list[str]) -> bool:
    return any("…" in str(item or "") for item in items)


def _filter_core_judgments_to_final_top(
    bullets: list[str],
    cards: list[str],
    domestic_top: list[dict[str, Any]],
    overseas_top: list[dict[str, Any]],
) -> tuple[list[str], list[str], int]:
    final_top = domestic_top + overseas_top
    if not bullets or not final_top:
        return bullets, cards, 0

    final_titles = [str(item.get("title") or item.get("card_title") or "") for item in final_top]
    final_titles = [title for title in final_titles if title.strip()]
    if not final_titles:
        return bullets, cards, 0

    kept_bullets: list[str] = []
    kept_cards: list[str] = []
    dropped_count = 0
    for idx, bullet in enumerate(bullets):
        card = cards[idx] if idx < len(cards) else bullet
        combined = f"{bullet} {card}"
        if _mentions_any_title(combined, final_titles):
            kept_bullets.append(bullet)
            kept_cards.append(card)
            continue
        dropped_count += 1

    if not dropped_count:
        return bullets, cards, 0

    combined_kept = " ".join(kept_bullets + kept_cards)
    for fallback in _core_judgments_from_final_top(domestic_top, overseas_top):
        if len(kept_bullets) >= 3:
            break
        if fallback in kept_bullets or _mentions_any_title(combined_kept, [fallback]):
            continue
        kept_bullets.append(fallback)
        kept_cards.append(fallback)
        combined_kept = f"{combined_kept} {fallback}"
    return kept_bullets[:3], kept_cards[:3], dropped_count


def _core_judgment_entity_tokens(text: str) -> set[str]:
    return _match_tokens(text) & _source_entity_tokens()


def _is_core_priority(value: Any) -> bool:
    return _priority_rank(value) in {0, 1}


def _record_for_source(source: dict[str, str], records: list[dict[str, str]]) -> dict[str, str] | None:
    evidence_id = _normalize_source_id(source.get("evidence_id"))
    url = _normalize_url(source.get("url", ""))
    for record in records:
        if evidence_id and _normalize_source_id(record.get("id")) == evidence_id:
            return record
        if url and _normalize_url(record.get("url", "")) == url:
            return record
    return None


def _prefer_top_tier_sources(sources: list[dict[str, str]], records: list[dict[str, str]]) -> list[dict[str, str]]:
    if len(sources) <= 1 or not records:
        return sources[:2]
    indexed: list[tuple[int, int, dict[str, str]]] = []
    has_top_tier = False
    for idx, source in enumerate(sources):
        record = _record_for_source(source, records)
        tier = str(record.get("source_tier") or "").upper() if record else ""
        rank = {"S1": 0, "S2": 1, "S3": 2, "S4": 3, "S5": 4}.get(tier, 5)
        if tier in TOP_SOURCE_TIERS:
            has_top_tier = True
        indexed.append((rank, idx, source))
    if has_top_tier:
        indexed = [row for row in indexed if row[0] <= 2]
    indexed.sort(key=lambda row: (row[0], row[1]))
    return [source for _rank, _idx, source in indexed[:2]]


def _fallback_sources_for_item(item: dict[str, Any], records: list[dict[str, str]], allowed_urls: set[str]) -> list[dict[str, str]]:
    query = _source_query_for_item(item)
    if not _source_query_is_specific(query) and not _source_title_query_is_specific(item):
        return []
    core_priority = _is_core_priority(item.get("priority"))
    required_entities = _source_required_entity_tokens(item)
    scored: list[tuple[float, dict[str, str]]] = []
    for record in records:
        normalized_url = _normalize_url(record.get("url", ""))
        if not normalized_url or normalized_url not in allowed_urls:
            continue
        if core_priority and not _record_core_top_eligible(record):
            continue
        record_text = _record_match_text(record)
        title_score = _source_title_relevance_score(item, record_text)
        score = title_score if title_score is not None else _source_relevance_score(query, record_text, required_entities=required_entities)
        if score >= 0.2:
            scored.append((score, record))
    scored.sort(key=lambda row: row[0], reverse=True)
    output = []
    for _score, record in scored[:2]:
        source = _source_from_record(record)
        if source:
            output.append(source)
    return output


def _source_query_for_item(item: dict[str, Any]) -> str:
    return " ".join(
        str(item.get(key) or "")
        for key in ("title", "card_title", "why", "card_why")
        if str(item.get(key) or "").strip()
    )


def _source_title_query_for_item(item: dict[str, Any]) -> str:
    return " ".join(
        str(item.get(key) or "")
        for key in ("title", "card_title")
        if str(item.get(key) or "").strip()
    )


def _source_required_entity_tokens(item: dict[str, Any]) -> set[str]:
    title_query = _source_title_query_for_item(item)
    return _match_tokens(title_query) & _source_entity_tokens()


def _record_match_text(record: dict[str, str]) -> str:
    return f"{record.get('title', '')} {record.get('source', '')} {record.get('summary', '')} {record.get('url', '')}"


def _source_relevance_score(query: str, text: str, *, required_entities: set[str] | None = None) -> float:
    query_tokens = _match_tokens(query)
    text_tokens = _match_tokens(text)
    if not query_tokens or not text_tokens:
        return 0.0
    if required_entities and not (required_entities & text_tokens):
        return 0.0
    strong_query = query_tokens - _WEAK_SOURCE_TOKENS
    strong_overlap = strong_query & text_tokens
    if not strong_overlap:
        return 0.0
    entity_query = strong_query & _ENTITY_SOURCE_TOKENS
    if entity_query and not (entity_query & text_tokens):
        return 0.0
    event_query = _event_specific_source_tokens(strong_query)
    if event_query:
        event_overlap = event_query & text_tokens
        if not event_overlap:
            return 0.0
        broad_bonus = 0.1 if strong_overlap & _BROAD_ENTITY_SOURCE_TOKENS else 0.0
        return min(1.0, 0.45 + (0.55 * len(event_overlap) / max(len(event_query), 1)) + broad_bonus)
    if strong_overlap & _BROAD_ENTITY_SOURCE_TOKENS:
        return 0.8
    return len(strong_overlap) / max(len(strong_query), 1)


def _source_title_relevance_score(item: dict[str, Any], text: str) -> float | None:
    title_query = _source_title_query_for_item(item)
    if not _source_title_query_is_specific(item):
        return None
    required_entities = _source_required_entity_tokens(item)
    return _source_relevance_score(title_query, text, required_entities=required_entities)


def _source_query_is_specific(query: str) -> bool:
    tokens = _match_tokens(query) - _WEAK_SOURCE_TOKENS
    return bool(tokens & _ENTITY_SOURCE_TOKENS)


def _source_title_query_is_specific(item: dict[str, Any]) -> bool:
    title_query = _source_title_query_for_item(item)
    title_tokens = _match_tokens(title_query) - _WEAK_SOURCE_TOKENS
    if title_tokens & _source_entity_tokens():
        return True
    if not _event_specific_source_tokens(title_tokens):
        return False
    lowered = title_query.lower()
    numeric_signal = bool(re.search(r"\d", lowered))
    domain_signal = any(
        marker in lowered
        for marker in (
            "api",
            "token",
            "tokens",
            "美元",
            "欧元",
            "融资",
            "估值",
            "成本",
            "订阅",
            "用量",
            "用户",
            "客户",
            "收入",
            "mau",
            "dau",
            "arr",
        )
    )
    return numeric_signal and domain_signal


def _source_entity_tokens() -> set[str]:
    return set(_ENTITY_SOURCE_TOKENS) | set(_DOMESTIC_SUBJECT_TOKENS) | set(_OVERSEAS_SUBJECT_TOKENS)


def _record_core_top_eligible(record: dict[str, str]) -> bool:
    tier = str(record.get("source_tier") or "").upper()
    return not _record_not_core_eligible(record) and (not tier or tier in TOP_SOURCE_TIERS)


def _record_not_core_eligible(record: dict[str, str]) -> bool:
    return str(record.get("not_core_eligible") or "").strip().lower() == "true"


def _event_specific_source_tokens(tokens: set[str]) -> set[str]:
    output: set[str] = set()
    for token in tokens:
        if token in _BROAD_ENTITY_SOURCE_TOKENS or token in _WEAK_SOURCE_TOKENS:
            continue
        if re.search(r"[a-z0-9]", token):
            output.add(token)
            continue
        if token not in _GENERIC_CJK_SOURCE_TOKENS:
            output.add(token)
    return output


_WEAK_SOURCE_TOKENS = {
    "ai",
    "agent",
    "agents",
    "app",
    "apps",
    "business",
    "model",
    "models",
    "skill",
    "skills",
    "tool",
    "tools",
    "global",
    "news",
    "blog",
    "open",
    "new",
    "发布",
    "上线",
    "推出",
    "全球",
    "工具",
    "应用",
    "智能体",
    "模型",
    "商业",
    "事件",
}

_ENTITY_SOURCE_TOKENS = {
    "openai",
    "microsoft",
    "meta",
    "whatsapp",
    "ios",
    "iphone",
    "siri",
    "wwdc",
    "nvidia",
    "google",
    "uber",
    "coralogix",
    "anthropic",
    "mistral",
    "aws",
    "codex",
    "claude",
    "amazon",
    "perplexity",
    "semianalysis",
    "kpmg",
    "xai",
    "grok",
    "tesla",
    "deepseek",
    "qwen",
    "kimi",
    "coze",
    "字节",
    "阿里",
    "腾讯",
    "微信",
    "支付宝",
    "豆包",
    "火山",
    "千问",
    "月之",
}

_DOMESTIC_SUBJECT_TOKENS = (
    "deepseek",
    "qwen",
    "kimi",
    "coze",
    "alibaba",
    "bytedance",
    "doubao",
    "volcengine",
    "tencent",
    "wechat",
    "baidu",
    "zhipu",
    "minimax",
    "kuaishou",
    "huawei",
    "阿里",
    "通义",
    "千问",
    "字节",
    "豆包",
    "火山",
    "扣子",
    "腾讯",
    "微信",
    "百度",
    "智谱",
    "月之暗面",
    "零一万物",
    "阶跃",
    "商汤",
    "快手",
    "华为",
    "美团",
    "京东",
)

_OVERSEAS_SUBJECT_TOKENS = (
    "openai",
    "anthropic",
    "claude",
    "meta",
    "whatsapp",
    "mistral",
    "microsoft",
    "google",
    "gemini",
    "deepmind",
    "nvidia",
    "amazon",
    "aws",
    "apple",
    "perplexity",
    "xai",
    "grok",
    "huggingface",
    "hugging face",
    "semianalysis",
    "semi analysis",
    "kpmg",
    "artificial analysis",
    "andrew yang",
)

_BROAD_ENTITY_SOURCE_TOKENS = {
    "openai",
    "microsoft",
    "meta",
    "nvidia",
    "google",
    "anthropic",
    "mistral",
    "aws",
    "amazon",
    "perplexity",
    "semianalysis",
    "kpmg",
    "xai",
    "grok",
    "deepseek",
    "qwen",
    "kimi",
    "coze",
    "codex",
    "字节",
    "阿里",
    "腾讯",
    "微信",
    "支付宝",
    "豆包",
    "火山",
    "千问",
    "月之",
}

_GENERIC_CJK_SOURCE_TOKENS = {
    "发布",
    "发布新",
    "布新",
    "布新模",
    "新模",
    "新模型",
    "模型",
    "推出",
    "上线",
    "影响",
    "开发",
    "开发者",
    "发者",
    "响开",
    "响开发",
    "影响开",
    "工具",
    "能力",
    "企业",
    "商业",
    "事件",
    "重要",
    "核心",
}


def _match_tokens(value: str) -> set[str]:
    text = str(value or "").lower()
    tokens = set(re.findall(r"[a-z0-9][a-z0-9+.-]{1,}", text))
    cjk_chunks = re.findall(r"[\u4e00-\u9fff]{2,}", text)
    for chunk in cjk_chunks:
        if len(chunk) <= 4:
            tokens.add(chunk)
        else:
            tokens.update(chunk[idx : idx + 2] for idx in range(0, len(chunk) - 1))
            tokens.update(chunk[idx : idx + 3] for idx in range(0, len(chunk) - 2))
    if "融资" in text:
        tokens.update({"funding", "fundraise", "raising", "raise"})
    if "估值" in text:
        tokens.update({"valuation", "valued"})
    if "政府" in text:
        tokens.update({"government", "order"})
    if "叫停" in text or "切断" in text or "关停" in text:
        tokens.update({"cut", "cuts", "access", "block", "blocked", "order"})
    return {token.strip(".-+_") for token in tokens if token.strip(".-+_")}


def _align_items_to_core_events(
    items: list[dict[str, Any]],
    core_events: list[dict[str, Any]],
    records: list[dict[str, str]],
    allowed_urls: set[str],
    warnings: list[str] | None = None,
) -> list[dict[str, Any]]:
    aligned: list[dict[str, Any]] = []
    used_indexes: set[int] = set()
    for event in core_events:
        match_idx = _best_item_match(event, items, used_indexes)
        if match_idx is None:
            item = _brief_item_from_core_event(event, records, allowed_urls)
        else:
            used_indexes.add(match_idx)
            item = dict(items[match_idx])
            if not item.get("priority"):
                item["priority"] = _priority_from_text(event.get("priority", ""))
            event_why = _why_from_event(event)
            if event_why != "详见完整日报。" and _bad_why_fragment(str(item.get("why") or ""), str(item.get("title") or "")):
                item["why"] = _limit_brief_why(event_why)
            if event_why != "详见完整日报。" and _bad_why_fragment(str(item.get("card_why") or ""), str(item.get("title") or "")):
                item["card_why"] = _limit_text(event_why, 120)
            event_sources = _sources_from_event(event, records, allowed_urls, warnings)
            if event_sources:
                filtered_event_sources = _filter_sources_for_item(item, event_sources, records, warnings if warnings is not None else [])
                if filtered_event_sources:
                    item["sources"] = filtered_event_sources
            elif not item.get("sources"):
                item["sources"] = event_sources
        aligned.append(item)
    return sort_top_items(aligned)


def _best_item_match(event: dict[str, Any], items: list[dict[str, Any]], used_indexes: set[int]) -> int | None:
    event_text = f"{event.get('title', '')} {event.get('raw_block', '')}"
    best_idx = None
    best_score = 0.0
    for idx, item in enumerate(items):
        if idx in used_indexes:
            continue
        score = _match_score(str(item.get("title") or ""), str(event.get("title") or ""))
        score = max(score, _match_score(f"{item.get('title', '')} {item.get('why', '')}", event_text))
        if score > best_score:
            best_idx = idx
            best_score = score
    return best_idx if best_score >= 0.18 else None


def _brief_item_from_core_event(
    event: dict[str, Any],
    records: list[dict[str, str]],
    allowed_urls: set[str],
) -> dict[str, Any]:
    item = {
        "title": _limit_text(event.get("title"), 80),
        "card_title": _limit_text(event.get("title"), 40),
        "why": _limit_brief_why(_why_from_event(event)),
        "card_why": _limit_text(_why_from_event(event), 120),
        "priority": _limit_text(event.get("priority"), 8) or "观察",
        "sources": _sources_from_event(event, records, allowed_urls),
    }
    return item


def _why_from_event(event: dict[str, Any]) -> str:
    raw_block = str(event.get("raw_block") or "")
    raw = re.sub(r"\s+", " ", raw_block).strip()
    title = str(event.get("title") or "")
    if not raw:
        return "详见完整日报。"
    text = _extract_natural_why_from_block(raw_block) or _clean_event_why_candidate(raw, title)
    if not text:
        return "详见完整日报。"
    sentence = re.split(r"[。！？!?]\s*", text, maxsplit=1)[0].strip(" ：:；;，,。")
    return sentence if not _bad_why_fragment(sentence, title) else "详见完整日报。"


def _clean_brief_why_value(value: Any, title: Any = "") -> str:
    if _bad_raw_why_fragment(str(value or ""), str(title or "")):
        return "详见完整日报。"
    text = _clean_event_why_candidate(str(value or ""), str(title or ""))
    if not text or _bad_why_fragment(text, str(title or "")):
        return "详见完整日报。"
    return text


def _extract_natural_why_from_block(raw: str) -> str:
    candidates_by_label: dict[str, str] = {}
    for line in str(raw or "").splitlines():
        text = line.strip()
        if not text:
            continue
        text = re.sub(r"^\s*[-*]\s*", "", text)
        text = re.sub(r"^\s*#{1,6}\s*", "", text)
        match = re.match(
            r"^\*\*(影响\s*/\s*So what|So what|概述|重要性判断|商业模式\s*/\s*新应用信号|商业模式|新应用信号)\*\*\s*[:：]\s*(.+)$",
            text,
            flags=re.IGNORECASE,
        )
        if match:
            label = re.sub(r"\s+", "", match.group(1).lower())
            candidate = _clean_event_why_candidate(match.group(2), "")
            if candidate and not _bad_why_fragment(candidate, ""):
                candidates_by_label[label] = candidate
    for label in ("影响/sowhat", "sowhat", "概述", "重要性判断", "商业模式/新应用信号", "商业模式", "新应用信号"):
        if candidates_by_label.get(label):
            return candidates_by_label[label]
    return ""


def _clean_event_why_candidate(raw: str, title: str) -> str:
    text = URL_RE.sub("", str(raw or ""))
    text = re.sub(r"\*\*", "", text)
    text = re.sub(r"^\s*#{1,6}\s*", "", text)
    text = _remove_title_when_safe(text, str(title or ""))
    if "|" in text:
        cells = [cell.strip() for cell in text.split("|")]
        candidates = []
        for cell in cells:
            cleaned = cell.strip(" ：:；;，,。")
            if not cleaned or cleaned == title:
                continue
            if re.fullmatch(r"L[0-4]", cleaned, flags=re.IGNORECASE):
                continue
            if re.fullmatch(r"P[12]|观察|高|中|低", cleaned, flags=re.IGNORECASE):
                continue
            if _is_source_like_cell(cleaned):
                continue
            candidates.append(cleaned)
        text = max(candidates, key=len, default="")
    text = re.sub(r"^\s*(?:\d+[.)、]\s*)?", "", text)
    text = re.sub(r"^\s*(?:P[12]|观察|L[0-4]|高|中|低)\s*[:：|,，、-]*\s*", "", text, flags=re.IGNORECASE)
    text = _strip_leading_analysis_label(text)
    text = re.sub(r"\bL[0-4]\b\s*[|,，、-]*\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bP[12]\b\s*[|,，、-]*\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:高|中|低)\b\s*[|,，、-]*\s*", "", text)
    text = re.sub(r"[，,]{2,}", "，", text)
    text = re.sub(r"[。]{2,}", "。", text)
    text = re.sub(r"\s+", " ", text).strip(" |：:-；;，,。")
    if _is_source_like_cell(text) or _bad_why_fragment(text, title):
        return ""
    return text


def _strip_leading_analysis_label(value: str) -> str:
    text = str(value or "").strip()
    labels = (
        r"它改变了什么",
        r"利好\s*/\s*利空谁",
        r"对后续启发(?:的启发)?",
        r"后续启发",
        r"So\s*what",
    )
    label_pattern = "|".join(labels)
    return re.sub(rf"^\s*(?:{label_pattern})\s*[?？]\s*", "", text, flags=re.IGNORECASE).strip()


def _remove_title_when_safe(text: str, title: str) -> str:
    title_text = str(title or "").strip()
    if not title_text or title_text not in text:
        return text
    stripped = text.replace(title_text, "")
    stripped = re.sub(r"\s+", " ", stripped).strip(" |：:-；;，,。")
    if not stripped:
        return text
    if _weak_attribution_fragment(stripped):
        return text
    if len(stripped) < 8 and not re.search(r"\d|融资|收费|降价|上线|发布|商用|监管|增长|收入|成本", stripped):
        return text
    return stripped


def _bad_why_fragment(value: str, title: str = "") -> bool:
    text = str(value or "").strip()
    if not text:
        return True
    if text == str(title or "").strip():
        return True
    if "详见完整日报" in text:
        return True
    if re.fullmatch(r"\d+[.)、]?", text):
        return True
    if re.match(r"^\d+[.)、]\s*", text):
        return True
    if re.search(r"\|\s*P[12]\s*\|", text):
        return True
    if text.startswith(("**", "###", "##")):
        return True
    if _weak_attribution_fragment(text):
        return True
    if len(text) <= 4 and not re.search(r"(融资|收费|降价|上线|发布|商用|监管)", text):
        return True
    return False


def _weak_attribution_fragment(value: str) -> bool:
    text = re.sub(r"\s+", "", str(value or "").strip(" ：:；;，,。"))
    if not text:
        return True
    if text in {"当前内容为空", "内容为空", "暂无摘要"}:
        return True
    return bool(re.fullmatch(r"[\u4e00-\u9fffA-Za-z0-9·]{0,12}(透露|表示|称|披露|发布|宣布|报道|指出)", text))


def _bad_raw_why_fragment(value: str, title: str = "") -> bool:
    text = str(value or "").strip()
    if not text:
        return True
    stripped = re.sub(r"^\s*\*\*", "", text)
    stripped = re.sub(r"\*\*\s*$", "", stripped).strip()
    if re.match(r"^\s*#{1,6}\s*", stripped):
        return True
    if re.match(r"^\s*\d+[.)、]\s*", stripped):
        return True
    if title and stripped.strip(" ：:；;，,。") == str(title).strip(" ：:；;，,。"):
        return True
    return False


def _is_source_like_cell(value: str) -> bool:
    text = str(value or "")
    return bool(URL_RE.search(text) or text.startswith("来源") or text.lower().startswith("source"))


def _sources_from_event(
    event: dict[str, Any],
    records: list[dict[str, str]],
    allowed_urls: set[str],
    warnings: list[str] | None = None,
) -> list[dict[str, str]]:
    output = []
    for url in event.get("source_urls") or []:
        normalized_url = _normalize_url(url)
        if not normalized_url or normalized_url not in allowed_urls:
            continue
        record = next((record for record in records if _normalize_url(record.get("url", "")) == normalized_url), None)
        if record:
            source = _source_from_record(record)
            if source:
                output.append(source)
        else:
            label = _clean_source_label("", url)
            if label:
                output.append({"title": label, "url": url, "source": label, "evidence_id": ""})
        if len(output) == 2:
            break
    fallback_item = {"title": event.get("title", ""), "why": event.get("raw_block", ""), "priority": event.get("priority", "")}
    if output:
        filtered = _filter_sources_for_item(
            fallback_item,
            _prefer_top_tier_sources(output, records),
            records,
            warnings if warnings is not None else [],
        )
        if filtered:
            return filtered
    return _prefer_top_tier_sources(_fallback_sources_for_item(fallback_item, records, allowed_urls), records)


def _count_mismatch_type(
    domestic_count: int,
    overseas_count: int,
    expected_domestic_count: int,
    expected_overseas_count: int,
    empty_placeholder_removed_count: int,
) -> str:
    if domestic_count > MAX_TOP_EVENTS_PER_REGION or overseas_count > MAX_TOP_EVENTS_PER_REGION:
        return "too_many"
    if expected_domestic_count > 0 and domestic_count < expected_domestic_count:
        return "too_few"
    if expected_overseas_count > 0 and overseas_count < expected_overseas_count:
        return "too_few"
    if expected_domestic_count > 0 and domestic_count > expected_domestic_count:
        return "too_many"
    if expected_overseas_count > 0 and overseas_count > expected_overseas_count:
        return "too_many"
    if empty_placeholder_removed_count:
        return "fake_empty_item"
    return "none"


def _count_mismatch_handled(
    mismatch_type: str,
    *,
    count_repair_attempted: bool,
    domestic_final_count: int,
    overseas_final_count: int,
    expected_domestic_count: int,
    expected_overseas_count: int,
) -> bool:
    if mismatch_type == "none":
        return False
    if mismatch_type in {"too_many", "fake_empty_item"}:
        return True
    if mismatch_type == "too_few":
        return bool(
            count_repair_attempted
            and domestic_final_count >= expected_domestic_count
            and overseas_final_count >= expected_overseas_count
        )
    return False


def _brief_count_mismatch(brief: dict[str, Any]) -> bool:
    return bool(brief.get("brief_count_mismatch")) and not bool(brief.get("brief_count_mismatch_handled"))


def _match_score(query: str, text: str) -> float:
    query_chars = _match_chars(query)
    text_chars = _match_chars(text)
    if not query_chars or not text_chars:
        return 0.0
    overlap = query_chars & text_chars
    if len(overlap) < 2:
        return 0.0
    char_score = len(overlap) / max(len(query_chars), 1)
    sequence_score = SequenceMatcher(None, str(query or "").lower(), str(text or "").lower()).ratio()
    return max(char_score, sequence_score)


def _match_chars(value: str) -> set[str]:
    return {
        char.lower()
        for char in str(value or "")
        if char.isalnum() or "\u4e00" <= char <= "\u9fff"
    }


def _llm_items_count(items: Any) -> int:
    if not isinstance(items, list):
        return 0
    return sum(1 for item in items if isinstance(item, dict) and not _is_empty_placeholder_item(item))


def _validated_brief_schema(raw: dict[str, Any]) -> dict[str, Any]:
    if not _has_top_list(raw):
        raise ValueError("brief schema missing domestic_top/overseas_top")
    return raw


def _repair_payload_empty(parsed: dict[str, Any], core_events: dict[str, Any]) -> bool:
    expected_domestic = len((core_events or {}).get("domestic_core_events") or [])
    expected_overseas = len((core_events or {}).get("overseas_core_events") or [])
    if not expected_domestic and not expected_overseas:
        return False
    return _llm_items_count(parsed.get("domestic_top")) == 0 and _llm_items_count(parsed.get("overseas_top")) == 0


def _card_field_issues(brief: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for region in ("domestic_top", "overseas_top"):
        for idx, item in enumerate(brief.get(region) or []):
            if not isinstance(item, dict):
                continue
            _collect_item_card_issue(issues, item, region, idx, "card_title", "title", CARD_TITLE_MAX_CHARS)
            _collect_item_card_issue(issues, item, region, idx, "card_why", "why", CARD_WHY_MAX_CHARS)
    for field in ("core_judgments_card", "watch_signals_card"):
        values = list(brief.get(field) or [])
        source_values = list(brief.get(field.replace("_card", "")) or [])
        while len(values) < len(source_values[:3]):
            values.append(source_values[len(values)])
        brief[field] = values[:3]
        for idx, value in enumerate(brief[field]):
            if not _valid_card_value(str(value), CARD_BULLET_MAX_CHARS):
                issues.append(
                    {
                        "path": f"{field}[{idx}]",
                        "container": brief[field],
                        "index": idx,
                        "field": None,
                        "value": str(value),
                        "max_chars": CARD_BULLET_MAX_CHARS,
                        "kind": field,
                    }
                )
    return issues


def _collect_item_card_issue(
    issues: list[dict[str, Any]],
    item: dict[str, Any],
    region: str,
    idx: int,
    card_field: str,
    source_field: str,
    max_chars: int,
) -> None:
    value = str(item.get(card_field) or item.get(source_field) or "").strip()
    item[card_field] = value
    if not _valid_card_value(value, max_chars):
        issues.append(
            {
                "path": f"{region}[{idx}].{card_field}",
                "container": item,
                "index": None,
                "field": card_field,
                "value": value,
                "max_chars": max_chars,
                "kind": card_field,
            }
        )


def _valid_card_value(value: str, max_chars: int) -> bool:
    text = str(value or "").strip()
    return bool(text) and len(text) <= max_chars


def _deterministic_card_field_fallback(issue: dict[str, Any]) -> str:
    max_chars = int(issue["max_chars"])
    value = str(issue.get("value") or "")
    cleaned = _clean_event_why_candidate(value, "")
    if not cleaned:
        cleaned = value.strip()
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ：:；;，,。")
    if not cleaned:
        cleaned = "详见完整日报"
    return _limit_text(cleaned, max_chars)


def _set_card_field(issue: dict[str, Any], value: str) -> None:
    container = issue["container"]
    if issue.get("field"):
        container[issue["field"]] = value
    else:
        container[int(issue["index"])] = value


def _parse_card_field_repair_response(text: str) -> str:
    try:
        parsed = json.loads(_strip_json_fence(text))
        if isinstance(parsed, dict):
            return str(parsed.get("value") or parsed.get("card") or parsed.get("text") or "").strip()
    except Exception:  # noqa: BLE001
        pass
    return str(text or "").strip().strip('"')


def _parse_top_section_response(text: str, key: str) -> tuple[bool, list[dict[str, Any]]]:
    cleaned = _strip_json_fence(str(text or ""))
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict) and isinstance(parsed.get(key), list):
            return True, [item for item in parsed[key] if isinstance(item, dict)]
        if isinstance(parsed, list):
            return True, [item for item in parsed if isinstance(item, dict)]
    except json.JSONDecodeError:
        pass
    items = [item for item in _salvage_object_array(cleaned, key) if isinstance(item, dict)]
    return bool(items), items


def _parse_bullet_section_response(text: str) -> dict[str, Any]:
    cleaned = _strip_json_fence(str(text or ""))
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        parsed = salvage_brief_items_from_partial_json(cleaned)
    if not isinstance(parsed, dict):
        return {}
    output = {}
    for key in ("core_judgments", "watch_signals"):
        value = parsed.get(key)
        if isinstance(value, list):
            output[key] = value
    return output


def _normalization_error(
    llm_domestic_items_count: int,
    llm_overseas_items_count: int,
    final_domestic_items_count: int,
    final_overseas_items_count: int,
    *,
    domestic_source_quality_dropped_count: int = 0,
    overseas_source_quality_dropped_count: int = 0,
    region_reassigned_count: int = 0,
) -> str:
    errors = []
    if (
        llm_domestic_items_count
        and not final_domestic_items_count
        and not domestic_source_quality_dropped_count
        and not region_reassigned_count
    ):
        errors.append("normalization dropped domestic_top items")
    if (
        llm_overseas_items_count
        and not final_overseas_items_count
        and not overseas_source_quality_dropped_count
        and not region_reassigned_count
    ):
        errors.append("normalization dropped overseas_top items")
    return "; ".join(errors)


def _raise_if_normalization_dropped_items(brief: dict[str, Any]) -> None:
    error = str(brief.get("brief_normalization_error") or "")
    if error:
        raise ValueError(error)


def _source_markdown(sources: list[dict[str, Any]]) -> str:
    links = []
    for source in sources[:2]:
        url = str(source.get("url") or "")
        if not url:
            continue
        label = _source_label(source)
        if not label:
            continue
        links.append(f"[{label}]({url})")
    return " / ".join(links)


def _source_label(source: dict[str, Any]) -> str:
    return _clean_source_label(
        source.get("source") or source.get("source_name") or source.get("title"),
        str(source.get("url") or ""),
        provider=source.get("provider") or source.get("source_type"),
    )


def _clean_source_label(value: Any, url: str = "", *, provider: Any = "") -> str:
    if _is_disallowed_source_url(url):
        return ""
    label = _dedupe_label(str(value or "").strip())
    provider_label = _dedupe_label(str(provider or "").strip())
    if _is_bad_source_label(label):
        label = ""
    if label:
        label = _human_source_label(label)
    if not label and url:
        label = _human_source_label(_domain(url))
    if not label and not _is_bad_source_label(provider_label):
        label = _human_source_label(provider_label)
    return _limit_text(label, 24)


def _dedupe_label(value: str) -> str:
    text = value.strip()
    if not text:
        return ""
    parts = [part for part in re.split(r"[.\s]+", text) if part]
    if len(parts) == 2 and parts[0].lower() == parts[1].lower():
        return parts[0]
    return text


def _is_bad_source_label(value: str) -> bool:
    cleaned = value.strip().lower()
    return cleaned in BAD_SOURCE_LABELS or cleaned.startswith("tavily") or cleaned.startswith("rss")


def _human_source_label(value: str) -> str:
    cleaned = _clean_domain_label_key(value)
    return DOMAIN_LABELS.get(cleaned, DOMAIN_LABELS.get(_root_domain(cleaned), value.strip()))


def _clean_domain_label_key(value: str) -> str:
    cleaned = value.lower().strip().removeprefix("www.")
    for prefix in ("m.", "wap.", "mobile."):
        cleaned = cleaned.removeprefix(prefix)
    return cleaned


def _root_domain(host: str) -> str:
    parts = host.split(".")
    if len(parts) >= 3 and parts[-2] in {"com", "net", "org", "co"}:
        return ".".join(parts[-3:])
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return host


def _is_disallowed_source_url(url: str) -> bool:
    host = _domain(url)
    return bool(host and ("tavily" in host or host in {"google.com", "bing.com", "search.yahoo.com"}))


def _normalize_url(url: str) -> str:
    cleaned = unquote(url.rstrip(".,;，。；/"))
    parts = urlsplit(cleaned)
    if not parts.netloc:
        return ""
    query = urlencode(
        [
            (key, value)
            for key, value in parse_qsl(parts.query, keep_blank_values=True)
            if not key.lower().startswith("utm_")
        ]
    )
    return urlunsplit(("https", parts.netloc.lower(), parts.path.rstrip("/"), query, ""))


def _domain(url: str) -> str:
    return urlsplit(str(url or "")).netloc.lower().replace("www.", "")


def _source_resolution_status(
    items: list[dict[str, Any]],
    source_ids_requested_count: int,
    source_ids_resolved_count: int,
    source_ids_unresolved_count: int,
) -> str:
    sources_count = sum(len(item.get("sources") or []) for item in items)
    if source_ids_requested_count == 0:
        return "no_source_ids"
    if sources_count == 0:
        return "no_sources"
    if source_ids_unresolved_count or source_ids_resolved_count < source_ids_requested_count:
        return "partial"
    if any(not item.get("sources") for item in items):
        return "partial"
    return "ok"


def _redact_summary(value: str) -> str:
    text = _limit_text(value, 1000)
    text = re.sub(
        r'(?i)("?(?:webhook|sign|token|app_secret|secret|api[_-]?key)"?\s*[:=]\s*")([^"]+)(")',
        r'"redacted_field": "[REDACTED]"',
        text,
    )
    return re.sub(
        r"(?i)((?:webhook|sign|token|app_secret|secret|api[_-]?key)\s*[:=]\s*)([^\s,;}&]+)",
        r"redacted_field=[REDACTED]",
        text,
    )
