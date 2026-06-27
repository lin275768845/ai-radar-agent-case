from types import SimpleNamespace
import json

import pytest

from ai_radar_agent import __main__ as main_module
from ai_radar_agent.feishu_bot import BotResult
from ai_radar_agent.feishu_result import FeishuResult
from ai_radar_agent.models import EvidenceItem, RecallAudit
from ai_radar_agent.report_lint import ReportLintResult


def _audit():
    return RecallAudit(
        target_date="2026-06-01",
        target_window="2026-06-01 00:00:00 CST – 2026-06-01 23:59:59 CST",
        rss_item_count=1,
        tavily_item_count=0,
        total_evidence_count=1,
        failed_source_count=0,
    )


def _valid_report():
    return "\n".join(
        [
            "# AI Radar",
            "## 国内候选事件筛选表",
            "国内核心事件：不强行凑数。",
            "## 海外候选事件筛选表",
            "海外核心事件：不强行凑数。",
            "## 国内版正式雷达",
            "无。",
            "## 海外版正式雷达",
            "无。",
            "## 输出前自我检查清单",
            "已检查。",
            "来源：https://example.com",
        ]
    )


def test_raw_generated_llm_preamble_is_not_preserved_after_clean_reconcile():
    report_lint = ReportLintResult().finalize(strict=False)
    raw_report = "好的，以下是今日雷达。\n" + _valid_report()

    merged = main_module._merge_raw_generated_critical_lint(
        report_lint,
        raw_report,
        [EvidenceItem(title="Event", url="https://example.com", content="Summary")],
        strict=False,
        target_date="2026-06-01",
    )

    assert not merged.critical_errors


def test_raw_generated_placeholder_remains_blocking_after_reconcile():
    report_lint = ReportLintResult().finalize(strict=False)
    raw_report = _valid_report() + "\nTODO"

    merged = main_module._merge_raw_generated_critical_lint(
        report_lint,
        raw_report,
        [EvidenceItem(title="Event", url="https://example.com", content="Summary")],
        strict=False,
        target_date="2026-06-01",
    )

    assert "placeholder found: todo" in merged.critical_errors


def test_dry_run_does_not_upload_to_feishu(monkeypatch, tmp_path):
    settings = SimpleNamespace(
            radar_timezone="Asia/Shanghai",
            output_dir=tmp_path,
            output_mode="feishu_drive_md",
            send_bot=True,
            event_history_enabled=True,
            event_history_write_enabled=True,
            event_history_path=tmp_path / "state" / "event_history.jsonl",
            validate_for_generation=lambda: None,
            validate_for_feishu=lambda: (_ for _ in ()).throw(AssertionError("Feishu validation called")),
        )

    class FakeGenerator:
        def __init__(self, received_settings):
            assert received_settings is settings

        def generate(self, window, evidence_md):
            return _valid_report()

    class FakeFeishuClient:
        def __init__(self, received_settings):
            raise AssertionError("Feishu upload client should not be created in dry_run")

    monkeypatch.setattr(
        main_module,
        "parse_args",
        lambda: SimpleNamespace(
            date="2026-06-01", dry_run=True, skip_llm=False, output_mode=None, send_bot=None, verbose=False
        ),
    )
    monkeypatch.setattr(main_module, "Settings", lambda: settings)
    monkeypatch.setattr(
        main_module,
        "collect_evidence_with_audit",
        lambda received_settings, window: (
            [EvidenceItem(title="Event", url="https://example.com", content="Summary", region_hint="overseas")],
            _audit(),
        ),
    )
    monkeypatch.setattr(main_module, "DeepSeekGenerator", FakeGenerator)
    monkeypatch.setattr(main_module, "FeishuClient", FakeFeishuClient)
    monkeypatch.setattr(
        main_module,
        "DeepSeekBriefGenerator",
        lambda received_settings: SimpleNamespace(
            generate=lambda window, report, audit, doc_url="", evidence=None: {
                "date": "2026-06-01",
                "title": "AI Radar｜2026-06-01",
                "domestic_top": [],
                "overseas_top": [],
                "core_judgments": [],
                "watch_signals": [],
                "doc_url": "",
                "evidence_count": 1,
                "recall_summary": {"rss_count": 1, "tavily_count": 0, "total_count": 1},
            }
        ),
    )
    monkeypatch.setattr(
        main_module,
        "maybe_send_bot_card",
        lambda settings, brief, dry_run, skip_llm, send_bot: {"sent": False, "skipped": True, "reason": "dry_run"},
    )

    main_module.main()

    report_path = tmp_path / "2026-06-01" / "AI_radar_2026-06-01.md"
    assert "国内候选事件筛选表" in report_path.read_text(encoding="utf-8")
    assert (tmp_path / "2026-06-01" / "brief.json").exists()
    assert (tmp_path / "2026-06-01" / "top_event_audit.json").exists()
    assert not (tmp_path / "state" / "event_history.jsonl").exists()


def test_skip_llm_writes_only_evidence(monkeypatch, tmp_path):
    settings = SimpleNamespace(
            radar_timezone="Asia/Shanghai",
            output_dir=tmp_path,
            output_mode="feishu_drive_md",
            send_bot=True,
            validate_for_generation=lambda: (_ for _ in ()).throw(AssertionError("LLM validation called")),
        )

    monkeypatch.setattr(
        main_module,
        "parse_args",
        lambda: SimpleNamespace(
            date="2026-06-01", dry_run=False, skip_llm=True, output_mode=None, send_bot=None, verbose=False
        ),
    )
    monkeypatch.setattr(main_module, "Settings", lambda: settings)
    monkeypatch.setattr(
        main_module,
        "collect_evidence_with_audit",
        lambda received_settings, window: (
            [EvidenceItem(title="Event", url="https://example.com", content="Summary", region_hint="domestic")],
            _audit(),
        ),
    )
    monkeypatch.setattr(
        main_module,
        "DeepSeekGenerator",
        lambda received_settings: (_ for _ in ()).throw(AssertionError("LLM should not run")),
    )

    main_module.main()

    output_dir = tmp_path / "2026-06-01"
    assert (output_dir / "evidence.json").exists()
    assert (output_dir / "evidence.md").exists()
    assert not (output_dir / "AI_radar_2026-06-01.md").exists()


def test_event_history_artifacts_and_prompt_context(monkeypatch, tmp_path):
    captured = {}
    history_path = tmp_path / "state" / "event_history.jsonl"
    history_path.parent.mkdir(parents=True)
    history_path.write_text(
        json.dumps(
            {
                "date": "2026-05-31",
                "event_id": "domestic_tencent_deepseek",
                "region": "domestic",
                "title": "腾讯云下调DeepSeek-V4价格",
                "normalized_title": "腾讯云 下调 deepseek v4",
                "entities": ["腾讯云", "DeepSeek"],
                "priority": "P2",
                "source_urls": ["https://cloud.tencent.com/a"],
                "summary": "此前已报道价格调整。",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    settings = SimpleNamespace(
        radar_timezone="Asia/Shanghai",
        output_dir=tmp_path,
        output_mode="none",
        send_bot=False,
        evidence_gate_enabled=True,
        event_history_enabled=True,
        event_history_write_enabled=True,
        event_history_path=history_path,
        event_history_lookback_days=3,
        primary_source_enrichment_enabled=False,
        source_quality_path=tmp_path / "missing.yaml",
        max_evidence_items=80,
        validate_for_generation=lambda: None,
    )

    class FakeGenerator:
        def __init__(self, received_settings):
            pass

        def generate(self, window, evidence_md):
            captured["evidence_md"] = evidence_md
            return _valid_report()

    monkeypatch.setattr(
        main_module,
        "parse_args",
        lambda: SimpleNamespace(
            date="2026-06-01", dry_run=True, skip_llm=False, output_mode=None, send_bot=None, verbose=False, force_republish=False
        ),
    )
    monkeypatch.setattr(main_module, "Settings", lambda: settings)
    monkeypatch.setattr(
        main_module,
        "collect_evidence_with_audit",
        lambda received_settings, window: (
            [
                EvidenceItem(
                    title="腾讯云大幅下调DeepSeek-V4 API价格",
                    url="https://example.com/tencent",
                    content="媒体转载此前价格消息",
                    published_at="2026-06-01T08:00:00+08:00",
                    region_hint="domestic",
                )
            ],
            _audit(),
        ),
    )
    monkeypatch.setattr(main_module, "DeepSeekGenerator", FakeGenerator)
    monkeypatch.setattr(
        main_module,
        "DeepSeekBriefGenerator",
        lambda received_settings: SimpleNamespace(
            generate=lambda window, report, audit, doc_url="", evidence=None: {
                "date": "2026-06-01",
                "title": "AI Radar｜2026-06-01",
                "domestic_top": [],
                    "overseas_top": [],
                    "core_judgments": [],
                    "watch_signals": [],
                    "doc_url": "",
                    "evidence_count": 1,
                }
            ),
    )
    monkeypatch.setattr(main_module, "maybe_send_bot_card", lambda *args, **kwargs: {"sent": False, "skipped": True})

    main_module.main()

    output_dir = tmp_path / "2026-06-01"
    matches = json.loads((output_dir / "event_history_matches.json").read_text(encoding="utf-8"))
    assert matches["matched_candidates_count"] == 1
    assert matches["old_repeated_count"] == 1
    assert (output_dir / "final_top_dedupe.json").exists()
    assert "最近3日已入选Top事件" in captured["evidence_md"]
    assert "仅候选/观察证据（禁止入选正式雷达）" in captured["evidence_md"]
    assert "not_core_eligible：true" in captured["evidence_md"]
    assert "已从主报告 LLM 输入排除 not_core_eligible 证据：1 条" in captured["evidence_md"]
    assert (output_dir / "event_history_context.md").exists()


def test_event_history_write_failure_does_not_raise(monkeypatch, tmp_path):
    settings = SimpleNamespace(
        event_history_enabled=True,
        event_history_write_enabled=True,
        event_history_path=tmp_path / "state" / "event_history.jsonl",
        event_history_lookback_days=3,
    )
    audit = main_module.EventHistoryMatchAudit(date="2026-06-01", lookback_days=3)
    monkeypatch.setattr(
        main_module,
        "append_event_history",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("disk full")),
    )

    summary = main_module._write_event_history_after_success(
        settings,
        SimpleNamespace(target_date=__import__("datetime").date(2026, 6, 1), date_str="2026-06-01"),
        {"domestic_top": [{"title": "事件"}], "overseas_top": []},
        "doc-url",
        dry_run=False,
        skip_llm=False,
        match_audit=audit,
    )

    assert summary["event_history_write_succeeded"] is False
    assert "disk full" in str(summary["event_history_write_error"])


def test_event_history_filter_mode_mark_keeps_old_repeated_evidence():
    audit = main_module.EventHistoryMatchAudit(date="2026-06-01", lookback_days=5)
    evidence = [EvidenceItem(title="旧事件", url="https://example.com", content="")]
    evidence[0].date_status = "old_repeated"
    evidence[0].not_core_eligible = True

    result = main_module._apply_event_history_filter_mode(
        SimpleNamespace(event_history_filter_mode="mark"),
        evidence,
        audit,
    )

    assert result == evidence
    assert audit.filter_mode == "mark"
    assert audit.pre_llm_dropped_count == 0


def test_event_history_filter_mode_drop_removes_old_repeated_but_keeps_new_signal():
    audit = main_module.EventHistoryMatchAudit(date="2026-06-01", lookback_days=5)
    old = EvidenceItem(title="旧事件", url="https://example.com/old", content="")
    old.date_status = "old_repeated"
    old.not_core_eligible = True
    new_signal = EvidenceItem(title="旧事件有新信号", url="https://example.com/new", content="")
    new_signal.date_status = "new_signal"
    new_signal.not_core_eligible = False

    result = main_module._apply_event_history_filter_mode(
        SimpleNamespace(event_history_filter_mode="drop"),
        [old, new_signal],
        audit,
    )

    assert result == [new_signal]
    assert audit.filter_mode == "drop"
    assert audit.pre_llm_dropped_count == 1


def test_main_writes_final_brief_doc_url_before_bot(monkeypatch, tmp_path):
    settings = SimpleNamespace(
        radar_timezone="Asia/Shanghai",
        output_dir=tmp_path,
        output_mode="feishu_docx_import",
        send_bot=True,
        validate_for_generation=lambda: None,
    )
    bot_seen = {}

    class FakeGenerator:
        def __init__(self, received_settings):
            pass

        def generate(self, window, evidence_md):
            return _valid_report()

    monkeypatch.setattr(
        main_module,
        "parse_args",
        lambda: SimpleNamespace(
            date="2026-06-01", dry_run=False, skip_llm=False, output_mode=None, send_bot=None, verbose=False
        ),
    )
    monkeypatch.setattr(main_module, "Settings", lambda: settings)
    monkeypatch.setattr(
        main_module,
        "collect_evidence_with_audit",
        lambda received_settings, window: (
            [EvidenceItem(title="Event", url="https://example.com", content="Summary", region_hint="domestic")],
            _audit(),
        ),
    )
    monkeypatch.setattr(main_module, "DeepSeekGenerator", FakeGenerator)
    monkeypatch.setattr(
        main_module,
        "DeepSeekBriefGenerator",
        lambda received_settings: SimpleNamespace(
            generate=lambda window, report, audit, doc_url="", evidence=None: {
                "date": "2026-06-01",
                "title": "AI Radar｜2026-06-01",
                "domestic_top": [],
                "overseas_top": [],
                "core_judgments": [],
                "watch_signals": [],
                "doc_url": doc_url,
                "evidence_count": 1,
                "recall_summary": {"rss_count": 1, "tavily_count": 0, "total_count": 1},
            }
        ),
    )
    monkeypatch.setattr(
        main_module,
        "_handle_feishu_output",
        lambda settings, report_path, window, dry_run, force_republish=False: {
            "output_mode": "feishu_docx_import",
            "docx_url": "docx-url",
            "md_url": "",
            "canonical_url": "docx-url",
            "canonical_type": "docx",
            "fallback_used": False,
        },
    )
    def fake_bot(settings, brief, dry_run, skip_llm, send_bot):
        bot_seen["brief"] = brief
        return {"sent": True, "reason": ""}

    monkeypatch.setattr(main_module, "maybe_send_bot_card", fake_bot)

    main_module.main()

    brief_path = tmp_path / "2026-06-01" / "brief.json"
    brief = json.loads(brief_path.read_text(encoding="utf-8"))
    assert brief["doc_url"] == "docx-url"
    assert brief["canonical_type"] == "docx"
    assert bot_seen["brief"]["doc_url"] == "docx-url"


def test_no_evidence_does_not_call_deepseek(monkeypatch, tmp_path):
    settings = SimpleNamespace(
        radar_timezone="Asia/Shanghai",
        output_dir=tmp_path,
        output_mode="none",
        send_bot=False,
        validate_for_generation=lambda: None,
    )
    empty_audit = _audit()
    empty_audit.rss_item_count = 0
    empty_audit.tavily_item_count = 0
    empty_audit.total_evidence_count = 0
    empty_audit.tavily_status = "connectivity_failed"

    monkeypatch.setattr(
        main_module,
        "parse_args",
        lambda: SimpleNamespace(
            date="2026-06-01", dry_run=False, skip_llm=False, output_mode=None, send_bot=None, verbose=False
        ),
    )
    monkeypatch.setattr(main_module, "Settings", lambda: settings)
    monkeypatch.setattr(main_module, "collect_evidence_with_audit", lambda received_settings, window: ([], empty_audit))
    monkeypatch.setattr(
        main_module,
        "DeepSeekGenerator",
        lambda received_settings: (_ for _ in ()).throw(AssertionError("DeepSeek should not be called")),
    )

    with pytest.raises(RuntimeError, match="No evidence collected from RSS, Bocha, or Tavily"):
        main_module.main()

    assert (tmp_path / "2026-06-01" / "evidence.md").exists()


def test_github_summary_includes_tavily_status(monkeypatch, tmp_path):
    summary = tmp_path / "summary.md"
    audit = _audit()
    audit.bocha_item_count = 4
    audit.bocha_status = "ok"
    audit.bocha_error_summary = ""
    audit.search_providers_used = "rss,bocha,tavily"
    audit.search_query_budget = 30
    audit.search_queries_used = 8
    audit.provider_queries_used = {"rss": 0, "bocha": 5, "tavily": 3}
    audit.provider_results_count = {"rss": 1, "bocha": 4, "tavily": 2}
    audit.tavily_status = "connectivity_failed"
    audit.tavily_error_summary = "connect timeout"
    audit.rss_fallback_used = True
    monkeypatch.setenv("GITHUB_SHA", "abc123")
    monkeypatch.setenv("GITHUB_REF", "refs/heads/main")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "workflow_dispatch")
    brief_path = tmp_path / "brief.json"
    brief_path.write_text(
        json.dumps(
            {
                "brief_generation_status": "repaired",
                "domestic_top": [{"sources": [{"url": "https://example.com/a"}]}, {"sources": []}],
                "overseas_top": [{"sources": []}],
                "brief_source_validation_warnings": ["dropped source"],
                "brief_error_summary": "",
                "brief_repair_attempted": True,
                "brief_repair_succeeded": True,
                "brief_parse_stage": "repaired",
                "brief_raw_response_length": 123,
                "brief_raw_response_summary": "{\"ok\":true}",
                "brief_json_parse_error": "first parse failed",
                "brief_normalization_error": "",
                "brief_source_resolution_status": "partial",
                "brief_invalid_source_ids_count": 1,
                "brief_llm_domestic_items_count": 1,
                "brief_llm_overseas_items_count": 1,
                "brief_final_domestic_items_count": 1,
                "brief_final_overseas_items_count": 1,
                "brief_domestic_items_count_raw": 2,
                "brief_overseas_items_count_raw": 7,
                "brief_domestic_items_count_capped": 2,
                "brief_overseas_items_count_capped": 6,
                "brief_domestic_truncated": False,
                "brief_overseas_truncated": True,
                "brief_source_ids_requested_count": 3,
                "brief_source_ids_resolved_count": 2,
                "brief_source_ids_unresolved_count": 1,
                "brief_unresolved_source_ids_sample": ["BAD"],
                "brief_sources_filled_by_matching_count": 1,
                "report_domestic_core_events_count": 2,
                "report_overseas_core_events_count": 1,
                "report_domestic_core_events_count_raw": 2,
                "report_overseas_core_events_count_raw": 12,
                "report_domestic_core_events_count_capped": 2,
                "report_overseas_core_events_count_capped": 6,
                "domestic_core_events_truncated": False,
                "overseas_core_events_truncated": True,
                "domestic_core_events_truncated_from": 0,
                "overseas_core_events_truncated_from": 12,
                "report_domestic_zero_core_explicit": False,
                "report_overseas_zero_core_explicit": True,
                "report_domestic_zero_core_conflict_resolved": "",
                "report_overseas_zero_core_conflict_resolved": "events_found",
                "report_domestic_extraction_suspect": False,
                "report_overseas_extraction_suspect": False,
                "report_domestic_section_found": True,
                "report_overseas_section_found": True,
                "report_domestic_extraction_method": "table",
                "report_overseas_extraction_method": "none",
                "report_domestic_extracted_titles_sample": ["国内A", "国内B"],
                "report_overseas_extracted_titles_sample": [],
                "report_domestic_empty_reason": "",
                "report_overseas_empty_reason": "zero_core_explicit",
                "brief_empty_placeholder_removed_count": 1,
                "brief_count_mismatch": True,
                "brief_count_mismatch_type": "fake_empty_item",
                "brief_count_mismatch_handled": True,
                "brief_count_repair_attempted": True,
                "brief_count_repair_succeeded": True,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))

    main_module._write_github_summary(
        window=SimpleNamespace(date_str="2026-06-01"),
        audit=audit,
        output_mode="none",
        report_path=None,
        brief_path=brief_path,
        feishu_result=FeishuResult(
            output_mode="feishu_docx_import",
            docx_attempted=True,
            docx_import_started=True,
            docx_import_succeeded=True,
            docx_last_job_status="0",
            docx_poll_attempts=2,
            docx_poll_duration_seconds=3.0,
            docx_url="docx-url",
            docx_error_summary="",
            docx_raw_result_summary='{"result":{"url":"docx-url"}}',
            temp_file_token="boxcnsource",
            temp_file_deleted=False,
            temp_file_delete_error="status_code=403; body=forbidden",
        ).finalize(),
        bot_result=BotResult(
            attempted=True,
            sent=False,
            skipped=False,
            reason="signature_error",
            status_code=200,
            response_code=19024,
            response_msg="invalid signature",
            response_body_summary='{"code":19024,"msg":"invalid signature","redacted_field":"[REDACTED]"}',
            error_summary="",
            card_title="AI Radar｜2026-06-01",
            doc_url_present=True,
            link_target="docx",
            domestic_items_input_count=2,
            overseas_items_input_count=12,
            domestic_items_rendered_count=2,
            overseas_items_rendered_count=6,
            domestic_items_truncated=False,
            overseas_items_truncated=True,
            card_items_truncated=True,
            card_truncated_reason="max_6_per_region",
            title_truncation_count=2,
            title_truncation_examples=["Travelers全美部署OpenAI AI理赔助手 -> Travelers全美部署OpenAI…"],
        ),
        report_lint_policy="warn",
        bot_lint_action="ignored_by_policy_warn",
        report_lint=ReportLintResult(
            critical_errors=[
                "placeholder found: TODO token=secret-token",
                "report has no source URL",
                "report is empty",
                "fourth item should not appear",
            ]
        ).finalize(),
    )

    text = summary.read_text(encoding="utf-8")
    assert "app_version: week2_standardization" in text
    assert "github_sha: abc123" in text
    assert "github_ref: refs/heads/main" in text
    assert "github_event_name: workflow_dispatch" in text
    assert "Tavily status: connectivity_failed" in text
    assert "Bocha count: 4" in text
    assert "Bocha status: ok" in text
    assert "search providers used: rss,bocha,tavily" in text
    assert "search_query_budget: 30" in text
    assert "search_queries_used: 8" in text
    assert "provider_queries_used: {'rss': 0, 'bocha': 5, 'tavily': 3}" in text
    assert "provider_results_count: {'rss': 1, 'bocha': 4, 'tavily': 2}" in text
    assert "docx_attempted: true" in text
    assert "docx_import_started: true" in text
    assert "docx_import_succeeded: true" in text
    assert "docx_last_job_status: 0" in text
    assert "docx_poll_attempts: 2" in text
    assert "docx_poll_duration_seconds: 3.0" in text
    assert "docx_url exists: true" in text
    assert "brief_generation_status: repaired" in text
    assert "brief_repair_attempted: true" in text
    assert "brief_repair_succeeded: true" in text
    assert "brief_parse_stage: repaired" in text
    assert "brief_raw_response_length: 123" in text
    assert "brief_raw_response_summary: {\"ok\":true}" in text
    assert "brief_json_parse_error: first parse failed" in text
    assert "brief_normalization_error:" in text
    assert "brief_source_resolution_status: partial" in text
    assert "brief_invalid_source_ids_count: 1" in text
    assert "brief_items_count: 3" in text
    assert "report_domestic_core_events_count: 2" in text
    assert "report_overseas_core_events_count: 1" in text
    assert "report_domestic_core_events_count_raw: 2" in text
    assert "report_overseas_core_events_count_raw: 12" in text
    assert "report_domestic_core_events_count_capped: 2" in text
    assert "report_overseas_core_events_count_capped: 6" in text
    assert "domestic_core_events_truncated: false" in text
    assert "overseas_core_events_truncated: true" in text
    assert "domestic_core_events_truncated_from: 0" in text
    assert "overseas_core_events_truncated_from: 12" in text
    assert "report_domestic_zero_core_explicit: false" in text
    assert "report_overseas_zero_core_explicit: true" in text
    assert "report_domestic_zero_core_conflict_resolved:" in text
    assert "report_overseas_zero_core_conflict_resolved: events_found" in text
    assert "report_domestic_extraction_suspect: false" in text
    assert "report_overseas_extraction_suspect: false" in text
    assert "report_domestic_section_found: true" in text
    assert "report_overseas_section_found: true" in text
    assert "report_domestic_extraction_method: table" in text
    assert "report_overseas_extraction_method: none" in text
    assert "report_domestic_extracted_titles_sample: 国内A, 国内B" in text
    assert "report_overseas_extracted_titles_sample:" in text
    assert "report_domestic_empty_reason:" in text
    assert "report_overseas_empty_reason: zero_core_explicit" in text
    assert "core event extraction warning:" in text
    assert "brief_domestic_items_count: 2" in text
    assert "brief_overseas_items_count: 1" in text
    assert "brief_domestic_items_count_raw: 2" in text
    assert "brief_overseas_items_count_raw: 7" in text
    assert "brief_domestic_items_count_capped: 2" in text
    assert "brief_overseas_items_count_capped: 6" in text
    assert "brief_domestic_truncated: false" in text
    assert "brief_overseas_truncated: true" in text
    assert "brief_llm_domestic_items_count: 1" in text
    assert "brief_llm_overseas_items_count: 1" in text
    assert "brief_final_domestic_items_count: 1" in text
    assert "brief_final_overseas_items_count: 1" in text
    assert "brief_sources_count: 1" in text
    assert "brief_items_without_sources_count: 2" in text
    assert "brief_source_ids_requested_count: 3" in text
    assert "brief_source_ids_resolved_count: 2" in text
    assert "brief_source_ids_unresolved_count: 1" in text
    assert "brief_unresolved_source_ids_sample: BAD" in text
    assert "brief_sources_filled_by_matching_count: 1" in text
    assert "brief_empty_placeholder_removed_count: 1" in text
    assert "brief_count_mismatch: true" in text
    assert "brief_count_mismatch_type: fake_empty_item" in text
    assert "brief_count_mismatch_handled: true" in text
    assert "brief_count_repair_attempted: true" in text
    assert "brief_count_repair_succeeded: true" in text
    assert "brief_source_validation_warnings_count: 1" in text
    assert "report_lint_policy: warn" in text
    assert "report_lint critical_errors count: 4" in text
    assert "report_lint critical_errors summary: placeholder found: TODO redacted_field=[REDACTED]" in text
    assert "report has no source URL" in text
    assert "report is empty" in text
    assert "fourth item should not appear" not in text
    assert "secret-token" not in text
    assert "fallback_used: false" in text
    assert "fallback_reason:" in text
    assert "canonical_type: docx" in text
    assert "canonical_url exists: true" in text
    assert "temp_file_token exists: true" in text
    assert "temp_file_deleted: false" in text
    assert "temp_file_delete_error: status_code=403; body=forbidden" in text
    assert "Tavily error summary: connect timeout" in text
    assert "RSS fallback used: True" in text
    assert "bot lint action: ignored_by_policy_warn" in text
    assert "bot attempted: true" in text
    assert "bot sent: false" in text
    assert "bot skipped/reason: signature_error" in text
    assert "bot status_code: 200" in text
    assert "bot response_code: 19024" in text
    assert "bot response_msg: invalid signature" in text
    assert "bot response_body_summary:" in text
    assert "bot link target: docx" in text
    assert "bot_domestic_items_input_count: 2" in text
    assert "bot_overseas_items_input_count: 12" in text
    assert "bot_domestic_items_rendered_count: 2" in text
    assert "bot_overseas_items_rendered_count: 6" in text
    assert "bot_domestic_items_truncated: false" in text
    assert "bot_overseas_items_truncated: true" in text
    assert "bot_card_items_truncated: true" in text
    assert "bot_card_truncated_reason: max_6_per_region" in text
    assert "bot_title_truncation_count: 2" in text
    assert "bot_title_truncation_examples: Travelers全美部署OpenAI AI理赔助手 -> Travelers全美部署OpenAI…" in text
    assert "bot doc_url present: true" in text
    assert "sign-token-secret" not in text
    assert "boxcnsource" not in text


def test_output_mode_none_does_not_send_bot(monkeypatch, tmp_path):
    settings = SimpleNamespace(
        radar_timezone="Asia/Shanghai",
        output_dir=tmp_path,
        output_mode="none",
        send_bot=True,
        validate_for_generation=lambda: None,
    )
    bot_seen = {}

    monkeypatch.setattr(
        main_module,
        "parse_args",
        lambda: SimpleNamespace(
            date="2026-06-01", dry_run=False, skip_llm=False, output_mode=None, send_bot=None, verbose=False
        ),
    )
    monkeypatch.setattr(main_module, "Settings", lambda: settings)
    monkeypatch.setattr(
        main_module,
        "collect_evidence_with_audit",
        lambda received_settings, window: (
            [EvidenceItem(title="Event", url="https://example.com", content="Summary", region_hint="domestic")],
            _audit(),
        ),
    )
    monkeypatch.setattr(
        main_module,
        "DeepSeekGenerator",
        lambda received_settings: SimpleNamespace(generate=lambda window, evidence_md: _valid_report()),
    )
    monkeypatch.setattr(
        main_module,
        "DeepSeekBriefGenerator",
        lambda received_settings: SimpleNamespace(
            generate=lambda window, report, audit, doc_url="", evidence=None: {
                "date": "2026-06-01",
                "title": "AI Radar｜2026-06-01",
                "domestic_top": [],
                "overseas_top": [],
                "core_judgments": [],
                "watch_signals": [],
                "doc_url": doc_url,
                "evidence_count": 1,
                "recall_summary": {"rss_count": 1, "tavily_count": 0, "total_count": 1},
            }
        ),
    )

    def fake_bot(settings, brief, dry_run, skip_llm, send_bot):
        bot_seen["send_bot"] = send_bot
        return {"sent": False, "skipped": True, "reason": "send_bot=false"}

    monkeypatch.setattr(main_module, "maybe_send_bot_card", fake_bot)

    main_module.main()

    assert bot_seen["send_bot"] is False


def test_publish_result_json_reuses_canonical_url(monkeypatch, tmp_path):
    settings = SimpleNamespace(
        output_dir=tmp_path,
        output_mode="feishu_docx_import",
    )
    output_dir = tmp_path / "2026-06-01"
    output_dir.mkdir()
    (output_dir / "publish_result.json").write_text(
        json.dumps(
            {
                "date": "2026-06-01",
                "output_mode": "feishu_docx_import",
                "canonical_type": "docx",
                "canonical_url": "docx-url",
                "docx_url": "docx-url",
                "md_url": "",
                "published_at": "2026-06-02T00:00:00+00:00",
                "github_run_id": "1",
                "fallback_used": False,
            }
        ),
        encoding="utf-8",
    )
    report = output_dir / "AI_radar_2026-06-01.md"
    report.write_text(_valid_report(), encoding="utf-8")
    monkeypatch.setattr(
        main_module,
        "publish_report",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("publish should not be called")),
    )

    result = main_module._handle_feishu_output(
        settings,
        report,
        window=SimpleNamespace(date_str="2026-06-01"),
        dry_run=False,
        force_republish=False,
    )

    assert result.canonical_url == "docx-url"
    assert result.reused_publish_result is True


def test_force_republish_writes_new_publish_result(monkeypatch, tmp_path):
    settings = SimpleNamespace(
        output_dir=tmp_path,
        output_mode="feishu_docx_import",
    )
    output_dir = tmp_path / "2026-06-01"
    output_dir.mkdir()
    (output_dir / "publish_result.json").write_text(
        json.dumps({"date": "2026-06-01", "canonical_url": "old-url"}),
        encoding="utf-8",
    )
    report = output_dir / "AI_radar_2026-06-01.md"
    report.write_text(_valid_report(), encoding="utf-8")
    calls = {"count": 0}

    def fake_publish(output_mode, report_path, settings, window):
        calls["count"] += 1
        return FeishuResult(output_mode=output_mode, docx_url="new-url").finalize()

    monkeypatch.setattr(main_module, "publish_report", fake_publish)

    result = main_module._handle_feishu_output(
        settings,
        report,
        window=SimpleNamespace(date_str="2026-06-01"),
        dry_run=False,
        force_republish=True,
    )

    assert calls["count"] == 1
    assert result.canonical_url == "new-url"
    data = json.loads((output_dir / "publish_result.json").read_text(encoding="utf-8"))
    assert data["canonical_url"] == "new-url"


def test_report_lint_policy_warn_errors_still_sends_bot(monkeypatch, tmp_path):
    settings = SimpleNamespace(
        radar_timezone="Asia/Shanghai",
        output_dir=tmp_path,
        output_mode="feishu_docx_import",
        send_bot=True,
        strict_report_lint=False,
        report_lint_policy="warn",
        print_feishu_url_in_summary=True,
        validate_for_generation=lambda: None,
    )
    bot_called = {"value": False}

    monkeypatch.setattr(
        main_module,
        "parse_args",
        lambda: SimpleNamespace(
            date="2026-06-01",
            dry_run=False,
            skip_llm=False,
            output_mode=None,
            send_bot=None,
            force_republish=False,
            verbose=False,
        ),
    )
    monkeypatch.setattr(main_module, "Settings", lambda: settings)
    monkeypatch.setattr(
        main_module,
        "collect_evidence_with_audit",
        lambda received_settings, window: (
            [EvidenceItem(title="Event", url="https://example.com", content="Summary", region_hint="domestic")],
            _audit(),
        ),
    )
    monkeypatch.setattr(
        main_module,
        "DeepSeekGenerator",
        lambda received_settings: SimpleNamespace(
            generate=lambda window, evidence_md: "\n".join(
                [
                    "## 国内候选事件筛选表",
                    "## 海外候选事件筛选表",
                    "## 国内版正式雷达",
                    "## 海外版正式雷达",
                    "## 来源附录",
                    "来源：https://example.com",
                    "额外来源：https://not-evidence.example.com/a",
                ]
            )
        ),
    )
    monkeypatch.setattr(
        main_module,
        "_handle_feishu_output",
        lambda settings, report_path, window, dry_run, force_republish=False: FeishuResult(
            output_mode="feishu_docx_import", docx_url="docx-url"
        ).finalize(),
    )
    monkeypatch.setattr(
        main_module,
        "DeepSeekBriefGenerator",
        lambda received_settings: SimpleNamespace(
            generate=lambda window, report, audit, doc_url="", evidence=None: {
                "date": "2026-06-01",
                "title": "AI Radar｜2026-06-01",
                "domestic_top": [],
                "overseas_top": [],
                "core_judgments": [],
                "watch_signals": [],
                "doc_url": doc_url,
                "evidence_count": 1,
                "recall_summary": {"rss_count": 1, "tavily_count": 0, "total_count": 1},
            }
        ),
    )
    monkeypatch.setattr(
        main_module,
        "maybe_send_bot_card",
        lambda *args, **kwargs: bot_called.update(value=True),
    )

    main_module.main()

    assert bot_called["value"] is True
    lint = json.loads((tmp_path / "2026-06-01" / "report_lint.json").read_text(encoding="utf-8"))
    assert lint["errors"]
    assert lint["critical_errors"] == []


def test_report_lint_policy_block_bot_errors_skip_bot(monkeypatch, tmp_path):
    settings = SimpleNamespace(
        radar_timezone="Asia/Shanghai",
        output_dir=tmp_path,
        output_mode="feishu_docx_import",
        send_bot=True,
        strict_report_lint=False,
        report_lint_policy="block_bot",
        bot_block_on_lint_critical=False,
        print_feishu_url_in_summary=True,
        validate_for_generation=lambda: None,
    )
    bot_called = {"value": False}
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))

    monkeypatch.setattr(
        main_module,
        "parse_args",
        lambda: SimpleNamespace(
            date="2026-06-01",
            dry_run=False,
            skip_llm=False,
            output_mode=None,
            send_bot=None,
            force_republish=False,
            verbose=False,
        ),
    )
    monkeypatch.setattr(main_module, "Settings", lambda: settings)
    monkeypatch.setattr(
        main_module,
        "collect_evidence_with_audit",
        lambda received_settings, window: (
            [EvidenceItem(title="Event", url="https://example.com", content="Summary", region_hint="domestic")],
            _audit(),
        ),
    )
    monkeypatch.setattr(
        main_module,
        "DeepSeekGenerator",
        lambda received_settings: SimpleNamespace(
            generate=lambda window, evidence_md: "\n".join(
                [
                    "## 国内候选事件筛选表",
                    "## 海外候选事件筛选表",
                    "## 国内版正式雷达",
                    "## 海外版正式雷达",
                    "## 来源附录",
                    "来源：https://example.com",
                    "额外来源：https://not-evidence.example.com/a",
                ]
            )
        ),
    )
    monkeypatch.setattr(
        main_module,
        "_handle_feishu_output",
        lambda settings, report_path, window, dry_run, force_republish=False: FeishuResult(
            output_mode="feishu_docx_import", docx_url="docx-url"
        ).finalize(),
    )
    monkeypatch.setattr(
        main_module,
        "DeepSeekBriefGenerator",
        lambda received_settings: SimpleNamespace(
            generate=lambda window, report, audit, doc_url="", evidence=None: {
                "date": "2026-06-01",
                "title": "AI Radar｜2026-06-01",
                "domestic_top": [],
                "overseas_top": [],
                "core_judgments": [],
                "watch_signals": [],
                "doc_url": doc_url,
                "evidence_count": 1,
                "recall_summary": {"rss_count": 1, "tavily_count": 0, "total_count": 1},
            }
        ),
    )
    monkeypatch.setattr(
        main_module,
        "maybe_send_bot_card",
        lambda *args, **kwargs: bot_called.update(value=True),
    )

    main_module.main()

    assert bot_called["value"] is False
    text = summary.read_text(encoding="utf-8")
    assert "bot attempted: false" in text
    assert "bot skipped/reason: report_lint_errors" in text
    assert "bot link target: docx" in text


def test_report_lint_runs_after_reconcile_before_bot_gate(monkeypatch, tmp_path):
    settings = SimpleNamespace(
        radar_timezone="Asia/Shanghai",
        output_dir=tmp_path,
        output_mode="feishu_docx_import",
        send_bot=True,
        strict_report_lint=False,
        report_lint_policy="block_bot",
        bot_block_on_lint_critical=False,
        print_feishu_url_in_summary=True,
        validate_for_generation=lambda: None,
    )
    bot_called = {"value": False}

    monkeypatch.setattr(
        main_module,
        "parse_args",
        lambda: SimpleNamespace(
            date="2026-06-01",
            dry_run=False,
            skip_llm=False,
            output_mode=None,
            send_bot=None,
            force_republish=False,
            verbose=False,
        ),
    )
    monkeypatch.setattr(main_module, "Settings", lambda: settings)
    monkeypatch.setattr(
        main_module,
        "collect_evidence_with_audit",
        lambda received_settings, window: (
            [EvidenceItem(title="Event", url="https://example.com", content="Summary", region_hint="domestic")],
            _audit(),
        ),
    )
    monkeypatch.setattr(
        main_module,
        "DeepSeekGenerator",
        lambda received_settings: SimpleNamespace(
            generate=lambda window, evidence_md: "\n".join(
                [
                    "# AI Radar",
                    "## 国内版正式雷达",
                    "无。",
                    "## 海外版正式雷达",
                    "无。",
                    "## 输出前自我检查清单",
                    "已检查。",
                    "来源：https://example.com",
                ]
            )
        ),
    )
    monkeypatch.setattr(
        main_module,
        "_handle_feishu_output",
        lambda settings, report_path, window, dry_run, force_republish=False: FeishuResult(
            output_mode="feishu_docx_import", docx_url="docx-url"
        ).finalize(),
    )
    monkeypatch.setattr(
        main_module,
        "DeepSeekBriefGenerator",
        lambda received_settings: SimpleNamespace(
            generate=lambda window, report, audit, doc_url="", evidence=None: {
                "date": "2026-06-01",
                "title": "AI Radar｜2026-06-01",
                "domestic_top": [],
                "overseas_top": [],
                "core_judgments": [],
                "watch_signals": [],
                "doc_url": doc_url,
                "evidence_count": 1,
                "recall_summary": {"rss_count": 1, "tavily_count": 0, "total_count": 1},
            }
        ),
    )
    monkeypatch.setattr(
        main_module,
        "maybe_send_bot_card",
        lambda *args, **kwargs: bot_called.update(value=True)
        or BotResult(
            attempted=True,
            sent=True,
            reason="sent",
            card_title="AI Radar｜2026-06-01",
            doc_url_present=True,
            link_target="docx",
        ),
    )

    main_module.main()

    lint = json.loads((tmp_path / "2026-06-01" / "report_lint.json").read_text(encoding="utf-8"))
    report = (tmp_path / "2026-06-01" / "AI_radar_2026-06-01.md").read_text(encoding="utf-8")
    assert lint["errors"] == []
    assert "## 国内候选事件筛选表" in report
    assert "## 海外候选事件筛选表" in report
    assert bot_called["value"] is True


def test_report_source_appendix_runs_after_reconcile(monkeypatch, tmp_path):
    settings = SimpleNamespace(
        radar_timezone="Asia/Shanghai",
        output_dir=tmp_path,
        output_mode="none",
        send_bot=False,
        strict_report_lint=False,
        report_lint_policy="warn",
        print_feishu_url_in_summary=True,
        validate_for_generation=lambda: None,
    )

    monkeypatch.setattr(
        main_module,
        "parse_args",
        lambda: SimpleNamespace(
            date="2026-06-01",
            dry_run=True,
            skip_llm=False,
            output_mode=None,
            send_bot=None,
            force_republish=False,
            verbose=False,
        ),
    )
    monkeypatch.setattr(main_module, "Settings", lambda: settings)
    monkeypatch.setattr(
        main_module,
        "collect_evidence_with_audit",
        lambda received_settings, window: (
            [EvidenceItem(title="Source event", url="https://example.com/source", content="Summary", region_hint="domestic")],
            _audit(),
        ),
    )
    monkeypatch.setattr(
        main_module,
        "DeepSeekGenerator",
        lambda received_settings: SimpleNamespace(
            generate=lambda window, evidence_md: "\n".join(
                [
                    "## 国内候选事件筛选表",
                    "## 海外候选事件筛选表",
                    "## 国内版正式雷达",
                    "### 一、今日总览",
                    "| 标题 | 层级 | 优先级 | 可信度 | 影响方向 |",
                    "|---|---|---|---|---|",
                    "| Source event | L3 | P2 | 高 | 应用 |",
                    "## 海外版正式雷达",
                    "无。",
                    "## 输出前自我检查清单",
                    "已检查。",
                ]
            )
        ),
    )
    monkeypatch.setattr(
        main_module,
        "DeepSeekBriefGenerator",
        lambda received_settings: SimpleNamespace(
            generate=lambda window, report, audit, doc_url="", evidence=None: {
                "date": "2026-06-01",
                "title": "AI Radar｜2026-06-01",
                "domestic_top": [],
                "overseas_top": [],
                "core_judgments": [],
                "watch_signals": [],
                "doc_url": doc_url,
                "evidence_count": 1,
                "recall_summary": {"rss_count": 1, "tavily_count": 0, "total_count": 1},
            }
        ),
    )

    main_module.main()

    report = (tmp_path / "2026-06-01" / "AI_radar_2026-06-01.md").read_text(encoding="utf-8")
    lint = json.loads((tmp_path / "2026-06-01" / "report_lint.json").read_text(encoding="utf-8"))
    assert "## 附录：本次证据来源索引" in report
    assert "https://example.com/source" in report
    assert lint["source_appendix_present"] is True
    assert lint["source_url_count"] == 1
    assert lint["errors"] == []


def test_bot_lint_policy_actions():
    from ai_radar_agent.report_lint import ReportLintResult

    errors = ReportLintResult(errors=["format"]).finalize()
    critical = ReportLintResult(critical_errors=["empty"]).finalize()

    assert main_module._bot_lint_action(errors, "warn") == "ignored_by_policy_warn"
    assert main_module._bot_lint_action(critical, "warn") == "ignored_critical_by_policy_warn"
    assert (
        main_module._bot_lint_action(critical, "warn", bot_block_on_lint_critical=True)
        == "blocked_by_critical_errors"
    )
    assert main_module._bot_lint_action(errors, "block_bot") == "blocked_by_errors"
    assert main_module._bot_lint_action(critical, "block_bot") == "blocked_by_critical_errors"
    assert main_module._bot_lint_action(errors, "strict") == "blocked_by_errors"
    assert main_module._bot_lint_action(errors, "off") == "off"


def test_report_lint_policy_warn_critical_still_sends_bot(monkeypatch, tmp_path):
    settings = SimpleNamespace(
        radar_timezone="Asia/Shanghai",
        output_dir=tmp_path,
        output_mode="feishu_docx_import",
        send_bot=True,
        strict_report_lint=False,
        report_lint_policy="warn",
        bot_block_on_lint_critical=False,
        print_feishu_url_in_summary=True,
        validate_for_generation=lambda: None,
    )
    bot_called = {"value": False}
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))

    monkeypatch.setattr(
        main_module,
        "parse_args",
        lambda: SimpleNamespace(
            date="2026-06-01",
            dry_run=False,
            skip_llm=False,
            output_mode=None,
            send_bot=None,
            force_republish=False,
            verbose=False,
        ),
    )
    monkeypatch.setattr(main_module, "Settings", lambda: settings)
    monkeypatch.setattr(
        main_module,
        "collect_evidence_with_audit",
        lambda received_settings, window: (
            [EvidenceItem(title="Event", url="https://example.com", content="Summary", region_hint="domestic")],
            _audit(),
        ),
    )
    monkeypatch.setattr(
        main_module,
        "DeepSeekGenerator",
        lambda received_settings: SimpleNamespace(generate=lambda window, evidence_md: _valid_report() + "\nTBD"),
    )
    monkeypatch.setattr(
        main_module,
        "_handle_feishu_output",
        lambda settings, report_path, window, dry_run, force_republish=False: FeishuResult(
            output_mode="feishu_docx_import", docx_url="docx-url"
        ).finalize(),
    )
    monkeypatch.setattr(
        main_module,
        "DeepSeekBriefGenerator",
        lambda received_settings: SimpleNamespace(
            generate=lambda window, report, audit, doc_url="", evidence=None: {
                "date": "2026-06-01",
                "title": "AI Radar｜2026-06-01",
                "domestic_top": [],
                "overseas_top": [],
                "core_judgments": [],
                "watch_signals": [],
                "doc_url": doc_url,
                "evidence_count": 1,
                "recall_summary": {"rss_count": 1, "tavily_count": 0, "total_count": 1},
            }
        ),
    )
    monkeypatch.setattr(
        main_module,
        "maybe_send_bot_card",
        lambda *args, **kwargs: bot_called.update(value=True)
        or BotResult(
            attempted=True,
            sent=True,
            reason="sent",
            card_title="AI Radar｜2026-06-01",
            doc_url_present=True,
            link_target="docx",
        ),
    )

    main_module.main()

    assert bot_called["value"] is True
    text = summary.read_text(encoding="utf-8")
    assert "report_lint critical_errors summary: placeholder found: tbd" in text
    assert "bot lint action: ignored_critical_by_policy_warn" in text
    assert "bot attempted: true" in text
    assert "bot sent: true" in text
    assert "bot skipped/reason: sent" in text
    assert "bot link target: docx" in text


def test_report_lint_policy_warn_critical_can_block_bot(monkeypatch, tmp_path):
    settings = SimpleNamespace(
        radar_timezone="Asia/Shanghai",
        output_dir=tmp_path,
        output_mode="feishu_docx_import",
        send_bot=True,
        strict_report_lint=False,
        report_lint_policy="warn",
        bot_block_on_lint_critical=True,
        print_feishu_url_in_summary=True,
        validate_for_generation=lambda: None,
    )
    bot_called = {"value": False}
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))

    monkeypatch.setattr(
        main_module,
        "parse_args",
        lambda: SimpleNamespace(
            date="2026-06-01",
            dry_run=False,
            skip_llm=False,
            output_mode=None,
            send_bot=None,
            force_republish=False,
            verbose=False,
        ),
    )
    monkeypatch.setattr(main_module, "Settings", lambda: settings)
    monkeypatch.setattr(
        main_module,
        "collect_evidence_with_audit",
        lambda received_settings, window: (
            [EvidenceItem(title="Event", url="https://example.com", content="Summary", region_hint="domestic")],
            _audit(),
        ),
    )
    monkeypatch.setattr(
        main_module,
        "DeepSeekGenerator",
        lambda received_settings: SimpleNamespace(generate=lambda window, evidence_md: _valid_report() + "\nTBD"),
    )
    monkeypatch.setattr(
        main_module,
        "_handle_feishu_output",
        lambda settings, report_path, window, dry_run, force_republish=False: FeishuResult(
            output_mode="feishu_docx_import", docx_url="docx-url"
        ).finalize(),
    )
    monkeypatch.setattr(
        main_module,
        "DeepSeekBriefGenerator",
        lambda received_settings: SimpleNamespace(
            generate=lambda window, report, audit, doc_url="", evidence=None: {
                "date": "2026-06-01",
                "title": "AI Radar｜2026-06-01",
                "domestic_top": [],
                "overseas_top": [],
                "core_judgments": [],
                "watch_signals": [],
                "doc_url": doc_url,
                "evidence_count": 1,
                "recall_summary": {"rss_count": 1, "tavily_count": 0, "total_count": 1},
            }
        ),
    )
    monkeypatch.setattr(
        main_module,
        "maybe_send_bot_card",
        lambda *args, **kwargs: bot_called.update(value=True),
    )

    main_module.main()

    assert bot_called["value"] is False
    text = summary.read_text(encoding="utf-8")
    assert "bot lint action: blocked_by_critical_errors" in text
    assert "bot attempted: false" in text
    assert "bot skipped/reason: report_lint_critical_errors" in text
    assert "bot link target: docx" in text


def test_report_lint_policy_strict_errors_block_publish(monkeypatch, tmp_path):
    settings = SimpleNamespace(
        radar_timezone="Asia/Shanghai",
        output_dir=tmp_path,
        output_mode="feishu_docx_import",
        send_bot=True,
        strict_report_lint=False,
        report_lint_policy="strict",
        print_feishu_url_in_summary=True,
        validate_for_generation=lambda: None,
    )

    monkeypatch.setattr(
        main_module,
        "parse_args",
        lambda: SimpleNamespace(
            date="2026-06-01",
            dry_run=False,
            skip_llm=False,
            output_mode=None,
            send_bot=None,
            force_republish=False,
            verbose=False,
        ),
    )
    monkeypatch.setattr(main_module, "Settings", lambda: settings)
    monkeypatch.setattr(
        main_module,
        "collect_evidence_with_audit",
        lambda received_settings, window: (
            [EvidenceItem(title="Event", url="https://example.com", content="Summary", region_hint="domestic")],
            _audit(),
        ),
    )
    monkeypatch.setattr(
        main_module,
        "DeepSeekGenerator",
        lambda received_settings: SimpleNamespace(
            generate=lambda window, evidence_md: "\n".join(
                [
                    "## 国内候选事件筛选表",
                    "## 海外候选事件筛选表",
                    "## 国内版正式雷达",
                    "## 海外版正式雷达",
                    "## 来源附录",
                    "来源：https://example.com",
                    "额外来源：https://not-evidence.example.com/a",
                ]
            )
        ),
    )
    monkeypatch.setattr(
        main_module,
        "_handle_feishu_output",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("publish should not be called")),
    )
    monkeypatch.setattr(
        main_module,
        "DeepSeekBriefGenerator",
        lambda received_settings: SimpleNamespace(
            generate=lambda window, report, audit, doc_url="", evidence=None: {
                "date": "2026-06-01",
                "title": "AI Radar｜2026-06-01",
                "domestic_top": [],
                "overseas_top": [],
                "core_judgments": [],
                "watch_signals": [],
                "doc_url": doc_url,
                "evidence_count": 1,
                "recall_summary": {"rss_count": 1, "tavily_count": 0, "total_count": 1},
            }
        ),
    )

    with pytest.raises(RuntimeError, match="Report lint failed"):
        main_module.main()


def test_report_lint_policy_off_critical_still_sends_bot(monkeypatch, tmp_path):
    settings = SimpleNamespace(
        radar_timezone="Asia/Shanghai",
        output_dir=tmp_path,
        output_mode="feishu_docx_import",
        send_bot=True,
        strict_report_lint=False,
        report_lint_policy="off",
        print_feishu_url_in_summary=True,
        validate_for_generation=lambda: None,
    )
    bot_called = {"value": False}

    monkeypatch.setattr(
        main_module,
        "parse_args",
        lambda: SimpleNamespace(
            date="2026-06-01",
            dry_run=False,
            skip_llm=False,
            output_mode=None,
            send_bot=None,
            force_republish=False,
            verbose=False,
        ),
    )
    monkeypatch.setattr(main_module, "Settings", lambda: settings)
    monkeypatch.setattr(
        main_module,
        "collect_evidence_with_audit",
        lambda received_settings, window: (
            [EvidenceItem(title="Event", url="https://example.com", content="Summary", region_hint="domestic")],
            _audit(),
        ),
    )
    monkeypatch.setattr(
        main_module,
        "DeepSeekGenerator",
        lambda received_settings: SimpleNamespace(generate=lambda window, evidence_md: _valid_report() + "\nTBD"),
    )
    monkeypatch.setattr(
        main_module,
        "_handle_feishu_output",
        lambda settings, report_path, window, dry_run, force_republish=False: FeishuResult(
            output_mode="feishu_docx_import", docx_url="docx-url"
        ).finalize(),
    )
    monkeypatch.setattr(
        main_module,
        "DeepSeekBriefGenerator",
        lambda received_settings: SimpleNamespace(
            generate=lambda window, report, audit, doc_url="", evidence=None: {
                "date": "2026-06-01",
                "title": "AI Radar｜2026-06-01",
                "domestic_top": [],
                "overseas_top": [],
                "core_judgments": [],
                "watch_signals": [],
                "doc_url": doc_url,
                "evidence_count": 1,
                "recall_summary": {"rss_count": 1, "tavily_count": 0, "total_count": 1},
            }
        ),
    )
    monkeypatch.setattr(
        main_module,
        "maybe_send_bot_card",
        lambda *args, **kwargs: bot_called.update(value=True),
    )

    main_module.main()

    assert bot_called["value"] is True
