from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import date as Date
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit, urlunsplit

from .models import EvidenceItem


URL_RE = re.compile(r"https?://[^\s)\]}>\"']+")


@dataclass
class ReportLintResult:
    passed: bool = True
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    critical_errors: list[str] = field(default_factory=list)
    source_url_count: int = 0
    source_appendix_present: bool = False
    summary: dict[str, int] = field(default_factory=dict)

    def finalize(self, *, strict: bool = False) -> ReportLintResult:
        self.summary = {
            "warnings_count": len(self.warnings),
            "errors_count": len(self.errors),
            "critical_errors_count": len(self.critical_errors),
        }
        self.passed = not self.critical_errors and (not strict or not self.errors)
        return self

    def to_dict(self) -> dict[str, bool | list[str] | dict[str, int]]:
        self.summary = {
            "warnings_count": len(self.warnings),
            "errors_count": len(self.errors),
            "critical_errors_count": len(self.critical_errors),
        }
        return asdict(self)


def lint_report(
    report_md: str,
    evidence: list[EvidenceItem],
    *,
    strict: bool = False,
    target_date: str | Date | None = None,
) -> ReportLintResult:
    result = ReportLintResult()
    if not report_md.strip():
        result.critical_errors.append("report is empty")
        return result.finalize(strict=strict)
    result.source_appendix_present = "## 附录：本次证据来源索引" in report_md
    if not evidence:
        result.critical_errors.append("evidence_count is 0")
    _check_llm_preamble(report_md, result)
    _check_required_sections(report_md, result)
    _check_urls(report_md, evidence, result)
    _check_placeholders(report_md, result)
    _check_no_forced_count(report_md, result)
    _check_formal_radar_count_limit(report_md, result)
    _check_empty_so_what(report_md, result)
    _check_non_daily_core_judgment_heading(report_md, result)
    _check_future_candidate_dates(report_md, result, target_date)
    _check_candidate_tables_before_formal(report_md, result)
    _check_candidate_table_prose_after_rows(report_md, result)
    _check_no_p3_candidate_rows(report_md, result)
    _check_obvious_llm_failure(report_md, result)
    return result.finalize(strict=strict)


def _check_required_sections(report_md: str, result: ReportLintResult) -> None:
    required = {
        "domestic_candidates": ("国内候选事件筛选表", "国内版候选事件筛选表", "国内候选事件表", "国内候选池", "国内候选", "国内版候选", "国内事件筛选"),
        "overseas_candidates": ("海外候选事件筛选表", "海外版候选事件筛选表", "海外候选事件表", "海外候选池", "海外候选", "海外版候选", "海外事件筛选"),
        "domestic_radar": (
            "国内版正式雷达",
            "国内正式雷达",
            "国内版雷达",
            "国内版",
            "国内雷达",
            "国内核心事件",
            "国内核心判断",
        ),
        "overseas_radar": (
            "海外版正式雷达",
            "海外正式雷达",
            "海外版雷达",
            "海外版",
            "海外雷达",
            "海外核心事件",
            "海外核心判断",
        ),
        "self_check": (
            "输出前自我检查清单",
            "自我检查清单",
            "输出前检查",
            "输出前自检",
            "自检清单",
            "检查清单",
            "自我校验",
            "self check",
            "checklist",
        ),
    }
    for key, aliases in required.items():
        haystack = report_md if key != "self_check" else report_md.lower()
        if any(alias in haystack for alias in aliases) or (key == "self_check" and _has_checkbox_self_check(report_md)):
            continue
        if key == "self_check":
            result.warnings.append("missing required section: self_check")
        else:
            result.errors.append(f"missing required section: {key}")
    if not any(alias in report_md for alias in required["domestic_radar"]) and not any(
        alias in report_md for alias in required["overseas_radar"]
    ):
        result.critical_errors.append("report missing domestic/overseas basic structure")


def _check_llm_preamble(report_md: str, result: ReportLintResult) -> None:
    for line_number, line in enumerate(report_md.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped == "---":
            continue
        if stripped.startswith("#"):
            return
        compact = re.sub(r"\s+", "", stripped)
        markers = (
            "好的",
            "以下是",
            "以下严格",
            "我将",
            "我会",
            "已根据",
            "首先检查",
            "严格按指令",
            "严格遵循",
            "先输出候选事件筛选表",
        )
        if compact.startswith(markers) or any(marker in compact[:120] for marker in markers[6:]):
            result.critical_errors.append(f"LLM preamble leaked before first heading at line {line_number}")
        return


def _check_urls(report_md: str, evidence: list[EvidenceItem], result: ReportLintResult) -> None:
    evidence_urls = {_normalize_url(item.url) for item in evidence if item.url}
    unmatched: list[str] = []
    report_source_urls: list[str] = []
    for url in URL_RE.findall(report_md):
        if _is_allowed_non_evidence_url(url):
            continue
        normalized = _normalize_url(url)
        report_source_urls.append(normalized)
        if normalized not in evidence_urls:
            unmatched.append(normalized)
    result.source_url_count = len(report_source_urls)
    if not report_source_urls:
        if evidence_urls:
            result.warnings.append("report body had no source URL; evidence source appendix appended")
        else:
            result.critical_errors.append("report and evidence have no source URL")
    elif result.source_appendix_present:
        result.warnings.append("report body had no source URL; evidence source appendix appended")
    for normalized in unmatched:
        result.errors.append(f"report URL not found in evidence: {normalized}")
    if evidence and report_source_urls and len(unmatched) / len(report_source_urls) > 0.5:
        result.critical_errors.append("more than 50% of report URLs were not found in evidence")


def _check_placeholders(report_md: str, result: ReportLintResult) -> None:
    lowered = report_md.lower()
    for marker in ("tbd", "source needed", "待补充", "todo"):
        if marker in lowered:
            result.critical_errors.append(f"placeholder found: {marker}")


def _check_no_forced_count(report_md: str, result: ReportLintResult) -> None:
    explanations = (
        "不强行凑数",
        "今日无强核心事件",
        "无强核心事件",
        "未发现足够强事件",
        "无 P1/P2",
        "国内无 P1/P2",
        "海外无 P1/P2",
        "无足够证据进入核心",
        "核心事件不足",
        "本期无入选核心",
    )
    if not _has_region_formal_radar(report_md, "domestic") and "国内核心事件" not in report_md and not any(
        text in report_md for text in explanations
    ):
        result.warnings.append("domestic core event section absent without no-forced-count explanation")
    if not _has_region_formal_radar(report_md, "overseas") and "海外核心事件" not in report_md and not any(
        text in report_md for text in explanations
    ):
        result.warnings.append("overseas core event section absent without no-forced-count explanation")


def _has_region_formal_radar(report_md: str, region: str) -> bool:
    aliases = (
        ("国内版正式雷达", "国内正式雷达", "AI 前沿能力与应用雷达 - 国内版", "国内版【")
        if region == "domestic"
        else ("海外版正式雷达", "海外正式雷达", "AI 前沿能力与应用雷达 - 海外版", "海外版【")
    )
    return any(alias in report_md for alias in aliases) and ("今日总览" in report_md or "逐条深度解读" in report_md)


def _check_obvious_llm_failure(report_md: str, result: ReportLintResult) -> None:
    stripped = report_md.strip()
    if len(stripped) < 200 and any(text in stripped.lower() for text in ("error", "failed", "无法", "失败")):
        result.critical_errors.append("report appears to be an LLM failure message")


def _check_formal_radar_count_limit(report_md: str, result: ReportLintResult) -> None:
    from .brief import extract_core_events_from_report

    extracted = extract_core_events_from_report(report_md)
    if int(extracted.get("domestic_core_events_raw_count") or 0) > 6 or int(extracted.get("overseas_core_events_raw_count") or 0) > 6:
        result.warnings.append("formal radar has more than 6 core events; capped for brief/card")


def _check_empty_so_what(report_md: str, result: ReportLintResult) -> None:
    lines = report_md.splitlines()
    for line_number, line in enumerate(lines, start=1):
        text = re.sub(r"[*`]", "", line.strip())
        if re.match(r"^[-*]?\s*(?:影响\s*/\s*So what|So what|影响)\s*[:：]\s*$", text, flags=re.IGNORECASE):
            if _has_following_so_what_body(lines, line_number):
                continue
            result.critical_errors.append(f"empty So what section at line {line_number}")


def _check_non_daily_core_judgment_heading(report_md: str, result: ReportLintResult) -> None:
    bad_markers = ("本周核心判断", "本月核心判断", "本季度核心判断", "趋势判断", "综合判断")
    for line_number, line in enumerate(report_md.splitlines(), start=1):
        stripped = re.sub(r"[\s*`]+", "", line.strip())
        if not stripped.startswith("#"):
            continue
        if any(marker in stripped for marker in bad_markers):
            result.critical_errors.append(f"non-daily core judgment heading at line {line_number}")


def _has_following_so_what_body(lines: list[str], line_number: int) -> bool:
    for next_line in lines[line_number:]:
        stripped = next_line.strip()
        if not stripped:
            continue
        if stripped.startswith("#") or stripped.startswith("|"):
            return False
        if re.match(r"^[-*]\s*\*\*[^*]+?\*\*\s*[:：]", stripped):
            return False
        return bool(re.match(r"^(?:\d+[.、]|[-*]\s+)", stripped) or len(stripped) >= 8)
    return False


def _check_future_candidate_dates(report_md: str, result: ReportLintResult, target_date: str | Date | None) -> None:
    target = _target_date_str(target_date) or _infer_target_date(report_md)
    if not target:
        return
    in_candidate_table = False
    for line_number, line in enumerate(report_md.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            in_candidate_table = "候选" in stripped
            continue
        if not in_candidate_table or not stripped.startswith("|") or _is_table_separator(stripped):
            continue
        if "事件" in stripped and ("event_date" in stripped or "report_date" in stripped):
            continue
        future_dates = [value for value in re.findall(r"\b20\d{2}-\d{2}-\d{2}\b", stripped) if value > target]
        if future_dates:
            result.critical_errors.append(
                f"candidate row has future date after target {target} at line {line_number}: {', '.join(sorted(set(future_dates)))}"
            )


def _check_candidate_tables_before_formal(report_md: str, result: ReportLintResult) -> None:
    first_formal_line = 0
    candidate_after_formal: list[int] = []
    for line_number, line in enumerate(report_md.splitlines(), start=1):
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue
        if _is_formal_heading(stripped) and not first_formal_line:
            first_formal_line = line_number
        if first_formal_line and "候选" in stripped and ("国内" in stripped or "海外" in stripped):
            candidate_after_formal.append(line_number)
    for line_number in candidate_after_formal:
        result.critical_errors.append(f"candidate table appears after formal radar at line {line_number}")


def _check_candidate_table_prose_after_rows(report_md: str, result: ReportLintResult) -> None:
    in_candidate_section = False
    table_started = False
    for line_number, line in enumerate(report_md.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            in_candidate_section = "候选" in stripped and ("国内" in stripped or "海外" in stripped)
            table_started = False
            continue
        if not in_candidate_section:
            continue
        if stripped.startswith("|"):
            table_started = True
            continue
        if not table_started or not stripped or stripped == "---":
            continue
        result.critical_errors.append(f"candidate table has prose after rows at line {line_number}")
        table_started = False


def _check_no_p3_candidate_rows(report_md: str, result: ReportLintResult) -> None:
    in_candidate_table = False
    for line_number, line in enumerate(report_md.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            in_candidate_table = "候选" in stripped
            continue
        if not in_candidate_table or not stripped.startswith("|") or _is_table_separator(stripped):
            continue
        if re.search(r"\|\s*P3\s*\|", stripped, flags=re.IGNORECASE):
            result.critical_errors.append(f"P3 row found in candidate table at line {line_number}")


def _is_formal_heading(line: str) -> bool:
    if "候选" in line:
        return False
    return "AI 前沿能力与应用雷达" in line or "国内版" in line or "海外版" in line


def _target_date_str(target_date: str | Date | None) -> str:
    if target_date is None:
        return ""
    if isinstance(target_date, Date):
        return target_date.isoformat()
    return str(target_date or "").strip()[:10]


def _infer_target_date(report_md: str) -> str:
    match = re.search(r"【(20\d{2})年(\d{2})月(\d{2})日】", report_md)
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
    match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", report_md)
    return match.group(1) if match else ""


def _is_table_separator(line: str) -> bool:
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
    return bool(cells) and all(re.fullmatch(r":?-{2,}:?", cell) for cell in cells)


def _has_checkbox_self_check(report_md: str) -> bool:
    checkbox_count = len(re.findall(r"- \[[ xX]\]", report_md))
    emoji_count = report_md.count("✅")
    return checkbox_count + emoji_count >= 2


def _normalize_url(url: str) -> str:
    cleaned = unquote(url.rstrip(".,;，。；/"))
    parts = urlsplit(cleaned)
    scheme = "https"
    netloc = parts.netloc.lower()
    query = urlencode(
        [
            (key, value)
            for key, value in parse_qsl(parts.query, keep_blank_values=True)
            if not key.lower().startswith("utm_")
        ]
    )
    return urlunsplit((scheme, netloc, parts.path.rstrip("/"), query, ""))


def _is_allowed_non_evidence_url(url: str) -> bool:
    host = urlsplit(url).netloc.lower()
    return "feishu.cn" in host or "larksuite.com" in host
