# 13 Runtime Object Map

- Project: AI Radar Agent
- Agent Type: evidence-first intelligence and publishing agent
- Status: active
- Last Updated: 2026-06-19
- Source of Truth: Phase A docs, current artifacts, schema contracts in `schemas/`
- Related Files: `schemas/run_manifest.schema.json`, `schemas/tool_call.schema.json`, `docs/03_WORKFLOW.md`, `docs/09_GATES_AND_GUARDRAILS.md`, `docs/10_EVAL_PLAN.md`, `docs/11_OBSERVABILITY.md`, `docs/12_RUNBOOK.md`

## Purpose

This map defines the intended runtime objects for standardizing AI Radar as an evidence-first intelligence and publishing agent case.

Phase B implements schema contracts for `RunManifest` and `ToolCall`. Phase C implements 10 local eval case definitions and a minimal static checker. Phase D implements a sanitized simulated demo run, and Phase E adds the portfolio README plus case study draft. These docs and checks do not change runtime behavior and do not imply that the current runtime emits `run_manifest.json`, a tool-call trace artifact, or runtime `EvalResult` artifacts yet.

## Status Vocabulary

- implemented: the object, artifact, or schema exists in the repo or current runtime.
- partial: the object is described by docs/artifacts/tests, but runtime integration, formal schema validation, or durable trace support is incomplete.
- planned: future work for Phase F or later; not implemented by this Phase E task.

## Object Relationship

```text
RunbookMode / SafetyMode
-> RunManifest
   -> ToolCall[]
   -> EvidenceItem[]
   -> GateResult[]
   -> ArtifactRef[]
   -> PublishDecision / PublishAttempt
   -> EvalCase / EvalResult, when running future eval/static checks
```

The manifest should hold redacted summaries and references, not raw secrets, raw private logs, raw HTTP payloads, webhook URLs, cookies, credentials, localStorage dumps, or private notes.

## Runtime Object Inventory

| Object | Purpose | Producer | Consumer | Lifecycle stage | Persistence location | Schema status | Runtime emission status | Validation status | Sensitive-data handling notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `RunManifest` | Run-level evidence, gate, tool, artifact, safety, and publish summary | planned runtime manifest writer | operators, eval checker, portfolio/case-study sanitizer | whole run | planned `outputs/<date>/run_manifest.json` or `runs/<run_id>/run_manifest.json` | implemented: `schemas/run_manifest.schema.json` | planned | planned | Store redacted summaries and refs only; never store secrets, raw logs, webhook URLs, or private artifacts |
| `ToolCall` | Sanitized per-tool invocation metadata | planned runtime manifest writer or tool wrapper | `RunManifest`, future eval/static checker, audit review | per tool/provider/local action | planned manifest `tool_calls[]` or tool-call trace artifact | implemented: `schemas/tool_call.schema.json` | planned | planned | Raw tool inputs are optional and should be replaced by redacted `input_summary`/`output_summary` |
| `EvidenceItem` | Source-bound AI signal candidate used for report generation and audits | implemented recall providers and Evidence Gate | report generator, report lint, brief, top event audit | recall and evidence gating | implemented `outputs/<date>/evidence.json`; summarized in planned manifest | partial: described in docs/current artifacts, no dedicated formal schema in Phase B | implemented as current artifact | partial via tests and gates | May include source URLs/snippets; do not commit or share unsanitized artifacts |
| `GateResult` | Records pass/warn/fail/block decisions for safety and quality gates | implemented gates; planned manifest collector | runbook, Summary, eval checker, release review | after each gate | implemented gate artifacts such as `evidence_gate.json`, `report_lint.json`; planned manifest `gates[]` | partial: embedded in RunManifest schema `$defs` | partial | partial | Store counters and summaries; redact sensitive text in failure messages |
| `ArtifactRef` | Lightweight reference to a run artifact without copying content | current runtime artifacts; planned manifest collector | operators, case-study sanitizer, eval checker | artifact write and final summary | implemented `outputs/<date>/...`; planned manifest `artifacts[]` | partial: embedded in RunManifest and ToolCall schemas | partial | partial | Use relative/logical paths; do not include signed URLs, tokens, or private absolute paths |
| `PublishDecision` | Whether publish/bot side effects were allowed, skipped, blocked, or attempted | implemented publish/bot logic; planned manifest collector | operators, approval review, privacy gate | pre-publish and post-publish | implemented `publish_result.json` and Summary fields; planned manifest section | partial: embedded in RunManifest schema | partial | partial | Feishu URLs may be private; record URL status or redacted summary when needed |
| `PublishAttempt` | Concrete external publish/send attempt and outcome | implemented Feishu docx/Drive/bot code | runbook, post-run audit | publish/bot stage | implemented `publish_result.json` plus bot metadata; planned external side-effect entries | partial | partial | partial | Must mark external side effects explicitly and avoid exposing webhook or credential values |
| `EvalCase` | Synthetic or sanitized test case for golden/failure/edge/regression checks | implemented Phase C eval authoring | eval/static checker | pre-change and regression validation | implemented `evals/ai_radar_week2_eval_cases.jsonl` | partial: JSONL contract implemented, standalone schema planned | implemented as static definitions | implemented for case-file shape; runtime integration planned | Use sanitized summaries and synthetic inputs; never use raw private run outputs |
| `EvalResult` | Local no-external-side-effect checker output | implemented Phase C static checker for definition validation; runtime eval result planned | release review, case-study evidence | eval execution | checker stdout only for Phase C; planned local result artifact later | planned | planned | partial: checker validates definitions and schema JSON, not runtime outputs | Should contain aggregate outcomes and failure summaries only |
| `DemoRun` | Sanitized local simulation that shows expected artifact shape without external side effects | implemented Phase D demo authoring | portfolio review, case study, future demo polish | demo review | implemented `demo_run/` | partial: conceptually aligned to RunManifest and ToolCall schemas | implemented as simulated artifacts | partial: JSON/JSONL static checks only | Deterministic mock data only; not production output or live data |
| `RunbookMode` | Operator-facing mode such as dry-run, skip-llm, output-mode none, eval-only, emergency stop | implemented CLI/config/docs; planned manifest summary | operators and future checker | before run | docs/runbook; planned `safety_mode` in RunManifest | partial: represented by `safety_mode` in RunManifest schema | partial | partial | Mode summaries must not include `.env` values, tokens, or private config values |
| `SafetyMode` | Machine-readable safety posture controlling external side effects | current flags/settings; planned manifest writer | Publish Gate, Bot Gate, eval/static checker | before external actions | planned RunManifest `safety_mode` | implemented in RunManifest schema | partial | planned | Record booleans such as `publish_allowed` and `bot_send_allowed`; do not record secret values |

## Contract Boundaries

- Implemented in Phase B: `schemas/run_manifest.schema.json`, `schemas/tool_call.schema.json`, and this runtime object map.
- Partial after Phase B: docs describe `EvidenceItem`, `GateResult`, `ArtifactRef`, `PublishDecision`, `PublishAttempt`, `RunbookMode`, and `SafetyMode`, but not all have standalone schema files or manifest emission.
- Implemented in Phase C: 10 local eval case definitions and a minimal static checker for case-file and Phase B schema validation.
- Implemented in Phase D: sanitized simulated demo artifacts under `demo_run/`.
- Implemented in Phase E: portfolio README and Week 2 case study draft.
- Planned after Phase E: runtime generation of `RunManifest`, runtime `ToolCall` traces, schema validation gates for emitted manifests, dashboard/screenshots, external publishing review artifacts, and further portfolio polish.

## Phase Alignment

| Phase | Status | Scope |
| --- | --- | --- |
| Phase B: schema contracts and runtime object map | implemented | Defines RunManifest and ToolCall schema contracts; documents object relationships |
| Phase C: eval cases and static checker | implemented | Adds JSONL eval cases and a local no-external-side-effect checker |
| Phase D: sanitized demo run | implemented | Produces sanitized simulated demo artifacts and output bundle |
| Phase E: README portfolio rewrite and case study draft | implemented | Turns validated evidence into portfolio-facing narrative |
| Phase F: Obsidian pattern notes | planned | Captures reusable patterns without installing global rules automatically |

## Non-goals For Phase B

- No runtime behavior change.
- No production pipeline run.
- No Feishu, webhook, GitHub workflow dispatch, or external publish action.
- No prompt-source change.
- No runtime eval execution or demo artifact creation.
- No demo artifact creation.
- No README or portfolio rewrite.
