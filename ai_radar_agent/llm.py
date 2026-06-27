from __future__ import annotations

import logging

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import Settings
from .models import EvidenceItem, TimeWindow
from .utils import evidence_to_markdown, load_text

logger = logging.getLogger(__name__)

_RECOMMENDED_CORE_LIMIT_PER_REGION = 4
_SOURCE_TIER_SCORES = {"S1": 40, "S2": 32, "S3": 26}
_SOURCE_FIT_SCORES = {"high": 18, "medium": 10, "unknown": 4, "": 4}
_DATE_STATUS_SCORES = {"in_window": 14, "new_signal": 12, "unknown": 2, "": 2}
_SIGNAL_KEYWORDS = (
    ("agent/workflow", ("agent", "智能体", "工作流", "workflow", "computer use", "coding")),
    ("commercialization", ("收入", "营收", "arr", "mrr", "付费", "pricing", "price", "revenue")),
    ("adoption", ("调用量", "token", "tokens", "月活", "mau", "下载", "用户", "customers", "seats")),
    ("model/capability", ("模型", "benchmark", "leaderboard", "推理", "上下文", "开源", "release")),
)


class DeepSeekGenerator:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = OpenAI(api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url)

    @retry(wait=wait_exponential(multiplier=2, min=2, max=30), stop=stop_after_attempt(3))
    def generate(self, window: TimeWindow, evidence_md: str) -> str:
        system_prompt = load_text(self.settings.prompt_path)
        user_prompt = f"""
请按“日报模式”生成 AI 前沿能力与应用雷达。

时间范围必须严格锁定：{window.display_range}
输出日期标题使用：{window.zh_date}

下面是程序 Recall-first 阶段抓取到的候选证据。你必须只基于这些证据与其链接做筛选、降级、剔除和正式输出；如果证据不足，宁可少写，不要补编事实。

【证据列表】
{evidence_md}

生成要求：
1. 先输出国内候选事件筛选表，再输出海外候选事件筛选表。
2. 再分别输出国内版和海外版正式雷达。
3. 每条核心事件必须在“来源”字段使用 Markdown link 引用证据列表中的 URL，格式必须是：[E1 来源名](https://...)；URL 必须来自证据列表。
4. 证据列表中的 E1、E2、E3... 是稳定证据 ID；如果引用证据，请写：来源：[E1 TechCrunch](URL)。
5. 严格区分 official actual、third-party data、media-reported estimate、analyst estimate、media summary、rumor。
6. 对时间窗口外事件按“前延回看”规则处理，不能强行写成当天事件。
7. “仅候选/观察证据（禁止入选正式雷达）”只能写入候选事件筛选表或观察信号，候选表“是否入选”必须写“否”；不得进入国内版/海外版正式雷达。
8. 如果证据列表包含“推荐核心候选（确定性预筛）”，正式雷达 Top 应优先从该表中选择；若表内高分 P1/P2 不入选，必须在候选事件筛选表写明剔除原因。该表不是新增事实来源，所有来源仍必须引用 E 编号对应 URL。
""".strip()
        logger.info("Calling DeepSeek model=%s", self.settings.deepseek_model)
        response = self.client.chat.completions.create(
            model=self.settings.deepseek_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=20000,
        )
        return response.choices[0].message.content or ""


def build_evidence_context(items, audit=None, gate_audit=None) -> str:
    core_md = evidence_to_markdown(items, audit, gate_audit, include_dropped=False, core_eligible_only=True)
    recommended_md = _recommended_core_candidates_markdown(items)
    candidate_only_md = evidence_to_markdown(items, None, None, include_dropped=False, not_core_only=True)
    sections = [section for section in [recommended_md, core_md] if section.strip()]
    if not candidate_only_md.strip():
        return "\n\n".join(sections)
    sections.extend(
        [
            "## 仅候选/观察证据（禁止入选正式雷达）\n\n"
            "以下证据保留用于候选事件筛选表、观察信号和剔除原因说明；"
            "不得在候选表“是否入选”列写“是”，不得进入正式雷达深度解读。",
            candidate_only_md,
        ]
    )
    return "\n\n".join(sections)


def _recommended_core_candidates_markdown(items: list[EvidenceItem]) -> str:
    ranked: list[tuple[str, int, int, EvidenceItem, list[str]]] = []
    for idx, item in enumerate(items, start=1):
        if _skip_recommended_core_candidate(item):
            continue
        score, reasons = _score_recommended_core_candidate(item)
        if score <= 0:
            continue
        ranked.append((_candidate_region(item), score, idx, item, reasons))
    if not ranked:
        return ""

    selected: list[tuple[str, int, int, EvidenceItem, list[str]]] = []
    for region in ("domestic", "overseas", "global", "unknown"):
        region_items = [row for row in ranked if row[0] == region]
        region_items.sort(key=lambda row: (-row[1], row[2]))
        selected.extend(region_items[:_RECOMMENDED_CORE_LIMIT_PER_REGION])

    lines = [
        "## 推荐核心候选（确定性预筛）",
        "",
        "以下候选由程序按来源层级、source_fit、日期状态、一手来源和采用/商业化信号排序。"
        "正式雷达 Top 应优先从这里选择；若不选择表内高分候选，需要在候选事件筛选表说明剔除原因。",
        "",
        "| 地区 | 推荐序 | evidence_id | 分数 | 标题 | source_tier | source_fit | date_status | 推荐理由 | URL |",
        "|---|---:|---|---:|---|---|---|---|---|---|",
    ]
    for rank, (region, score, idx, item, reasons) in enumerate(selected, start=1):
        lines.append(
            f"| {_md_cell(region)} | {rank} | E{idx} | {score} | {_md_cell(item.title)} | "
            f"{_md_cell(item.source_tier or 'unknown')} | {_md_cell(item.source_fit or 'unknown')} | "
            f"{_md_cell(item.date_status or 'unknown')} | {_md_cell(', '.join(reasons))} | "
            f"{_md_cell(item.url)} |"
        )
    return "\n".join(lines)


def _skip_recommended_core_candidate(item: EvidenceItem) -> bool:
    if item.not_core_eligible:
        return True
    tier = (item.source_tier or "").upper()
    fit = (item.source_fit or "").lower()
    date_status = (item.date_status or "").lower()
    if tier in {"S4", "S5"} or fit == "low":
        return True
    return date_status in {"old_repeated", "out_of_window"}


def _score_recommended_core_candidate(item: EvidenceItem) -> tuple[int, list[str]]:
    tier = (item.source_tier or "").upper()
    fit = (item.source_fit or "").lower()
    date_status = (item.date_status or "").lower()
    score = _SOURCE_TIER_SCORES.get(tier, 0)
    if score <= 0 and not item.is_primary_source:
        return 0, []

    reasons = [tier or "tier_unknown"]
    score += _SOURCE_FIT_SCORES.get(fit, 0)
    score += _DATE_STATUS_SCORES.get(date_status, 0)
    reasons.append(f"fit={fit or 'unknown'}")
    reasons.append(f"date={date_status or 'unknown'}")
    if item.is_primary_source:
        score += 8
        reasons.append("primary_source")
    if item.url:
        score += 2

    text = f"{item.title} {item.content}".lower()
    for label, keywords in _SIGNAL_KEYWORDS:
        if any(keyword in text for keyword in keywords):
            score += 4
            reasons.append(label)
    return score, reasons[:6]


def _candidate_region(item: EvidenceItem) -> str:
    region = (item.region_hint or "unknown").lower()
    if region in {"domestic", "overseas", "global"}:
        return region
    return "unknown"


def _md_cell(value: object) -> str:
    return " ".join(str(value or "").replace("|", "\\|").split())
