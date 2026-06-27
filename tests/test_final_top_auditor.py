from __future__ import annotations

from ai_radar_agent.final_top_auditor import _build_prompt, _parse_decisions


def test_final_top_auditor_prompt_only_asks_for_drop_decisions():
    prompt = _build_prompt(
        {
            "date": "2026-06-05",
            "domestic_top": [{"title": "DeepSeek登顶美企软件趋势榜", "priority": "P1"}],
            "overseas_top": [{"title": "DeepSeek登顶美企软件趋势榜", "priority": "P1"}],
        },
        [],
        max_history_events=30,
    )

    assert "不要输出 keep 决策" in prompt
    assert '"action": "drop"' in prompt
    assert '"decisions":[]' in prompt


def test_parse_decisions_accepts_markdown_wrapped_json():
    decisions = _parse_decisions(
        """
```json
{"decisions":[{"id":"overseas_1","action":"drop","duplicate_of":"domestic_1","reason":"same event","confidence":"high","new_signal":false}]}
```
"""
    )

    assert decisions[0]["id"] == "overseas_1"
    assert decisions[0]["action"] == "drop"
