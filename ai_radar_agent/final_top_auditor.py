from __future__ import annotations

import json
import logging
import re
from typing import Any

from openai import OpenAI

from .config import Settings
from .event_history import (
    EventHistoryMatchAudit,
    FinalTopDedupeAudit,
    HistoryEvent,
    apply_final_top_llm_decisions,
    select_history_context_events,
)

logger = logging.getLogger(__name__)


def audit_final_top_with_llm(
    settings: Settings,
    brief: dict[str, object],
    history_events: list[HistoryEvent],
    audit: FinalTopDedupeAudit,
) -> tuple[dict[str, object], FinalTopDedupeAudit, dict[str, object]]:
    payload: dict[str, object] = {
        "enabled": bool(getattr(settings, "final_top_llm_audit_enabled", True)),
        "attempted": False,
        "succeeded": False,
        "failed": False,
        "decisions": [],
        "dropped_titles": [],
        "error": "",
        "repair_attempted": False,
        "repair_succeeded": False,
    }
    if not payload["enabled"] or _top_count(brief) < 2:
        return brief, audit, payload

    audit.llm_audit_attempted = True
    payload["attempted"] = True
    try:
        auditor = FinalTopLLMAuditor(settings)
        raw_response = auditor.call(brief, history_events)
        try:
            decisions = _parse_decisions(raw_response)
        except Exception:
            payload["repair_attempted"] = True
            raw_response = auditor.repair(raw_response)
            decisions = _parse_decisions(raw_response)
            payload["repair_succeeded"] = True
        updated, audit = apply_final_top_llm_decisions(brief, decisions, audit)
        audit.llm_audit_succeeded = True
        payload.update(
            {
                "succeeded": True,
                "decisions": decisions,
                "dropped_titles": audit.llm_audit_dropped_titles,
            }
        )
        return updated, audit, payload
    except Exception as exc:  # noqa: BLE001
        message = str(exc)[:300]
        logger.warning("Final top LLM audit skipped after failure: %s", message)
        audit.llm_audit_failed = True
        audit.llm_audit_error = message
        payload.update({"failed": True, "error": message})
        return brief, audit, payload


class FinalTopLLMAuditor:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = OpenAI(api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url)

    def call(self, brief: dict[str, object], history_events: list[HistoryEvent]) -> str:
        prompt = _build_prompt(
            brief,
            history_events,
            max_history_events=int(getattr(self.settings, "final_top_llm_audit_max_history_events", 30) or 30),
        )
        logger.info("Calling DeepSeek final top audit model=%s", self.settings.deepseek_model)
        response = self.client.chat.completions.create(
            model=self.settings.deepseek_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是AI日报最终Top去重审计器。只判断当前Top事件是否与历史Top或同批次Top重复；"
                        "不要改写内容，不要新增事件，只输出JSON。"
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=int(getattr(self.settings, "final_top_llm_audit_max_tokens", 1200) or 1200),
        )
        return response.choices[0].message.content or ""

    def repair(self, raw_response: str) -> str:
        logger.info("Repairing DeepSeek final top audit JSON")
        response = self.client.chat.completions.create(
            model=self.settings.deepseek_model,
            messages=[
                {
                    "role": "system",
                    "content": "你只负责把用户给出的内容修复成合法JSON对象，不要新增任何决策。",
                },
                {
                    "role": "user",
                    "content": (
                        "请把下面内容修复成严格 JSON，格式必须为 "
                        '{"decisions":[{"id":"...","action":"drop","duplicate_of":"...",'
                        '"reason":"...","confidence":"high","new_signal":false}]}。'
                        "只保留 action=drop 的决策；如果没有可保留决策，返回 {\"decisions\":[]}。\n\n"
                        f"{str(raw_response or '')[:4000]}"
                    ),
                },
            ],
            temperature=0,
            max_tokens=int(getattr(self.settings, "final_top_llm_audit_max_tokens", 1200) or 1200),
        )
        return response.choices[0].message.content or ""


def _build_prompt(
    brief: dict[str, object],
    history_events: list[HistoryEvent],
    *,
    max_history_events: int,
) -> str:
    current = _current_top_items(brief)
    history = [
        {
            "date": item.date,
            "region": item.region,
            "priority": item.priority,
            "title": item.title,
            "summary": item.summary,
            "source_labels": item.source_labels[:2],
        }
        for item in select_history_context_events(
            history_events,
            EventHistoryMatchAudit(date=str(brief.get("date") or ""), lookback_days=5),
            max_events=max_history_events,
        )
    ]
    data = {"current_top": current, "recent_history_top": history}
    return f"""
请审计 current_top 中是否有应从最终Top删除的重复事件。

规则：
1. 只在“高置信重复”时输出该事件，action 必须为 drop。
2. 如果只是同一公司但事件不同，必须 keep。
3. 如果有今天新增官方披露、新数据、新价格、新上线、新采用度信号，必须 keep，并标记 new_signal=true。
4. 如果不确定，必须 keep。
5. 可以识别同批次国内/海外重复，也可以识别与 recent_history_top 的语义重复。
6. 不要输出 keep 决策；没有要删除的重复事件时，输出 {{"decisions":[]}}。
7. 只输出 JSON，不要 Markdown。

输出格式：
{{
  "decisions": [
    {{
      "id": "domestic_1",
      "action": "drop",
      "duplicate_of": "history title or current id/title",
      "reason": "short reason",
      "confidence": "high",
      "new_signal": false
    }}
  ]
}}

输入：
{json.dumps(data, ensure_ascii=False)}
""".strip()


def _current_top_items(brief: dict[str, object]) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    for region, key in (("domestic", "domestic_top"), ("overseas", "overseas_top")):
        items = brief.get(key)
        if not isinstance(items, list):
            continue
        for index, item in enumerate(items, 1):
            if not isinstance(item, dict):
                continue
            sources = item.get("sources") if isinstance(item.get("sources"), list) else []
            output.append(
                {
                    "id": f"{region}_{index}",
                    "region": region,
                    "priority": item.get("priority") or "",
                    "title": item.get("title") or item.get("card_title") or "",
                    "card_title": item.get("card_title") or "",
                    "why": item.get("card_why") or item.get("why") or "",
                    "source_labels": [
                        str(source.get("label") or source.get("title") or "")
                        for source in sources
                        if isinstance(source, dict)
                    ][:2],
                }
            )
    return output


def _parse_decisions(raw_response: str) -> list[dict[str, object]]:
    parsed = _parse_json_object(raw_response)
    decisions = parsed.get("decisions")
    if not isinstance(decisions, list):
        raise ValueError("final top audit response missing decisions")
    return [item for item in decisions if isinstance(item, dict)]


def _parse_json_object(raw_response: str) -> dict[str, Any]:
    text = str(raw_response or "").strip()
    if not text:
        raise ValueError("empty final top audit response")
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.S)
        if not match:
            raise
        parsed = json.loads(match.group(0))
    if not isinstance(parsed, dict):
        raise ValueError("final top audit response is not an object")
    return parsed


def _top_count(brief: dict[str, object]) -> int:
    return sum(
        len(brief.get(key) or []) if isinstance(brief.get(key), list) else 0
        for key in ("domestic_top", "overseas_top")
    )
