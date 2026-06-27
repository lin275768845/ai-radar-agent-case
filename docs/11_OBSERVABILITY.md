# 11 Observability

- Project: AI Radar Agent
- Agent Type: Intelligence / research / daily report publishing agent
- Status: Active
- Last Updated: 2026-06-27
- Owner: Unknown
- Source of Truth: ai_radar_agent/__main__.py, utils.py, report_lint.py, brief.py, feishu_result.py, feishu_bot.py, evidence_gate.py, event_history.py, top_event_audit.py
- Related Files: ai_radar_agent/__main__.py, ai_radar_agent/utils.py, ai_radar_agent/report_lint.py, ai_radar_agent/brief.py, ai_radar_agent/feishu_result.py, ai_radar_agent/feishu_bot.py, ai_radar_agent/evidence_gate.py, ai_radar_agent/event_history.py, ai_radar_agent/top_event_audit.py, outputs/

## AS-IS 当前实现

### Observability Goal

Make each run explainable enough to debug source recall, LLM/report issues, Feishu publishing, bot sending, and safety gates without exposing secrets.

### Current Logging

Runtime uses Python logging. `setup_logging` keeps third-party HTTP libraries at WARNING even in verbose mode. GitHub Step Summary records many run fields when `GITHUB_STEP_SUMMARY` exists.

### Run ID

No first-class `run_id` object exists. GitHub run metadata is captured from environment variables such as `GITHUB_RUN_ID`, `GITHUB_SHA`, `GITHUB_REF`, and run URL when available.

### Run Manifest

Formal `RunManifest` and `ToolCall` schema contracts exist under `schemas/`. The production runtime does not yet emit a first-class `run_manifest.json` or `tool_calls.jsonl`; current observability is still distributed across GitHub metadata, local output artifacts, and structured JSON audit files.

### Logs

Logs are process logs plus GitHub Actions logs. Local artifacts under `outputs/<date>/` carry structured JSON for evidence, Evidence Gate, event history matching, final Top dedupe/audit, lint, brief, publish result, and bot outcomes.

### Trace

No distributed trace exists. Step-level trace is implicit in artifacts and GitHub Summary fields.

### Redaction

Runtime logging is designed not to emit full prompts, evidence payloads, LLM payloads, headers, tokens, webhooks, or secrets. Summary/error bodies should remain truncated and safe.

### Error Records

- Provider errors in `RecallAudit`.
- Report lint errors in `report_lint.json`.
- Brief parse/repair errors in `brief.json`.
- Feishu errors in `FeishuResult`.
- Bot errors in `BotResult`.

### Audit Records

- `evidence.md` includes recall/provider audit.
- `report_lint.json` includes warnings/errors/critical errors.
- `evidence_gate.json`, `event_history_matches.json`, `final_top_dedupe.json`, `final_top_llm_audit.json`, and `top_event_audit.json` record v5.2 audit details.
- GitHub Summary includes many audit counters.

### Current Artifact Map

| Artifact | Status | Purpose | Handling Notes |
|---|---|---|---|
| `evidence.json` | implemented | Structured evidence records passed into later stages | Treat as private run artifact before review |
| `evidence.md` | implemented | Human-readable recall/provider audit | May include URLs and source summaries |
| `evidence_gate.json` | implemented | Evidence Gate counts and decisions | Safe to share only after review/redaction |
| `evidence_dropped.md` | implemented | Dropped evidence reasons | May include URLs; review before sharing |
| `AI_radar_<date>.md` | implemented | Full generated radar report | Do not publish/share without review |
| `report_lint.json` | implemented | Report quality warnings/errors | Inspect before promotion |
| `brief.json` | implemented | Structured card/report brief | May include source URLs and publish metadata |
| `brief.md` | implemented | Human-readable brief | Review before sharing |
| `final_top_dedupe.json` | implemented | Final Top dedupe decisions | May include titles/source refs |
| `final_top_llm_audit.json` | implemented | LLM duplicate-audit decisions | May include event titles/history context |
| `top_event_audit.json` | implemented | Top event source/date quality audit | Good case-study candidate after sanitization |
| `publish_result.json` | implemented | Feishu publish/canonical URL result | Private; may include Feishu URLs |
| GitHub Summary / artifact bundle | implemented | Operational summary and downloadable artifacts | Must remain redacted |
| `RunManifest` | schema implemented; runtime planned | Unified run trace with steps/gates/tool calls/artifacts | Contract exists; runtime artifact not emitted yet |
| `ToolCall` trace | schema implemented; runtime planned | Sanitized per-tool call metadata | Contract exists; runtime trace not emitted yet |

### Cost Records

No explicit cost record exists. Search query counts are tracked, but token usage and provider costs are not persisted.

### Debug Workflow

Safe debug modes:

- `--skip-llm`
- `--dry-run`
- `--date YYYY-MM-DD --dry-run --output-mode none`
- `--skip-llm`
- `OUTPUT_MODE=none`

### Current Gaps

- No runtime-emitted `RunManifest`.
- No runtime-emitted `ToolCall` trace artifact.
- No durable observability store outside GitHub artifacts/local outputs.
- No formal token/cost ledger.
- No dashboard.

### Proposed Run Manifest

Status: schema implemented; runtime generation planned. Do not record real secrets, webhooks, tokens, private logs, full prompts, full evidence payloads, or private artifact contents.

```json
{
  "run_id": "github-run-id-or-local-uuid",
  "trigger": "workflow_dispatch",
  "input_summary": {
    "date": "YYYY-MM-DD",
    "dry_run": true,
    "skip_llm": false,
    "output_mode": "none",
    "production_ref": "main"
  },
  "steps": [
    {"name": "recall", "status": "ok", "started_at": "...", "ended_at": "..."}
  ],
  "llm_calls": [
    {"name": "report_generation", "model": "deepseek-v4-pro", "status": "ok", "prompt_ref": "prompts/radar_prompt.md"}
  ],
  "tool_calls": [
    {"tool": "bocha", "queries_used": 10, "status": "ok"}
  ],
  "gates": [
    {"gate": "report_lint", "status": "warn", "errors_count": 0, "critical_errors_count": 0}
  ],
  "outputs": [
    {"type": "report", "path": "outputs/YYYY-MM-DD/AI_radar_YYYY-MM-DD.md"}
  ],
  "errors": [],
  "cost": {
    "search_queries_used": 0,
    "llm_prompt_tokens": null,
    "llm_completion_tokens": null
  },
  "status": "ok"
}
```

### Failure Reading Order

1. GitHub Summary, if available.
2. `evidence.md` and provider audit.
3. `evidence_gate.json` and `evidence_dropped.md`.
4. `report_lint.json`.
5. `brief.json` and `brief.md`.
6. `final_top_dedupe.json`, `final_top_llm_audit.json`, and `top_event_audit.json`.
7. `publish_result.json`, only if publish was allowed.
8. Bot result/Summary fields, only if bot send was allowed.

### Redaction Checklist

Before sharing or committing any artifact, confirm it does not expose:

- Secrets, `.env` values, tokens, cookies, webhook URLs, private keys, or credentials.
- Private logs or full HTTP payloads.
- Feishu document URLs unless intentionally public-safe.
- Full prompts, full evidence payloads, or private source dumps.
- Private business notes or unreviewed generated claims.

## GAPS 当前缺口

- `RunManifest` / `ToolCall` contracts exist, but runtime emission is still planned.
- No token/cost telemetry.
- No durable observability store outside GitHub artifacts/local outputs.
- Some README observability claims may be ahead of current code and should be verified before relying on them.

## TO-BE 后续建议

- Add `outputs/<date>/run_manifest.json`.
- Record sanitized LLM call metadata without full prompts by default.
- Add cost fields once API responses expose token usage.
- Add a runbook section for reading Summary and artifacts in failure order.
