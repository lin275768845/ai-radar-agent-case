from pathlib import Path


def test_env_example_defaults_to_low_cost_search_and_history_mark_mode():
    text = Path(".env.example").read_text(encoding="utf-8")

    assert "SEARCH_PROVIDERS=rss,bocha" in text
    assert "TAVILY_ENABLED=true" not in text
    assert "TAVILY_ENABLED=false" in text
    assert "TAVILY_MAX_QUERIES=8" in text
    assert "BOCHA_MAX_QUERIES=20" in text
    assert "DEEPSEEK_MODEL=deepseek-v4-pro" in text
    assert "REPORT_LINT_POLICY=block_bot" in text
    assert "EVENT_HISTORY_LOOKBACK_DAYS=5" in text
    assert "EVENT_HISTORY_COMMIT_REF=main" in text
    assert "EVENT_HISTORY_FILTER_MODE=mark" in text
    assert "EVIDENCE_GATE_ENABLED=true" in text
