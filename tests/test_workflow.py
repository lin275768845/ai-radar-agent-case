from pathlib import Path

import yaml


def test_daily_workflow_inputs_and_node24_settings():
    text = Path(".github/workflows/daily.yml").read_text(encoding="utf-8")
    workflow = yaml.safe_load(text)
    on_block = workflow.get("on") or workflow.get(True)
    inputs = on_block["workflow_dispatch"]["inputs"]

    assert "schedule" not in on_block
    for name in (
        "date",
        "dry_run",
        "skip_llm",
        "output_mode",
        "send_bot",
        "tavily_enabled",
        "force_republish",
        "report_lint_policy",
        "bot_block_on_lint_critical",
        "deepseek_model",
    ):
        assert f"{name}:" in text
    assert "FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true" in text
    assert "actions/checkout@v5" in text
    assert "ref: ${{ github.ref_name }}" in text
    assert "actions/setup-python@v6" in text
    assert "actions/upload-artifact@v4" in text
    assert "if: always()" in text
    assert "--force-republish" in text
    assert "REPORT_LINT_POLICY" in text
    assert "deepseek-v4-pro" in text
    assert "BOT_BLOCK_ON_LINT_CRITICAL" in text
    assert "FEISHU_BOT_FALLBACK_TEXT" in text
    assert "SEARCH_PROVIDERS" in text
    assert "BOCHA_API_KEY" in text
    assert "BOCHA_MAX_QUERIES" in text
    assert "MAX_SEARCH_QUERIES_PER_RUN" in text
    assert "EVENT_HISTORY_PATH" in text
    assert "EVENT_HISTORY_WRITE_ENABLED" in text
    assert "EVENT_HISTORY_COMMIT_ENABLED" in text
    assert "EVENT_HISTORY_COMMIT_REF" in text
    assert "EVENT_HISTORY_FILTER_MODE" in text
    assert "vars.EVENT_HISTORY_LOOKBACK_DAYS || '5'" in text
    assert "vars.EVENT_HISTORY_COMMIT_ENABLED || 'true'" in text
    assert "vars.EVENT_HISTORY_COMMIT_REF || 'main'" in text
    assert "Commit event history" in text
    assert "Update AI Radar event history" in text
    assert 'GITHUB_REF_TYPE" = "tag"' in text
    assert "unsupported_ref_for_history_commit" in text
    assert 'GITHUB_REF_NAME" != "$EVENT_HISTORY_COMMIT_REF"' in text
    assert "ref_not_allowed_for_history_commit" in text
    assert "event_history_commit_ref" in text
    assert "event_history_current_ref" in text
    assert 'git push origin "HEAD:${GITHUB_REF_NAME}"' in text
    assert "TAVILY_MAX_RESULTS_PER_QUERY" in text
    assert "vars.TAVILY_ENABLED || 'false'" in text
    assert "vars.TAVILY_MAX_QUERIES || '8'" in text
    assert inputs["date"]["default"] == ""
    assert inputs["dry_run"]["default"] is False
    assert inputs["skip_llm"]["default"] is False
    assert inputs["send_bot"]["default"] is True
    assert inputs["output_mode"]["default"] == "feishu_docx_import"
    assert inputs["output_mode"]["options"][0] == "feishu_docx_import"
    assert inputs["tavily_enabled"]["default"] is False
    assert inputs["force_republish"]["default"] is False
    assert inputs["report_lint_policy"]["default"] == "block_bot"
    assert inputs["bot_block_on_lint_critical"]["default"] is False
    assert inputs["deepseek_model"]["default"] == "deepseek-v4-pro"
    assert "Target date, YYYY-MM-DD" in inputs["date"]["description"]
    assert "Dry run:" in inputs["dry_run"]["description"]
    assert "Evidence only:" in inputs["skip_llm"]["description"]
    assert "costs Tavily quota" in inputs["tavily_enabled"]["description"]
