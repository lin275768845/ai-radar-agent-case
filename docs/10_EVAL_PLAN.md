# 10 Eval Plan

- Project: AI Radar Agent
- Agent Type: evidence-first intelligence and publishing agent
- Status: active
- Last Updated: 2026-06-19
- Source of Truth: tests, `evals/`, runtime artifacts, report lint, brief normalization, Evidence Gate
- Related Files: `evals/*.jsonl`, `tests/`, `report_lint.py`, `brief.py`, `evidence_gate.py`, `event_history.py`, `top_event_audit.py`, `feishu_bot.py`

## Eval Philosophy

AI Radar should be evaluated on source fidelity, time-window correctness, duplicate suppression, stale-rate control, report structure, brief/card reliability, publish safety, and observability.

Current status: partial. The pytest suite is strong, and Phase C adds a Week 2 JSONL eval definition file plus a minimal local static checker. Runtime integration of these evals remains planned.

## Current Coverage

Implemented tests cover:

- Beijing date windows.
- RSS / Bocha / Tavily provider behavior.
- Provider degradation and query budgets.
- Evidence Gate, source quality, event history, final-top dedupe, and top-event audit behavior.
- Report source appendix and `report_lint`.
- Brief JSON parsing, repair, source binding, count matching, and card field quality.
- Feishu docx fallback and bot card behavior.
- Log redaction and GitHub workflow configuration.

Implemented in Phase C:

- `evals/ai_radar_week2_eval_cases.jsonl` with 10 no-external-side-effect case definitions.
- `evals/check_ai_radar_week2_eval_cases.py`, a standard-library static checker for the Week 2 case file and Phase B schemas.

Planned for later phases:

- Metric report for stale rate, duplicate rate, hallucinated citation rate, and source validity.

## Eval Case Catalog

| ID | Type | Status | Case | Expected behavior | Checks | no_external_side_effects |
| --- | --- | --- | --- | --- | --- | ---:|
| `regression_old_news_repeat` | regression | planned | 旧新闻重复: same event appears in recent history and today's recall without strong new signal | Evidence or final top is marked/dropped as old repeated; report/card should not promote as today's core event | `evidence_gate.json`, `event_history_matches.json`, `final_top_dedupe.json`, no repeated top title | Yes |
| `failure_out_of_window_news` | failure | planned | 窗口外新闻: evidence date is outside Beijing natural-day window | Item is dropped or marked out-of-window; not eligible for core top event | Evidence Gate drop reason; top_event_audit out-of-window count | Yes |
| `failure_low_quality_aggregator` | failure | planned | 低质量聚合源: aggregator/reprint source with weak fit | Source is dropped, demoted, or not core-eligible | `source_tier`, `source_fit`, `dropped_low_source_fit_count` | Yes |
| `edge_missing_official_source` | edge | planned | 官方来源缺失: only second/third-party source exists | Event may remain with warning/uncertainty; no fake official source is created | top_event_audit warnings; no invented URL | Yes |
| `failure_llm_old_event_today` | failure | planned | LLM 把旧事件写成今日事件 | report_lint/top_event_audit/history flags catch stale framing; final top dedupe removes when applicable | stale warning, old_repeated count, no publish in eval | Yes |
| `failure_report_url_not_in_evidence` | failure | planned | report 正文 URL 不在 evidence | `report_lint` reports unmatched URL or critical error according to policy | `report_lint.json` unmatched URL fields | Yes |
| `failure_brief_source_ids_unresolved` | failure | planned | brief `source_ids` 无法解析 | Brief keeps item but unresolved IDs do not become fabricated source URLs; warnings/counters record mismatch | `brief_source_ids_unresolved_count`, `sources=[]` where needed | Yes |
| `regression_final_top_duplicate` | regression | planned | final top 重复: same top event appears multiple days or same region duplicate | Duplicate top event is dropped unless strong new signal exists | `final_top_dedupe_dropped_count`, final list uniqueness | Yes |
| `edge_feishu_card_too_long` | edge | planned | 飞书卡片过长: too many/too long top items or why text | Card truncates/splits safely, preserves meaning, avoids bad fragments | bot render metadata, card text quality counters | Yes |
| `golden_provider_fallback_dry_run_no_publish` | golden | planned | provider 失败 fallback / dry-run no publish | Provider failure is audited; remaining evidence can continue; `dry_run` or `output_mode=none` prevents Feishu and bot side effects | provider audit, publish skipped reason, bot skipped reason | Yes |

## Required Eval Record Shape

Status: implemented for `evals/ai_radar_week2_eval_cases.jsonl`; broader eval record migration remains planned.

Each future JSONL case should include:

- `id`
- `type`: `golden`, `failure`, `edge`, or `regression`
- `status`: `planned`, `implemented`, or `disabled`
- `input_ref` or synthetic inline input
- `expected_behavior`
- `checks`
- `no_external_side_effects: true`
- `privacy_notes`

## Acceptance Thresholds

Status: planned.

Initial thresholds for a non-publishing eval/static check:

- 0 fabricated source URLs in sampled eval outputs.
- 0 core events outside the target window unless explicitly marked and justified.
- 0 repeated final top events without strong new signal.
- 0 external publish, bot send, workflow dispatch, or provider write side effects.
- Eval fixtures contain no secrets, webhooks, tokens, private logs, or raw private artifacts.

## Eval Execution Policy

- Eval/static check mode must not call Feishu.
- Eval/static check mode must not trigger GitHub workflow dispatch.
- Eval/static check mode must not call production providers unless explicitly approved.
- Prefer synthetic or sanitized fixtures.
- Do not read private `outputs/` artifacts unless the user explicitly approves a redaction task.

## Current Gaps

- Existing scaffold files remain for future expansion, while `evals/ai_radar_week2_eval_cases.jsonl` is implemented for Week 2.
- A minimal static checker exists for the Week 2 eval case file and Phase B schema JSON.
- `RunManifest` and `ToolCall` schema contracts exist after Phase B, but no runtime-emitted manifest is validated yet.
- Human labeling rubric for top-event quality is planned, not implemented.

## Phase C Delivered Work

- Added 10 Week 2 JSONL cases covering evidence gate, publish gate, tool permission, safety mode, schema contract, observability, redaction, failure handling, eval static check, and emergency stop.
- Added a minimal local checker that validates JSONL shape, required fields, case ids, category coverage, forbidden external actions, `no_external_side_effects`, related docs/schemas, and Phase B schema JSON.
- Checker is local-only and no-publish; it does not import production code, call external APIs, invoke LLMs, trigger Feishu/GitHub/webhooks, or run the production pipeline.
