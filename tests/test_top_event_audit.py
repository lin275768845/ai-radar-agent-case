from __future__ import annotations

import importlib.util
import json
import sys
from datetime import date
from pathlib import Path

from ai_radar_agent.dates import window_for_date
from ai_radar_agent.models import EvidenceItem
from ai_radar_agent.top_event_audit import audit_top_events


def _window():
    return window_for_date(date(2026, 5, 2), "Asia/Shanghai")


def _evidence(
    title: str,
    url: str,
    *,
    source_tier: str = "S1",
    source_fit: str = "high",
    date_status: str = "in_window",
    primary: bool = True,
):
    return EvidenceItem(
        title=title,
        url=url,
        content="summary",
        source="source",
        source_tier=source_tier,
        source_fit=source_fit,
        date_status=date_status,
        is_primary_source=primary,
    )


def test_top_event_audit_generates_counts_and_events():
    brief = {
        "domestic_top": [
            {
                "title": "OpenAI发布新模型",
                "priority": "P1",
                "sources": [{"url": "https://openai.com/news/model"}],
            }
        ],
        "overseas_top": [],
    }
    audit = audit_top_events(brief, [_evidence("OpenAI发布新模型", "https://openai.com/news/model")], _window())
    data = audit.to_dict()

    assert data["top_events_count"] == 1
    assert data["top_events_with_primary_source_count"] == 1
    assert data["top_events_with_s1_source_count"] == 1
    assert data["top_events_with_s1_or_s2_source_count"] == 1
    assert data["top_events_with_s1_s2_or_s3_source_count"] == 1
    assert data["events"][0]["source_tiers"] == ["S1"]


def test_top_event_low_source_warns():
    brief = {"domestic_top": [{"title": "低质来源事件", "sources": [{"url": "https://example.com/a"}]}]}
    audit = audit_top_events(
        brief,
        [_evidence("低质来源事件", "https://example.com/a", source_tier="S5", source_fit="low", primary=False)],
        _window(),
    )

    assert audit.top_events_with_low_source_count == 1
    assert "source_fit=low" in audit.events[0].warnings


def test_top_event_old_repeated_warns():
    brief = {"domestic_top": [{"title": "旧事件", "sources": [{"url": "https://example.com/old"}]}]}
    audit = audit_top_events(
        brief,
        [_evidence("旧事件", "https://example.com/old", source_tier="S2", date_status="old_repeated", primary=False)],
        _window(),
    )

    assert audit.top_events_old_repeated_count == 1
    assert "date_status=old_repeated" in audit.events[0].warnings


def test_top_event_missing_s1_s2_warns():
    brief = {"overseas_top": [{"title": "普通媒体事件", "sources": [{"url": "https://example.com/a"}]}]}
    audit = audit_top_events(
        brief,
        [_evidence("普通媒体事件", "https://example.com/a", source_tier="S4", source_fit="medium", primary=False)],
        _window(),
    )

    assert audit.top_events_with_s1_or_s2_source_count == 0
    assert audit.top_events_with_s1_s2_or_s3_source_count == 0
    assert "missing S1/S2/S3 source" in audit.events[0].warnings


def test_top_event_s3_data_source_is_acceptable():
    brief = {"domestic_top": [{"title": "OpenRouter排名更新", "sources": [{"url": "https://openrouter.ai/rankings"}]}]}
    audit = audit_top_events(
        brief,
        [_evidence("OpenRouter排名更新", "https://openrouter.ai/rankings", source_tier="S3", source_fit="high", primary=False)],
        _window(),
    )

    assert audit.top_events_with_s1_or_s2_source_count == 0
    assert audit.top_events_with_s1_s2_or_s3_source_count == 1
    assert "missing S1/S2/S3 source" not in audit.events[0].warnings


def test_compare_top_events_outputs_jaccard_and_clusters(tmp_path):
    first = tmp_path / "2026-05-01" / "brief.json"
    second = tmp_path / "2026-05-02" / "brief.json"
    third = tmp_path / "2026-05-03" / "brief.json"
    first.parent.mkdir(parents=True)
    second.parent.mkdir(parents=True)
    third.parent.mkdir(parents=True)
    first.write_text(json.dumps({"date": "2026-05-01", "domestic_top": [{"title": "OpenAI发布新模型"}]}), encoding="utf-8")
    second.write_text(json.dumps({"date": "2026-05-02", "domestic_top": [{"title": "OpenAI推出新模型"}]}), encoding="utf-8")
    third.write_text(json.dumps({"date": "2026-05-03", "domestic_top": [{"title": "Anthropic发布Claude"}]}), encoding="utf-8")

    script = Path(__file__).resolve().parents[1] / "scripts" / "compare_top_events.py"
    spec = importlib.util.spec_from_file_location("compare_top_events", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["compare_top_events"] = module
    spec.loader.exec_module(module)

    output = module.render_markdown(
        {
            "2026-05-01": module.load_top_events(first),
            "2026-05-02": module.load_top_events(second),
            "2026-05-03": module.load_top_events(third),
        }
    )

    assert "## Pairwise Jaccard" in output
    assert "repeat_clusters: 1" in output
    assert "OpenAI发布新模型" in output
