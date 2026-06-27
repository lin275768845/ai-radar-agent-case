# 09 Gates And Guardrails

- Project: AI Radar Agent
- Agent Type: evidence-first intelligence and publishing agent
- Status: active
- Last Updated: 2026-06-19
- Source of Truth: public docs, schemas, evals, sanitized demo artifacts, and
  private production runtime files.
- Public Mirror Note: production prompts, full tests, provider integrations,
  Feishu implementation, and production artifacts are omitted from this curated
  mirror.
- Related Files: selected public code slices, schemas, evals, and sanitized
  demo artifacts; private production implementation files are omitted.

## Guardrail Philosophy

AI Radar relies on layered gates: date and input checks before recall; Evidence Gate and source quality before report generation; report lint and brief normalization after LLM output; final top dedupe/audits before card/history; publish and privacy gates before external side effects.

## Gate Inventory

| Gate | Status | Trigger timing | Pass condition | Failure handling | Blocking? | Evidence / code |
| --- | --- | --- | --- | --- | ---:| --- |
| Input/date gate | implemented in private runtime | CLI/settings load | Args parse; date is valid or blank | Raise or stop | Yes | `dates.py`, private runtime tests |
| Time window gate | implemented | Date-window creation and provider filtering | Exact Beijing natural-day window | Invalid date raises; provider date gaps audited best-effort | Yes for date, partial for provider metadata | `dates.py`, provider audit |
| Evidence Gate | implemented in private runtime | After recall | Evidence exists and low-quality/stale/duplicate items are filtered or marked | No evidence blocks; dropped evidence recorded | Yes for no evidence | evidence gate artifacts |
| Source quality gate | implemented in private runtime | Evidence Gate and top event audit | Source tier/fit applied; low-quality sources filtered or warned | Drop, demote, or warn | Partial | source-quality design and audit artifacts |
| Provider degradation / fallback gate | implemented in private runtime | During recall | Provider succeeds or failure is recorded without hiding outage | Warn/continue unless no evidence remains | No unless all evidence fails | provider audit |
| Bocha provider control gate | implemented | Workflow/Worker dispatch before recall | `bocha_enabled=true` is selected for the run; omitted or false resolves `BOCHA_ENABLED=false` | Bocha stays disabled; RSS can continue | Yes for Bocha provider access | `.github/workflows/daily.yml`, `cloudflare/ai-radar-trigger/src/index.js` |
| Source URL guardrail | implemented in private runtime | Report and brief generation | URLs must come from evidence or allowed report/Feishu URLs | `report_lint` errors; brief drops unsafe sources | Policy-dependent | report-lint and brief artifacts |
| History / dedupe gate | implemented in private runtime | Evidence Gate and final top processing | Recent repeated events are marked/dropped unless strong new signal exists | Drop, mark, or allow with audit | Partial | event-history and final-top artifacts |
| report_lint gate | implemented in private runtime | After report generation | Required sections, source URLs, no placeholders, size/shape checks | Warn, block bot, or strict raise based on policy | Policy-dependent | `report_lint.json` |
| Brief source_ids normalization gate | implemented in private runtime | Brief generation/repair | LLM source IDs resolve to evidence records; unsafe/unresolved sources do not become fabricated URLs | Repair, salvage, fallback, warn | Partial | `brief.json` |
| final_top_dedupe gate | implemented in private runtime | After brief | Repeated final top events are removed unless strong new signal exists | Drop repeated top and related bullets | Partial | `final_top_dedupe.json` |
| final_top_llm_audit gate | implemented in private runtime | After deterministic final top dedupe when enabled | High-confidence duplicate decisions only | Audit failure does not block publish by default | Non-blocking | `final_top_llm_audit.json` |
| top_event_audit gate | implemented in private runtime | After final brief top events | Top events have acceptable source/date quality or warnings | Warn and record counts | Non-blocking | `top_event_audit.json` |
| Publish Gate | implemented in private runtime | Before Feishu docx/Drive publish | Not `dry_run`, not `output_mode=none`, publish config available, policy permits | Skip, fallback, or record failure | Yes/partial depending mode | `publish_result.json` |
| Bot Gate | implemented in private runtime | Before Feishu bot webhook | Send flag, webhook, lint policy, doc link/card payload acceptable | Skip or record bot failure | Usually non-blocking | Summary fields |
| Privacy / redaction gate | partial | Logs, Summary, artifacts, completion reports | No secrets, webhook values, full payloads, private logs, or raw private artifacts exposed | Redact/truncate/stop manually | Partial | schemas, evals, and redaction policy |
| Approval gate | partial | Production trigger/ref/publish decision | Human selected ref/inputs externally | No formal approval artifact | Partial | GitHub/Feishu ops, runbook |
| Future RunManifest gate | planned | End of run / before release acceptance | Sanitized run manifest records steps, gates, ToolCall records, artifacts, approval state | Block standardization acceptance if missing | Planned | Phase B schema contracts; runtime gate planned |
| Future eval gate | planned | Before prompt/schema/gate changes | JSONL eval/static check passes without external side effects | Keep change as draft | Planned | Future eval checker |

## Blocking Rules

- Date/input failures block.
- No evidence blocks.
- Bocha is disabled unless the run explicitly passes `bocha_enabled=true`.
- Strict `report_lint` can block when configured.
- Publish is blocked by `dry_run`, `skip_llm`, `output_mode=none`, missing required config, or publish policy.
- Bot send is blocked by `dry_run`, `skip_llm`, missing webhook, send flag, output mode, or lint policy.

## Non-blocking But Recorded

- Single provider degradation when other evidence remains.
- Feishu docx import fallback to Drive Markdown.
- Bot webhook failure after report publish.
- final_top_llm_audit failure, unless future policy changes.
- top_event_audit warnings.

## Current Gaps

- No runtime `RunManifest` gate.
- No `ToolCall` trace artifact.
- No formal approval record before publish.
- No formal eval thresholds for stale rate, duplicate rate, hallucinated citation rate, or source validity.
- Privacy gate is partly convention/test-based rather than a single blocking runtime policy.

## Planned Work

- `RunManifest` and `ToolCall` schema contracts are defined in Phase B; runtime emission and gate integration remain planned.
- Add at least 10 eval cases and a no-external-side-effect static checker in Phase C.
- Keep all publish, workflow dispatch, Feishu, and bot actions outside Phase A documentation work.
