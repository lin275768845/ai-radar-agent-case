from __future__ import annotations

import json
from datetime import date

from ai_radar_agent.event_history import (
    append_event_history,
    apply_final_top_llm_decisions,
    dedupe_final_top_events,
    EventHistoryMatchAudit,
    FinalTopDedupeAudit,
    HistoryMatchResult,
    load_recent_event_history,
    mark_history_matches,
    match_recent_history,
    detect_final_top_new_signal,
    select_history_context_events,
)
from ai_radar_agent.models import EvidenceItem


def _brief():
    return {
        "domestic_top": [
            {
                "title": "扣子Coze 3.0发布",
                "priority": "P1",
                "card_why": "扣子升级多人多Agent协作。",
                "sources": [{"label": "腾讯网", "url": "https://example.com/coze"}],
            },
            {"title": "今日无强核心事件，不强行凑数。", "priority": "观察"},
        ],
        "overseas_top": [
            {
                "title": "OpenAI Codex插件上线",
                "priority": "P2",
                "why": "Codex扩展到白领工具。",
                "sources": [{"label": "OpenAI", "url": "https://openai.com/codex"}],
            }
        ],
        "watch_signals": [{"title": "不应写入"}],
    }


def test_append_event_history_writes_domestic_and_overseas_only(tmp_path):
    path = tmp_path / "state" / "event_history.jsonl"
    append_event_history(path, date(2026, 6, 3), _brief(), "doc-url")

    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert [row["region"] for row in rows] == ["domestic", "overseas"]
    assert "watch_signals" not in path.read_text(encoding="utf-8")
    assert all("今日无强核心事件" not in row["title"] for row in rows)
    assert rows[0]["doc_url"] == "doc-url"


def test_append_event_history_does_not_duplicate_same_day_event(tmp_path):
    path = tmp_path / "state" / "event_history.jsonl"
    append_event_history(path, "2026-06-03", _brief(), "doc-url")
    append_event_history(path, "2026-06-03", _brief(), "doc-url")

    assert len(path.read_text(encoding="utf-8").splitlines()) == 2


def test_append_event_history_skips_dash_placeholder(tmp_path):
    path = tmp_path / "state" / "event_history.jsonl"
    append_event_history(
        path,
        "2026-06-03",
        {"domestic_top": [{"title": "—", "why": "详见完整日报。", "priority": "观察"}], "overseas_top": []},
        "doc-url",
    )

    assert not path.exists()


def test_append_event_history_skips_region_no_core_placeholders(tmp_path):
    path = tmp_path / "state" / "event_history.jsonl"
    append_event_history(
        path,
        "2026-06-03",
        {
            "domestic_top": [{"title": "今日国内候选池无任何进入核心的事件。", "card_title": "当日无符合标准的国内核心事件", "priority": "观察"}],
            "overseas_top": [{"title": "今日海外无核心事件", "card_title": "今日无海外核心事件", "priority": "观察"}],
        },
        "doc-url",
    )

    assert not path.exists()


def test_append_event_history_skips_report_section_headings(tmp_path):
    path = tmp_path / "state" / "event_history.jsonl"
    append_event_history(
        path,
        "2026-06-03",
        {"domestic_top": [{"title": "二、核心解读", "priority": "P1"}], "overseas_top": []},
        "doc-url",
    )

    assert not path.exists()


def test_load_recent_event_history_only_loads_prior_lookback_days(tmp_path):
    path = tmp_path / "event_history.jsonl"
    for day, title in (("2026-05-30", "太旧"), ("2026-06-01", "一天内"), ("2026-06-03", "昨天"), ("2026-06-04", "已跑过的目标日")):
        append_event_history(path, day, {"domestic_top": [{"title": title}], "overseas_top": []}, "doc")

    events = load_recent_event_history(path, date(2026, 6, 4), 3)

    assert [event.title for event in events] == ["一天内", "昨天"]


def test_final_top_dedupe_ignores_same_target_date_history(tmp_path):
    path = tmp_path / "event_history.jsonl"
    append_event_history(path, "2026-06-04", {"domestic_top": [{"title": "腾讯云TokenHub日Token消耗量突破5万亿", "priority": "P2"}], "overseas_top": []}, "")
    history = load_recent_event_history(path, date(2026, 6, 4), 5)
    brief = {
        "domestic_top": [{"title": "腾讯云TokenHub日Token消耗量突破5万亿", "priority": "P2"}],
        "overseas_top": [],
    }

    deduped, audit = dedupe_final_top_events(brief, history, target_date="2026-06-04", lookback_days=5)

    assert history == []
    assert [item["title"] for item in deduped["domestic_top"]] == ["腾讯云TokenHub日Token消耗量突破5万亿"]
    assert audit.dropped_count == 0


def test_select_history_context_events_prefers_recent_and_caps(tmp_path):
    path = tmp_path / "event_history.jsonl"
    for index in range(60):
        day = 1 + index // 12
        priority = "P1" if index % 3 == 0 else "P2"
        append_event_history(
            path,
            f"2026-06-{day:02d}",
            {"domestic_top": [{"title": f"事件{index}", "priority": priority}], "overseas_top": []},
            "doc",
        )
    history = load_recent_event_history(path, date(2026, 6, 6), 5)

    selected = select_history_context_events(history, EventHistoryMatchAudit(date="2026-06-06", lookback_days=5))

    assert len(selected) == 30
    assert selected[0].date == "2026-06-05"
    assert selected[0].priority == "P1"
    assert all(event.date in {"2026-06-03", "2026-06-04", "2026-06-05"} for event in selected[:30])


def test_select_history_context_events_puts_matched_event_first(tmp_path):
    path = tmp_path / "event_history.jsonl"
    append_event_history(path, "2026-06-01", {"domestic_top": [{"title": "较旧但命中的事件", "priority": "P2"}], "overseas_top": []}, "doc")
    append_event_history(path, "2026-06-05", {"domestic_top": [{"title": "最新事件", "priority": "P1"}], "overseas_top": []}, "doc")
    history = load_recent_event_history(path, date(2026, 6, 6), 5)
    matched = next(event for event in history if event.title == "较旧但命中的事件")
    audit = EventHistoryMatchAudit(
        date="2026-06-06",
        lookback_days=5,
        matches=[
            HistoryMatchResult(
                matched=True,
                matched_event_id=matched.event_id,
                matched_title=matched.title,
                matched_date=matched.date,
            )
        ],
    )

    selected = select_history_context_events(history, audit)

    assert selected[0].title == "较旧但命中的事件"
    assert selected[1].title == "最新事件"


def test_similar_coze_titles_match_recent_history(tmp_path):
    path = tmp_path / "event_history.jsonl"
    append_event_history(path, "2026-06-02", {"domestic_top": [{"title": "扣子Coze 3.0发布"}]}, "")
    history = load_recent_event_history(path, date(2026, 6, 4), 3)

    result = match_recent_history(EvidenceItem(title="扣子Coze 3.0上线", url="", content="媒体转载"), history)

    assert result.matched is True
    assert result.similarity >= 0.55
    assert result.is_old_repeated is True


def test_similar_tencent_deepseek_titles_match_recent_history(tmp_path):
    path = tmp_path / "event_history.jsonl"
    append_event_history(path, "2026-06-02", {"domestic_top": [{"title": "腾讯云下调DeepSeek-V4价格"}]}, "")
    history = load_recent_event_history(path, date(2026, 6, 4), 3)

    result = match_recent_history(
        EvidenceItem(title="腾讯云大幅下调DeepSeek-V4 API价格", url="", content="媒体转载"),
        history,
    )

    assert result.matched is True
    assert result.is_old_repeated is True


def test_old_event_without_new_signal_is_marked_drop_core(tmp_path):
    path = tmp_path / "event_history.jsonl"
    append_event_history(path, "2026-06-02", {"domestic_top": [{"title": "腾讯云下调DeepSeek-V4价格"}]}, "")
    history = load_recent_event_history(path, date(2026, 6, 4), 3)
    evidence = [EvidenceItem(title="腾讯云下调DeepSeek-V4价格", url="", content="回顾此前消息")]

    audit = mark_history_matches(evidence, history, target_date="2026-06-04", lookback_days=3)

    assert audit.old_repeated_count == 1
    assert audit.dropped_from_core_count == 1
    assert evidence[0].not_core_eligible is True
    assert evidence[0].date_status == "old_repeated"
    assert audit.matches[0].action == "drop_core"


def test_old_event_with_new_signal_is_allowed(tmp_path):
    path = tmp_path / "event_history.jsonl"
    append_event_history(path, "2026-06-02", {"domestic_top": [{"title": "腾讯云下调DeepSeek-V4价格"}]}, "")
    history = load_recent_event_history(path, date(2026, 6, 4), 3)
    evidence = [
        EvidenceItem(
            title="腾讯云下调DeepSeek-V4价格",
            url="",
            content="今日官方发布新价格，API 调用量新增。",
        )
    ]

    audit = mark_history_matches(evidence, history, target_date="2026-06-04", lookback_days=3)

    assert audit.new_signal_repeat_count == 1
    assert evidence[0].not_core_eligible is False
    assert evidence[0].date_status == "new_signal"
    assert audit.matches[0].action == "allow_new_signal"


def test_old_event_with_new_signal_keeps_weak_source_not_core_eligible(tmp_path):
    path = tmp_path / "event_history.jsonl"
    append_event_history(path, "2026-06-02", {"overseas_top": [{"title": "Mastercard推出AI支付协议"}]}, "")
    history = load_recent_event_history(path, date(2026, 6, 4), 3)
    evidence = [
        EvidenceItem(
            title="Mastercard推出AI支付协议",
            url="https://news.qq.com/rain/a/1",
            content="今日支付 API 正式上线，支持AI代理间小额支付。",
            source="腾讯网",
            source_tier="S4",
            source_fit="medium",
        )
    ]

    audit = mark_history_matches(evidence, history, target_date="2026-06-04", lookback_days=3)

    assert audit.new_signal_repeat_count == 1
    assert evidence[0].date_status == "new_signal"
    assert evidence[0].not_core_eligible is True
    assert "source tier not core eligible" in evidence[0].date_reason
    assert audit.matches[0].action == "allow_new_signal"


def test_final_top_dedupe_drops_repeated_top_without_new_signal(tmp_path):
    path = tmp_path / "event_history.jsonl"
    append_event_history(path, "2026-06-02", {"domestic_top": [{"title": "腾讯云下调DeepSeek-V4价格"}]}, "")
    history = load_recent_event_history(path, date(2026, 6, 4), 5)
    brief = {
        "domestic_top": [
            {
                "title": "腾讯云大幅下调DeepSeek-V4 API价格",
                "card_why": "腾讯云大幅下调DeepSeek-V4系列模型调用价。",
                "priority": "P2",
            }
        ],
        "overseas_top": [{"title": "OpenAI发布新工具", "priority": "P1"}],
        "core_judgments": ["腾讯云价格战继续影响模型生态。"],
        "watch_signals": ["观察腾讯云价格战后续扩散。"],
    }

    deduped, audit = dedupe_final_top_events(brief, history, target_date="2026-06-04", lookback_days=5)

    assert deduped["domestic_top"] == []
    assert len(deduped["overseas_top"]) == 1
    assert deduped["core_judgments"] == ["OpenAI发布新工具进入最终 Top。"]
    assert deduped["watch_signals"] == []
    assert audit.cleared_core_judgments_count == 1
    assert audit.cleared_watch_signals_count == 1
    assert audit.dropped_count == 1
    assert audit.matches_count == 1
    assert audit.dropped_titles == ["腾讯云大幅下调DeepSeek-V4 API价格"]
    assert deduped["brief_final_domestic_items_count"] == 0
    assert deduped["brief_items_count"] == 1


def test_final_top_dedupe_clears_bullets_when_all_top_dropped(tmp_path):
    path = tmp_path / "event_history.jsonl"
    append_event_history(path, "2026-06-02", {"domestic_top": [{"title": "腾讯云下调DeepSeek-V4价格"}]}, "")
    history = load_recent_event_history(path, date(2026, 6, 4), 5)
    brief = {
        "domestic_top": [
            {
                "title": "腾讯云大幅下调DeepSeek-V4 API价格",
                "card_why": "腾讯云大幅下调DeepSeek-V4系列模型调用价。",
                "priority": "P2",
            }
        ],
        "overseas_top": [],
        "core_judgments": ["腾讯云价格战继续影响模型生态。"],
        "core_judgments_card": ["腾讯云价格战继续影响模型生态。"],
        "watch_signals": ["观察腾讯云价格战后续扩散。"],
        "watch_signals_card": ["观察腾讯云价格战后续扩散。"],
        "brief_core_judgments_count": 1,
        "brief_watch_signals_count": 1,
    }

    deduped, audit = dedupe_final_top_events(brief, history, target_date="2026-06-04", lookback_days=5)

    assert deduped["domestic_top"] == []
    assert deduped["overseas_top"] == []
    assert deduped["core_judgments"] == []
    assert deduped["core_judgments_card"] == []
    assert deduped["watch_signals"] == []
    assert deduped["watch_signals_card"] == []
    assert deduped["brief_core_judgments_count"] == 0
    assert deduped["brief_watch_signals_count"] == 0
    assert audit.cleared_core_judgments_count == 1
    assert audit.cleared_watch_signals_count == 1
    assert "cleared_top_dependent_bullets_after_final_top_dedupe" in audit.warnings


def test_final_top_dedupe_only_removes_bullets_for_dropped_top(tmp_path):
    path = tmp_path / "event_history.jsonl"
    append_event_history(path, "2026-06-02", {"domestic_top": [{"title": "豆包5月MAU环比下降1.81%，约607万用户流失"}]}, "")
    history = load_recent_event_history(path, date(2026, 6, 4), 5)
    brief = {
        "domestic_top": [
            {
                "title": "豆包5月MAU首次下滑",
                "card_why": "豆包5月MAU首次下滑，约607万用户流失。",
                "priority": "P2",
            },
            {
                "title": "DeepSeek登顶美国企业付费榜单",
                "card_why": "DeepSeek在美国企业付费榜单登顶。",
                "priority": "P2",
            },
            {
                "title": "阿里AI电商618全场景落地",
                "card_why": "阿里AI电商在618打通购物链路。",
                "priority": "P2",
            },
        ],
        "overseas_top": [],
        "core_judgments": [
            "豆包5月MAU首次下滑，说明C端AI助手用户对涨价敏感。",
            "DeepSeek登顶美国企业付费榜，中国模型海外采用度突破。",
            "阿里AI电商成618主战场，AI从对话走向交易入口。",
        ],
        "core_judgments_card": [
            "豆包MAU首次下滑，C端AI助手付费化遇冷。",
            "DeepSeek登顶美国企业付费榜，中国模型海外采用度突破。",
            "AI电商成618主战场，阿里AI从对话走向交易入口。",
        ],
        "watch_signals": [
            "DeepSeek永久降价，小米跟降，需观察是否加速模型价格战。",
            "阿里AI电商618落地后，需观察真实转化率。",
        ],
        "watch_signals_card": [
            "DeepSeek永久降价，需观察模型价格战。",
            "阿里AI电商618落地后，需观察真实转化率。",
        ],
    }

    deduped, audit = dedupe_final_top_events(brief, history, target_date="2026-06-04", lookback_days=5)

    assert [item["title"] for item in deduped["domestic_top"]] == [
        "DeepSeek登顶美国企业付费榜单",
        "阿里AI电商618全场景落地",
    ]
    assert deduped["core_judgments"] == [
        "DeepSeek登顶美国企业付费榜，中国模型海外采用度突破。",
        "阿里AI电商成618主战场，AI从对话走向交易入口。",
    ]
    assert deduped["core_judgments_card"] == [
        "DeepSeek登顶美国企业付费榜，中国模型海外采用度突破。",
        "AI电商成618主战场，阿里AI从对话走向交易入口。",
    ]
    assert deduped["watch_signals"] == [
        "DeepSeek永久降价，小米跟降，需观察是否加速模型价格战。",
        "阿里AI电商618落地后，需观察真实转化率。",
    ]
    assert deduped["watch_signals_card"] == [
        "DeepSeek永久降价，需观察模型价格战。",
        "阿里AI电商618落地后，需观察真实转化率。",
    ]
    assert audit.dropped_count == 1
    assert audit.cleared_core_judgments_count == 1
    assert audit.cleared_watch_signals_count == 0


def test_final_top_dedupe_does_not_drop_same_entity_different_signal(tmp_path):
    path = tmp_path / "event_history.jsonl"
    append_event_history(path, "2026-06-09", {"domestic_top": [{"title": "DeepSeek周调用量全球第一"}]}, "")
    history = load_recent_event_history(path, date(2026, 6, 11), 5)
    brief = {
        "domestic_top": [
            {
                "title": "DeepSeek主动退款维护API经济",
                "card_why": "DeepSeek API缓存计费系统故障后主动退款。",
                "priority": "P2",
            },
            {
                "title": "编程和办公：国内大模型的认知盲区",
                "card_why": "国内模型行业忽视编程和办公商业化赛道。",
                "priority": "P2",
            },
        ],
        "overseas_top": [],
        "core_judgments": [
            "国内模型商业化仍应回到高频工作流，而不是只比较模型参数。",
            "编程和办公是最直接的付费转化入口。",
        ],
        "core_judgments_card": [
            "商业化应回到高频工作流。",
            "编程和办公是付费转化入口。",
        ],
        "watch_signals": [
            "观察模型公司是否披露更清晰的API计费和补偿机制。",
            "观察办公与编程场景的企业付费数据。",
        ],
        "watch_signals_card": [
            "观察API计费和补偿机制。",
            "观察办公与编程企业付费数据。",
        ],
    }

    deduped, audit = dedupe_final_top_events(brief, history, target_date="2026-06-11", lookback_days=5)

    assert [item["title"] for item in deduped["domestic_top"]] == [
        "DeepSeek主动退款维护API经济",
        "编程和办公：国内大模型的认知盲区",
    ]
    assert deduped["core_judgments"] == brief["core_judgments"]
    assert deduped["watch_signals"] == brief["watch_signals"]
    assert audit.dropped_count == 0


def test_semantic_history_match_does_not_merge_deepseek_usage_and_billing_incident(tmp_path):
    path = tmp_path / "event_history.jsonl"
    append_event_history(
        path,
        "2026-06-09",
        {
            "domestic_top": [
                {
                    "title": "DeepSeek周调用量全球第一",
                    "card_why": "DeepSeek Token调用量登顶，体现模型采用度提升。",
                }
            ],
            "overseas_top": [],
        },
        "",
    )
    history = load_recent_event_history(path, date(2026, 6, 11), 5)

    result = match_recent_history(
        EvidenceItem(
            title="DeepSeek API 缓存计费系统出故障后主动向用户退款",
            url="",
            content="DeepSeek称API缓存计费系统故障，已向受影响用户发放退款和赠金。",
        ),
        history,
        strict_new_signal=True,
    )

    assert result.matched is False


def test_final_top_dedupe_allows_repeated_top_with_strong_new_signal(tmp_path):
    path = tmp_path / "event_history.jsonl"
    append_event_history(path, "2026-06-02", {"domestic_top": [{"title": "扣子Coze 3.0发布"}]}, "")
    history = load_recent_event_history(path, date(2026, 6, 4), 5)
    brief = {
        "domestic_top": [
            {
                "title": "扣子Coze 3.0上线",
                "card_why": "今日官方正式上线企业版，并新增付费客户数据。",
                "priority": "P1",
            }
        ],
        "overseas_top": [],
    }

    deduped, audit = dedupe_final_top_events(brief, history, target_date="2026-06-04", lookback_days=5)

    assert len(deduped["domestic_top"]) == 1
    assert audit.dropped_count == 0
    assert audit.new_signal_count == 1


def test_final_top_dedupe_caps_final_p2_items_even_without_history():
    brief = {
        "domestic_top": [
            {"title": "国内P1", "priority": "P1"},
            {"title": "国内P2一", "priority": "P2"},
            {"title": "国内P2二", "priority": "P2"},
            {"title": "国内P2三", "priority": "P2"},
            {"title": "国内观察", "priority": "观察"},
        ],
        "overseas_top": [
            {"title": "海外P2一", "priority": "P2"},
            {"title": "海外P2二", "priority": "P2"},
            {"title": "海外P2三", "priority": "P2"},
        ],
    }

    deduped, audit = dedupe_final_top_events(brief, [], target_date="2026-06-04", lookback_days=5)

    assert [item["title"] for item in deduped["domestic_top"]] == ["国内P1", "国内P2一", "国内P2二", "国内观察"]
    assert [item["title"] for item in deduped["overseas_top"]] == ["海外P2一", "海外P2二"]
    assert audit.p2_capped_count == 2
    assert audit.p2_capped_titles == ["国内P2三", "海外P2三"]


def test_apply_final_top_llm_decisions_drops_high_confidence_duplicate():
    brief = {
        "domestic_top": [{"title": "DeepSeek登顶美企软件趋势榜", "priority": "P1"}],
        "overseas_top": [{"title": "DeepSeek登顶美企软件趋势榜", "priority": "P1"}],
        "core_judgments": ["DeepSeek企业采用率继续提升。"],
        "watch_signals": [],
    }
    audit = FinalTopDedupeAudit(date="2026-06-05", lookback_days=5)

    deduped, audit = apply_final_top_llm_decisions(
        brief,
        [
            {
                "id": "overseas_1",
                "action": "drop",
                "duplicate_of": "domestic_1",
                "confidence": "high",
                "new_signal": False,
            }
        ],
        audit,
    )

    assert [item["title"] for item in deduped["domestic_top"]] == ["DeepSeek登顶美企软件趋势榜"]
    assert deduped["overseas_top"] == []
    assert audit.llm_audit_dropped_count == 1
    assert audit.dropped_count == 1
    assert audit.llm_audit_dropped_titles == ["DeepSeek登顶美企软件趋势榜"]


def test_apply_final_top_llm_decisions_rechecks_core_judgments_against_remaining_top():
    brief = {
        "domestic_top": [],
        "overseas_top": [
            {"title": "AI订阅制Token补贴模式遭结构性拷问", "priority": "P1"},
            {"title": "诺奖得主John Jumper从DeepMind出走Anthropic", "priority": "P1"},
            {"title": "iOS 27披露系统级AI能力，重塑L4入口", "priority": "P2"},
        ],
        "core_judgments": [
            "AI订阅高额补贴难持续，Token成本倒挂拷问商业模式，或加速行业转型。",
            "诺贝尔奖得主John Jumper加入Anthropic，顶级人才竞争升级。",
            "苹果iOS 27将AI系统化嵌入，重新定义移动端交互入口。",
        ],
        "core_judgments_card": [
            "AI订阅补贴倒挂，商业模式承压。",
            "Jumper跳槽Anthropic，人才竞争升级。",
            "iOS 27系统级AI重塑移动入口。",
        ],
        "watch_signals": [],
    }
    audit = FinalTopDedupeAudit(date="2026-06-21", lookback_days=5)

    deduped, audit = apply_final_top_llm_decisions(
        brief,
        [
            {
                "id": "overseas_1",
                "action": "drop",
                "duplicate_of": "history",
                "confidence": "high",
                "new_signal": False,
            }
        ],
        audit,
    )

    assert [item["title"] for item in deduped["overseas_top"]] == [
        "诺奖得主John Jumper从DeepMind出走Anthropic",
        "iOS 27披露系统级AI能力，重塑L4入口",
    ]
    assert not any("订阅" in item or "Token" in item for item in deduped["core_judgments"])
    assert not any("订阅" in item or "Token" in item for item in deduped["core_judgments_card"])
    assert audit.cleared_core_judgments_count == 1


def test_apply_final_top_llm_decisions_fills_core_judgment_when_filter_clears_all():
    brief = {
        "domestic_top": [],
        "overseas_top": [
            {"title": "AI订阅制Token补贴模式遭结构性拷问", "priority": "P1"},
            {
                "title": "苹果iOS 27推出系统级AI功能",
                "card_title": "iOS 27内置系统级AI",
                "why": "苹果在操作系统层面深度集成AI，改变移动端AI分发与Agent入口格局。",
                "card_why": "iOS 27系统级AI重塑移动入口。",
                "priority": "P1",
            },
        ],
        "core_judgments": [
            "AI订阅高额补贴难持续，Token成本倒挂拷问商业模式，或加速行业转型。",
        ],
        "core_judgments_card": [
            "AI订阅补贴倒挂，商业模式承压。",
        ],
        "watch_signals": [],
    }
    audit = FinalTopDedupeAudit(date="2026-06-21", lookback_days=5)

    deduped, audit = apply_final_top_llm_decisions(
        brief,
        [
            {
                "id": "overseas_1",
                "action": "drop",
                "duplicate_of": "history",
                "confidence": "high",
                "new_signal": False,
            }
        ],
        audit,
    )

    assert [item["title"] for item in deduped["overseas_top"]] == ["苹果iOS 27推出系统级AI功能"]
    assert deduped["core_judgments"] == [
        "苹果iOS 27推出系统级AI功能：苹果在操作系统层面深度集成AI，改变移动端AI分发与Agent入口格局。"
    ]
    assert deduped["core_judgments_card"] == ["苹果iOS 27推出系统级AI功能：iOS 27系统级AI重塑移动入口。"]
    assert audit.cleared_core_judgments_count == 1


def test_apply_final_top_llm_decisions_rejects_uncertain_or_new_signal_drop():
    brief = {
        "domestic_top": [{"title": "DeepSeek登顶美企软件趋势榜", "priority": "P1"}],
        "overseas_top": [{"title": "Anthropic年收入创新高", "priority": "P1"}],
    }
    audit = FinalTopDedupeAudit(date="2026-06-05", lookback_days=5)

    deduped, audit = apply_final_top_llm_decisions(
        brief,
        [
            {
                "id": "domestic_1",
                "action": "drop",
                "duplicate_of": "2026-06-04 DeepSeek登顶美企付费榜首",
                "confidence": "medium",
                "new_signal": False,
            },
            {
                "id": "overseas_1",
                "action": "drop",
                "duplicate_of": "2026-06-04 Anthropic IPO",
                "confidence": "high",
                "new_signal": True,
            },
        ],
        audit,
    )

    assert len(deduped["domestic_top"]) == 1
    assert len(deduped["overseas_top"]) == 1
    assert audit.llm_audit_dropped_count == 0
    assert audit.llm_audit_rejected_count == 2


def test_apply_final_top_llm_decisions_rejects_drop_all():
    brief = {
        "domestic_top": [{"title": "DeepSeek登顶美企软件趋势榜", "priority": "P1"}],
        "overseas_top": [],
    }
    audit = FinalTopDedupeAudit(date="2026-06-05", lookback_days=5)

    deduped, audit = apply_final_top_llm_decisions(
        brief,
        [
            {
                "id": "domestic_1",
                "action": "drop",
                "duplicate_of": "2026-06-04 DeepSeek登顶美企付费榜首",
                "confidence": "high",
                "new_signal": False,
            }
        ],
        audit,
    )

    assert len(deduped["domestic_top"]) == 1
    assert audit.llm_audit_dropped_count == 0
    assert "llm_audit_drop_all_rejected" in audit.warnings


def test_formal_price_wording_alone_is_not_final_top_new_signal():
    assert detect_final_top_new_signal("腾讯云正式下调DeepSeek-V4 API价格") is False


def test_descriptive_new_capability_alone_is_not_final_top_new_signal():
    assert detect_final_top_new_signal("ChatGPT新增Dreaming记忆系统能力") is False


def test_final_top_dedupe_matches_paid_mau_drop_rewrite(tmp_path):
    path = tmp_path / "event_history.jsonl"
    append_event_history(
        path,
        "2026-06-03",
        {
            "domestic_top": [
                {
                    "title": "豆包将推付费版，上月MAU首次下滑",
                    "card_why": "豆包计划推出专业版付费订阅；5月MAU3.3亿环比降1.81%，为增长以来首次下跌。",
                    "priority": "P2",
                }
            ],
            "overseas_top": [],
        },
        "",
    )
    history = load_recent_event_history(path, date(2026, 6, 4), 5)
    brief = {
        "domestic_top": [
            {
                "title": "豆包付费版冲击月活，算力成本压力显现",
                "card_title": "豆包付费版导致MAU首降",
                "card_why": "豆包5月MAU环比下降1.81%，流失约607万用户，高额算力成本推动付费模式转型。",
                "priority": "P2",
            }
        ],
        "overseas_top": [],
    }

    deduped, audit = dedupe_final_top_events(brief, history, target_date="2026-06-04", lookback_days=5)

    assert deduped["domestic_top"] == []
    assert audit.matches_count == 1
    assert audit.dropped_count == 1
    assert audit.matches[0].match_reason == "entity_and_paid_mau_signal"


def test_final_top_dedupe_drops_alphabet_financing_rewrite(tmp_path):
    path = tmp_path / "event_history.jsonl"
    append_event_history(
        path,
        "2026-06-03",
        {"overseas_top": [{"title": "Alphabet 850亿美元融资创纪录", "card_why": "Alphabet筹集850亿美元用于AI基础设施。"}], "domestic_top": []},
        "",
    )
    history = load_recent_event_history(path, date(2026, 6, 4), 5)
    brief = {"domestic_top": [], "overseas_top": [{"title": "Alphabet完成850亿美元AI融资", "card_why": "AI基建融资规模创纪录。"}]}

    deduped, audit = dedupe_final_top_events(brief, history, target_date="2026-06-04", lookback_days=5)

    assert deduped["overseas_top"] == []
    assert audit.dropped_count == 1
    assert audit.matches[0].new_signal_detected is False


def test_final_top_dedupe_drops_dreaming_punctuation_rewrite(tmp_path):
    path = tmp_path / "event_history.jsonl"
    append_event_history(
        path,
        "2026-06-03",
        {"overseas_top": [{"title": "ChatGPT推出“Dreaming”记忆系统", "card_why": "ChatGPT增加长期记忆能力。"}], "domestic_top": []},
        "",
    )
    history = load_recent_event_history(path, date(2026, 6, 4), 5)
    brief = {"domestic_top": [], "overseas_top": [{"title": "ChatGPT推出Dreaming记忆系统", "card_why": "增强记忆体验。"}]}

    deduped, audit = dedupe_final_top_events(brief, history, target_date="2026-06-04", lookback_days=5)

    assert deduped["overseas_top"] == []
    assert audit.dropped_count == 1


def test_final_top_dedupe_drops_google_cloud_gcp_rewrite(tmp_path):
    path = tmp_path / "event_history.jsonl"
    append_event_history(
        path,
        "2026-06-03",
        {
            "overseas_top": [
                {
                    "title": "Lovable与Google Cloud签署多年合同，使用量扩大5倍",
                    "card_why": "Lovable把Google Cloud使用量扩大5倍。",
                }
            ],
            "domestic_top": [],
        },
        "",
    )
    history = load_recent_event_history(path, date(2026, 6, 4), 5)
    brief = {"domestic_top": [], "overseas_top": [{"title": "Lovable与GCP签约5倍扩张", "card_why": "云合同扩张。"}]}

    deduped, audit = dedupe_final_top_events(brief, history, target_date="2026-06-04", lookback_days=5)

    assert deduped["overseas_top"] == []
    assert audit.dropped_count == 1
    assert audit.matches[0].match_reason in {"entity_numeric_semantic_overlap", "numeric_semantic_overlap"}


def test_final_top_dedupe_drops_crowdstrike_q1_arr_rewrite(tmp_path):
    path = tmp_path / "event_history.jsonl"
    append_event_history(
        path,
        "2026-06-03",
        {"overseas_top": [{"title": "CrowdStrike Q1业绩超预期，AI安全需求驱动", "card_why": "Q1 ARR增长。"}], "domestic_top": []},
        "",
    )
    history = load_recent_event_history(path, date(2026, 6, 4), 5)
    brief = {"domestic_top": [], "overseas_top": [{"title": "CrowdStrike Q1 ARR创历史新高", "card_why": "AI安全需求推动ARR增长。"}]}

    deduped, audit = dedupe_final_top_events(brief, history, target_date="2026-06-04", lookback_days=5)

    assert deduped["overseas_top"] == []
    assert audit.dropped_count == 1


def test_semantic_history_match_catches_agent_ecosystem_rewrite(tmp_path):
    path = tmp_path / "event_history.jsonl"
    append_event_history(
        path,
        "2026-06-02",
        {
            "domestic_top": [
                {
                    "title": "千问Agent生态向第三方全面开放",
                    "card_why": "千问APP开放第三方Agent和Skill入驻，品牌可接入服务生态。",
                }
            ],
            "overseas_top": [],
        },
        "",
    )
    history = load_recent_event_history(path, date(2026, 6, 4), 5)

    result = match_recent_history(
        EvidenceItem(
            title="千问向企业Agent全面开放入驻",
            url="",
            content="千问APP允许第三方企业Agent入驻，用户可通过对话完成下单和服务。",
        ),
        history,
    )

    assert result.matched is True
    assert result.is_old_repeated is True
    assert result.match_reason in {"entity_and_semantic_facets", "entity_numeric_semantic_overlap"}


def test_semantic_history_match_catches_ai_payment_metric_rewrite(tmp_path):
    path = tmp_path / "event_history.jsonl"
    append_event_history(
        path,
        "2026-06-02",
        {
            "domestic_top": [
                {
                    "title": "支付宝AI支付累计完成3亿笔",
                    "card_why": "支付宝AI支付通过对话完成下单和支付，验证交易闭环。",
                }
            ],
            "overseas_top": [],
        },
        "",
    )
    history = load_recent_event_history(path, date(2026, 6, 4), 5)

    result = match_recent_history(
        EvidenceItem(
            title="支付宝对话式AI支付交易规模扩大",
            url="",
            content="支付宝AI支付累计交易达到3亿笔，用户可通过智能体完成下单和支付。",
        ),
        history,
    )

    assert result.matched is True
    assert result.is_old_repeated is True
    assert result.match_reason in {"entity_and_semantic_facets", "entity_numeric_semantic_overlap"}


def test_semantic_history_match_does_not_merge_same_entity_different_event(tmp_path):
    path = tmp_path / "event_history.jsonl"
    append_event_history(
        path,
        "2026-06-02",
        {
            "domestic_top": [
                {
                    "title": "豆包推付费版，MAU首次下滑",
                    "card_why": "豆包推出专业版付费订阅，同时月活首次下滑。",
                }
            ],
            "overseas_top": [],
        },
        "",
    )
    history = load_recent_event_history(path, date(2026, 6, 4), 5)

    result = match_recent_history(
        EvidenceItem(
            title="豆包发布视频生成模型能力",
            url="",
            content="豆包新增视频生成模型，用于创作者生成短视频内容。",
        ),
        history,
    )

    assert result.matched is False


def test_semantic_history_match_requires_title_entity_not_content_noise(tmp_path):
    path = tmp_path / "event_history.jsonl"
    append_event_history(
        path,
        "2026-06-02",
        {"domestic_top": [{"title": "OpenAI Codex扩展至所有角色工作流", "card_why": "Codex扩展为通用白领工具。"}], "overseas_top": []},
        "",
    )
    history = load_recent_event_history(path, date(2026, 6, 4), 5)

    result = match_recent_history(
        EvidenceItem(
            title="How Endava is redesigning software delivery around AI agents",
            url="",
            content="文章背景段落提到 OpenAI Codex，但主体是 Endava 的软件交付方法。",
        ),
        history,
    )

    assert result.matched is False


def test_semantic_history_match_requires_title_facet_not_content_noise(tmp_path):
    path = tmp_path / "event_history.jsonl"
    append_event_history(
        path,
        "2026-06-02",
        {"domestic_top": [{"title": "腾讯云大幅下调DeepSeek-V4 API价格", "card_why": "腾讯云下调DeepSeek API调用价格。"}], "overseas_top": []},
        "",
    )
    history = load_recent_event_history(path, date(2026, 6, 4), 5)

    result = match_recent_history(
        EvidenceItem(
            title="中兴携手腾讯推出AI云电脑",
            url="",
            content="文章末尾回顾腾讯云此前下调DeepSeek-V4 API价格，但今日主体是AI云电脑。",
        ),
        history,
    )

    assert result.matched is False
