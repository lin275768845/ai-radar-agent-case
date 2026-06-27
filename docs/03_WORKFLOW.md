# 03 Workflow

- Project: AI Radar Agent
- Agent Type: evidence-first intelligence and publishing agent
- Status: active
- Last Updated: 2026-06-19
- Owner: project owner
- Source of Truth: repository code, `README.md`, `.github/workflows/daily.yml`, tests
- Related Files: `ai_radar_agent/__main__.py`, `collector.py`, `evidence_gate.py`, `event_history.py`, `llm.py`, `report_lint.py`, `brief.py`, `final_top_auditor.py`, `top_event_audit.py`, `feishu_docx.py`, `feishu_bot.py`

## Workflow Overview

AI Radar is an evidence-first intelligence and publishing agent. It should turn public AI signals into a source-bound daily radar report, then publish only when an explicit trigger and publish controls allow it.

Current production-style flow:

```text
workflow_dispatch / CLI
-> Beijing day window
-> RSS / Bocha / Tavily recall
-> Evidence Gate + history
-> report
-> report_lint
-> brief
-> final top dedupe / LLM audit / top event audit
-> Feishu publish or dry-run
-> bot card
-> artifacts / Summary
```

## Stage Map

| Stage | Status | Input | Output | Artifact | Gate |
| --- | --- | --- | --- | --- | --- |
| Trigger: `workflow_dispatch` / CLI | implemented | GitHub workflow inputs or CLI args | Parsed settings and requested date | GitHub run metadata when available | Input/date gate |
| Beijing day window | implemented | Target date or blank date | `TimeWindow` for Asia/Shanghai natural day | Summary fields; date-specific output path | Time window gate |
| RSS recall | implemented | `config/sources.yaml`, target window | RSS evidence items and RSS audit | `evidence.json`, `evidence.md` | Provider degradation gate; Evidence Gate |
| Bocha recall | implemented | Query baskets, target window, configured key | Search evidence items and provider audit | `evidence.json`, `evidence.md` | Tool permission gate; provider degradation gate |
| Tavily recall | implemented | Query baskets, target window, enabled flag, configured key | Optional search evidence items and provider audit | `evidence.json`, `evidence.md` | Cost gate; provider degradation gate |
| Evidence dedupe and cap | implemented | Raw evidence list | Unique capped evidence list | `evidence.json` | Dedupe gate |
| Evidence Gate + history | implemented | Raw evidence, source quality config, event history | Filtered/marked evidence and dropped evidence audit | `evidence_gate.json`, `evidence_dropped.md`, `event_history_matches.json`, `event_history_context.md` | Evidence Gate; history gate; privacy gate |
| Report generation | implemented | `prompts/radar_prompt.md`, target window, filtered evidence context | Markdown radar report | `AI_radar_<date>.md` | Prompt source gate; source URL guardrail |
| Report source appendix | implemented | Report Markdown and evidence | Report with fallback source appendix when needed | `AI_radar_<date>.md` | Source URL guardrail |
| `report_lint` | implemented | Report Markdown and evidence | Lint warnings/errors/critical errors | `report_lint.json` | report_lint gate |
| Brief generation and repair | implemented | Report, audit, evidence catalog | Normalized brief data and brief Markdown | `brief.json`, `brief.md` | Brief schema/source_ids normalization gate |
| Final top dedupe | implemented | `brief.json`, recent history, evidence | Final top list with repeated events removed or marked | `final_top_dedupe.json` | history / dedupe gate |
| Final top LLM audit | implemented | Final top candidates and history context | LLM duplicate-review decisions when enabled | `final_top_llm_audit.json` | final_top_llm_audit gate |
| Top event audit | implemented | Final `brief.json`, evidence, history | Source/date/quality audit for top events | `top_event_audit.json` | top_event_audit gate |
| Feishu publish or dry-run | implemented | Report file, settings, publish flags | Feishu docx/MD result or skipped dry-run result | `publish_result.json` | Publish Gate; privacy/redaction gate |
| Bot card send | implemented | `brief.json`, doc URL, bot settings | Feishu bot result or skipped result | Summary fields; bot result metadata | Bot Gate; Publish Gate |
| Artifacts / GitHub Summary | implemented | All run outputs and audit results | Local artifacts and GitHub Step Summary | `outputs/<date>/...`, GitHub artifact bundle | Observability gate; privacy/redaction gate |
| Formal RunManifest | planned | Sanitized run steps, gates, tool calls, artifact refs | `RunManifest` object | Planned `run_manifest.json` | Future run manifest gate |
| ToolCall trace artifact | planned | Sanitized tool-call metadata | `ToolCall` records | Planned tool-call trace or manifest section | Future ToolCall trace gate |

## State Transitions

Current runtime state is implicit in artifacts rather than a formal state machine.

```text
triggered
-> settings_loaded
-> window_ready
-> evidence_recalled
-> evidence_gated
-> report_generated
-> report_linted
-> brief_ready
-> final_top_audited
-> publish_skipped_or_completed
-> summary_written
```

Status: partial. The transitions are visible in code paths and artifacts, but no formal `RunManifest` records every transition yet.

## Current Artifacts

Implemented artifacts include:

- `outputs/<date>/evidence.json`
- `outputs/<date>/evidence.md`
- `outputs/<date>/evidence_gate.json`
- `outputs/<date>/evidence_dropped.md`
- `outputs/<date>/AI_radar_<date>.md`
- `outputs/<date>/report_lint.json`
- `outputs/<date>/brief.json`
- `outputs/<date>/brief.md`
- `outputs/<date>/final_top_dedupe.json`
- `outputs/<date>/final_top_llm_audit.json`
- `outputs/<date>/top_event_audit.json`
- `outputs/<date>/publish_result.json`
- GitHub Summary / artifact bundle when running in GitHub Actions

## Safe Workflow Modes

| Mode | Status | External side effect? | Use |
| --- | --- | ---:| --- |
| `--skip-llm` | implemented | No report/publish side effect | Evidence-only recall debugging |
| `--dry-run` | implemented | No Feishu publish or bot send | Local artifact generation without publishing |
| `output_mode=none` | implemented | No Feishu publish | GitHub/local validation that should not publish |
| Static eval/check mode | planned | No | Future JSONL/static eval validation without Feishu or workflow dispatch |

## Human Review Points

Status: partial.

Human approval is currently operational rather than represented as a formal artifact:

- Choosing a production GitHub ref.
- Triggering a production workflow.
- Enabling Feishu publish or bot send.
- Changing prompts, schemas, workflow behavior, provider configuration, or publish behavior.
- Cleaning up or deleting any remote artifact.

## Current Gaps

- No formal `RunManifest`.
- No `ToolCall` trace artifact.
- Approval is implicit in trigger/ref choice rather than recorded in a run artifact.
- Cross-run publish idempotency is partial.
- Formal eval/static check mode is planned but not implemented in this Phase A task.

## P2 Future Work: Read-only Artifact Workbench

Status: planned.

A future read-only Artifact Workbench may inspect sanitized artifacts and summaries. It must not trigger Feishu, GitHub workflow dispatch, provider calls, or production writes.
