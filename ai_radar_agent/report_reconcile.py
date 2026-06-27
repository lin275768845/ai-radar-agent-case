from __future__ import annotations

from copy import deepcopy
from datetime import date
import re
from difflib import SequenceMatcher
from typing import Any

from .models import TimeWindow


def reconcile_report_with_final_brief(report_md: str, brief: dict[str, Any], window: TimeWindow) -> str:
    report = _strip_llm_preamble(report_md)
    report = _strip_llm_transition_lines(report)
    report = _drop_pre_candidate_formal_regions(report)
    brief = drop_stale_final_top_from_candidate_metadata(report, brief, window)
    report = _sync_candidate_tables(report, brief, window)
    report = _remove_combined_formal_prelude(report)
    for region in ("domestic", "overseas"):
        report = _replace_formal_region(report, region, brief.get(f"{region}_top") or [], window)
    report = _ensure_formal_sections(report, brief, window)
    report = _move_candidate_sections_before_formal(report)
    report = _drop_existing_self_check_sections(report)
    report = _ensure_self_check_section(report)
    report = _strip_leading_horizontal_rules(report)
    return report


def drop_stale_final_top_from_candidate_metadata(report_md: str, brief: dict[str, Any], window: TimeWindow) -> dict[str, Any]:
    stale_indices = _stale_final_top_indices_from_candidate_tables(report_md, brief, window)
    if not any(stale_indices.values()):
        return brief
    output = deepcopy(brief)
    for region, key in (("domestic", "domestic_top"), ("overseas", "overseas_top")):
        indexes = stale_indices[region]
        if not indexes:
            continue
        items = output.get(key)
        if not isinstance(items, list):
            continue
        output[key] = [item for idx, item in enumerate(items) if idx not in indexes]
    _update_filtered_brief_top_counts(output)
    return output


def drop_stale_final_top_from_evidence(
    brief: dict[str, Any], evidence: list[Any], window: TimeWindow
) -> dict[str, Any]:
    evidence_records = _indexed_evidence_records(evidence)
    if not evidence_records:
        return brief
    stale_indices: dict[str, set[int]] = {"domestic": set(), "overseas": set()}
    for region, key in (("domestic", "domestic_top"), ("overseas", "overseas_top")):
        items = _candidate_items(brief.get(key))
        for index, item in enumerate(items):
            records = _matching_evidence_records_for_item(item, evidence_records)
            if records and _final_item_evidence_is_stale_without_new_signal(item, records, window):
                stale_indices[region].add(index)
    if not any(stale_indices.values()):
        return brief
    output = deepcopy(brief)
    for region, key in (("domestic", "domestic_top"), ("overseas", "overseas_top")):
        indexes = stale_indices[region]
        if not indexes:
            continue
        items = output.get(key)
        if not isinstance(items, list):
            continue
        output[key] = [item for idx, item in enumerate(items) if idx not in indexes]
    _update_filtered_brief_top_counts(output)
    return output


def _update_filtered_brief_top_counts(brief: dict[str, Any]) -> None:
    domestic_count = len(brief.get("domestic_top") or []) if isinstance(brief.get("domestic_top"), list) else 0
    overseas_count = len(brief.get("overseas_top") or []) if isinstance(brief.get("overseas_top"), list) else 0
    brief["brief_final_domestic_items_count"] = domestic_count
    brief["brief_final_overseas_items_count"] = overseas_count
    brief["brief_domestic_items_count"] = domestic_count
    brief["brief_overseas_items_count"] = overseas_count
    brief["brief_actual_domestic_items_count"] = domestic_count
    brief["brief_actual_overseas_items_count"] = overseas_count
    brief["brief_items_count"] = domestic_count + overseas_count


def _stale_final_top_indices_from_candidate_tables(
    report_md: str, brief: dict[str, Any], window: TimeWindow
) -> dict[str, set[int]]:
    selected_items = {
        "domestic": _candidate_items(brief.get("domestic_top")),
        "overseas": _candidate_items(brief.get("overseas_top")),
    }
    stale_indices: dict[str, set[int]] = {"domestic": set(), "overseas": set()}
    region = ""
    in_table = False
    header: list[str] = []
    title_idx = None
    for line in report_md.splitlines():
        stripped = line.strip()
        heading_region = _candidate_heading_region(stripped)
        if heading_region:
            region = heading_region
            in_table = False
            header = []
            title_idx = None
            continue
        if region and stripped.startswith("#") and not heading_region:
            region = ""
            in_table = False
            header = []
            title_idx = None
            continue
        if not region or not stripped.startswith("|"):
            continue
        cells = _split_row(stripped)
        if not cells:
            continue
        if not in_table:
            header = cells
            title_idx = _find_col(header, ("事件", "标题"))
            in_table = title_idx is not None and _find_col(header, ("是否入选",)) is not None
            continue
        if all(re.fullmatch(r":?-{2,}:?", cell.strip()) for cell in cells):
            continue
        if title_idx is None or title_idx >= len(cells):
            continue
        if not _candidate_row_is_stale_without_new_signal(cells, header, window):
            continue
        matched_item_idx = _matching_selected_item_index(cells[title_idx], selected_items[region])
        if matched_item_idx is not None:
            stale_indices[region].add(matched_item_idx)
    return stale_indices


def _indexed_evidence_records(evidence: list[Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for index, item in enumerate(evidence, start=1):
        if isinstance(item, dict):
            record = dict(item)
        else:
            record = {
                "title": getattr(item, "title", ""),
                "url": getattr(item, "url", ""),
                "content": getattr(item, "content", ""),
                "published_at": getattr(item, "published_at", ""),
            }
        record.setdefault("evidence_id", f"E{index}")
        records.append(record)
    return records


def _matching_evidence_records_for_item(
    item: dict[str, Any], evidence_records: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    source_ids: set[str] = set()
    urls: set[str] = set()
    titles: list[str] = []
    sources = item.get("sources")
    if isinstance(sources, list):
        for source in sources:
            if not isinstance(source, dict):
                continue
            source_id = str(source.get("evidence_id") or "").strip().lower()
            if source_id:
                source_ids.add(source_id)
            url = str(source.get("url") or "").strip()
            if url:
                urls.add(url)
            title = str(source.get("title") or "").strip()
            if title:
                titles.append(title)
    item_source_ids = item.get("source_ids")
    if isinstance(item_source_ids, list):
        source_ids.update(str(source_id or "").strip().lower() for source_id in item_source_ids if str(source_id or "").strip())
    matches: list[dict[str, Any]] = []
    for record in evidence_records:
        evidence_id = str(record.get("evidence_id") or "").strip().lower()
        url = str(record.get("url") or "").strip()
        title = str(record.get("title") or "").strip()
        if evidence_id and evidence_id in source_ids:
            matches.append(record)
            continue
        if url and url in urls:
            matches.append(record)
            continue
        if title and any(_matches_any(title, [_normalize_title(source_title)]) for source_title in titles):
            matches.append(record)
    return matches


def _final_item_evidence_is_stale_without_new_signal(
    item: dict[str, Any], records: list[dict[str, Any]], window: TimeWindow
) -> bool:
    for record in records:
        if _evidence_record_is_stale_without_new_signal(record, window):
            return True
    return False


def _evidence_record_is_stale_without_new_signal(record: dict[str, Any], window: TimeWindow) -> bool:
    text = " ".join(
        str(record.get(key) or "")
        for key in (
            "title",
            "url",
            "content",
        )
    )
    target = _parse_iso_date(window.date_str)
    if target is None:
        return False
    old_dates = [value for value in _extract_event_dates(text, target.year) if (target - value).days >= 2]
    if not old_dates:
        return False
    if _has_target_day_new_signal(text, target):
        return False
    return True


def _parse_iso_date(value: str) -> date | None:
    match = re.fullmatch(r"(20\d{2})-(\d{2})-(\d{2})", str(value or ""))
    if not match:
        return None
    try:
        return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError:
        return None


def _extract_event_dates(text: str, default_year: int) -> list[date]:
    compact = re.sub(r"[\u200e\u200f\u202a-\u202e]", "", str(text or ""))
    compact = re.sub(r"\s+", "", compact)
    dates: list[date] = []
    for year, month, day in re.findall(r"\b(20\d{2})[-/](\d{1,2})[-/](\d{1,2})\b", compact):
        parsed = _safe_date(int(year), int(month), int(day))
        if parsed:
            dates.append(parsed)
    for month, day in re.findall(r"(?<!\d)(\d{1,2})月(\d{1,2})日", compact):
        parsed = _safe_date(default_year, int(month), int(day))
        if parsed:
            dates.append(parsed)
    return dates


def _safe_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _has_target_day_new_signal(text: str, target: date) -> bool:
    zh_date = f"{target.month}月{target.day}日"
    iso_date = target.isoformat()
    compact = re.sub(r"\s+", "", text)
    if zh_date not in compact and iso_date not in text:
        return False
    target_index = compact.find(zh_date) if zh_date in compact else compact.find(iso_date.replace("-", ""))
    if target_index < 0:
        return False
    window = compact[max(0, target_index - 80) : target_index + 120]
    return bool(re.search(r"新增|新披露|首次披露|最新披露|数据更新|新数据|新上线|新采用|新客户|新营收|新调用量", window))


def _strip_llm_preamble(report_md: str) -> str:
    lines = report_md.splitlines()
    first_heading = next((idx for idx, line in enumerate(lines) if line.strip().startswith("#")), None)
    if first_heading is None or first_heading == 0:
        return report_md
    preamble = "\n".join(lines[:first_heading]).strip()
    if not _looks_like_llm_preamble(preamble):
        return report_md
    output = "\n".join(lines[first_heading:]).strip()
    return output + ("\n" if report_md.endswith("\n") else "")


def _looks_like_llm_preamble(value: str) -> bool:
    text = re.sub(r"\s+", "", str(value or ""))
    return (
        text.startswith(("好的", "以下是", "以下严格", "我将", "我会", "已根据"))
        or "严格遵循" in text[:120]
        or "严格按指令" in text[:120]
        or "首先检查" in text[:120]
        or "先输出候选事件筛选表" in text[:120]
    )


def _strip_llm_transition_lines(report_md: str) -> str:
    output = [line for line in report_md.splitlines() if not _looks_like_llm_transition_line(line)]
    return "\n".join(output).strip() + ("\n" if report_md.endswith("\n") else "")


def _looks_like_llm_transition_line(line: str) -> bool:
    text = re.sub(r"\s+", "", str(line or ""))
    if not text:
        return False
    return text.startswith(("现在，我将", "接下来，我将", "下面，我将", "以下生成", "以下为正式日报", "现在生成正式日报"))


def _sync_candidate_tables(report_md: str, brief: dict[str, Any], window: TimeWindow) -> str:
    selected_items = {
        "domestic": _candidate_items(brief.get("domestic_top")),
        "overseas": _candidate_items(brief.get("overseas_top")),
    }
    selected = {
        "domestic": _selected_titles(selected_items["domestic"]),
        "overseas": _selected_titles(selected_items["overseas"]),
    }
    lines = report_md.splitlines()
    output: list[str] = []
    region = ""
    in_table = False
    header: list[str] = []
    title_idx = selected_idx = reason_idx = None
    seen_selected_item_indices: set[int] = set()
    for line in lines:
        stripped = line.strip()
        heading_region = _candidate_heading_region(stripped)
        if heading_region:
            region = heading_region
            in_table = False
            header = []
            title_idx = selected_idx = reason_idx = None
            seen_selected_item_indices = set()
            output.append(_canonical_candidate_heading(heading_region))
            continue
        if region and stripped.startswith("#") and not heading_region:
            region = ""
            in_table = False
            seen_selected_item_indices = set()
        if region and in_table and not stripped.startswith("|"):
            if stripped.startswith("#"):
                output.append(line)
            elif not stripped:
                output.append(line)
            continue
        if not region or not stripped.startswith("|"):
            output.append(line)
            continue
        cells = _split_row(stripped)
        if not cells:
            output.append(line)
            continue
        if not in_table:
            header = cells
            title_idx = _find_col(header, ("事件", "标题"))
            selected_idx = _find_col(header, ("是否入选",))
            reason_idx = _find_col(header, ("入选/剔除原因", "原因"))
            in_table = title_idx is not None and selected_idx is not None
            output.append(line)
            continue
        if all(re.fullmatch(r":?-{2,}:?", cell.strip()) for cell in cells):
            output.append(line)
            continue
        if title_idx is None or selected_idx is None or title_idx >= len(cells) or selected_idx >= len(cells):
            output.append(line)
            continue
        if _has_future_date(cells, window.date_str):
            continue
        row_context = " ".join(_cell(cell) for cell in cells)
        matched_item_idx = _matching_selected_item_index(cells[title_idx], selected_items[region])
        if matched_item_idx is None:
            matched_item_idx = _matching_selected_item_index(row_context, selected_items[region])
        is_selected = matched_item_idx is not None or _matches_any(cells[title_idx], selected[region]) or _matches_any(
            row_context, selected[region]
        )
        if not is_selected and _is_p3_candidate(cells, header):
            continue
        if (
            is_selected
            and matched_item_idx is not None
            and matched_item_idx in seen_selected_item_indices
            and not _has_candidate_evidence_context(cells, header)
        ):
            continue
        cells[selected_idx] = "是" if is_selected else "否"
        if reason_idx is not None and reason_idx < len(cells):
            reason = cells[reason_idx].strip()
            if is_selected and (_is_placeholder_reason(reason) or _is_exclusion_reason(reason)):
                cells[reason_idx] = "进入最终 Top；由后置 gate/brief 回写。"
            elif not is_selected:
                cells[reason_idx] = _candidate_exclusion_reason(cells, header, reason)
        if is_selected and matched_item_idx is not None:
            seen_selected_item_indices.add(matched_item_idx)
        output.append(_format_row(cells))
    synced = "\n".join(output) + ("\n" if report_md.endswith("\n") else "")
    synced = _ensure_selected_candidate_rows(synced, brief)
    return _ensure_candidate_sections(synced, brief)


def _drop_pre_candidate_formal_regions(report_md: str) -> str:
    lines = report_md.splitlines()
    first_candidate = next((idx for idx, line in enumerate(lines) if _candidate_heading_region(line.strip())), None)
    if first_candidate is None:
        return report_md
    first_formal = next(
        (idx for idx, line in enumerate(lines[:first_candidate]) if _loose_or_canonical_formal_region(line.strip())),
        None,
    )
    if first_formal is None:
        return report_md
    output = lines[:first_formal] + lines[first_candidate:]
    return "\n".join(output).strip() + ("\n" if report_md.endswith("\n") else "")


def _move_candidate_sections_before_formal(report_md: str) -> str:
    lines = report_md.splitlines()
    candidate_blocks: list[list[str]] = []
    output: list[str] = []
    idx = 0
    while idx < len(lines):
        heading_region = _candidate_heading_region(lines[idx].strip())
        if not heading_region:
            output.append(lines[idx])
            idx += 1
            continue
        block: list[str] = []
        while idx < len(lines):
            stripped = lines[idx].strip()
            if block and (stripped.startswith("#") or stripped == "---"):
                break
            block.append(lines[idx])
            idx += 1
        candidate_blocks.append(_trim_blank_lines(block))
    if not candidate_blocks:
        return report_md
    insert_at = next((idx for idx, line in enumerate(output) if _loose_or_canonical_formal_region(line.strip())), 0)
    candidate_lines: list[str] = []
    for block in candidate_blocks:
        if candidate_lines and (candidate_lines[-1].strip() or (block and block[0].strip())):
            candidate_lines.append("")
        candidate_lines.extend(block)
    merged = output[:insert_at]
    if merged and merged[-1].strip():
        merged.append("")
    merged.extend(candidate_lines)
    if output[insert_at:] and merged and merged[-1].strip():
        merged.append("")
    merged.extend(output[insert_at:])
    return "\n".join(_collapse_blank_runs(merged)).strip() + ("\n" if report_md.endswith("\n") else "")


def _ensure_selected_candidate_rows(report_md: str, brief: dict[str, Any]) -> str:
    selected_items = {
        "domestic": _candidate_items(brief.get("domestic_top")),
        "overseas": _candidate_items(brief.get("overseas_top")),
    }
    lines = report_md.splitlines()
    output: list[str] = []
    region = ""
    in_table = False
    header: list[str] = []
    title_idx = selected_idx = None
    seen_contexts: list[str] = []

    def flush_missing_rows() -> None:
        if not region or not in_table or title_idx is None or selected_idx is None:
            return
        for item in _missing_candidate_items(selected_items[region], seen_contexts):
            output.append(_format_row(_candidate_row_from_final_item(header, item, region)))
            seen_contexts.append(_item_title(item))

    for line in lines:
        stripped = line.strip()
        heading_region = _candidate_heading_region(stripped)
        if heading_region or (region and stripped.startswith("#") and not heading_region):
            flush_missing_rows()
            region = heading_region
            in_table = False
            header = []
            title_idx = selected_idx = None
            seen_contexts = []
            output.append(line)
            continue
        if region and in_table and not stripped.startswith("|"):
            flush_missing_rows()
            region = ""
            in_table = False
            header = []
            title_idx = selected_idx = None
            seen_contexts = []
            output.append(line)
            continue
        if not region or not stripped.startswith("|"):
            output.append(line)
            continue
        cells = _split_row(stripped)
        if not cells:
            output.append(line)
            continue
        if not in_table:
            header = cells
            title_idx = _find_col(header, ("事件", "标题"))
            selected_idx = _find_col(header, ("是否入选",))
            in_table = title_idx is not None and selected_idx is not None
            output.append(line)
            continue
        output.append(line)
        if all(re.fullmatch(r":?-{2,}:?", cell.strip()) for cell in cells):
            continue
        if title_idx is not None and title_idx < len(cells):
            seen_contexts.append(_cell(cells[title_idx]))
            seen_contexts.append(" ".join(_cell(cell) for cell in cells))
    flush_missing_rows()
    return "\n".join(output) + ("\n" if report_md.endswith("\n") else "")


def _remove_combined_formal_prelude(report_md: str) -> str:
    lines = report_md.splitlines()
    first_region_idx = next(
        (
            idx
            for idx, line in enumerate(lines)
            if line.strip().startswith("#") and ("国内版" in line or "海外版" in line) and "候选" not in line
        ),
        None,
    )
    if first_region_idx is None:
        return report_md
    last_candidate_idx = max(
        (idx for idx, line in enumerate(lines[:first_region_idx]) if line.strip().startswith("#") and "候选" in line),
        default=-1,
    )
    prelude_start = next(
        (
            idx
            for idx in range(last_candidate_idx + 1, first_region_idx)
            if lines[idx].strip().startswith("#") and "今日总览" in lines[idx]
        ),
        None,
    )
    if prelude_start is None:
        return report_md
    output = lines[:prelude_start] + lines[first_region_idx:]
    return "\n".join(output).strip() + ("\n" if report_md.endswith("\n") else "")


def _ensure_candidate_sections(report_md: str, brief: dict[str, Any]) -> str:
    missing = [region for region in ("domestic", "overseas") if not _has_candidate_region(report_md, region)]
    if not missing:
        return report_md
    block = _candidate_fallback_block(brief, missing)
    lines = report_md.splitlines()
    insert_at = next(
        (
            idx
            for idx, line in enumerate(lines)
            if line.strip().startswith("#") and ("国内版" in line or "海外版" in line) and "候选" not in line
        ),
        0,
    )
    output = lines[:insert_at] + block + [""] + lines[insert_at:]
    return "\n".join(output).strip() + ("\n" if report_md.endswith("\n") else "")


def _has_candidate_region(report_md: str, region: str) -> bool:
    marker = "国内" if region == "domestic" else "海外"
    return any(_candidate_heading_region(line.strip()) == region for line in report_md.splitlines() if marker in line)


def _candidate_fallback_block(brief: dict[str, Any], regions: list[str]) -> list[str]:
    header = [
        "事件",
        "地区",
        "来源层级",
        "来源类型",
        "source_fit",
        "信号类型",
        "event_date",
        "report_date",
        "signal_date",
        "是否前延回看",
        "层级",
        "类别",
        "初步优先级",
        "可信度",
        "数据口径",
        "是否入选",
        "入选/剔除原因",
    ]
    lines = ["## 候选事件筛选表"]
    for region in regions:
        lines.extend(["", _canonical_candidate_heading(region), "", _format_row(header), _format_row(["---"] * len(header))])
        for item in _candidate_items(brief.get(f"{region}_top")):
            lines.append(_format_row(_candidate_row_from_final_item(header, item, region)))
    return lines


def _canonical_candidate_heading(region: str) -> str:
    label = "国内" if region == "domestic" else "海外"
    return f"## {label}候选事件筛选表"


def _candidate_items(items: Any) -> list[dict[str, Any]]:
    return [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []


def _missing_candidate_items(items: list[dict[str, Any]], seen_contexts: list[str]) -> list[dict[str, Any]]:
    missing: list[dict[str, Any]] = []
    for item in items:
        selected_titles = _selected_titles([item])
        if not selected_titles:
            continue
        if any(_matches_any(seen_context, selected_titles) for seen_context in seen_contexts):
            continue
        missing.append(item)
    return missing


def _candidate_row_from_final_item(header: list[str], item: dict[str, Any], region: str) -> list[str]:
    label = "国内" if region == "domestic" else "海外"
    return [_candidate_cell_for_column(column, item, label) for column in header]


def _candidate_cell_for_column(column: str, item: dict[str, Any], region_label: str) -> str:
    cleaned = column.strip().lower()
    if "事件" in column or "标题" in column:
        return _item_title(item)
    if "地区" in column:
        return region_label
    if "是否入选" in column:
        return "是"
    if "入选" in column or "剔除" in column or "原因" in column:
        return "进入最终 Top；由后置 gate/brief 回写。"
    if "优先级" in column:
        return _cell(str(item.get("priority") or "-"))
    if "可信度" in column:
        return _cell(str(item.get("confidence") or "-"))
    if "层级" in column and "来源" not in column:
        return _cell(str(item.get("layer") or "-"))
    if "来源层级" in column:
        return "-"
    if "来源类型" in column:
        return "final_top"
    if cleaned == "source_fit":
        return "-"
    if "信号类型" in column:
        return "final_top"
    return "-"


def _replace_formal_region(report_md: str, region: str, items: Any, window: TimeWindow) -> str:
    lines = report_md.splitlines()
    start = _formal_region_start(lines, region)
    if start is None:
        return report_md
    end = _formal_region_end(lines, start, region)
    item_list = [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []
    original_section = lines[start:end]
    replacement = _preserve_formal_section_from_report(original_section, region, item_list, window)
    if replacement is None:
        replacement = _formal_section_from_final_top(lines[start], region, item_list, window)
    replacement[0] = _canonical_formal_heading(region, window)
    output = lines[:start] + replacement + lines[end:]
    return "\n".join(output) + ("\n" if report_md.endswith("\n") else "")


def _preserve_formal_section_from_report(
    section_lines: list[str], region: str, items: list[dict[str, Any]], window: TimeWindow
) -> list[str] | None:
    if not section_lines:
        return None
    if not items:
        return _empty_formal_section_from_report(section_lines, region, window)

    overview = _preserved_overview_section(section_lines, items)
    deep = _preserved_deep_dive_section(section_lines, items)
    observations = _preserved_observation_section(section_lines)
    if not overview and not deep:
        return None

    output = [section_lines[0], ""]
    output.extend(overview or _generated_overview_section(items))
    output.extend(["", "### 二、逐条深度解读", ""])
    output.extend(deep or _generated_deep_dive_blocks(items))
    if observations:
        output.extend(["", *observations, "", *_generated_core_judgment_section(region, items, window)])
    else:
        output.extend(["", *_generated_formal_tail(region, items, window)])
    return output


def _preserved_overview_section(section_lines: list[str], items: list[dict[str, Any]]) -> list[str]:
    start, end = _named_subsection_range(section_lines, "今日总览")
    if start is None:
        return []
    section = section_lines[start:end]
    header_idx = next((idx for idx, line in enumerate(section) if line.strip().startswith("|") and "标题" in line), None)
    if header_idx is None:
        return []
    output = ["### 一、今日总览", ""]
    output.append(section[header_idx])
    if header_idx + 1 < len(section) and _is_table_separator(section[header_idx + 1]):
        output.append(section[header_idx + 1])
        row_start = header_idx + 2
    else:
        output.append("|---|---|---|---|---|")
        row_start = header_idx + 1
    used_rows: set[int] = set()
    rows = [line for line in section[row_start:] if line.strip().startswith("|") and not _is_table_separator(line)]
    for item in items:
        match_idx = next(
            (row_index for row_index, row in enumerate(rows) if row_index not in used_rows and _row_matches_item(row, item)),
            None,
        )
        if match_idx is not None:
            output.append(rows[match_idx])
            used_rows.add(match_idx)
        else:
            output.append(_overview_row_from_item(item))
    return output


def _preserved_deep_dive_section(section_lines: list[str], items: list[dict[str, Any]]) -> list[str]:
    start, end = _named_subsection_range(section_lines, "逐条深度解读")
    if start is None:
        return []
    blocks = _deep_dive_blocks(section_lines[start + 1 : end])
    if not blocks:
        return []
    output: list[str] = []
    used: set[int] = set()
    for index, item in enumerate(items, start=1):
        match_idx = next(
            (
                block_idx
                for block_idx, block in enumerate(blocks)
                if block_idx not in used and _block_matches_item(block, item)
            ),
            None,
        )
        if match_idx is None:
            output.extend(_generated_deep_dive_block(item, index))
        else:
            used.add(match_idx)
            block = _renumber_deep_dive_block(blocks[match_idx], index)
            block = _ensure_block_has_so_what(block, item)
            output.extend(_ensure_block_has_source(block, item))
        if index < len(items) and (not output or output[-1].strip()):
            output.append("")
    return output


def _preserved_formal_tail(section_lines: list[str]) -> list[str]:
    watch_start, _ = _named_subsection_range(section_lines, "观察信号")
    judgment_start, _ = _named_subsection_range(section_lines, "今日核心判断")
    candidates = [idx for idx in (watch_start, judgment_start) if idx is not None]
    if not candidates:
        return []
    tail = section_lines[min(candidates) :]
    return tail if any(line.strip() for line in tail[1:]) else []


def _preserved_observation_section(section_lines: list[str]) -> list[str]:
    start, end = _named_subsection_range(section_lines, "观察信号")
    if start is None:
        return []
    section = section_lines[start:end]
    section[0] = "### 三、观察信号"
    return section if any(line.strip() for line in section[1:]) else []


def _generated_overview_section(items: list[dict[str, Any]]) -> list[str]:
    lines = [
        "### 一、今日总览",
        "",
        "| 标题 | 层级 | 优先级 | 可信度 | 影响方向 |",
        "|---|---|---|---|---|",
    ]
    lines.extend(_overview_row_from_item(item) for item in items)
    return lines


def _overview_row_from_item(item: dict[str, Any]) -> str:
    return (
        "| "
        + " | ".join(
            [
                _cell(_item_title(item)),
                _cell(str(item.get("layer") or "-")),
                _cell(str(item.get("priority") or "-")),
                _cell(str(item.get("confidence") or "-")),
                _cell(str(item.get("card_why") or item.get("why") or "进入最终 Top。")),
            ]
        )
        + " |"
    )


def _generated_deep_dive_blocks(items: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for index, item in enumerate(items, start=1):
        lines.extend(_generated_deep_dive_block(item, index))
        if index < len(items):
            lines.append("")
    return lines


def _generated_deep_dive_block(item: dict[str, Any], index: int) -> list[str]:
    why = _cell(str(item.get("why") or item.get("card_why") or "该事件进入最终 Top。"))
    return [
        f"{index}. **{_cell(_item_title(item))}**",
        f"   - 优先级：{_cell(str(item.get('priority') or '-'))}",
        f"   - 为什么重要：{why}",
        f"   - 来源：{_source_summary(item)}",
    ]


def _generated_formal_tail(region: str, items: list[dict[str, Any]], window: TimeWindow) -> list[str]:
    label = "国内" if region == "domestic" else "海外"
    return [
        "### 三、观察信号",
        "",
        "详见候选事件筛选表中未入选条目。",
        "",
        "### 四、今日核心判断",
        "",
        f"- {window.zh_date} {label}正式雷达共保留 {len(items)} 条最终 Top；候选表继续保留未入选事件的核心判断、观察信号与阻断原因。",
    ]


def _generated_core_judgment_section(region: str, items: list[dict[str, Any]], window: TimeWindow) -> list[str]:
    label = "国内" if region == "domestic" else "海外"
    lines = ["### 四、今日核心判断", ""]
    for item in items:
        why = _cell(str(item.get("why") or item.get("card_why") or "")).strip()
        title = _cell(_item_title(item))
        if why:
            lines.append(f"- **{title}**：{why}")
        else:
            lines.append(f"- **{title}**：进入 {window.zh_date} {label}正式雷达最终 Top。")
    if not items:
        lines.append(f"- {window.zh_date} {label}未形成可发布的最终 Top。")
    return lines


def _named_subsection_range(section_lines: list[str], keyword: str) -> tuple[int | None, int]:
    start = next(
        (idx for idx, line in enumerate(section_lines) if line.strip().startswith("#") and keyword in line),
        None,
    )
    if start is None:
        return None, len(section_lines)
    for idx in range(start + 1, len(section_lines)):
        stripped = section_lines[idx].strip()
        if stripped.startswith("#") and _is_formal_subsection_heading(stripped):
            return start, idx
    return start, len(section_lines)


def _is_formal_subsection_heading(line: str) -> bool:
    return any(keyword in line for keyword in ("今日总览", "逐条深度解读", "观察信号", "核心判断", "输出前", "自我检查"))


def _deep_dive_blocks(lines: list[str]) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if _deep_dive_item_title(line):
            if current:
                blocks.append(_trim_blank_lines(current))
            current = [line]
            continue
        if current:
            current.append(line)
    if current:
        blocks.append(_trim_blank_lines(current))
    return blocks


def _deep_dive_item_title(line: str) -> str:
    if re.match(r"^\s+\d+[.、]", line):
        return ""
    stripped = line.strip()
    patterns = (
        r"^\*\*\s*\d+[.、]\s*(.+?)\*\*",
        r"^\d+[.、]\s*\*\*(.+?)\*\*",
        r"^\d+[.、]\s*(.+)$",
        r"^#{3,6}\s*(?:\d+[.、]\s*)?\*\*(.+?)\*\*",
        r"^#{3,6}\s*(?:\d+[.、]\s*)?(.+?)$",
    )
    for pattern in patterns:
        match = re.match(pattern, stripped)
        if not match:
            continue
        title = re.sub(r"^【[^】]+】", "", match.group(1)).strip()
        if _is_formal_subsection_heading(title):
            return ""
        return title.strip("* ")
    return ""


def _renumber_deep_dive_block(block: list[str], index: int) -> list[str]:
    if not block:
        return []
    output = list(block)
    title = _deep_dive_item_title(output[0])
    if re.match(r"^\s*\d+[.、]", output[0]):
        output[0] = re.sub(r"^(\s*)\d+([.、])", rf"\g<1>{index}\2", output[0], count=1)
    elif title:
        output[0] = f"{index}. **{_cell(title)}**"
    return _trim_blank_lines(output)


def _ensure_block_has_source(block: list[str], item: dict[str, Any]) -> list[str]:
    if any("http://" in line or "https://" in line for line in block):
        return block
    return [*block, f"   - 来源：{_source_summary(item)}"]


def _ensure_block_has_so_what(block: list[str], item: dict[str, Any]) -> list[str]:
    why = _cell(str(item.get("why") or item.get("card_why") or "")).strip()
    if not why:
        return block
    output: list[str] = []
    for line in block:
        if _is_empty_so_what_line(line):
            indent = re.match(r"^(\s*)", line).group(1)
            output.append(f"{indent}- **影响 / So what**：{why}")
        else:
            output.append(line)
    return output


def _is_empty_so_what_line(line: str) -> bool:
    text = re.sub(r"[*`]", "", str(line or "").strip())
    return bool(re.match(r"^[-*]?\s*(?:影响\s*/\s*So what|So what|影响)\s*[:：]\s*$", text, flags=re.IGNORECASE))


def _block_matches_item(block: list[str], item: dict[str, Any]) -> bool:
    if not block:
        return False
    title = _deep_dive_item_title(block[0])
    if title and _matches_any(title, _selected_titles([item])):
        return True
    return _matches_any(" ".join(_cell(line) for line in block[:3]), _selected_titles([item]))


def _row_matches_item(row: str, item: dict[str, Any]) -> bool:
    cells = _split_row(row)
    if not cells:
        return False
    return _matches_any(cells[0], _selected_titles([item]))


def _is_table_separator(line: str) -> bool:
    cells = _split_row(line)
    return bool(cells) and all(re.fullmatch(r":?-{2,}:?", cell.strip()) for cell in cells)


def _trim_blank_lines(lines: list[str]) -> list[str]:
    start = 0
    end = len(lines)
    while start < end and not lines[start].strip():
        start += 1
    while end > start and not lines[end - 1].strip():
        end -= 1
    return lines[start:end]


def _ensure_formal_sections(report_md: str, brief: dict[str, Any], window: TimeWindow) -> str:
    report = report_md
    for region in ("domestic", "overseas"):
        lines = report.splitlines()
        if _formal_region_start(lines, region) is not None:
            continue
        report = _insert_formal_region(report, region, brief.get(f"{region}_top") or [], window)
    return report


def _insert_formal_region(report_md: str, region: str, items: Any, window: TimeWindow) -> str:
    lines = report_md.splitlines()
    item_list = [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []
    replacement = _formal_section_from_final_top(_canonical_formal_heading(region, window), region, item_list, window)
    insert_at = _formal_insert_index(lines, region)
    output = _insert_block(lines, insert_at, replacement)
    return "\n".join(output).strip() + ("\n" if report_md.endswith("\n") else "")


def _empty_formal_section_from_report(section_lines: list[str], region: str, window: TimeWindow) -> list[str]:
    label = "国内" if region == "domestic" else "海外"
    observations = _preserved_observation_section(section_lines)
    output = [
        section_lines[0],
        "",
        "### 一、今日总览",
        "",
        "| 标题 | 层级 | 优先级 | 可信度 | 影响方向 |",
        "|---|---|---|---|---|",
        f"| 今日{label}无强核心事件 | - | - | - | 不强行凑数 |",
        "",
        "### 二、逐条深度解读",
        "",
        f"今日{label}未保留最终 Top。候选事件仍保留在筛选表中，核心判断、观察信号与阻断原因以候选表为准。",
        "",
    ]
    if observations:
        output.extend(observations)
    else:
        output.extend(["### 三、观察信号", "", "详见候选事件筛选表中未入选条目。"])
    output.extend(
        [
            "",
            "### 四、今日核心判断",
            "",
            f"- {window.zh_date} {label}未形成可发布的最终 Top；候选事件可能包含核心判断或观察信号，但仍受来源、新增性、确定性、去重或发布预算约束。",
        ]
    )
    return output


def _canonical_formal_heading(region: str, window: TimeWindow) -> str:
    label = "国内" if region == "domestic" else "海外"
    return f"# AI 前沿能力与应用雷达 - {label}版【{window.zh_date}】"


def _formal_insert_index(lines: list[str], region: str) -> int:
    if region == "domestic":
        overseas_start = _formal_region_start(lines, "overseas")
        if overseas_start is not None:
            return overseas_start
    domestic_start = _formal_region_start(lines, "domestic")
    if region == "overseas" and domestic_start is not None:
        return _formal_region_end(lines, domestic_start, "domestic")
    footer_start = _footer_section_start(lines)
    if footer_start is not None:
        return footer_start
    return len(lines)


def _footer_section_start(lines: list[str]) -> int | None:
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue
        if any(marker in stripped for marker in ("输出前", "自我检查", "来源", "附录", "Source", "source", "Appendix", "appendix")):
            return idx
    return None


def _insert_block(lines: list[str], insert_at: int, block: list[str]) -> list[str]:
    output = list(lines[:insert_at])
    if output and output[-1].strip():
        output.append("")
    output.extend(block)
    if lines[insert_at:] and output and output[-1].strip():
        output.append("")
    output.extend(lines[insert_at:])
    return output


def _ensure_self_check_section(report_md: str) -> str:
    if _has_self_check_section(report_md):
        return report_md
    lines = report_md.splitlines()
    insert_at = _footer_section_start(lines)
    if insert_at is None:
        insert_at = len(lines)
    output = _insert_block(lines, insert_at, _self_check_block())
    return "\n".join(output).strip() + ("\n" if report_md.endswith("\n") else "")


def _has_self_check_section(report_md: str) -> bool:
    text = report_md.lower()
    if any(marker in text for marker in ("输出前自我检查清单", "自我检查清单", "输出前检查", "输出前自检", "自检清单", "self check", "checklist")):
        return True
    return len(re.findall(r"- \[[ xX]\]", report_md)) >= 2


def _self_check_block() -> list[str]:
    return [
        "## 输出前自我检查清单",
        "",
        "- [x] 候选事件筛选表已保留，入选状态由 final brief 回写。",
        "- [x] 国内/海外正式雷达已对齐 final Top；无强核心事件时明确不强行凑数。",
        "- [x] 发布前由 report_lint/top_event_audit 继续校验证据、URL 与 Top 质量。",
    ]


def _selected_titles(items: Any) -> list[str]:
    titles: list[str] = []

    def add(value: Any) -> None:
        title = str(value or "").strip()
        if not title:
            return
        normalized = _normalize_title(title)
        if normalized and normalized not in titles:
            titles.append(normalized)

    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        for key in ("title", "card_title"):
            add(item.get(key))
        sources = item.get("sources")
        if isinstance(sources, list):
            for source in sources:
                if not isinstance(source, dict):
                    continue
                add(source.get("title"))
                add(source.get("evidence_id"))
        source_ids = item.get("source_ids")
        if isinstance(source_ids, list):
            for source_id in source_ids:
                add(source_id)
    return titles


def _candidate_heading_region(line: str) -> str:
    if not line.startswith("#") or "候选" not in line:
        return ""
    if "国内" in line:
        return "domestic"
    if "海外" in line:
        return "overseas"
    return ""


def _loose_or_canonical_formal_region(line: str) -> bool:
    if not line.startswith("#") or "候选" in line:
        return False
    return "国内版" in line or "海外版" in line


def _formal_region_start(lines: list[str], region: str) -> int | None:
    marker = "国内版" if region == "domestic" else "海外版"
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("#") and marker in stripped and "候选" not in stripped:
            return idx
    return None


def _formal_region_end(lines: list[str], start: int, region: str) -> int:
    next_marker = "海外版" if region == "domestic" else ""
    for idx in range(start + 1, len(lines)):
        stripped = lines[idx].strip()
        if not stripped.startswith("#"):
            continue
        if next_marker and next_marker in stripped and "候选" not in stripped:
            return idx
        if any(marker in stripped for marker in ("候选", "输出前", "自我检查", "来源", "附录", "Source", "source", "Appendix", "appendix")):
            return idx
    return len(lines)


def _drop_existing_self_check_sections(report_md: str) -> str:
    lines = report_md.splitlines()
    output: list[str] = []
    skipping = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#") and ("输出前" in stripped or "自我检查" in stripped):
            skipping = True
            continue
        if skipping and (
            stripped.startswith("#")
            or stripped.startswith(("来源", "Source", "source"))
            or stripped.startswith(("http://", "https://"))
        ):
            skipping = False
        if not skipping:
            output.append(line)
    return "\n".join(output).strip() + ("\n" if report_md.endswith("\n") else "")


def _strip_leading_horizontal_rules(report_md: str) -> str:
    lines = report_md.splitlines()
    while lines and (not lines[0].strip() or lines[0].strip() == "---"):
        lines.pop(0)
    return "\n".join(lines).strip() + ("\n" if report_md.endswith("\n") else "")


def _collapse_blank_runs(lines: list[str]) -> list[str]:
    output: list[str] = []
    blank_count = 0
    for line in lines:
        if line.strip():
            blank_count = 0
            output.append(line)
            continue
        blank_count += 1
        if blank_count <= 2:
            output.append(line)
    return output


def _empty_formal_section(original_heading: str, region: str, window: TimeWindow) -> list[str]:
    label = "国内" if region == "domestic" else "海外"
    return [
        original_heading,
        "",
        "### 一、今日总览",
        "",
        "| 标题 | 层级 | 优先级 | 可信度 | 影响方向 |",
        "|---|---|---|---|---|",
        f"| 今日{label}无强核心事件 | - | - | - | 不强行凑数 |",
        "",
        "### 二、逐条深度解读",
        "",
        f"今日{label}未保留最终 Top。候选事件仍保留在筛选表中，核心判断、观察信号与阻断原因以候选表为准。",
        "",
        "### 三、观察信号",
        "",
        "详见候选事件筛选表中未入选条目。",
        "",
        "### 四、今日核心判断",
        "",
        f"- {window.zh_date} {label}未形成可发布的最终 Top；候选事件可能包含核心判断或观察信号，但仍受来源、新增性、确定性、去重或发布预算约束。",
    ]


def _formal_section_from_final_top(original_heading: str, region: str, items: list[dict[str, Any]], window: TimeWindow) -> list[str]:
    if not items:
        return _empty_formal_section(original_heading, region, window)
    label = "国内" if region == "domestic" else "海外"
    lines = [
        original_heading,
        "",
        "### 一、今日总览",
        "",
        "| 标题 | 层级 | 优先级 | 可信度 | 影响方向 |",
        "|---|---|---|---|---|",
    ]
    for item in items:
        lines.append(
            "| "
            + " | ".join(
                [
                    _cell(_item_title(item)),
                    _cell(str(item.get("layer") or "-")),
                    _cell(str(item.get("priority") or "-")),
                    _cell(str(item.get("confidence") or "-")),
                    _cell(str(item.get("card_why") or item.get("why") or "进入最终 Top。")),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "### 二、逐条深度解读",
            "",
        ]
    )
    for index, item in enumerate(items, start=1):
        why = item.get("why") or item.get("card_why") or "该事件进入最终 Top。"
        lines.extend(
            [
                f"{index}. **{_cell(_item_title(item))}**",
                f"   - 优先级：{_cell(str(item.get('priority') or '-'))}",
                f"   - 为什么重要：{_cell(why)}",
                f"   - 来源：{_source_summary(item)}",
                "",
            ]
        )
    lines.extend(
        [
            "### 三、观察信号",
            "",
            "详见候选事件筛选表中未入选条目。",
            "",
            "### 四、今日核心判断",
            "",
            f"- {window.zh_date} {label}正式雷达共保留 {len(items)} 条最终 Top；候选表继续保留未入选事件的核心判断、观察信号与阻断原因。",
        ]
    )
    return lines


def _item_title(item: dict[str, Any]) -> str:
    return str(item.get("title") or item.get("card_title") or "未命名事件").strip()


def _source_summary(item: dict[str, Any]) -> str:
    sources = item.get("sources")
    parts: list[str] = []
    if isinstance(sources, list):
        for source in sources:
            if not isinstance(source, dict):
                continue
            name = _cell(str(source.get("source") or source.get("title") or source.get("evidence_id") or "来源").strip())
            url = str(source.get("url") or "").strip()
            parts.append(f"[{name}]({url})" if url else name)
    if parts:
        return "；".join(parts[:3])
    source_ids = item.get("source_ids")
    if isinstance(source_ids, list) and source_ids:
        return "source_ids: " + ", ".join(_cell(str(source_id)) for source_id in source_ids[:3])
    return "来源见候选事件筛选表。"


def _compact_text(value: Any, max_len: int) -> str:
    text = _cell(str(value or "").strip())
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


def _cell(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("|", "｜")).strip()


def _split_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _format_row(cells: list[str]) -> str:
    return "| " + " | ".join(cells) + " |"


def _find_col(header: list[str], names: tuple[str, ...]) -> int | None:
    for idx, cell in enumerate(header):
        if any(name in cell for name in names):
            return idx
    return None


def _has_future_date(cells: list[str], target_date: str) -> bool:
    for cell in cells:
        for match in re.findall(r"\b20\d{2}-\d{2}-\d{2}\b", str(cell or "")):
            if match > target_date:
                return True
    return False


def _is_p3_candidate(cells: list[str], header: list[str]) -> bool:
    priority = _cell_for_header(cells, header, "初步优先级")
    return "P3" in priority.upper()


def _is_placeholder_reason(value: str) -> bool:
    normalized = str(value or "").strip()
    return normalized in {"", "候选", "入选", "是", "否", "否（观察信号）", "观察", "—", "-"}


def _is_exclusion_reason(value: str) -> bool:
    normalized = re.sub(r"\s+", "", str(value or "")).lower()
    return (
        normalized.startswith("未进入最终top")
        or "新增性不足" in normalized
        or "后置gate/brief未保留" in normalized
        or "不是同一事件" in normalized
        or "未达当日核心事件阈值" in normalized
        or "来源层级或source_fit不足" in normalized
    )


def _candidate_exclusion_reason(cells: list[str], header: list[str], original_reason: str = "") -> str:
    combined = " ".join(
        _cell(value)
        for value in (
            original_reason,
            _cell_for_header(cells, header, "来源层级"),
            _cell_for_header(cells, header, "来源类型"),
            _cell_for_header(cells, header, "source_fit"),
            _cell_for_header(cells, header, "信号类型"),
            _cell_for_header(cells, header, "event_date"),
            _cell_for_header(cells, header, "是否前延回看"),
            _cell_for_header(cells, header, "初步优先级"),
            _cell_for_header(cells, header, "可信度"),
            _cell_for_header(cells, header, "数据口径"),
            _cell_for_header(cells, header, "类别"),
        )
        if str(value or "").strip()
    )
    normalized = combined.lower()
    lookback = _cell_for_header(cells, header, "是否前延回看").strip()
    if "传闻" in combined or "rumor" in normalized or "media-reported estimate" in normalized or "待官方确认" in combined:
        return "未进入最终 Top：仍属传闻或待确认信息，缺少足够官方证据。"
    if "重复" in combined or "无新增" in combined or "旧闻" in combined:
        return "未进入最终 Top：与既有事件重复或缺少当日新增官方事实。"
    if "不是同一事件" in combined:
        return "未进入最终 Top：与最终 Top 不是同一事件，可继续作为观察信号跟踪。"
    if "未最终保留" in combined or "后置 gate" in normalized or "后置gate" in combined:
        return "未进入最终 Top：后置 gate/brief 未保留，可继续作为观察信号跟踪。"
    if lookback.startswith("是") or "前延" in combined or "回看" in combined or "out_of_window" in normalized or "old_repeated" in normalized:
        return "未进入最终 Top：属于前延/后续报道，新增性不足。"
    if "s4" in normalized or "s5" in normalized or (("source_fit" in normalized or "sourcefit" in normalized) and "低" in combined) or "低source_fit" in combined:
        return "未进入最终 Top：来源层级或 source_fit 不足，可继续作为观察信号跟踪。"
    if any(marker in normalized for marker in ("media summary", "analyst estimate", "third-party data")) or any(
        marker in combined for marker in ("媒体总结", "媒体摘要", "分析", "观点", "研报", "第三方数据", "券商")
    ):
        return "未进入最终 Top：属于媒体总结/分析观点或第三方数据，缺少当日直接官方进展。"
    if any(marker in combined for marker in ("法律未决", "诉讼", "公关", "组织", "案例演示", "小工具", "促销")):
        return "未进入最终 Top：事件相关性或直接行业影响不足，可继续作为观察信号跟踪。"
    if "p3" in normalized or "观察" in combined:
        return "未进入最终 Top：相对当日最终 Top 的新增性、确定性或影响强度不足，可继续作为观察信号跟踪。"
    return "未进入最终 Top：相对当日最终 Top 的新增性、确定性或影响强度不足。"


def _candidate_row_is_stale_without_new_signal(cells: list[str], header: list[str], window: TimeWindow) -> bool:
    if not _has_candidate_evidence_context(cells, header):
        return False
    combined = " ".join(_cell(value) for value in cells if str(value or "").strip())
    normalized = combined.lower()
    event_date = _cell_for_header(cells, header, "event_date")
    lookback = _cell_for_header(cells, header, "是否前延回看")
    reason_idx = _find_col(header, ("入选/剔除原因", "原因"))
    metadata_context = " ".join(
        _cell(value) for idx, value in enumerate(cells) if idx != reason_idx and str(value or "").strip()
    )
    stale = (
        _has_date_before_target(event_date, window.date_str)
        or lookback.strip().startswith("是")
        or "前延" in combined
        or "回看" in combined
        or "old_repeated" in normalized
        or "out_of_window" in normalized
    )
    if not stale:
        return False
    if _has_strong_same_day_signal(metadata_context):
        return False
    if any(marker in combined for marker in ("新增性不足", "无新增", "旧闻", "旧事件", "缺少当日新增", "属于前延/后续")):
        return True
    if not _has_strong_same_day_signal(combined):
        return True
    return False


def _has_date_before_target(value: str, target_date: str) -> bool:
    return any(match < target_date for match in re.findall(r"\b20\d{2}-\d{2}-\d{2}\b", str(value or "")))


def _has_strong_same_day_signal(value: str) -> bool:
    text = re.sub(r"\s+", "", str(value or ""))
    if "新增性不足" in text or "无新增" in text or "缺少当日新增" in text:
        return False
    if re.search(r"披露.*?(roi|效率|缺陷|节省|客户|采用|收入|调用|数据|token)", text, flags=re.IGNORECASE):
        return True
    return bool(
        re.search(
            r"(今日|当日|当天)?(新增|新披露|首次披露|最新披露|数据更新|新数据|新价格|新融资|新上线|新采用|新客户|新营收|新调用量)",
            text,
            flags=re.IGNORECASE,
        )
    )


def _cell_for_header(cells: list[str], header: list[str], name: str) -> str:
    idx = _find_col(header, (name,))
    if idx is None or idx >= len(cells):
        return ""
    return cells[idx]


def _matching_selected_item_index(title: str, items: list[dict[str, Any]]) -> int | None:
    for index, item in enumerate(items):
        if _matches_any(title, _selected_titles([item])):
            return index
    return None


def _has_candidate_evidence_context(cells: list[str], header: list[str]) -> bool:
    title_idx = _find_col(header, ("事件", "标题"))
    if title_idx is not None and title_idx < len(cells) and re.search(r"\bE\d+\b", cells[title_idx], flags=re.IGNORECASE):
        return True
    context_columns = (
        "来源层级",
        "来源类型",
        "source_fit",
        "信号类型",
        "event_date",
        "report_date",
        "signal_date",
        "数据口径",
    )
    for column in context_columns:
        value = _cell_for_header(cells, header, column).strip()
        if value and value not in {"-", "—", "final_top"}:
            return True
    return False


def _matches_any(title: str, selected_titles: list[str]) -> bool:
    normalized = _normalize_title(title)
    if not normalized:
        return False
    row_evidence_ids = set(re.findall(r"e\d+", normalized))
    for selected in selected_titles:
        if re.fullmatch(r"e\d+", selected) and selected in row_evidence_ids:
            return True
        if normalized == selected:
            return True
        if len(normalized) >= 8 and len(selected) >= 8 and (normalized in selected or selected in normalized):
            return True
        if _shares_key_event_tokens(normalized, selected):
            return True
        if min(len(normalized), len(selected)) >= 8 and SequenceMatcher(None, normalized, selected).ratio() >= 0.74:
            return True
        if _longest_common_substring_len(normalized, selected) >= 7 and SequenceMatcher(None, normalized, selected).ratio() >= 0.62:
            return True
    return False


def _normalize_title(value: str) -> str:
    text = re.sub(r"\[[^\]]+\]\([^)]+\)", "", str(value or "")).lower()
    text = re.sub(r"[\s\-_—:：|｜，,。.!！?？（）()【】\[\]\"'“”‘’…]+", "", text)
    return text


def _shares_key_event_tokens(left: str, right: str) -> bool:
    left_tokens = _event_terms(left)
    right_tokens = _event_terms(right)
    shared_tokens = left_tokens & right_tokens
    action_markers = ("收购", "发布", "推出", "上线", "限制", "道歉", "部署", "扩展", "授权", "恢复", "借", "融资", "支付", "退款")
    shared_actions = [marker for marker in action_markers if marker in left and marker in right]
    private_service_terms = {"私域", "客服", "企微", "企业微信", "群聊", "社群", "运营", "新标配", "3chat"}
    if len(shared_tokens & private_service_terms) >= 3 and {"私域", "客服"} <= shared_tokens:
        return True
    if "3chat" in shared_tokens and "客服" in shared_tokens:
        return True
    if {"私域", "客服"} <= shared_tokens and (left_tokens | right_tokens) & {"3chat", "企微", "企业微信", "群聊", "社群"}:
        return True
    feishu_roi_terms = {"飞书", "大湾区", "德赛西威", "roi", "产研", "智能体", "制造业", "年省", "节省", "5800", "5832"}
    if "飞书" in shared_tokens and len(shared_tokens & feishu_roi_terms) >= 2:
        return True
    gpt_terms = {"gpt5", "gpt56"}
    preview_terms = {"预览", "previewing"}
    if shared_tokens & gpt_terms and (left_tokens & preview_terms or right_tokens & preview_terms):
        return True
    delay_terms = {"delay", "slowroll", "slow", "roll", "whitehouse", "白宫", "缓释", "推迟", "要求"}
    if "openai" in shared_tokens and shared_tokens & gpt_terms and left_tokens & delay_terms and right_tokens & delay_terms:
        return True
    codex_work_terms = {"codex", "chatgpt", "输出"}
    openai_agent_terms = {"agent", "adoption", "采用", "内部"}
    if "openai" in shared_tokens and (
        (left_tokens & openai_agent_terms and right_tokens & codex_work_terms)
        or (right_tokens & openai_agent_terms and left_tokens & codex_work_terms)
    ):
        return True
    strong_anchor_tokens = {"ona", "bbva", "chatgptenterprise", "doordash", "askdoordash", "diffusiongemma"}
    if shared_tokens & strong_anchor_tokens and (len(shared_tokens) >= 2 or bool(shared_actions)):
        return True
    if "36氪" in left and "36氪" in right and "发文" in left and "发文" in right:
        return True
    return len(shared_tokens) >= 2 and bool(shared_actions)


def _event_terms(value: str) -> set[str]:
    text = str(value or "")
    terms = set(re.findall(r"[a-z0-9]{3,}", text))
    known_terms = (
        "openai",
        "gpt56",
        "gpt5",
        "whitehouse",
        "previewing",
        "slowroll",
        "slow",
        "roll",
        "delay",
        "codex",
        "chatgpt",
        "token",
        "agent",
        "adoption",
        "claude",
        "anthropic",
        "mythos",
        "mythos5",
        "doordash",
        "ona",
        "bbva",
        "nvidia",
        "apple",
        "输出",
        "预览",
        "采用",
        "内部",
        "私域",
        "客服",
        "企微",
        "企业微信",
        "群聊",
        "社群",
        "运营",
        "新标配",
        "3chat",
        "白宫",
        "缓释",
        "推迟",
        "要求",
        "政府",
        "授权",
        "有限",
        "恢复",
        "实体",
        "战略资源",
        "飞书",
        "大湾区",
        "德赛西威",
        "roi",
        "产研",
        "智能体",
        "制造业",
        "年省",
        "节省",
        "5800",
        "5832",
    )
    for term in known_terms:
        if term in text:
            terms.add(term)
    return terms


def _longest_common_substring_len(left: str, right: str) -> int:
    if not left or not right:
        return 0
    previous = [0] * (len(right) + 1)
    best = 0
    for left_char in left:
        current = [0] * (len(right) + 1)
        for idx, right_char in enumerate(right, start=1):
            if left_char == right_char:
                current[idx] = previous[idx - 1] + 1
                best = max(best, current[idx])
        previous = current
    return best
