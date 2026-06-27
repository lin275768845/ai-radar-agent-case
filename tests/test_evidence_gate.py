from __future__ import annotations

import json
from types import SimpleNamespace

from ai_radar_agent import __main__ as main_module
from ai_radar_agent.evidence_gate import (
    DroppedEvidence,
    EvidenceGateAudit,
    event_id_for_title,
    render_dropped_markdown,
    run_evidence_gate,
)
from ai_radar_agent.models import EvidenceItem, RecallAudit
from ai_radar_agent.dates import window_for_date
from datetime import date


def _window():
    return window_for_date(date(2026, 5, 2), "Asia/Shanghai")


def _item(title, url="https://openai.com/news/a", published_at="2026-05-02T08:00:00+08:00", content="AI news", source="OpenAI"):
    return EvidenceItem(title=title, url=url, content=content, source=source, published_at=published_at, provider="bocha")


def test_gate_drops_out_of_window_without_new_signal():
    result = run_evidence_gate([_item("OpenAI旧消息", published_at="2026-05-01T08:00:00+08:00")], _window())
    assert result.filtered == []
    assert result.audit.dropped_out_of_window_count == 1
    assert result.dropped[0].reason == "out_of_window"


def test_gate_marks_review_content_as_old_repeated():
    result = run_evidence_gate([_item("一文看懂 OpenAI 旧发布回顾")], _window())
    assert result.filtered == []
    assert result.audit.dropped_old_repeated_count == 1
    assert result.dropped[0].reason == "old_repeated"


def test_gate_drops_prior_day_action_even_when_article_published_in_window():
    window = window_for_date(date(2026, 6, 11), "Asia/Shanghai")
    item = _item(
        "千问总裁吴嘉:为每个考生提供一位免费专业的 AI 志愿填报专家",
        url="https://www.ithome.com/0/962/797.htm",
        published_at="2026-06-11T11:13:37+08:00",
        content="6 月 10 日，千问 APP 上线国内首个全周期高考志愿填报 Agent，为全国考生免费提供志愿填报服务。",
        source="IT之家",
    )

    result = run_evidence_gate([item], window)

    assert result.filtered == []
    assert result.dropped[0].reason == "old_repeated"
    assert item.event_date == "2026-06-10"
    assert item.date_status == "old_repeated"
    assert "explicit event_date 2026-06-10 before target date" in item.date_reason


def test_gate_drops_event_seen_in_recent_history_without_new_signal(tmp_path):
    history = tmp_path / "event_history.jsonl"
    title = "OpenAI Agent功能"
    url = "https://openai.com/news/agent"
    history.write_text(
        json.dumps(
            {
                "event_id": event_id_for_title(title, url),
                "title": title,
                "first_seen_date": "2026-04-30",
                "last_seen_date": "2026-05-01",
                "source_urls": [url],
                "status": "reported",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    result = run_evidence_gate([_item(title, url=url)], _window(), event_history_path=history)
    assert result.filtered == []
    assert result.audit.event_history_repeated_count == 1
    assert result.dropped[0].reason == "old_repeated"


def test_gate_keeps_history_event_when_new_price_signal_exists(tmp_path):
    history = tmp_path / "event_history.jsonl"
    title = "OpenAI API价格降价"
    url = "https://openai.com/news/pricing"
    history.write_text(
        json.dumps(
            {
                "event_id": event_id_for_title(title, url),
                "title": title,
                "first_seen_date": "2026-04-30",
                "last_seen_date": "2026-05-01",
                "source_urls": [url],
                "status": "reported",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    result = run_evidence_gate([_item(title, url=url, content="今日新增 API 新价格，调用量增长")], _window(), event_history_path=history)
    assert len(result.filtered) == 1
    assert result.filtered[0].date_status == "new_signal"


def test_gate_drops_low_source_fit():
    result = run_evidence_gate(
        [_item("OpenAI发布新模型", url="https://baijiahao.baidu.com/s?id=1", source="bocha")],
        _window(),
    )
    assert result.filtered == []
    assert result.audit.dropped_low_source_fit_count == 1


def test_gate_marks_s4_medium_source_not_core_eligible():
    result = run_evidence_gate(
        [_item("阿里千问高考志愿填报Agent", url="https://www.php.cn/faq/2625347.html", source="php中文网")],
        _window(),
    )

    assert len(result.filtered) == 1
    assert result.filtered[0].source_tier == "S4"
    assert result.filtered[0].source_fit == "medium"
    assert result.filtered[0].not_core_eligible is True


def test_gate_keeps_official_source_and_drops_aggregator_for_same_event():
    official = _item("OpenAI发布新模型", url="https://openai.com/news/model", source="bocha")
    aggregator = _item("OpenAI发布新模型", url="https://baijiahao.baidu.com/s?id=1", source="bocha")
    result = run_evidence_gate([official, aggregator], _window())
    assert [item.url for item in result.filtered] == ["https://openai.com/news/model"]
    assert result.dropped[0].reason == "aggregator"


def test_provider_name_is_not_visible_source_label():
    result = run_evidence_gate([_item("OpenAI发布新模型", source="bocha")], _window())
    assert result.filtered[0].source == "openai.com"


def test_primary_source_enrichment_uses_query_budget():
    calls = []

    def fake_search(query, window, max_results):
        calls.append(query)
        return [_item("OpenAI官方发布", url="https://openai.com/news/official", source="OpenAI")]

    result = run_evidence_gate(
        [_item("OpenAI发布新模型", url="https://techcrunch.com/openai-model", source="TechCrunch")],
        _window(),
        primary_source_enrichment_enabled=True,
        primary_source_search=fake_search,
        primary_source_max_queries=1,
        primary_source_max_results_per_query=3,
    )
    assert len(calls) == 1
    assert result.audit.primary_source_enrichment_attempted is True
    assert result.audit.primary_source_enrichment_added_count == 1
    assert any(item.is_primary_source for item in result.filtered)


def test_primary_source_enrichment_skips_out_of_window_items():
    calls = []

    def fake_search(query, window, max_results):
        calls.append(query)
        return [_item("OpenAI官方发布", url="https://openai.com/news/official", source="OpenAI")]

    result = run_evidence_gate(
        [_item("OpenAI旧消息", published_at="2026-05-01T08:00:00+08:00")],
        _window(),
        primary_source_enrichment_enabled=True,
        primary_source_search=fake_search,
        primary_source_max_queries=1,
    )

    assert calls == []
    assert result.audit.primary_source_enrichment_attempted is True
    assert result.audit.primary_source_enrichment_added_count == 0


def test_primary_source_enrichment_skips_old_repeated_items():
    calls = []

    def fake_search(query, window, max_results):
        calls.append(query)
        return [_item("OpenAI官方发布", url="https://openai.com/news/official", source="OpenAI")]

    result = run_evidence_gate(
        [_item("一文看懂 OpenAI 旧发布回顾")],
        _window(),
        primary_source_enrichment_enabled=True,
        primary_source_search=fake_search,
        primary_source_max_queries=1,
    )

    assert calls == []
    assert result.audit.primary_source_enrichment_attempted is True
    assert result.audit.primary_source_enrichment_added_count == 0


def test_deepseek_receives_filtered_evidence_only(monkeypatch, tmp_path):
    captured = {}
    settings = SimpleNamespace(
        radar_timezone="Asia/Shanghai",
        output_dir=tmp_path,
        output_mode="none",
        send_bot=False,
        evidence_gate_enabled=True,
        event_history_enabled=False,
        primary_source_enrichment_enabled=False,
        source_quality_path=tmp_path / "missing.yaml",
        max_evidence_items=80,
        validate_for_generation=lambda: None,
    )
    audit = RecallAudit(target_date="2026-05-02", target_window="window", total_evidence_count=2)

    class FakeGenerator:
        def __init__(self, received_settings):
            pass

        def generate(self, window, evidence_md):
            captured["evidence_md"] = evidence_md
            return "\n".join(
                [
                    "## 国内候选事件筛选表",
                    "## 海外候选事件筛选表",
                    "## 国内版正式雷达",
                    "## 海外版正式雷达",
                    "## 输出前自我检查清单",
                    "来源：https://openai.com/news/a",
                ]
            )

    monkeypatch.setattr(main_module, "Settings", lambda: settings)
    monkeypatch.setattr(
        main_module,
        "parse_args",
        lambda: SimpleNamespace(date="2026-05-02", dry_run=True, skip_llm=False, output_mode=None, send_bot=None, verbose=False, force_republish=False),
    )
    monkeypatch.setattr(
        main_module,
        "collect_evidence_with_audit",
        lambda received_settings, window: (
            [
                _item("OpenAI当天发布", url="https://openai.com/news/a"),
                _item("旧事件回顾", url="https://openai.com/news/old", published_at="2026-05-01T08:00:00+08:00"),
            ],
            audit,
        ),
    )
    monkeypatch.setattr(main_module, "DeepSeekGenerator", FakeGenerator)
    monkeypatch.setattr(
        main_module,
        "DeepSeekBriefGenerator",
        lambda received_settings: SimpleNamespace(
            generate=lambda window, report, audit, doc_url="", evidence=None: {
                "date": "2026-05-02",
                "title": "AI Radar",
                "domestic_top": [],
                "overseas_top": [],
                "core_judgments": [],
                "watch_signals": [],
                "evidence_count": 1,
            }
        ),
    )
    monkeypatch.setattr(main_module, "maybe_send_bot_card", lambda *args, **kwargs: {"sent": False, "skipped": True})
    main_module.main()
    assert "OpenAI当天发布" in captured["evidence_md"]
    assert "旧事件回顾" not in captured["evidence_md"]
    assert (tmp_path / "2026-05-02" / "evidence_dropped.md").exists()


def test_render_dropped_markdown_contains_table():
    audit = EvidenceGateAudit(
        date="2026-05-02",
        dropped_count=1,
        dropped=[
            DroppedEvidence(
                title="旧新闻",
                source="Example",
                source_tier="S4",
                date_status="out_of_window",
                reason="out_of_window",
                url="https://example.com/full/path?keep=true",
            )
        ],
    )
    result = render_dropped_markdown(audit)
    assert "| title | source | source_tier | date_status | reason | url |" in result
    assert "| out_of_window | 1 |" in result
    assert "https://example.com/full/path?keep=true" in result


def test_summary_includes_evidence_gate_fields(monkeypatch, tmp_path):
    summary = tmp_path / "summary.md"
    brief_path = tmp_path / "2026-05-02" / "brief.json"
    brief_path.parent.mkdir(parents=True)
    brief_path.write_text(json.dumps({"domestic_top": [], "overseas_top": []}), encoding="utf-8")
    (brief_path.parent / "top_event_audit.json").write_text(
        json.dumps(
            {
                "top_events_count": 2,
                "top_events_with_primary_source_count": 1,
                "top_events_with_s1_source_count": 1,
                "top_events_with_s1_or_s2_source_count": 2,
                "top_events_with_low_source_count": 0,
                "top_events_out_of_window_count": 0,
                "top_events_old_repeated_count": 0,
                "top_events_new_signal_count": 1,
                "top_event_audit_warnings_count": 1,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    audit = RecallAudit(target_date="2026-05-02", target_window="window", total_evidence_count=1)
    gate = EvidenceGateAudit(
        date="2026-05-02",
        raw_evidence_count=2,
        filtered_evidence_count=1,
        dropped_count=1,
        dropped_old_repeated_count=1,
        primary_sources_count=1,
        official_sources_count=1,
        primary_source_enrichment_attempted=True,
        primary_source_enrichment_added_count=1,
        event_history_enabled=True,
        event_history_repeated_count=1,
    )
    main_module._write_github_summary(
        window=SimpleNamespace(date_str="2026-05-02"),
        audit=audit,
        output_mode="none",
        report_path=None,
        brief_path=brief_path,
        feishu_result={"output_mode": "none", "skipped": True, "reason": "test"},
        bot_result={"sent": False, "skipped": True},
        evidence_gate_audit=gate,
        event_history_summary={
            "event_history_enabled": True,
            "event_history_write_enabled": True,
            "event_history_path": "state/event_history.jsonl",
            "event_history_lookback_days": 5,
            "event_history_filter_mode": "mark",
            "event_history_events_loaded": 3,
            "event_history_matches_count": 2,
            "event_history_old_repeated_count": 1,
            "event_history_new_signal_count": 1,
            "event_history_dropped_from_core_count": 1,
            "event_history_observe_only_count": 1,
            "event_history_pre_llm_dropped_count": 0,
            "event_history_write_succeeded": False,
            "event_history_write_error": "dry_run",
            "final_top_dedupe_matches_count": 1,
            "final_top_dedupe_dropped_count": 1,
            "final_top_dedupe_new_signal_count": 0,
            "final_top_dedupe_dropped_titles_sample": "腾讯云下调DeepSeek-V4价格",
        },
    )
    text = summary.read_text(encoding="utf-8")
    assert "raw_evidence_count: 2" in text
    assert "filtered_evidence_count: 1" in text
    assert "evidence_gate_dropped_count: 1" in text
    assert "primary_source_enrichment_added_count: 1" in text
    assert "top_events_count: 2" in text
    assert "top_events_with_s1_or_s2_source_count: 2" in text
    assert "top_event_audit_warnings_count: 1" in text
    assert "event_history_lookback_days: 5" in text
    assert "event_history_filter_mode: mark" in text
    assert "event_history_matches_count: 2" in text
    assert "event_history_old_repeated_count: 1" in text
    assert "event_history_new_signal_count: 1" in text
    assert "event_history_pre_llm_dropped_count: 0" in text
    assert "event_history_write_error: dry_run" in text
    assert "final_top_dedupe_dropped_count: 1" in text
    assert "final_top_dedupe_dropped_titles_sample: 腾讯云下调DeepSeek-V4价格" in text
