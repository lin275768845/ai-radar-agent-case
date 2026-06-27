# 07 Skills

- Project: AI Radar Agent
- Agent Type: Intelligence / research / daily report publishing agent
- Status: Active
- Last Updated: 2026-06-11
- Owner: Unknown
- Source of Truth: Repository modules and tests
- Related Files: ai_radar_agent/collector.py, ai_radar_agent/llm.py, ai_radar_agent/brief.py, ai_radar_agent/report_lint.py, ai_radar_agent/feishu_docx.py, ai_radar_agent/feishu_bot.py, tests/

## AS-IS 当前实现

### Skill Philosophy

In this project, a skill is a stable capability package with inputs, procedure, outputs, failure behavior, and tests. A standard `skills/` scaffold exists, but the current runtime does not load skill files; several Python modules behave like implemented skills.

### Skill Inventory

| Skill | Status | Current Code Location | Purpose | Inputs | Outputs | Failure Policy | Eval Coverage |
|---|---|---|---|---|---|---|---|
| Beijing Day Window | Implemented | `dates.py` | Build exact Asia/Shanghai natural-day window | target date or now | `TimeWindow` | invalid date raises | `tests/test_dates.py` |
| Recall Evidence | Implemented | `collector.py`, `fetchers/*` | Gather broad public evidence | settings, sources, window | evidence, recall audit | provider failures degrade/record | `tests/test_collector.py`, `test_rss.py`, `test_bocha_search.py`, `test_tavily_search.py` |
| Evidence Markdown Builder | Implemented | `utils.py` | Render evidence and provider audit for LLM | evidence, audit | Markdown context | no special failure policy | `tests/test_rss.py`, `test_collector.py` |
| Radar Report Generation | Implemented | `llm.py`, `prompts/radar_prompt.md` | Generate full AI radar | window, evidence Markdown | report Markdown | retries then raises | indirectly in `tests/test_main.py` via fakes |
| Report Source Appendix | Implemented | `report.py` | Ensure report has source URLs | report, evidence | report with appendix if needed | no-op if URLs/sources missing | `tests/test_report.py` |
| Report Lint | Implemented | `report_lint.py` | Detect structure/source/placeholder issues | report, evidence | lint result | policy decides blocking | `tests/test_report_lint.py`, `test_main.py` |
| Brief Generation and Repair | Implemented | `brief.py` | Generate card-ready JSON | report, audit, evidence | normalized brief | repair, salvage, fallback | `tests/test_brief.py` |
| Source Binding | Implemented | `brief.py` | Resolve LLM `source_ids` to evidence URLs | brief raw, evidence | `sources` arrays | drop/empty when unsafe | `tests/test_brief.py` |
| Feishu Docx Publish | Implemented | `feishu_docx.py`, `feishu.py` | Publish report as Feishu native docx | report, credentials | `FeishuResult` | fallback to Drive MD | `tests/test_feishu_docx.py`, `test_feishu.py` |
| Evidence Gate | Implemented | `evidence_gate.py`, `source_quality.py` | Filter/mark stale, low-quality, duplicate, or weak-source evidence | raw evidence, window, history | filtered evidence and gate audit | degrade with audit where possible | `tests/test_evidence_gate.py` |
| Event History / Final Top Dedupe | Implemented | `event_history.py` | Reduce repeated Top events across a 5-day window | brief, history state | updated brief and dedupe audit | preserve new-signal events | `tests/test_event_history.py`, `tests/test_main.py` |
| Final Top LLM Audit | Implemented | `final_top_auditor.py` | Review high-confidence duplicate final Top events | brief, history context | audit decisions | non-blocking on failure | `tests/test_final_top_auditor.py` |
| Feishu Bot Cards | Implemented | `feishu_bot.py` | Render/send group card(s) | brief, webhook | `BotResult` | skip/fallback/record errors | `tests/test_feishu_bot.py` |
| Run Manifest | Proposed | n/a | Trace full run decisions | run metadata | manifest JSON | block if invalid | No coverage |
| Formal Evals | Proposed | n/a | Evaluate source/report quality | golden cases | metrics | fail threshold | No coverage |

### Current Implemented Skills

Implemented skills are module-level capabilities rather than standalone skill folders.

### Proposed Skills

- `run_manifest_recording`
- `source_quality_eval`
- `cross_run_idempotency`
- `production_ref_validation`
- `formal_event_history_eval`

### Skill Name / Purpose / When to Use

Use existing module skills for normal daily runs. Proposed skills should only be implemented as explicit future tasks.

### Inputs

Inputs are CLI args, env settings, source config, prompt file, evidence, report, and Feishu settings.

### Outputs

Outputs are artifacts, reports, briefs, Feishu publish results, bot results, and summaries.

### Procedure

Each implemented skill is invoked by `ai_radar_agent/__main__.py` in workflow order.

### Failure Policy

Failure policy is layered: provider degradation, LLM raises, lint policy, Feishu fallback, bot non-blocking errors.

### Eval Cases

Current tests are regression tests, not formal eval cases. The `evals/` directory contains scaffold JSONL placeholders only; they are not wired into CI or runtime.

### Status

Core runtime skills are implemented as Python modules. Formal skill loading/packaging is not implemented.

## GAPS 当前缺口

- `skills/` exists as scaffold only.
- No machine-readable skill manifests are used by runtime.
- No real golden eval cases mapped to skills.
- Evidence/history/final-top audit skills are implemented in code but not yet backed by formal eval datasets.

## TO-BE 后续建议

- Keep skills as code modules unless repeated operational use needs formal packaging.
- Add eval IDs to tests/docs for source quality and report quality.
- Avoid creating a `skills/` abstraction until it removes real maintenance complexity.
