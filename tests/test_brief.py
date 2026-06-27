import json
from datetime import date

import ai_radar_agent.brief as brief_module
from ai_radar_agent.brief import (
    DeepSeekBriefGenerator,
    extract_core_events_from_report,
    fallback_brief,
    normalize_brief,
    parse_brief_json,
    render_brief_markdown,
    salvage_brief_items_from_partial_json,
)
from ai_radar_agent.config import Settings
from ai_radar_agent.dates import window_for_date
from ai_radar_agent.models import EvidenceItem, RecallAudit


def _audit():
    return RecallAudit("2026-06-01", "window", rss_item_count=2, tavily_item_count=3, total_evidence_count=5)


def _report_with_core_events(domestic_count=5, overseas_count=6):
    domestic_rows = [
        f"| 国内事件{i} | {'P1' if i in {2, 4} else 'P2' if i == 1 else '观察'} | L3 | 国内事件{i}影响 Agent 落地。 来源：https://example.com/d{i} |"
        for i in range(1, domestic_count + 1)
    ]
    overseas_rows = [
        f"| 海外事件{i} | {'P1' if i in {2, 5} else 'P2'} | L4 | 海外事件{i}影响资本和生态。 来源：https://example.com/o{i} |"
        for i in range(1, overseas_count + 1)
    ]
    return "\n".join(
        [
            "# AI Radar",
            "## 国内候选事件筛选表",
            "| 候选 | 结论 |",
            "| --- | --- |",
            "| 候选但未入选 | 剔除 |",
            "## 国内版正式雷达",
            "### 一、今日总览",
            "| 事件标题 | 优先级 | Level | 摘要 |",
            "| --- | --- | --- | --- |",
            *domestic_rows,
            "### 二、逐条深度解读",
            *[f"#### {i}. 国内事件{i}｜P1\n国内事件{i}深度解读。" for i in range(1, domestic_count + 1)],
            "## 海外候选事件筛选表",
            "| 候选 | 结论 |",
            "| --- | --- |",
            "| 海外候选但未入选 | 剔除 |",
            "## 海外版正式雷达",
            "### 一、今日总览",
            "| 事件标题 | 优先级 | Level | 摘要 |",
            "| --- | --- | --- | --- |",
            *overseas_rows,
            "### 二、逐条深度解读",
            *[f"#### {i}. 海外事件{i}｜P2\n海外事件{i}深度解读。" for i in range(1, overseas_count + 1)],
            "### 三、观察信号",
            "- 观察信号来自完整报告",
            "### 四、今日核心判断",
            "- 核心判断来自完整报告",
            "## 输出前自我检查清单",
            "已检查。",
        ]
    )


def _report_with_alias_sections():
    return "\n".join(
        [
            "# AI Radar",
            "## 国内版",
            "### 一、今日总览",
            "| 标题 | 层级 | 优先级 | 可信度 | 影响方向 |",
            "| --- | --- | --- | --- | --- |",
            "| 国内别名事件 | L3 | P1 | 高 | 正向 |",
            "## 海外 AI 雷达",
            "## 二、逐条深度解读",
            "### 1. 海外深度事件",
            "优先级：P2。来源：https://example.com/overseas",
            "### 2. 海外第二事件",
            "优先级：观察。",
            "## 输出前自我检查清单",
            "已检查。",
        ]
    )


def test_parse_brief_json_handles_code_fence():
    parsed = parse_brief_json('```json\n{"date":"2026-06-01"}\n```')

    assert parsed["date"] == "2026-06-01"


def test_parse_brief_json_prefers_object_with_top_lists():
    parsed = parse_brief_json(
        '先给一个内层对象 {"title":"DeepSeek V4-Pro永久降价75%","source_ids":["E30"]}\n'
        '{"domestic_top":[{"title":"DeepSeek V4-Pro永久降价75%","why":"价格下降","priority":"P1","source_ids":["E30"]}],'
        '"overseas_top":[{"title":"Anthropic提交IPO","why":"资本化","priority":"P1","source_ids":["E13"]}]}'
    )

    assert parsed["domestic_top"][0]["source_ids"] == ["E30"]
    assert parsed["overseas_top"][0]["title"] == "Anthropic提交IPO"


def test_parse_brief_json_salvages_complete_items_from_truncated_response():
    raw = """
{
  "date": "2026-06-03",
  "domestic_top": [
    {"title": "千问开放第三方Agent生态", "card_title": "千问开放第三方Agent生态", "why": "完整解释", "card_why": "卡片短句", "priority": "P1", "source_ids": ["E35"]},
    {"title": "Coze 3.0上线，支持多Agent协作", "card_title": "Coze 3.0上线", "why": "完整解释", "card_why": "卡片短句", "priority": "P1", "source_ids": ["E48"]},
    {"title": "火山引擎MaaS目标150亿", "card_title": "火山引擎MaaS目标150亿", "why": "完整解释", "card_why": "卡片短句", "priority": "P1", "source_ids": ["E50"]},
    {"title": "豆包推付费版", "card_title"
"""

    parsed, stage, _cleaned = brief_module.parse_brief_json_with_stage(raw)

    assert stage == "partial_json_salvaged"
    assert [item["title"] for item in parsed["domestic_top"]] == [
        "千问开放第三方Agent生态",
        "Coze 3.0上线，支持多Agent协作",
        "火山引擎MaaS目标150亿",
    ]


def test_salvage_brief_items_from_partial_json_ignores_unclosed_item():
    raw = '{"domestic_top":[{"title":"完整","why":"ok"},{"title":"未闭合"'

    parsed = salvage_brief_items_from_partial_json(raw)

    assert parsed["domestic_top"] == [{"title": "完整", "why": "ok"}]


def test_normalize_brief_limits_schema_fields():
    window = window_for_date(date(2026, 6, 1), "Asia/Shanghai")
    raw = {
        "domestic_top": [{"title": "很长很长很长很长很长很长很长很长很长很长标题", "why": "x" * 120, "priority": "P1"}] * 4,
        "overseas_top": [],
        "core_judgments": ["y" * 120] * 4,
        "watch_signals": ["z" * 120] * 4,
    }

    brief = normalize_brief(raw, window, _audit(), doc_url="https://example.com/docx/a")

    assert set(brief) == {
        "date",
        "title",
        "domestic_top",
        "overseas_top",
        "core_judgments",
        "watch_signals",
        "core_judgments_card",
        "watch_signals_card",
        "brief_core_judgments_count",
        "brief_watch_signals_count",
        "brief_core_judgments_dropped_non_top_count",
        "brief_watch_signals_demoted_from_top_count",
        "brief_watch_signals_demoted_from_top_examples",
        "core_judgments_filled_from_report",
        "watch_signals_filled_from_report",
        "doc_url",
        "evidence_count",
        "recall_summary",
        "brief_generation_status",
        "brief_source_validation_warnings",
        "brief_error_summary",
        "brief_repair_attempted",
        "brief_repair_succeeded",
        "brief_parse_stage",
        "brief_raw_response_length",
        "brief_raw_response_summary",
        "brief_json_parse_error",
        "brief_normalization_error",
        "brief_source_resolution_status",
        "brief_invalid_source_ids_count",
        "brief_llm_domestic_items_count",
        "brief_llm_overseas_items_count",
        "brief_final_domestic_items_count",
        "brief_final_overseas_items_count",
        "brief_domestic_items_count_raw",
        "brief_overseas_items_count_raw",
        "brief_domestic_items_count_capped",
        "brief_overseas_items_count_capped",
        "brief_domestic_truncated",
        "brief_overseas_truncated",
        "brief_source_ids_requested_count",
        "brief_source_ids_resolved_count",
        "brief_source_ids_unresolved_count",
        "brief_unresolved_source_ids_sample",
        "brief_sources_filled_by_matching_count",
        "brief_top_items_dropped_source_quality_count",
        "brief_top_items_dropped_source_quality_examples",
        "brief_top_items_region_reassigned_count",
        "brief_top_items_region_reassigned_examples",
        "report_domestic_core_events_count",
        "report_overseas_core_events_count",
        "report_domestic_core_events_count_raw",
        "report_overseas_core_events_count_raw",
        "report_domestic_core_events_count_capped",
        "report_overseas_core_events_count_capped",
        "domestic_core_events_truncated",
        "overseas_core_events_truncated",
        "domestic_core_events_truncated_from",
        "overseas_core_events_truncated_from",
        "report_domestic_zero_core_explicit",
        "report_overseas_zero_core_explicit",
        "report_domestic_zero_core_conflict_resolved",
        "report_overseas_zero_core_conflict_resolved",
        "report_domestic_extraction_suspect",
        "report_overseas_extraction_suspect",
        "report_domestic_section_found",
        "report_overseas_section_found",
        "report_domestic_extraction_method",
        "report_overseas_extraction_method",
        "report_domestic_extracted_titles_sample",
        "report_overseas_extracted_titles_sample",
        "report_domestic_empty_reason",
        "report_overseas_empty_reason",
        "brief_empty_placeholder_removed_count",
        "brief_count_mismatch",
        "brief_count_mismatch_initial",
        "brief_count_mismatch_final",
        "brief_count_mismatch_type",
        "brief_count_mismatch_handled",
        "brief_count_filled_from_core_events",
        "brief_expected_domestic_items_count",
        "brief_expected_overseas_items_count",
        "brief_actual_domestic_items_count",
        "brief_actual_overseas_items_count",
        "brief_count_repair_attempted",
        "brief_count_repair_succeeded",
    }
    assert len(brief["domestic_top"]) == 4
    assert len(brief["domestic_top"][0]["title"]) > 18
    assert "card_title" in brief["domestic_top"][0]
    assert brief["domestic_top"][0]["sources"] == []
    assert len(brief["overseas_top"]) == 0
    assert len(brief["core_judgments"]) == 1
    assert "很长很长" in brief["core_judgments"][0]
    assert brief["brief_core_judgments_dropped_non_top_count"] == 3


def test_normalize_brief_preserves_full_why_for_daily_text():
    window = window_for_date(date(2026, 6, 15), "Asia/Shanghai")
    full_why = (
        "月之暗面为编程模型Kimi K2.7 Code推出高速版，输出速度达普通版5-6倍，常规编程场景下约180 Tokens/s，"
        "定价为普通版两倍。此举开创了模型服务按速度分层定价的新模式，利好开发者生态，并验证了编程模型从单纯"
        "能力竞争向推理效率与成本结构优化的演进方向。"
    )
    raw = {
        "domestic_top": [
            {
                "title": "Kimi K2.7 Code高速版上线",
                "card_title": "Kimi Code高速版",
                "why": full_why,
                "card_why": "Kimi Code高速版上线，模型服务开始按速度分层定价。",
                "priority": "P2",
            }
        ],
        "overseas_top": [],
    }

    brief = normalize_brief(raw, window, _audit(), evidence=[])

    why = brief["domestic_top"][0]["why"]
    assert why.startswith("月之暗面为编程模型Kimi K2.7 Code推出高速版")
    assert "能力竞争向推理效率与成本结构优化的演进方向" in why
    assert "…" not in why


def test_normalize_brief_preserves_full_bullets_and_corrects_known_entity_typos():
    window = window_for_date(date(2026, 6, 15), "Asia/Shanghai")
    full_judgment = (
        "中国模型调用量格局出现结构性主导地位：OpenRouter数据显示中国模型连续7周调用量领先美国，"
        "DeepSeek-V4-Flash、MiniMax M3、腾讯Hy3形成前五主导格局，验证了低价开源策略在全球API调用市场的竞争力。"
        "该趋势若持续，将迫使OpenAI、Anthropic调整定价策略，并可能改变全球AI推理算力分配和开发者生态流向。"
    )
    raw = {
        "domestic_top": [
            {
                "title": "Kimi K2.7 Code高速版上线",
                "why": "月之暗夜上线Kim K2.7 Code高速版，输出速度180-260 Tokens/s，首次实现按速度分层定价。",
                "priority": "P1",
            },
            {
                "title": "中国模型调用量连续7周领跑",
                "why": "OpenRouter数据显示中国模型连续7周调用量领先美国。",
                "priority": "P1",
            },
        ],
        "overseas_top": [],
        "core_judgments": [full_judgment],
        "watch_signals": [],
    }

    brief = normalize_brief(raw, window, _audit(), evidence=[])
    markdown = render_brief_markdown(brief)

    assert "月之暗面上线Kimi K2.7 Code高速版" in markdown
    assert "月之暗夜" not in markdown
    assert "Kim K2.7" not in markdown
    assert "全球AI推理算力分配和开发者生态流向" in markdown
    assert "…" not in brief["core_judgments"][0]


def test_normalize_brief_replaces_truncated_core_judgment_from_final_top():
    window = window_for_date(date(2026, 6, 15), "Asia/Shanghai")
    full_why = (
        "月之暗面发布Kimi K2.7 Code模型高速版，输出速度达普通版5-6倍，常规编程场景约180 Tokens/s，"
        "短上下文可达260 Tokens/s，价格为普通版2倍，推动编程模型竞争从准确率转向速度、成本和体验。"
    )
    raw = {
        "domestic_top": [
            {
                "title": "月之暗面Kimi K2.7 Code高速版上线",
                "card_title": "Kimi K2.7高速版上线",
                "why": full_why,
                "card_why": "Kimi高速版提速并验证速度分层定价。",
                "priority": "P1",
            }
        ],
        "overseas_top": [],
        "core_judgments": ["月之暗面Kimi K2.7 Code高速版上线：月之暗面发布Kimi K2.7 Code高速版，输出速度提升5-6倍…"],
    }

    brief = normalize_brief(raw, window, _audit(), evidence=[])

    assert "…" not in "".join(brief["core_judgments"])
    assert "输出速度达普通版5-6倍" in brief["core_judgments"][0]
    assert "推动编程模型竞争从准确率转向速度、成本和体验" in brief["core_judgments"][0]
    assert "replaced truncated core judgment from final top" in brief["brief_source_validation_warnings"]


def test_normalize_brief_sorts_all_top_items_by_priority():
    window = window_for_date(date(2026, 6, 1), "Asia/Shanghai")
    raw = {
        "domestic_top": [
            {"title": "P2先来", "why": "重要", "priority": "P2 重要里程碑"},
            {"title": "P1第一", "why": "重要", "priority": "P1"},
            {"title": "观察项", "why": "观察", "priority": "观察"},
            {"title": "P1第二", "why": "重要", "priority": "P1 战略转折点"},
            {"title": "未知项", "why": "未知", "priority": "其他"},
        ],
        "overseas_top": [],
    }

    brief = normalize_brief(raw, window, _audit())

    assert [item["title"] for item in brief["domestic_top"]] == ["P1第一", "P1第二", "P2先来", "观察项", "未知项"]
    assert brief["brief_final_domestic_items_count"] == 5


def test_normalize_brief_does_not_strip_fact_title_into_attribution_fragment():
    window = window_for_date(date(2026, 6, 5), "Asia/Shanghai")
    raw = {
        "domestic_top": [
            {
                "title": "80%元宝用户使用混元大模型",
                "card_title": "80%元宝用户使用混元大模型",
                "why": "腾讯高管汤道生透露，80%元宝用户使用混元大模型，算力不足但内部需求旺盛。",
                "card_why": "汤道生透露80%元宝用户使用混元大模型。",
                "priority": "P2",
                "source_ids": [],
            }
        ],
        "overseas_top": [],
    }

    brief = normalize_brief(raw, window, _audit(), evidence=[])

    item = brief["domestic_top"][0]
    assert item["card_why"] != "汤道生透露"
    assert "80%元宝用户使用混元大模型" in item["card_why"]
    assert "，," not in item["why"]


def test_normalize_brief_caps_overseas_to_six_and_keeps_priority_order():
    window = window_for_date(date(2026, 6, 1), "Asia/Shanghai")
    raw = {
        "domestic_top": [],
        "overseas_top": [
            {"title": "海外P2先", "why": "重要", "priority": "P2"},
            {"title": "海外P1一", "why": "重要", "priority": "P1"},
            {"title": "海外观察", "why": "观察", "priority": "观察"},
            {"title": "海外P1二", "why": "重要", "priority": "P1 战略转折点"},
            {"title": "海外P2二", "why": "重要", "priority": "P2"},
            {"title": "海外P2三", "why": "重要", "priority": "P2"},
            {"title": "海外P2四", "why": "重要", "priority": "P2"},
            {"title": "海外观察二", "why": "观察", "priority": "观察"},
            {"title": "海外观察三", "why": "观察", "priority": "观察"},
            {"title": "海外观察四", "why": "观察", "priority": "观察"},
            {"title": "海外未知", "why": "未知", "priority": "其他"},
            {"title": "海外观察五", "why": "观察", "priority": "观察"},
        ],
    }

    brief = normalize_brief(raw, window, _audit())

    assert [item["title"] for item in brief["overseas_top"]] == ["海外P1一", "海外P1二", "海外P2先", "海外P2二", "海外观察", "海外观察二"]
    assert brief["brief_overseas_items_count_raw"] == 12
    assert brief["brief_overseas_items_count_capped"] == 6
    assert brief["brief_overseas_truncated"] is True
    assert brief["brief_final_overseas_items_count"] == 6
    assert brief["brief_count_mismatch_type"] == "too_many"
    assert brief["brief_count_mismatch_handled"] is True


def test_normalize_brief_caps_final_p2_items_per_region_to_two():
    window = window_for_date(date(2026, 6, 1), "Asia/Shanghai")
    raw = {
        "domestic_top": [
            {"title": "国内P1", "why": "重要", "priority": "P1"},
            {"title": "国内P2一", "why": "重要", "priority": "P2"},
            {"title": "国内P2二", "why": "重要", "priority": "P2"},
            {"title": "国内P2三", "why": "重要", "priority": "P2"},
            {"title": "国内观察", "why": "观察", "priority": "观察"},
        ],
        "overseas_top": [
            {"title": "海外P2一", "why": "重要", "priority": "P2"},
            {"title": "海外P2二", "why": "重要", "priority": "P2"},
            {"title": "海外P2三", "why": "重要", "priority": "P2"},
            {"title": "海外观察", "why": "观察", "priority": "观察"},
        ],
    }

    brief = normalize_brief(raw, window, _audit())

    assert [item["title"] for item in brief["domestic_top"]] == ["国内P1", "国内P2一", "国内P2二", "国内观察"]
    assert [item["title"] for item in brief["overseas_top"]] == ["海外P2一", "海外P2二", "海外观察"]
    assert sum(1 for item in brief["domestic_top"] if item["priority"] == "P2") == 2
    assert sum(1 for item in brief["overseas_top"] if item["priority"] == "P2") == 2


def test_extract_core_events_from_report_uses_formal_radar_tables():
    extracted = extract_core_events_from_report(_report_with_core_events())

    assert len(extracted["domestic_core_events"]) == 5
    assert len(extracted["overseas_core_events"]) == 6
    assert extracted["domestic_core_events_raw_count"] == 5
    assert extracted["overseas_core_events_raw_count"] == 6
    assert extracted["domestic_core_events"][0]["title"] == "国内事件2"
    assert "候选但未入选" not in str(extracted)


def test_normalize_brief_fallback_from_core_events_cleans_table_why_and_fills_bullets():
    window = window_for_date(date(2026, 6, 1), "Asia/Shanghai")
    report = _report_with_core_events(domestic_count=6, overseas_count=6)
    core_events = extract_core_events_from_report(report)

    brief = normalize_brief(
        {"domestic_top": [], "overseas_top": [], "core_judgments": [], "watch_signals": []},
        window,
        _audit(),
        report_md=report,
        core_events=core_events,
    )

    assert brief["brief_final_domestic_items_count"] == 6
    assert brief["brief_final_overseas_items_count"] == 4
    assert brief["brief_count_mismatch_initial"] is True
    assert brief["brief_count_mismatch_final"] is False
    assert brief["brief_count_mismatch_handled"] is True
    assert brief["brief_count_filled_from_core_events"] is True
    assert brief["core_judgments"] != ["核心判断来自完整报告"]
    assert any("国内事件" in item for item in brief["core_judgments"])
    assert brief["watch_signals"] == ["观察信号来自完整报告"]
    why_values = [item["why"] for item in brief["domestic_top"] + brief["overseas_top"]]
    assert all("|" not in why for why in why_values)
    assert all("L3" not in why and "L4" not in why and "P1" not in why and "P2" not in why for why in why_values)


def test_normalize_brief_filters_mismatched_core_event_sources():
    window = window_for_date(date(2026, 6, 13), "Asia/Shanghai")
    raw = {
        "overseas_top": [
            {
                "title": "Anthropic因政府令切断顶级模型访问",
                "why": "美国政府要求Anthropic切断Fable 5和Mythos 5访问。",
                "priority": "P1",
                "source_ids": ["E2"],
            }
        ],
        "core_judgments": [],
        "watch_signals": [],
    }
    core_events = {
        "domestic_core_events": [],
        "overseas_core_events": [
            {
                "title": "Anthropic因政府令切断顶级模型访问",
                "priority": "P1",
                "raw_block": "美国政府要求Anthropic切断Fable 5和Mythos 5访问。",
                "source_urls": ["https://blogs.nvidia.com/blog/nvidia-blackwell-agentperf-artificial-analysis/"],
            }
        ],
    }
    evidence = [
        EvidenceItem(
            title="NVIDIA Blackwell Leads on First Agentic AI Infrastructure Benchmark",
            url="https://blogs.nvidia.com/blog/nvidia-blackwell-agentperf-artificial-analysis/",
            content="AgentPerf benchmark shows NVIDIA Blackwell performance.",
            source="NVIDIA Blog",
            source_tier="S1",
            source_fit="high",
        ),
        EvidenceItem(
            title="Anthropic cuts off Fable 5 and Mythos 5 access following government order",
            url="https://www.theverge.com/anthropic-government-order",
            content="The government ordered Anthropic to block access to Fable 5 and Mythos 5.",
            source="The Verge",
            source_tier="S2",
            source_fit="high",
        ),
    ]

    brief = normalize_brief(raw, window, _audit(), evidence=evidence, core_events=core_events)

    sources = brief["overseas_top"][0]["sources"]
    assert [source["evidence_id"] for source in sources] == ["E2"]
    assert any("dropped low-confidence source binding: E1" in warning for warning in brief["brief_source_validation_warnings"])


def test_normalize_brief_keeps_existing_source_when_core_event_source_mismatches_title():
    window = window_for_date(date(2026, 6, 21), "Asia/Shanghai")
    raw = {
        "overseas_top": [
            {
                "title": "iOS 27披露系统级AI能力，重塑L4入口",
                "why": "iOS 27将AI深度集成至系统层，重新定义移动端AI入口。",
                "priority": "P2",
                "source_ids": ["E2"],
            }
        ],
        "core_judgments": [
            "苹果iOS 27深度集成AI文本重写、智能摘要、图像编辑等系统级功能，重新定义移动端交互入口。"
        ],
        "watch_signals": [],
    }
    core_events = {
        "domestic_core_events": [],
        "overseas_core_events": [
            {
                "title": "iOS 27披露系统级AI能力，重塑L4入口",
                "priority": "P2",
                "raw_block": "iOS 27将AI深度集成至系统层。",
                "source_urls": ["https://example.com/token-subsidy"],
            }
        ],
    }
    evidence = [
        EvidenceItem(
            title="AI巨头的Token补贴大战",
            url="https://example.com/token-subsidy",
            content="AI订阅Token成本倒挂。",
            source="36氪",
            source_tier="S2",
            source_fit="high",
        ),
        EvidenceItem(
            title="Beyond Siri: practical AI features coming to iOS 27",
            url="https://example.com/ios-27",
            content="iOS 27 brings AI features to iPhone.",
            source="TechCrunch",
            source_tier="S2",
            source_fit="high",
        ),
    ]

    brief = normalize_brief(raw, window, _audit(), evidence=evidence, core_events=core_events)

    assert [source["evidence_id"] for source in brief["overseas_top"][0]["sources"]] == ["E2"]
    assert any("dropped low-confidence source binding: E1" in warning for warning in brief["brief_source_validation_warnings"])


def test_extract_core_events_caps_each_region_to_six():
    extracted = extract_core_events_from_report(_report_with_core_events(domestic_count=12, overseas_count=12))

    assert extracted["domestic_core_events_raw_count"] == 12
    assert extracted["overseas_core_events_raw_count"] == 12
    assert extracted["domestic_core_events_capped_count"] == 6
    assert extracted["overseas_core_events_capped_count"] == 6
    assert extracted["domestic_core_events_truncated"] is True
    assert extracted["overseas_core_events_truncated"] is True
    assert extracted["domestic_core_events_truncated_from"] == 12
    assert len(extracted["domestic_core_events"]) == 6
    assert len(extracted["overseas_core_events"]) == 6


def test_extract_core_events_from_report_supports_alias_sections_and_deep_dive():
    extracted = extract_core_events_from_report(_report_with_alias_sections())

    assert extracted["domestic_section_found"] is True
    assert extracted["overseas_section_found"] is True
    assert extracted["domestic_extraction_method"] == "table"
    assert extracted["overseas_extraction_method"] == "deep_dive"
    assert extracted["domestic_core_events"][0]["title"] == "国内别名事件"
    assert [event["title"] for event in extracted["overseas_core_events"]] == ["海外深度事件", "海外第二事件"]


def test_extract_core_events_marks_explicit_zero_core():
    report = "\n".join(
        [
            "## 国内版正式雷达",
            "今日无强核心事件，不强行凑数。",
            "## 海外版正式雷达",
            "本日无入选核心事件。",
        ]
    )

    extracted = extract_core_events_from_report(report)

    assert extracted["domestic_core_events"] == []
    assert extracted["overseas_core_events"] == []
    assert extracted["domestic_zero_core_explicit"] is True
    assert extracted["overseas_zero_core_explicit"] is True
    assert extracted["domestic_extraction_suspect"] is False
    assert extracted["overseas_extraction_suspect"] is False


def test_extract_core_events_does_not_treat_core_analysis_heading_as_event():
    report = "\n".join(
        [
            "# AI 前沿能力与应用雷达 - 国内版【2026年06月03日】",
            "## 一、今日总览",
            "**今日国内无符合入选标准的核心事件。**",
            "| 标题 | 层级 | 优先级 | 可信度 | 影响方向 |",
            "|------|------|--------|--------|----------|",
            "| 无 | — | — | — | — |",
            "## 二、核心解读",
            "今日国内证据池无符合P1/P2标准的核心事件。",
            "## 三、观察信号",
            "- 无需纳入观察信号。",
            "# AI 前沿能力与应用雷达 - 海外版【2026年06月03日】",
            "## 一、今日总览",
            "| 标题 | 层级 | 优先级 | 可信度 | 影响方向 |",
            "|------|------|--------|--------|----------|",
            "| OpenAI事件 | L3 | P1 | 高 | 利好 |",
        ]
    )

    extracted = extract_core_events_from_report(report)

    assert extracted["domestic_core_events"] == []
    assert extracted["domestic_zero_core_explicit"] is True
    assert extracted["domestic_extraction_method"] == "none"
    assert extracted["domestic_extracted_titles_sample"] == []


def test_extract_core_events_resolves_zero_core_conflict_when_events_found():
    report = "\n".join(
        [
            "## 海外版正式雷达",
            "今日无强核心事件，不强行凑数。",
            "### 一、今日总览",
            "| 事件 | 优先级 | 层级 | 摘要 |",
            "| --- | --- | --- | --- |",
            "| OpenAI发布Codex更新 | P1 | L3 | 来源：https://openai.com/news/codex |",
        ]
    )

    extracted = extract_core_events_from_report(report)

    assert len(extracted["overseas_core_events"]) == 1
    assert extracted["overseas_zero_core_explicit"] is False
    assert extracted["overseas_zero_core_conflict_resolved"] == "events_found"


def test_brief_generator_uses_llm_fallback_when_extraction_suspect(monkeypatch):
    window = window_for_date(date(2026, 6, 1), "Asia/Shanghai")
    generator = object.__new__(DeepSeekBriefGenerator)
    calls = {"count": 0}
    report = "\n".join(
        [
            "## 国内版正式雷达",
            "这里有正式雷达内容，但不是表格或编号。",
            "## 海外版正式雷达",
            "今日无强核心事件，不强行凑数。",
        ]
    )

    def fake_call(prompt):
        calls["count"] += 1
        if calls["count"] == 1:
            return json.dumps(
                {
                    "domestic_core_events": [
                        {"title": "LLM补抽事件", "priority": "P1", "evidence_hint": "正式雷达内容", "source_urls": []}
                    ],
                    "overseas_core_events": [],
                },
                ensure_ascii=False,
            )
        return json.dumps(
            {
                "domestic_top": [{"title": "LLM补抽事件", "why": "来自正式雷达", "priority": "P1", "source_ids": []}],
                "overseas_top": [],
            },
            ensure_ascii=False,
        )

    monkeypatch.setattr(generator, "_call", fake_call)

    brief = generator.generate(window, report, _audit(), evidence=[])

    assert calls["count"] == 2
    assert brief["report_domestic_extraction_method"] == "llm_fallback"
    assert brief["report_domestic_extraction_suspect"] is False
    assert brief["report_domestic_core_events_count"] == 1
    assert brief["domestic_top"][0]["title"] == "LLM补抽事件"


def test_brief_generator_keeps_empty_when_llm_fallback_fails(monkeypatch):
    window = window_for_date(date(2026, 6, 1), "Asia/Shanghai")
    generator = object.__new__(DeepSeekBriefGenerator)
    calls = {"count": 0}
    report = "\n".join(
        [
            "## 国内版正式雷达",
            "这里有正式雷达内容，但不是表格或编号。",
            "## 海外版正式雷达",
            "今日无强核心事件，不强行凑数。",
        ]
    )

    def fake_call(prompt):
        calls["count"] += 1
        if calls["count"] == 1:
            return json.dumps({"domestic_core_events": [], "overseas_core_events": []}, ensure_ascii=False)
        return json.dumps(
            {
                "domestic_top": [{"title": "今日无强核心事件", "why": "不强行凑数", "priority": "观察", "source_ids": []}],
                "overseas_top": [],
            },
            ensure_ascii=False,
        )

    monkeypatch.setattr(generator, "_call", fake_call)

    brief = generator.generate(window, report, _audit(), evidence=[])

    assert calls["count"] == 2
    assert brief["report_domestic_extraction_method"] == "llm_fallback_failed"
    assert brief["report_domestic_extraction_suspect"] is True
    assert brief["report_domestic_empty_reason"] == "extraction_suspect_unresolved"
    assert brief["domestic_top"] == []
    assert brief["brief_empty_placeholder_removed_count"] == 1


def test_normalize_brief_drops_dash_placeholder_item():
    window = window_for_date(date(2026, 6, 1), "Asia/Shanghai")
    raw = {
        "date": "2026-06-01",
        "title": "AI Radar｜2026-06-01",
        "domestic_top": [{"title": "—", "card_title": "—", "why": "详见完整日报。", "card_why": "详见完整日报。", "priority": "观察"}],
        "overseas_top": [],
        "core_judgments": [],
        "watch_signals": [],
    }

    brief = normalize_brief(raw, window, _audit(), evidence=[])

    assert brief["domestic_top"] == []
    assert brief["brief_empty_placeholder_removed_count"] == 1


def test_brief_generator_repairs_count_mismatch_from_report_core_events(monkeypatch):
    window = window_for_date(date(2026, 6, 1), "Asia/Shanghai")
    generator = object.__new__(DeepSeekBriefGenerator)
    calls = {"count": 0}

    def fake_call(prompt):
        calls["count"] += 1
        if calls["count"] > 1:
            return json.dumps(
                {
                    "domestic_top": [
                        {"title": "国内事件1", "why": "修复补齐", "priority": "P2", "source_ids": []},
                        {"title": "国内事件2", "why": "修复补齐", "priority": "P1", "source_ids": []},
                        {"title": "国内事件3", "why": "修复补齐", "priority": "观察", "source_ids": []},
                        {"title": "国内事件4", "why": "修复补齐", "priority": "P1", "source_ids": []},
                        {"title": "国内事件5", "why": "修复补齐", "priority": "观察", "source_ids": []},
                    ],
                    "overseas_top": [
                        {"title": "海外事件1", "why": "修复补齐", "priority": "P2", "source_ids": []},
                        {"title": "海外事件2", "why": "修复补齐", "priority": "P1", "source_ids": []},
                        {"title": "海外事件3", "why": "修复补齐", "priority": "P2", "source_ids": []},
                        {"title": "海外事件4", "why": "修复补齐", "priority": "P2", "source_ids": []},
                        {"title": "海外事件5", "why": "修复补齐", "priority": "P1", "source_ids": []},
                        {"title": "海外事件6", "why": "修复补齐", "priority": "P2", "source_ids": []},
                    ],
                },
                ensure_ascii=False,
            )
        return json.dumps(
            {
                "domestic_top": [
                    {"title": f"国内事件{i}", "why": "LLM只给前三条", "priority": "P2", "source_ids": []}
                    for i in range(1, 4)
                ],
                "overseas_top": [
                    {"title": f"海外事件{i}", "why": "LLM只给前三条", "priority": "P2", "source_ids": []}
                    for i in range(1, 4)
                ],
            },
            ensure_ascii=False,
        )

    monkeypatch.setattr(generator, "_call", fake_call)

    brief = generator.generate(window, _report_with_core_events(), _audit(), evidence=[])

    assert calls["count"] == 2
    assert brief["brief_generation_status"] == "repaired"
    assert brief["brief_count_mismatch"] is True
    assert brief["brief_count_mismatch_initial"] is True
    assert brief["brief_count_mismatch_final"] is False
    assert brief["brief_count_mismatch_type"] == "too_many"
    assert brief["brief_count_mismatch_handled"] is True
    assert brief["brief_count_filled_from_core_events"] is True
    assert brief["brief_count_repair_attempted"] is True
    assert brief["brief_count_repair_succeeded"] is True
    assert brief["report_domestic_core_events_count"] == 5
    assert brief["report_overseas_core_events_count"] == 6
    assert brief["brief_final_domestic_items_count"] == 5
    assert brief["brief_expected_overseas_items_count"] == 4
    assert brief["brief_final_overseas_items_count"] == 4
    assert len(brief["domestic_top"]) == 5
    assert len(brief["overseas_top"]) == 4


def test_normalize_brief_keeps_valid_sources_and_limits_to_two():
    window = window_for_date(date(2026, 6, 1), "Asia/Shanghai")
    raw = {
        "domestic_top": [
            {
                "title": "事件",
                "why": "重要",
                "priority": "P1",
                "sources": [
                    {
                        "title": "A" * 40,
                        "url": "http://example.com/a/?utm_source=x#frag",
                        "source": "OpenAI",
                        "evidence_id": "e1",
                    },
                    {"title": "媒体", "url": "https://example.com/b/", "source": "TechCrunch"},
                    {"title": "第三条", "url": "https://example.com/c", "source": "第三方"},
                ],
            }
        ],
        "overseas_top": [],
    }
    evidence = [
        EvidenceItem(title="A", url="https://example.com/a", content="A"),
        EvidenceItem(title="B", url="https://example.com/b", content="B"),
        EvidenceItem(title="C", url="https://example.com/c", content="C"),
    ]

    brief = normalize_brief(raw, window, _audit(), report_md="", evidence=evidence)

    sources = brief["domestic_top"][0]["sources"]
    assert len(sources) == 2
    assert len(sources[0]["title"]) == 24
    assert sources[0]["url"] == "http://example.com/a/?utm_source=x#frag"
    assert sources[1]["source"] == "TechCrunch"


def test_normalize_brief_maps_source_ids_to_sources():
    window = window_for_date(date(2026, 6, 1), "Asia/Shanghai")
    raw = {
        "domestic_top": [
            {
                "title": "OpenAI发布新模型",
                "why": "影响开发者",
                "priority": "P1",
                "source_ids": ["E1", "E2", "E3"],
            }
        ],
    }
    evidence = [
        EvidenceItem(title="OpenAI news", url="https://openai.com/news/model", content="A", source="OpenAI"),
        EvidenceItem(title="TC analysis", url="https://techcrunch.com/a", content="B", source="TechCrunch"),
        EvidenceItem(title="Third", url="https://example.com/c", content="C", source="Example"),
    ]

    brief = normalize_brief(raw, window, _audit(), evidence=evidence)

    sources = brief["overseas_top"][0]["sources"]
    assert len(sources) == 2
    assert sources[0]["evidence_id"] == "E1"
    assert sources[0]["url"] == "https://openai.com/news/model"
    assert sources[1]["source"] == "TechCrunch"
    assert brief["brief_top_items_region_reassigned_count"] == 1


def test_normalize_brief_cleans_tavily_source_labels():
    window = window_for_date(date(2026, 6, 1), "Asia/Shanghai")
    raw = {"domestic_top": [{"title": "事件", "why": "重要", "priority": "P1", "source_ids": ["E1", "E2"]}]}
    evidence = [
        EvidenceItem(title="TC news", url="https://techcrunch.com/ai", content="A", source="Tavily", source_type="tavily_search"),
        EvidenceItem(title="No URL", url="", content="B", source="Tavily", source_type="tavily_search"),
    ]

    brief = normalize_brief(raw, window, _audit(), evidence=evidence)

    assert brief["domestic_top"][0]["sources"] == [
        {"title": "TC news", "url": "https://techcrunch.com/ai", "source": "TechCrunch", "evidence_id": "E1"}
    ]
    assert "tavily" not in str(brief["domestic_top"]).lower()


def test_normalize_brief_drops_no_core_fake_items_without_sources():
    window = window_for_date(date(2026, 6, 1), "Asia/Shanghai")
    raw = {
        "domestic_top": [{"title": "今日无强核心事件，不强行凑数。", "why": "", "priority": "观察", "source_ids": ["E1"]}],
        "overseas_top": [{"title": "无 P1/P2", "why": "", "priority": "观察", "sources": [{"url": "https://example.com/a"}]}],
    }
    evidence = [EvidenceItem(title="Tavily", url="https://example.com/a", content="A", source="Tavily", source_type="tavily_search")]

    brief = normalize_brief(raw, window, _audit(), evidence=evidence)

    assert brief["domestic_top"] == []
    assert brief["overseas_top"] == []
    assert brief["brief_llm_domestic_items_count"] == 0
    assert brief["brief_llm_overseas_items_count"] == 0
    assert brief["brief_empty_placeholder_removed_count"] == 2
    assert brief["brief_count_mismatch_type"] == "fake_empty_item"
    assert brief["brief_count_mismatch_handled"] is True


def test_normalize_brief_drops_invalid_source_ids_without_fallback():
    window = window_for_date(date(2026, 6, 1), "Asia/Shanghai")
    raw = {
        "domestic_top": [
            {
                "title": "OpenAI发布新模型",
                "why": "影响开发者",
                "priority": "P1",
                "source_ids": ["BAD", "E1"],
            }
        ],
    }
    evidence = [EvidenceItem(title="OpenAI news", url="https://openai.com/news/model", content="A", source="OpenAI")]

    brief = normalize_brief(raw, window, _audit(), evidence=evidence)

    assert brief["brief_generation_status"] == "ok"
    assert brief["brief_invalid_source_ids_count"] == 1
    assert brief["overseas_top"][0]["sources"][0]["evidence_id"] == "E1"


def test_normalize_brief_keeps_real_items_when_source_ids_invalid():
    window = window_for_date(date(2026, 6, 1), "Asia/Shanghai")
    raw = {
        "domestic_top": [
            {"title": "豆包订阅", "why": "商业化加速", "priority": "P1", "source_ids": ["BAD1"]},
            {"title": "Token套餐", "why": "运营商试水", "priority": "P2", "source_ids": ["BAD2"]},
            {"title": "模型降价", "why": "价格竞争", "priority": "观察", "source_ids": ["BAD3"]},
        ],
    }

    brief = normalize_brief(raw, window, _audit(), evidence=[EvidenceItem(title="无关", url="https://example.com/a", content="无关")])

    assert brief["brief_generation_status"] == "ok"
    assert brief["brief_source_resolution_status"] == "no_sources"
    assert brief["brief_llm_domestic_items_count"] == 3
    assert brief["brief_final_domestic_items_count"] == 1
    assert brief["brief_top_items_dropped_source_quality_count"] == 2
    assert [item["title"] for item in brief["domestic_top"]] == ["模型降价"]
    assert all(item["sources"] == [] for item in brief["domestic_top"])
    assert "无强核心事件" not in str(brief["domestic_top"])


def test_normalize_brief_drops_region_no_core_placeholder_items():
    window = window_for_date(date(2026, 6, 1), "Asia/Shanghai")
    raw = {
        "domestic_top": [
            {
                "title": "今日无国内核心事件",
                "card_title": "今日国内无核心事件",
                "why": "当日未发现国内强核心事件。",
                "priority": "观察",
                "source_ids": [],
            },
            {
                "title": "今日国内候选池无任何进入核心的事件。",
                "card_title": "当日无符合标准的国内核心事件",
                "why": "当日召回的信源中未发现国内AI厂商有模型能力突破或新应用发布。",
                "priority": "观察",
                "source_ids": [],
            }
        ],
        "overseas_top": [
            {
                "title": "今日海外无核心事件",
                "card_title": "今日无海外核心事件",
                "why": "当日未发现海外强核心事件。",
                "priority": "观察",
                "source_ids": [],
            }
        ],
    }

    brief = normalize_brief(raw, window, _audit(), evidence=[])

    assert brief["domestic_top"] == []
    assert brief["overseas_top"] == []
    assert brief["brief_empty_placeholder_removed_count"] == 3


def test_extract_core_events_ignores_no_core_explanation_block():
    report = """
## 一、国内版 AI 前沿能力与应用雷达【2026年06月10日】

### 今日总览

| 标题 | 层级 | 优先级 | 可信度 | 影响方向 |
|---|---|---|---|---|
| 今日无核心事件 | - | - | - | - |

### 逐条深度解读

今日国内版核心事件：无。

**说明：** 根据证据列表，今天国内没有符合P1/P2标准的新事件。今天无新增官方披露、新数据或新采用度信号足以重新纳入。因此国内版不强行凑数。

### 观察信号

1. **【L4】腾讯云Agent落地持续讨论**（无新数据，待观察）

## 二、海外版 AI 前沿能力与应用雷达【2026年06月10日】

### 今日总览

| 标题 | 层级 | 优先级 | 可信度 | 影响方向 |
|---|---|---|---|---|
| Anthropic Claude Fable 5 正式发布与定价 | L1 | P1 | 高 | 利好 |
""".strip()

    core_events = extract_core_events_from_report(report)

    assert core_events["domestic_core_events"] == []
    assert core_events["domestic_zero_core_explicit"] is True
    assert core_events["domestic_extraction_method"] == "none"


def test_extract_core_events_ignores_structural_no_event_sentence():
    report = """
# AI 前沿能力与应用雷达 - 国内版【2026年06月10日】

## 一、今日总览

| 标题 | 层级 | 优先级 | 可信度 | 影响方向 |
| :--- | :--- | :--- | :--- | :--- |
| 今日无符合入选标准的核心事件 | N/A | N/A | N/A | N/A |
| 本日无重大事件 | — | — | — | — |
| 本日无事件入选深度解读。 | - | 观察 | - | 本日无事件入选深度解读 |

## 二、逐条深度解读

**今日国内AI市场未出现符合筛选标准的结构性事件。**

证据列表中的所有国内相关线索，均指向数日前已报道事件，今日并无新的官方披露、关键数据更新或用户增长信号来支撑其再次进入核心。

1. **本日无事件入选深度解读。**
   - 优先级：观察
   - 为什么重要：本日无事件入选深度解读

## 三、观察信号

- 【L2】腾讯Agent生态持续落地，但无新增数据。

# AI 前沿能力与应用雷达 - 海外版【2026年06月10日】

## 一、今日总览

| 标题 | 层级 | 优先级 | 可信度 | 影响方向 |
| :--- | :--- | :--- | :--- | :--- |
| NVIDIA与苹果合作，助力AI隐私推理 | L0 | P1 | 高 | 利好 |
""".strip()

    core_events = extract_core_events_from_report(report)

    assert core_events["domestic_core_events"] == []
    assert core_events["domestic_zero_core_explicit"] is True
    assert core_events["domestic_extraction_method"] == "none"


def test_normalize_brief_drops_no_event_deep_dive_placeholder_items():
    window = window_for_date(date(2026, 6, 19), "Asia/Shanghai")
    raw = {
        "domestic_top": [
            {
                "title": "本日无事件入选深度解读。",
                "card_title": "本日无核心事件入选深度解读",
                "why": "今日国内AI产业没有监测到模型能力突破、新应用范式、重大商业化验证或显著采用度变化信号。",
                "card_why": "今日国内AI产业没有监测到模型能力突破、新应用范式、重大商业化验证或显著采用度变化信号。",
                "priority": "观察",
                "source_ids": [],
            }
        ],
        "overseas_top": [
            {
                "title": "今日无事件入选最终Top。",
                "why": "今日海外AI产业没有监测到强核心事件。",
                "priority": "观察",
                "source_ids": [],
            }
        ],
        "core_judgments": ["今日无P1/P2级核心事件，观察信号仍需继续跟踪。"],
        "watch_signals": [],
    }

    brief = normalize_brief(raw, window, _audit(), evidence=[])

    assert brief["domestic_top"] == []
    assert brief["overseas_top"] == []
    assert brief["core_judgments"] == ["今日无P1/P2级核心事件，观察信号仍需继续跟踪。"]
    assert brief["brief_empty_placeholder_removed_count"] == 2


def test_normalize_brief_resolves_source_ids_across_full_evidence_list():
    window = window_for_date(date(2026, 6, 1), "Asia/Shanghai")
    evidence = [
        EvidenceItem(
            title=f"Evidence {idx}",
            url=f"https://example.com/{idx}",
            content=f"content {idx}",
            source=f"Source {idx}",
            source_tier="S3",
            source_fit="high",
        )
        for idx in range(1, 81)
    ]
    evidence[12].title = "Anthropic IPO"
    evidence[29].title = "DeepSeek降价"
    evidence[35].title = "支付宝钱包"
    evidence[77].title = "Alphabet融资"
    raw = {
        "domestic_top": [
            {"title": "第21条事件", "why": "引用第21条证据", "priority": "P1", "source_ids": ["E21", "E78"]}
        ],
    }

    brief = normalize_brief(raw, window, _audit(), evidence=evidence)

    sources = brief["domestic_top"][0]["sources"]
    assert [source["evidence_id"] for source in sources] == ["E21", "E78"]
    assert sources[0]["url"] == "https://example.com/21"
    assert brief["brief_source_ids_requested_count"] == 2
    assert brief["brief_source_ids_resolved_count"] == 2
    assert brief["brief_source_ids_unresolved_count"] == 0
    assert len(sources) > 0


def test_normalize_brief_accepts_source_id_variants():
    window = window_for_date(date(2026, 6, 1), "Asia/Shanghai")
    evidence = [
        EvidenceItem(title=f"Evidence {idx}", url=f"https://example.com/{idx}", content=f"content {idx}", source=f"Source {idx}")
        for idx in range(1, 31)
    ]

    for source_id in ("E30", "e30", "30", "[30]", " E30 ", "E030"):
        brief = normalize_brief(
            {"domestic_top": [{"title": "事件", "why": "重要", "priority": "P1", "source_ids": [source_id]}]},
            window,
            _audit(),
            evidence=evidence,
        )
        assert brief["domestic_top"][0]["sources"][0]["evidence_id"] == "E30"


def test_normalize_brief_drops_source_urls_not_in_evidence_or_report():
    window = window_for_date(date(2026, 6, 1), "Asia/Shanghai")
    raw = {
        "domestic_top": [
            {
                "title": "事件",
                "why": "重要",
                "priority": "P1",
                "sources": [
                    {"title": "合法", "url": "https://example.com/report", "source": "官方"},
                    {"title": "非法", "url": "https://evil.example.com/a", "source": "编造"},
                ],
            }
        ],
    }

    brief = normalize_brief(
        raw,
        window,
        _audit(),
        report_md="来源：https://example.com/report?utm_campaign=x#part",
        evidence=[],
    )

    sources = brief["domestic_top"][0]["sources"]
    assert len(sources) == 1
    assert sources[0]["source"] == "官方"
    assert brief["brief_source_validation_warnings"]


def test_normalize_brief_fills_empty_sources_from_matching_evidence():
    window = window_for_date(date(2026, 6, 1), "Asia/Shanghai")
    raw = {
        "domestic_top": [
            {
                "title": "OpenAI发布新模型",
                "why": "OpenAI新模型影响开发者生态",
                "priority": "P1",
                "sources": [],
            }
        ],
    }
    evidence = [
        EvidenceItem(title="OpenAI发布新模型", url="https://openai.com/news/model", content="开发者生态", source="OpenAI"),
        EvidenceItem(title="无关新闻", url="https://example.com/other", content="完全无关", source="Example"),
    ]

    brief = normalize_brief(raw, window, _audit(), report_md="", evidence=evidence)

    sources = brief["overseas_top"][0]["sources"]
    assert sources == [
        {
            "title": "OpenAI发布新模型",
            "url": "https://openai.com/news/model",
            "source": "OpenAI",
            "evidence_id": "E1",
        }
    ]
    assert brief["brief_sources_filled_by_matching_count"] == 1


def test_normalize_brief_core_event_fallback_uses_deep_dive_why_and_matching_source():
    window = window_for_date(date(2026, 6, 3), "Asia/Shanghai")
    report = "\n".join(
        [
            "## 海外版正式雷达",
            "### 一、今日总览",
            "| 标题 | 层级 | 优先级 | 可信度 | 影响方向 |",
            "| --- | --- | --- | --- | --- |",
            "| Meta WhatsApp Business AI Agent全球商用 | L4 | P1 | 高 | 商业化验证 |",
            "### 二、逐条深度解读",
            "**1. Meta WhatsApp Business AI Agent全球商用，按Token收费**",
            "- **概述**：Meta宣布WhatsApp Business的AI Agent面向全球企业开放。",
            "- **影响 / So what**：按Token收费验证企业AI通信商业化，可能改变客服SaaS计费模式。",
            "- **来源**：[E12 TechCrunch](https://techcrunch.com/2026/06/03/metas-ai-agent-for-whatsapp-business-is-now-available-globally/)",
        ]
    )
    core_events = extract_core_events_from_report(report)
    evidence = [
        EvidenceItem(
            title="NVIDIA Research Unlocks Advanced Grasping",
            url="https://blogs.nvidia.com/blog/cvpr-research-grasping-driving-agent-training/",
            content="robotics and agent training",
            source="NVIDIA Blog AI",
        ),
        EvidenceItem(
            title="Meta’s AI agent for WhatsApp Business is now available globally",
            url="https://techcrunch.com/2026/06/03/metas-ai-agent-for-whatsapp-business-is-now-available-globally/",
            content="Meta WhatsApp Business AI Agent is globally available and charges by token.",
            source="TechCrunch AI",
        ),
    ]

    brief = normalize_brief({"domestic_top": [], "overseas_top": []}, window, _audit(), report_md=report, evidence=evidence, core_events=core_events)
    item = brief["overseas_top"][0]

    assert item["card_why"] == "按Token收费验证企业AI通信商业化，可能改变客服SaaS计费模式"
    assert "**1." not in item["card_why"]
    assert item["sources"][0]["evidence_id"] == "E2"
    assert "NVIDIA" not in item["sources"][0]["source"]


def test_normalize_brief_strips_so_what_label_from_core_event_fallback():
    window = window_for_date(date(2026, 6, 10), "Asia/Shanghai")
    report = "\n".join(
        [
            "## 国内版正式雷达",
            "### 一、今日总览",
            "| 标题 | 层级 | 优先级 | 可信度 | 影响方向 |",
            "| --- | --- | --- | --- | --- |",
            "| 全球AI调用量格局：中国包揽前四 | L1 | P2 | 中 | 采用度结构性变化 |",
            "### 二、逐条深度解读",
            "1. **标题：全球AI调用量格局：中国包揽前四**",
            "   - **影响 / So what：**",
            "     1. 它改变了什么？采用度结构性转向中国模型。中国模型调用量显著超过美国。",
            "   - **来源：** [E1 OpenRouter](https://openrouter.ai/rankings)",
        ]
    )
    core_events = extract_core_events_from_report(report)
    evidence = [
        EvidenceItem(
            title="OpenRouter model rankings",
            url="https://openrouter.ai/rankings",
            content="中国模型调用量领先。",
            source="OpenRouter",
            source_tier="S3",
            source_fit="high",
        )
    ]

    brief = normalize_brief({"domestic_top": [], "overseas_top": []}, window, _audit(), report_md=report, evidence=evidence, core_events=core_events)
    item = brief["domestic_top"][0]

    assert item["why"].startswith("采用度结构性转向中国模型")
    assert item["card_why"].startswith("采用度结构性转向中国模型")
    assert "它改变了什么" not in item["why"]


def test_normalize_brief_drops_numbered_card_why_and_wrong_sources():
    window = window_for_date(date(2026, 6, 3), "Asia/Shanghai")
    raw = {
        "overseas_top": [
            {
                "title": "Meta WhatsApp Business AI Agent全球商用",
                "card_title": "Meta WhatsApp AI Agent全球商用",
                "why": "**3. ，按Token收费**",
                "card_why": "**3. ，按Token收费**",
                "priority": "P1",
                "source_ids": ["E1"],
            }
        ]
    }
    evidence = [
        EvidenceItem(
            title="NVIDIA Research Unlocks Advanced Grasping",
            url="https://blogs.nvidia.com/blog/cvpr-research-grasping-driving-agent-training/",
            content="robotics and agent training",
            source="NVIDIA Blog AI",
        ),
        EvidenceItem(
            title="Meta’s AI agent for WhatsApp Business is now available globally",
            url="https://techcrunch.com/2026/06/03/metas-ai-agent-for-whatsapp-business-is-now-available-globally/",
            content="Meta WhatsApp Business AI Agent is globally available and charges by token.",
            source="TechCrunch AI",
        ),
    ]

    brief = normalize_brief(raw, window, _audit(), evidence=evidence)
    item = brief["overseas_top"][0]

    assert item["card_why"] == "详见完整日报。"
    assert item["sources"][0]["evidence_id"] == "E2"
    assert brief["brief_source_validation_warnings"]


def test_normalize_brief_drops_p1_p2_top_without_s1_s2_s3_source():
    window = window_for_date(date(2026, 6, 10), "Asia/Shanghai")
    raw = {
        "domestic_top": [
            {
                "title": "普通媒体事件",
                "why": "普通媒体报道的核心事件。",
                "priority": "P1",
                "source_ids": ["E1"],
            }
        ]
    }
    evidence = [
        EvidenceItem(
            title="普通媒体事件",
            url="https://example.com/a",
            content="普通媒体报道。",
            source="Example",
            source_tier="S4",
            source_fit="medium",
        )
    ]

    brief = normalize_brief(raw, window, _audit(), evidence=evidence)

    assert brief["domestic_top"] == []
    assert brief["brief_top_items_dropped_source_quality_count"] == 1
    assert "普通媒体事件" in brief["brief_top_items_dropped_source_quality_examples"]
    assert "dropped top event without S1/S2/S3 source: 普通媒体事件" in brief["brief_source_validation_warnings"]


def test_normalize_brief_drops_demoted_top_from_core_judgment_cards():
    window = window_for_date(date(2026, 6, 21), "Asia/Shanghai")
    raw = {
        "domestic_top": [],
        "overseas_top": [
            {
                "title": "AI订阅制面临“补贴倒挂”拷问",
                "why": "SemiAnalysis 数据显示高阶订阅存在补贴倒挂。",
                "card_why": "订阅补贴倒挂，待强源确认。",
                "priority": "P1",
                "source_ids": ["E1"],
            },
            {
                "title": "苹果iOS 27系统级AI路径显现",
                "why": "苹果将 AI 嵌入系统底层，重塑移动端 AI 入口。",
                "card_why": "苹果系统级 AI 路径明朗。",
                "priority": "P1",
                "source_ids": ["E2"],
            },
        ],
        "core_judgments": [
            {
                "full": "苹果iOS 27系统级AI路径显现，AI正从单点功能进化为操作系统底层能力。",
                "card": "苹果iOS 27将AI嵌入系统底层。",
            },
            {
                "full": "AI订阅制面临补贴倒挂拷问，可能加速按量计费。",
                "card": "AI订阅补贴倒挂，或推动按量计费。",
            },
        ],
        "watch_signals": [],
    }
    evidence = [
        EvidenceItem(
            title="AI订阅制面临“补贴倒挂”拷问",
            url="https://example.com/subscription-gap",
            content="SemiAnalysis 数据显示高阶订阅存在补贴倒挂。",
            source="Example",
            source_tier="S4",
            source_fit="medium",
        ),
        EvidenceItem(
            title="Beyond Siri: practical AI features coming to iOS 27",
            url="https://example.com/apple-ios-27",
            content="Apple is adding practical AI features to iOS 27.",
            source="TechCrunch",
            source_tier="S2",
            source_fit="high",
        ),
    ]

    brief = normalize_brief(raw, window, _audit(), evidence=evidence)

    assert [item["title"] for item in brief["overseas_top"]] == ["苹果iOS 27系统级AI路径显现"]
    assert not any("补贴倒挂" in item for item in brief["core_judgments"])
    assert not any("补贴倒挂" in item for item in brief["core_judgments_card"])
    assert any("苹果iOS 27" in item for item in brief["core_judgments"])
    assert any("dropped top event without S1/S2/S3 source: AI订阅制面临“补贴倒挂”拷问" in item for item in brief["brief_source_validation_warnings"])


def test_normalize_brief_keeps_only_final_top_bound_core_judgments():
    window = window_for_date(date(2026, 6, 21), "Asia/Shanghai")
    raw = {
        "domestic_top": [],
        "overseas_top": [
            {
                "title": "iOS 27曝光实用AI功能，Agent嵌入系统级交互",
                "why": "iOS 27将AI能力深度整合进系统，标志AI Agent从应用层向操作系统层迁移。",
                "card_why": "iOS 27推动Agent入口向OS层迁移。",
                "priority": "P1",
                "source_ids": ["E1"],
            }
        ],
        "core_judgments": [
            {
                "full": "AI商业模式面临盈利拷问：AI巨头的订阅模式被揭示存在严重的价值倒挂。",
                "card": "AI订阅模式价值倒挂，冲击头部玩家估值逻辑。",
            },
            {
                "full": "AI Agent入口加速向操作系统层迁移：Apple在iOS 27中系统级部署AI功能。",
                "card": "iOS 27系统级AI部署标志Agent入口向OS渗透。",
            },
            {
                "full": "国内AI竞争焦点转向超级入口卡位战，微信、阿里正加速将AI嵌入高频入口。",
                "card": "国内巨头争夺输入法、超级APP等高频AI入口。",
            },
        ],
        "watch_signals": [],
    }
    evidence = [
        EvidenceItem(
            title="Beyond Siri: practical AI features coming to iOS 27",
            url="https://example.com/apple-ios-27",
            content="Apple is adding practical AI features to iOS 27.",
            source="TechCrunch",
            source_tier="S2",
            source_fit="high",
        )
    ]

    brief = normalize_brief(raw, window, _audit(), evidence=evidence)

    assert len(brief["core_judgments"]) == 1
    assert len(brief["core_judgments_card"]) == 1
    assert "iOS 27" in brief["core_judgments"][0]
    assert not any("订阅" in item or "国内AI竞争" in item for item in brief["core_judgments"])
    assert not any("订阅" in item or "国内巨头" in item for item in brief["core_judgments_card"])
    assert brief["brief_core_judgments_dropped_non_top_count"] == 2


def test_normalize_brief_drops_top_with_only_not_core_eligible_source_id():
    window = window_for_date(date(2026, 6, 11), "Asia/Shanghai")
    raw = {
        "domestic_top": [
            {
                "title": "千问App向第三方Agent/Skill全面开放",
                "why": "千问开放第三方Agent生态。",
                "priority": "P1",
                "source_ids": ["E2"],
            }
        ]
    }
    unrelated = EvidenceItem(
        title="My yard is dying, so I built an AI app",
        url="https://www.theverge.com/example/yard-ai-app",
        content="A gardening app story unrelated to Qwen.",
        source="The Verge",
        source_tier="S2",
        source_fit="high",
    )
    weak = EvidenceItem(
        title="千问App向第三方Agent/Skill全面开放",
        url="https://finance.sina.com.cn/example/qwen-agent",
        content="新浪转载千问开放第三方Agent能力。",
        source="新浪",
        source_tier="S4",
        source_fit="medium",
    )
    weak.not_core_eligible = True

    brief = normalize_brief(raw, window, _audit(), evidence=[unrelated, weak])

    assert brief["domestic_top"] == []
    assert brief["brief_top_items_dropped_source_quality_count"] == 1
    assert any("dropped not-core-eligible source binding: E2" in warning for warning in brief["brief_source_validation_warnings"])


def test_normalize_brief_rejects_generic_app_source_mismatch():
    window = window_for_date(date(2026, 6, 11), "Asia/Shanghai")
    raw = {
        "domestic_top": [
            {
                "title": "千问App向第三方Agent/Skill全面开放",
                "why": "千问开放第三方Agent生态。",
                "priority": "P1",
                "source_ids": ["E1"],
            }
        ]
    }
    evidence = [
        EvidenceItem(
            title="My yard is dying, so I built an AI app",
            url="https://www.theverge.com/example/yard-ai-app",
            content="A gardening app story unrelated to Qwen or Alibaba.",
            source="The Verge",
            source_tier="S2",
            source_fit="high",
        )
    ]

    brief = normalize_brief(raw, window, _audit(), evidence=evidence)

    assert brief["domestic_top"] == []
    assert brief["brief_top_items_dropped_source_quality_count"] == 1
    assert any("dropped low-confidence source binding: E1" in warning for warning in brief["brief_source_validation_warnings"])


def test_normalize_brief_reassigns_top_items_by_subject_region():
    window = window_for_date(date(2026, 6, 11), "Asia/Shanghai")
    raw = {
        "domestic_top": [
            {
                "title": "Meta将AI助手扩展到WhatsApp Business",
                "why": "Meta扩大海外AI商业化入口。",
                "priority": "P1",
                "source_ids": ["E1"],
            }
        ],
        "overseas_top": [
            {
                "title": "DeepSeek API价格调整",
                "why": "DeepSeek调整API价格。",
                "priority": "P1",
                "source_ids": ["E2"],
            }
        ],
    }
    evidence = [
        EvidenceItem(
            title="Meta’s AI agent for WhatsApp Business is now available globally",
            url="https://techcrunch.com/example/meta-whatsapp-ai-agent",
            content="Meta WhatsApp Business AI Agent is available globally.",
            source="TechCrunch AI",
            source_tier="S2",
            source_fit="high",
        ),
        EvidenceItem(
            title="DeepSeek API价格调整",
            url="https://api-docs.deepseek.com/news/news250611",
            content="DeepSeek调整API价格。",
            source="DeepSeek Docs",
            source_tier="S1",
            source_fit="high",
        ),
    ]

    brief = normalize_brief(raw, window, _audit(), evidence=evidence)

    assert [item["title"] for item in brief["domestic_top"]] == ["DeepSeek API价格调整"]
    assert [item["title"] for item in brief["overseas_top"]] == ["Meta将AI助手扩展到WhatsApp Business"]
    assert brief["brief_top_items_region_reassigned_count"] == 2


def test_normalize_brief_demotes_source_quality_dropped_top_items_to_watch_signals():
    window = window_for_date(date(2026, 6, 10), "Asia/Shanghai")
    raw = {
        "domestic_top": [
            {
                "title": "腾讯发布效率智能体工具集",
                "why": "腾讯发布效率智能体工具集，覆盖企业工作流入口。",
                "priority": "P2",
                "source_ids": ["E1"],
            },
            {
                "title": "微信支付内测AI支付功能",
                "why": "微信支付内测AI支付功能。",
                "priority": "P2",
                "source_ids": ["E2"],
            },
        ],
        "overseas_top": [],
        "core_judgments": [
            "微信支付内测AI支付功能和腾讯Agent矩阵共同推进交易闭环。",
            "腾讯发布效率智能体工具集，企业工作流入口继续成形。",
        ],
        "watch_signals": ["微信支付内测AI支付功能仍需官方确认。"],
    }
    evidence = [
        EvidenceItem(
            title="腾讯发布效率智能体工具集",
            url="https://example.com/tencent-agent",
            content="腾讯发布效率智能体工具集。",
            source="第一财经",
            source_tier="S2",
            source_fit="medium",
        ),
        EvidenceItem(
            title="微信支付内测AI支付功能",
            url="https://example.com/wechat-pay",
            content="普通媒体转述微信支付AI功能。",
            source="普通媒体",
            source_tier="S4",
            source_fit="medium",
        ),
    ]

    brief = normalize_brief(raw, window, _audit(), evidence=evidence)

    assert [item["title"] for item in brief["domestic_top"]] == ["腾讯发布效率智能体工具集"]
    assert brief["brief_top_items_dropped_source_quality_count"] == 1
    assert not any("微信支付" in item for item in brief["core_judgments"])
    assert any("微信支付" in item and "待 S1/S2/S3 强源确认" in item for item in brief["watch_signals"])
    assert brief["brief_watch_signals_demoted_from_top_count"] == 1
    assert brief["brief_watch_signals_demoted_from_top_examples"] == ["微信支付内测AI支付功能"]
    assert brief["core_judgments"] == ["腾讯发布效率智能体工具集，企业工作流入口继续成形。"]


def test_normalize_brief_drops_core_judgment_mixing_demoted_top_item():
    window = window_for_date(date(2026, 6, 14), "Asia/Shanghai")
    raw = {
        "domestic_top": [],
        "overseas_top": [
            {
                "title": "KPMG推出企业级AI审计工作流",
                "why": "KPMG将AI嵌入审计流程，企业服务落地提速。",
                "priority": "P2",
                "source_ids": ["E1"],
            },
            {
                "title": "OpenAI上市前夜遭多州总检察长调查",
                "why": "OpenAI在IPO前夜遭遇监管压力，治理风险抬升。",
                "priority": "P2",
                "source_ids": ["E2"],
            },
        ],
        "core_judgments": [
            "OpenAI在IPO前夜遭遇监管围猎，同时KPMG的AI审计工作流说明企业落地提速。",
        ],
        "watch_signals": [],
    }
    evidence = [
        EvidenceItem(
            title="KPMG推出企业级AI审计工作流",
            url="https://example.com/kpmg-ai-audit",
            content="KPMG将AI嵌入审计流程，企业服务落地提速。",
            source="KPMG",
            source_tier="S2",
            source_fit="high",
        ),
        EvidenceItem(
            title="OpenAI上市前夜遭多州总检察长调查",
            url="https://example.com/openai-investigation",
            content="普通媒体转述OpenAI监管调查。",
            source="普通媒体",
            source_tier="S4",
            source_fit="medium",
        ),
    ]

    brief = normalize_brief(raw, window, _audit(), evidence=evidence)

    assert [item["title"] for item in brief["overseas_top"]] == ["KPMG推出企业级AI审计工作流"]
    assert not any("OpenAI" in item for item in brief["core_judgments"])
    assert any("KPMG" in item for item in brief["core_judgments"])
    assert any("OpenAI" in item and "待 S1/S2/S3 强源确认" in item for item in brief["watch_signals"])


def test_normalize_brief_drops_core_judgment_with_short_cjk_demoted_title():
    window = window_for_date(date(2026, 6, 14), "Asia/Shanghai")
    raw = {
        "overseas_top": [
            {
                "title": "亚马逊CEO被曝为Anthropic禁令幕后推手",
                "why": "亚马逊CEO安全担忧影响Anthropic模型访问。",
                "priority": "P1",
                "source_ids": ["E1"],
            }
        ],
        "domestic_top": [
            {
                "title": "蚂蚁被曝秘密测试“AI版支付宝”",
                "why": "蚂蚁测试AI版支付宝，超级App入口可能Agent化。",
                "priority": "P2",
                "source_ids": ["E2"],
            }
        ],
        "core_judgments": [
            "“AI原生入口”竞赛悄然打响：“AI版支付宝”的传闻，标志着超级App正在向Agent化中枢转型。",
        ],
        "watch_signals": [],
    }
    evidence = [
        EvidenceItem(
            title="Amazon CEO reportedly raised Anthropic model concerns",
            url="https://example.com/amazon-anthropic",
            content="Amazon CEO raised concerns over Anthropic model access.",
            source="TechCrunch",
            source_tier="S2",
            source_fit="high",
        ),
        EvidenceItem(
            title="蚂蚁被曝秘密测试AI版支付宝",
            url="https://example.com/ant-ai-alipay",
            content="普通媒体称蚂蚁测试AI版支付宝。",
            source="普通媒体",
            source_tier="S4",
            source_fit="medium",
        ),
    ]

    brief = normalize_brief(raw, window, _audit(), evidence=evidence)

    assert not any("AI版支付宝" in item for item in brief["core_judgments"])
    assert any("Anthropic" in item for item in brief["core_judgments"])
    assert any("AI版支付宝" in item and "待 S1/S2/S3 强源确认" in item for item in brief["watch_signals"])


def test_normalize_brief_drops_core_judgment_not_tied_to_final_top():
    window = window_for_date(date(2026, 6, 13), "Asia/Shanghai")
    raw = {
        "domestic_top": [
            {
                "title": "智谱GLM-5.2全量开放",
                "why": "智谱全量开放GLM-5.2，强化国产模型供给。",
                "card_why": "智谱开放GLM-5.2，强化国产模型供给。",
                "priority": "P2",
                "source_ids": ["E1"],
            }
        ],
        "overseas_top": [
            {
                "title": "美国政府勒令Anthropic切断最强AI模型",
                "why": "美国政府要求Anthropic限制模型访问，前沿模型访问权成为政策变量。",
                "card_why": "Anthropic模型访问权成为政策变量。",
                "priority": "P2",
                "source_ids": ["E2"],
            },
            {
                "title": "200美元AI订阅可榨取70倍Token用量",
                "why": "SemiAnalysis量化AI订阅Token用量，提示高阶订阅单位经济承压。",
                "card_why": "AI订阅Token用量提示高阶订阅单位经济承压。",
                "priority": "P2",
                "source_ids": ["E3"],
            },
        ],
        "core_judgments": [
            "千问App向第三方开放Agent/Skill生态，国内助手入口继续平台化。",
            "美国政府勒令Anthropic切断最强AI模型，模型访问权正在被政策化。",
        ],
        "watch_signals": [],
    }
    evidence = [
        EvidenceItem(
            title="智谱GLM-5.2全量开放",
            url="https://example.com/zhipu-glm-5-2",
            content="智谱GLM-5.2全量开放，强化国产模型供给。",
            source="第一财经",
            source_tier="S2",
            source_fit="high",
        ),
        EvidenceItem(
            title="美国政府勒令Anthropic切断最强AI模型",
            url="https://example.com/anthropic-access",
            content="美国政府要求Anthropic限制最强AI模型访问，Anthropic模型访问权成为政策变量。",
            source="TechCrunch",
            source_tier="S2",
            source_fit="high",
        ),
        EvidenceItem(
            title="200美元AI订阅可榨取70倍Token用量",
            url="https://example.com/ai-subscription-token-usage",
            content="SemiAnalysis量化200美元AI订阅可榨取70倍Token用量，提示高阶订阅单位经济承压。",
            source="SemiAnalysis",
            source_tier="S2",
            source_fit="high",
        ),
    ]

    brief = normalize_brief(raw, window, _audit(), evidence=evidence)

    assert brief["brief_core_judgments_dropped_non_top_count"] == 1
    assert not any("千问" in item for item in brief["core_judgments"])
    assert any("Anthropic" in item for item in brief["core_judgments"])
    assert any("智谱" in item for item in brief["core_judgments"])
    assert any("200美元AI订阅" in item for item in brief["core_judgments"])
    assert any("dropped core judgment not tied to final top: 1" in item for item in brief["brief_source_validation_warnings"])


def test_normalize_brief_keeps_p1_p2_top_with_s3_data_source():
    window = window_for_date(date(2026, 6, 10), "Asia/Shanghai")
    raw = {
        "domestic_top": [
            {
                "title": "OpenRouter调用量排名更新",
                "why": "原始数据源显示模型采用度变化。",
                "priority": "P2",
                "source_ids": ["E1"],
            }
        ]
    }
    evidence = [
        EvidenceItem(
            title="OpenRouter调用量排名更新",
            url="https://openrouter.ai/rankings",
            content="模型调用量排名。",
            source="OpenRouter",
            source_tier="S3",
            source_fit="high",
        )
    ]

    brief = normalize_brief(raw, window, _audit(), evidence=evidence)

    assert [item["title"] for item in brief["domestic_top"]] == ["OpenRouter调用量排名更新"]
    assert brief["brief_top_items_dropped_source_quality_count"] == 0


def test_normalize_brief_drops_unrelated_s2_sources_from_why_mentions():
    window = window_for_date(date(2026, 6, 10), "Asia/Shanghai")
    raw = {
        "domestic_top": [
            {
                "title": "扣子(Coze) 3.0发布：支持多Agent协作工作区",
                "why": "字节扣子允许将Claude Code、Codex等不同Agent拉入同一项目空间。",
                "priority": "P2",
                "source_ids": ["E1"],
            }
        ]
    }
    evidence = [
        EvidenceItem(
            title="Anthropic’s Claude Fable 5 can make video games",
            url="https://techcrunch.com/2026/06/09/anthropics-fable-5-can-make-weirdly-fun-video-games-with-the-click-of-a-button/",
            content="Anthropic Fable 5 Claude model news.",
            source="TechCrunch AI",
            source_tier="S2",
            source_fit="high",
        )
    ]

    brief = normalize_brief(raw, window, _audit(), evidence=evidence)

    assert brief["domestic_top"] == []
    assert brief["brief_top_items_dropped_source_quality_count"] == 1
    assert any("dropped low-confidence source binding" in warning for warning in brief["brief_source_validation_warnings"])


def test_normalize_brief_replaces_broad_entity_source_with_event_specific_match():
    window = window_for_date(date(2026, 6, 11), "Asia/Shanghai")
    raw = {
        "overseas_top": [
            {
                "title": "OpenAI收购Ona，强化Codex企业级Agent能力",
                "why": "OpenAI宣布收购Ona，为Codex提供持久化企业级云环境。",
                "priority": "P1",
                "source_ids": ["E1"],
            }
        ]
    }
    evidence = [
        EvidenceItem(
            title="How an astrophysicist uses Codex to help simulate black holes",
            url="https://openai.com/index/using-codex-to-simulate-black-holes",
            content="OpenAI Codex helps scientists simulate black holes.",
            source="OpenAI News",
            source_tier="S1",
            source_fit="high",
        ),
        EvidenceItem(
            title="OpenAI to acquire Ona",
            url="https://openai.com/index/openai-to-acquire-ona",
            content="OpenAI plans to acquire Ona to expand Codex with secure, persistent cloud environments.",
            source="OpenAI News",
            source_tier="S1",
            source_fit="high",
        ),
    ]

    brief = normalize_brief(raw, window, _audit(), evidence=evidence)

    sources = brief["overseas_top"][0]["sources"]
    assert [source["url"] for source in sources] == ["https://openai.com/index/openai-to-acquire-ona"]
    assert brief["brief_sources_filled_by_matching_count"] == 1
    assert any("dropped low-confidence source binding: E1" in warning for warning in brief["brief_source_validation_warnings"])


def test_normalize_brief_requires_entity_overlap_for_core_source_binding():
    window = window_for_date(date(2026, 6, 13), "Asia/Shanghai")
    raw = {
        "overseas_top": [
            {
                "title": "美国政府强制叫停最强AI模型服务",
                "card_title": "美国政府叫停Anthropic最强模型",
                "why": "美国政府要求Anthropic切断Fable 5和Mythos 5访问。",
                "priority": "P1",
                "source_ids": ["E1", "E2"],
            },
            {
                "title": "Mistral传闻以200亿欧元估值融资",
                "why": "Mistral传出以200亿欧元估值进行巨额融资。",
                "priority": "P2",
                "source_ids": ["E3", "E4"],
            },
        ]
    }
    evidence = [
        EvidenceItem(
            title="曝 Meta 发布 AI 使用限制令",
            url="https://www.ithome.com/meta",
            content="Meta员工AI token预算管理。",
            source="IT之家",
            source_tier="S2",
            source_fit="high",
        ),
        EvidenceItem(
            title="Anthropic cuts off Fable 5 and Mythos 5 access following government order",
            url="https://www.theverge.com/anthropic-government-order",
            content="Anthropic cut off Fable 5 and Mythos 5 access following a government order.",
            source="The Verge",
            source_tier="S2",
            source_fit="high",
        ),
        EvidenceItem(
            title="SemiAnalysis 洞察 Token 经济",
            url="https://www.ithome.com/semianalysis-token",
            content="SemiAnalysis compares Anthropic and OpenAI subscription economics.",
            source="IT之家",
            source_tier="S2",
            source_fit="high",
        ),
        EvidenceItem(
            title="Mistral is rumored to be raising €3B at €20B valuation",
            url="https://techcrunch.com/mistral-funding",
            content="Mistral is rumored to be raising 3B euros at a 20B euros valuation.",
            source="TechCrunch",
            source_tier="S2",
            source_fit="high",
        ),
    ]

    brief = normalize_brief(raw, window, _audit(), evidence=evidence)

    sources = [item["sources"][0]["evidence_id"] for item in brief["overseas_top"]]
    assert sources == ["E2", "E4"]
    assert any("dropped low-confidence source binding: E1" in warning for warning in brief["brief_source_validation_warnings"])
    assert any("dropped low-confidence source binding: E3" in warning for warning in brief["brief_source_validation_warnings"])


def test_normalize_brief_rejects_same_entity_but_wrong_event_source_ids():
    window = window_for_date(date(2026, 6, 13), "Asia/Shanghai")
    raw = {
        "overseas_top": [
            {
                "title": "美政府令Anthropic切断最强模型访问",
                "card_title": "Anthropic最强模型被切断访问",
                "why": "美国政府以国家安全为由要求Anthropic切断Fable 5和Mythos 5访问。",
                "priority": "P1",
                "source_ids": ["E1", "E2"],
            },
            {
                "title": "200美元订阅与万六API用量揭示成本鸿沟",
                "card_title": "200美元订阅榨出70倍Token用量",
                "why": "SemiAnalysis实测显示200美元订阅可消耗上万API用量，暴露订阅与API成本鸿沟。",
                "priority": "P1",
                "source_ids": ["E3", "E4"],
            },
        ]
    }
    evidence = [
        EvidenceItem(
            title="Anthropic cuts off Fable 5 and Mythos 5 access following government order",
            url="https://www.theverge.com/anthropic-government-order",
            content="The government ordered Anthropic to block access to Fable 5 and Mythos 5 due to national security.",
            source="The Verge",
            source_tier="S2",
            source_fit="high",
        ),
        EvidenceItem(
            title="SemiAnalysis 洞察 Token 经济:200 美元 AI 订阅榨出 70 倍用量",
            url="https://www.ithome.com/semianalysis-token",
            content="SemiAnalysis compares Anthropic Claude Max and OpenAI ChatGPT Pro subscription token economics.",
            source="IT之家",
            source_tier="S2",
            source_fit="high",
        ),
        EvidenceItem(
            title="SemiAnalysis 洞察 Token 经济:200 美元 AI 订阅榨出 70 倍用量",
            url="https://www.ithome.com/0/963/834.htm",
            content="200美元AI订阅可消耗价值14000美元API额度，订阅价仅为API成本的1/70。",
            source="IT之家",
            source_tier="S2",
            source_fit="high",
        ),
        EvidenceItem(
            title="SpaceX, Anthropic, and OpenAI’s hot IPO summer",
            url="https://techcrunch.com/video/spacex-anthropic-and-openais-hot-ipo-summer/",
            content="The IPO market is back, led by SpaceX, Anthropic, and OpenAI.",
            source="TechCrunch AI",
            source_tier="S2",
            source_fit="high",
        ),
    ]

    brief = normalize_brief(raw, window, _audit(), evidence=evidence)

    assert [[source["evidence_id"] for source in item["sources"]] for item in brief["overseas_top"]] == [["E1"], ["E3"]]
    assert any("dropped low-confidence source binding: E2" in warning for warning in brief["brief_source_validation_warnings"])
    assert any("dropped low-confidence source binding: E4" in warning for warning in brief["brief_source_validation_warnings"])


def test_normalize_brief_prefers_top_tier_sources_over_reprints():
    window = window_for_date(date(2026, 6, 11), "Asia/Shanghai")
    raw = {
        "overseas_top": [
            {
                "title": "OpenAI收购Ona：为Codex添加持久云环境",
                "why": "OpenAI收购Ona，为Codex添加持久云环境。",
                "priority": "P1",
                "source_ids": ["E1", "E2"],
            }
        ]
    }
    evidence = [
        EvidenceItem(
            title="OpenAI to acquire Ona",
            url="https://openai.com/index/openai-to-acquire-ona",
            content="OpenAI plans to acquire Ona to expand Codex with secure, persistent cloud environments.",
            source="OpenAI News",
            source_tier="S1",
            source_fit="high",
        ),
        EvidenceItem(
            title="OpenAI收购Ona转载",
            url="https://www.yoojia.com/article/9754053634779706012.html",
            content="OpenAI收购Ona的中文转载摘要。",
            source="有驾",
            source_tier="S4",
            source_fit="medium",
        ),
    ]

    brief = normalize_brief(raw, window, _audit(), evidence=evidence)

    assert [source["url"] for source in brief["overseas_top"][0]["sources"]] == [
        "https://openai.com/index/openai-to-acquire-ona"
    ]


def test_brief_generator_keeps_ok_when_source_gate_drops_only_top(monkeypatch):
    window = window_for_date(date(2026, 6, 10), "Asia/Shanghai")
    generator = object.__new__(DeepSeekBriefGenerator)

    def fake_call(_prompt):
        return json.dumps(
            {
                "domestic_top": [{"title": "普通媒体事件", "why": "只有普通媒体报道。", "priority": "P1", "source_ids": ["E1"]}],
                "overseas_top": [],
                "core_judgments": ["来源不足时不强行凑 Top。"],
                "watch_signals": [],
            },
            ensure_ascii=False,
        )

    monkeypatch.setattr(generator, "_call", fake_call)
    evidence = [
        EvidenceItem(
            title="普通媒体事件",
            url="https://example.com/a",
            content="普通媒体报道。",
            source="Example",
            source_tier="S4",
            source_fit="medium",
        )
    ]

    brief = generator.generate(window, "# report", _audit(), evidence=evidence)

    assert brief["brief_generation_status"] == "ok"
    assert brief["domestic_top"] == []
    assert brief["brief_top_items_dropped_source_quality_count"] == 1
    assert brief["brief_normalization_error"] == ""
    assert brief["core_judgments"] == ["来源不足时不强行凑 Top。"]


def test_normalize_brief_low_match_keeps_empty_sources_without_fallback():
    window = window_for_date(date(2026, 6, 1), "Asia/Shanghai")
    raw = {"domestic_top": [{"title": "完全不同", "why": "没有匹配", "priority": "观察"}]}
    evidence = [EvidenceItem(title="OpenAI", url="https://openai.com/news/model", content="model release", source="OpenAI")]

    brief = normalize_brief(raw, window, _audit(), evidence=evidence)

    assert brief["brief_generation_status"] == "ok"
    assert brief["domestic_top"][0]["sources"] == []
    assert brief["brief_source_resolution_status"] == "no_source_ids"


def test_render_brief_markdown_shows_sources():
    window = window_for_date(date(2026, 6, 1), "Asia/Shanghai")
    brief = normalize_brief(
        {
            "domestic_top": [
                {
                    "title": "事件",
                    "why": "重要",
                    "priority": "P1",
                    "sources": [{"title": "来源", "url": "https://example.com/a", "source": "OpenAI"}],
                }
            ],
        },
        window,
        _audit(),
        report_md="来源：https://example.com/a",
    )

    md = render_brief_markdown(brief)

    assert "1. 事件｜P1" in md
    assert "   来源：[OpenAI](https://example.com/a)" in md


def test_brief_generator_falls_back_after_invalid_json(monkeypatch):
    window = window_for_date(date(2026, 6, 1), "Asia/Shanghai")
    generator = object.__new__(DeepSeekBriefGenerator)
    calls = {"count": 0}

    def fake_call(prompt):
        calls["count"] += 1
        return "not json"

    monkeypatch.setattr(generator, "_call", fake_call)

    brief = generator.generate(window, "# report", _audit(), doc_url="")

    assert calls["count"] == 2
    assert brief["title"] == "AI Radar｜2026-06-01"
    assert brief["brief_generation_status"] == "fallback"
    assert brief["core_judgments"] == ["今日简报摘要未能稳定生成，请查看完整日报。"]
    assert brief["doc_url"] == ""
    assert "brief 生成失败" not in str(brief)
    assert "简报摘要生成异常" not in str(brief)


def test_brief_generator_marks_repaired_json(monkeypatch):
    window = window_for_date(date(2026, 6, 1), "Asia/Shanghai")
    generator = object.__new__(DeepSeekBriefGenerator)
    calls = {"count": 0}

    def fake_call(prompt):
        calls["count"] += 1
        if calls["count"] == 1:
            return "not json"
        return '{"domestic_top":[{"title":"OpenAI发布新模型","why":"影响开发者","priority":"P1","source_ids":["E1"]}]}'

    monkeypatch.setattr(generator, "_call", fake_call)

    brief = generator.generate(
        window,
        "来源：https://openai.com/news/model",
        _audit(),
        doc_url="",
        evidence=[EvidenceItem(title="OpenAI发布新模型", url="https://openai.com/news/model", content="影响开发者", source="OpenAI")],
    )

    assert brief["brief_generation_status"] == "repaired"
    assert brief["brief_repair_attempted"] is True
    assert brief["brief_repair_succeeded"] is True
    assert brief["overseas_top"][0]["sources"][0]["source"] == "OpenAI"


def test_brief_generator_keeps_full_json_items_and_source_counts(monkeypatch):
    window = window_for_date(date(2026, 6, 1), "Asia/Shanghai")
    generator = object.__new__(DeepSeekBriefGenerator)
    evidence = [
        EvidenceItem(
            title=f"Evidence {idx}",
            url=f"https://example.com/{idx}",
            content=f"content {idx}",
            source=f"Source {idx}",
            source_tier="S3",
            source_fit="high",
        )
        for idx in range(1, 81)
    ]
    evidence[12].title = "Anthropic IPO"
    evidence[29].title = "DeepSeek降价"
    evidence[35].title = "支付宝钱包"
    evidence[77].title = "Alphabet融资"
    raw = {
        "domestic_top": [
            {"title": "DeepSeek降价", "why": "API价格下降", "priority": "P1", "source_ids": ["E30"]},
            {"title": "支付宝钱包", "why": "Token Pay发布", "priority": "P2", "source_ids": ["E36"]},
            {"title": "Token套餐", "why": "运营商上线", "priority": "观察", "source_ids": ["E20"]},
        ],
        "overseas_top": [
            {"title": "Anthropic IPO", "why": "正式提交", "priority": "P1", "source_ids": ["E13"]},
            {"title": "Alphabet融资", "why": "大额融资", "priority": "P2", "source_ids": ["E78"]},
        ],
    }

    monkeypatch.setattr(generator, "_call", lambda prompt: json.dumps(raw, ensure_ascii=False))

    brief = generator.generate(window, "# report", _audit(), evidence=evidence)

    assert brief["brief_generation_status"] == "ok"
    assert brief["brief_parse_stage"] == "raw_json_ok"
    assert brief["brief_llm_domestic_items_count"] == 3
    assert brief["brief_final_domestic_items_count"] == 3
    assert brief["brief_llm_overseas_items_count"] == 2
    assert brief["brief_final_overseas_items_count"] == 2
    assert brief["brief_source_ids_requested_count"] == 5
    assert brief["brief_source_ids_resolved_count"] == 5
    assert brief["domestic_top"][0]["sources"][0]["evidence_id"] == "E30"
    assert brief["overseas_top"][1]["sources"][0]["evidence_id"] == "E78"
    assert "无强核心事件" not in str(brief["domestic_top"] + brief["overseas_top"])


def test_brief_generator_repairs_overlong_card_field(monkeypatch):
    window = window_for_date(date(2026, 6, 1), "Asia/Shanghai")
    generator = object.__new__(DeepSeekBriefGenerator)
    calls = {"count": 0}
    raw = {
        "domestic_top": [
            {
                "title": "Meta上线按Token收费的WhatsApp Business AI客服",
                "card_title": "Meta WhatsApp AI客服",
                "why": "完整解释保留给 brief。",
                "card_why": "这条卡片短句故意写得非常非常非常非常非常非常非常非常长，超过六十字限制，并且继续补充很多无关解释直到超过限制，还要再补充一句。",
                "priority": "P1",
                "source_ids": [],
            }
        ],
        "overseas_top": [],
    }

    def fake_call(prompt):
        calls["count"] += 1
        if calls["count"] == 1:
            return json.dumps(raw, ensure_ascii=False)
        return '{"value":"WhatsApp按Token收费，验证AI客服商业化路径。"}'

    monkeypatch.setattr(generator, "_call", fake_call)

    brief = generator.generate(window, "# report", _audit(), evidence=[])

    assert calls["count"] == 2
    assert brief["overseas_top"][0]["card_why"] == "WhatsApp按Token收费，验证AI客服商业化路径。"
    assert brief["brief_card_field_repair_attempted"] is True
    assert brief["brief_card_field_repair_succeeded_count"] == 1
    assert brief["brief_card_field_fallback_used_count"] == 0


def test_brief_generator_fallbacks_after_three_overlong_card_repairs(monkeypatch):
    window = window_for_date(date(2026, 6, 1), "Asia/Shanghai")
    generator = object.__new__(DeepSeekBriefGenerator)
    calls = {"count": 0}
    raw = {
        "domestic_top": [
            {
                "title": "Meta上线按Token收费的WhatsApp Business AI客服",
                "card_title": "Meta WhatsApp AI客服",
                "why": "完整解释保留给 brief。",
                "card_why": "这条卡片短句故意写得非常非常非常非常非常非常非常非常长，超过六十字限制，并且继续补充很多无关解释直到超过限制，还要再补充一句。",
                "priority": "P1",
                "source_ids": [],
            }
        ],
        "overseas_top": [],
    }

    def fake_call(prompt):
        calls["count"] += 1
        if calls["count"] == 1:
            return json.dumps(raw, ensure_ascii=False)
        return '{"value":"仍然写得非常非常非常非常非常非常非常非常非常非常非常非常非常长，继续超过限制，并且还要补充更多不必要解释直到超过六十字，仍然超长。"}'

    monkeypatch.setattr(generator, "_call", fake_call)

    brief = generator.generate(window, "# report", _audit(), evidence=[])

    assert calls["count"] == 4
    assert brief["overseas_top"][0]["card_why"].startswith("这条卡片短句故意写得非常")
    assert len(brief["overseas_top"][0]["card_why"]) <= 60
    assert "LLM返回" not in brief["overseas_top"][0]["card_why"]
    assert brief["brief_card_field_repair_failed_count"] == 1
    assert brief["brief_card_field_fallback_used_count"] == 1
    assert brief["brief_card_field_fallback_reason"] == "deterministic_truncate_after_llm_over_limit"


def test_normalize_brief_trims_incomplete_ascii_tail_in_bullets():
    window = window_for_date(date(2026, 6, 1), "Asia/Shanghai")
    raw = {
        "domestic_top": [],
        "overseas_top": [],
        "core_judgments": ["中" * 498 + "AgentPerf继续提升"],
        "watch_signals": [],
    }

    brief = normalize_brief(raw, window, _audit(), evidence=[])

    assert brief["core_judgments"] == ["中" * 498 + "…"]
    assert not brief["core_judgments"][0].endswith("Ag…")


def test_brief_generator_uses_section_level_generation(monkeypatch):
    window = window_for_date(date(2026, 6, 1), "Asia/Shanghai")
    generator = object.__new__(DeepSeekBriefGenerator)
    generator.settings = Settings()
    calls = []

    def fake_call(prompt):
        calls.append(prompt)
        if "domestic_top 字段" in prompt:
            return json.dumps(
                {
                    "domestic_top": [
                        {
                            "title": "国内事件",
                            "card_title": "国内事件",
                            "why": "完整解释",
                            "card_why": "卡片短句",
                            "priority": "P1",
                            "source_ids": [],
                        }
                    ]
                },
                ensure_ascii=False,
            )
        if "overseas_top 字段" in prompt:
            return json.dumps(
                {
                    "overseas_top": [
                        {
                            "title": "海外事件",
                            "card_title": "海外事件",
                            "why": "完整解释",
                            "card_why": "卡片短句",
                            "priority": "P2",
                            "source_ids": [],
                        }
                    ]
                },
                ensure_ascii=False,
            )
        return json.dumps(
            {
                "core_judgments": [{"full": "完整判断", "card": "判断短句"}],
                "watch_signals": [{"full": "完整观察", "card": "观察短句"}],
            },
            ensure_ascii=False,
        )

    monkeypatch.setattr(generator, "_call", fake_call)

    brief = generator.generate(window, "# report", _audit(), evidence=[])

    assert len(calls) == 3
    assert brief["brief_parse_stage"] == "sectioned_json_ok"
    assert brief["brief_section_generation_used"] is True
    assert brief["brief_section_generation_attempts_count"] == 3
    assert brief["domestic_top"][0]["title"] == "国内事件"
    assert brief["overseas_top"][0]["title"] == "海外事件"
    assert brief["core_judgments_card"] == ["国内事件：详见完整日报。"]
    assert brief["brief_core_judgments_dropped_non_top_count"] == 1


def test_brief_generator_retries_failed_section(monkeypatch):
    window = window_for_date(date(2026, 6, 1), "Asia/Shanghai")
    generator = object.__new__(DeepSeekBriefGenerator)
    generator.settings = Settings(brief_section_repair_max_attempts=3)
    domestic_calls = {"count": 0}

    def fake_call(prompt):
        if "domestic_top 字段" in prompt:
            domestic_calls["count"] += 1
            if domestic_calls["count"] == 1:
                return '{"domestic_top":[{"title":"未闭合"'
            return '{"domestic_top":[{"title":"国内事件","card_title":"国内事件","why":"完整解释","card_why":"卡片短句","priority":"P1","source_ids":[]}]}'
        if "overseas_top 字段" in prompt:
            return '{"overseas_top":[]}'
        return '{"core_judgments":[],"watch_signals":[]}'

    monkeypatch.setattr(generator, "_call", fake_call)

    brief = generator.generate(window, "# report", _audit(), evidence=[])

    assert domestic_calls["count"] == 2
    assert brief["domestic_top"][0]["title"] == "国内事件"
    assert brief["brief_section_generation_attempts_count"] == 4


def test_brief_generator_repairs_schema_missing_top_lists(monkeypatch):
    window = window_for_date(date(2026, 6, 1), "Asia/Shanghai")
    generator = object.__new__(DeepSeekBriefGenerator)
    calls = {"count": 0}

    def fake_call(prompt):
        calls["count"] += 1
        if calls["count"] == 1:
            return '{"title":"不是完整 brief"}'
        return '{"domestic_top":[{"title":"DeepSeek降价","why":"价格下降","priority":"P1","source_ids":[]}],"overseas_top":[]}'

    monkeypatch.setattr(generator, "_call", fake_call)

    brief = generator.generate(window, "# report", _audit(), evidence=[])

    assert calls["count"] == 2
    assert brief["brief_generation_status"] == "repaired"
    assert brief["brief_parse_stage"] == "repaired"
    assert "missing domestic_top/overseas_top" in brief["brief_json_parse_error"]
    assert brief["brief_final_domestic_items_count"] == 1


def test_brief_generator_marks_empty_repair_payload_and_uses_report_fallback(monkeypatch):
    window = window_for_date(date(2026, 6, 1), "Asia/Shanghai")
    generator = object.__new__(DeepSeekBriefGenerator)
    calls = {"count": 0}
    report = _report_with_core_events(domestic_count=6, overseas_count=6)

    def fake_call(prompt):
        calls["count"] += 1
        if calls["count"] == 1:
            return "不是 JSON"
        return '{"domestic_top":[],"overseas_top":[],"core_judgments":[],"watch_signals":[]}'

    monkeypatch.setattr(generator, "_call", fake_call)

    brief = generator.generate(window, report, _audit(), evidence=[])

    assert calls["count"] == 2
    assert brief["brief_generation_status"] == "repaired"
    assert brief["brief_repair_succeeded"] is False
    assert brief["brief_repair_empty_payload"] is True
    assert brief["brief_final_domestic_items_count"] == 6
    assert brief["brief_final_overseas_items_count"] == 4
    assert brief["core_judgments"] != ["核心判断来自完整报告"]
    assert any("国内事件" in item for item in brief["core_judgments"])
    assert brief["watch_signals"] == ["观察信号来自完整报告"]
    assert all("|" not in item["why"] for item in brief["domestic_top"] + brief["overseas_top"])


def test_brief_generator_does_not_keep_ok_when_normalization_drops_items(monkeypatch):
    window = window_for_date(date(2026, 6, 1), "Asia/Shanghai")
    generator = object.__new__(DeepSeekBriefGenerator)
    raw = '{"domestic_top":[{"title":"DeepSeek降价","why":"价格下降","priority":"P1","source_ids":[]}],"overseas_top":[]}'
    calls = {"count": 0}
    original_normalize = brief_module.normalize_brief

    def fake_call(prompt):
        calls["count"] += 1
        return raw

    def broken_normalize(*args, **kwargs):
        brief = original_normalize(*args, **kwargs)
        if kwargs.get("generation_status") == "ok":
            brief["domestic_top"] = []
            brief["brief_final_domestic_items_count"] = 0
            brief["brief_normalization_error"] = "normalization dropped domestic_top items"
            brief["brief_error_summary"] = "normalization dropped domestic_top items"
        return brief

    monkeypatch.setattr(generator, "_call", fake_call)
    monkeypatch.setattr(brief_module, "normalize_brief", broken_normalize)

    brief = generator.generate(window, "# report", _audit(), evidence=[])

    assert calls["count"] == 2
    assert brief["brief_generation_status"] == "repaired"
    assert brief["brief_final_domestic_items_count"] == 1


def test_brief_generator_parses_code_fence_json_with_source_ids(monkeypatch):
    window = window_for_date(date(2026, 6, 1), "Asia/Shanghai")
    generator = object.__new__(DeepSeekBriefGenerator)

    monkeypatch.setattr(
        generator,
        "_call",
        lambda prompt: '```json\n{"domestic_top":[{"title":"OpenAI发布新模型","why":"影响开发者","priority":"P1","source_ids":["E1"]}],}\n```',
    )

    brief = generator.generate(
        window,
        "来源：https://openai.com/news/model",
        _audit(),
        doc_url="https://example.feishu.cn/docx/a",
        evidence=[EvidenceItem(title="OpenAI发布新模型", url="https://openai.com/news/model", content="影响开发者", source="OpenAI")],
    )

    assert brief["brief_generation_status"] == "ok"
    assert brief["doc_url"] == "https://example.feishu.cn/docx/a"
    assert brief["overseas_top"][0]["sources"][0]["evidence_id"] == "E1"
