from datetime import date

from ai_radar_agent.dates import window_for_date
from ai_radar_agent.models import EvidenceItem
from ai_radar_agent.report import ensure_report_has_source_urls, save_report


def test_ensure_report_has_source_urls_appends_source_index():
    report = "# AI Radar\n\n正文没有链接。"
    evidence = [
        EvidenceItem(title="OpenAI news", url="https://openai.com/news/a", content="A", source="OpenAI"),
        EvidenceItem(title="No URL", url="", content="B", source="Example"),
    ]

    updated = ensure_report_has_source_urls(report, evidence)

    assert "## 附录：本次证据来源索引" in updated
    assert "- [E1] [OpenAI news](https://openai.com/news/a) — OpenAI" in updated
    assert "No URL" not in updated


def test_ensure_report_has_source_urls_does_not_duplicate_when_url_exists():
    report = "# AI Radar\n\n来源：[OpenAI](https://openai.com/news/a)"
    evidence = [EvidenceItem(title="OpenAI news", url="https://openai.com/news/a", content="A", source="OpenAI")]

    updated = ensure_report_has_source_urls(report, evidence)

    assert updated == report
    assert "附录：本次证据来源索引" not in updated


def test_save_report_can_be_rewritten_after_source_appendix(tmp_path):
    window = window_for_date(date(2026, 6, 1), "Asia/Shanghai")
    path = save_report(tmp_path, window, "# AI Radar")
    updated = ensure_report_has_source_urls(
        path.read_text(encoding="utf-8"),
        [EvidenceItem(title="A", url="https://example.com/a", content="A", source="Example")],
    )
    path.write_text(updated, encoding="utf-8")

    assert "https://example.com/a" in path.read_text(encoding="utf-8")
