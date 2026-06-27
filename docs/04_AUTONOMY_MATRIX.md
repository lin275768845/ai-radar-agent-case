# 04 Autonomy Matrix

- Project: AI Radar Agent
- Agent Type: evidence-first intelligence and publishing agent
- Status: active
- Last Updated: 2026-06-19
- Source of Truth: repository code, `README.md`, `AGENTS.md`, `.github/workflows/daily.yml`
- Related Files: selected public code slices, schemas, evals, demo artifacts;
  full production runtime files are omitted from this curated mirror.

## Autonomy Principle

AI Radar may automate public-signal recall, evidence filtering, drafting, linting, local artifact writing, and configured publishing after an explicit trigger. It must not autonomously change production configuration, secrets, code, prompts, schemas, GitHub refs, or user-confirmed operational state.

Publish, bot send, workflow dispatch, Feishu document creation, and remote cleanup are external side effects. They require human approval or explicit no-publish controls such as `dry_run`, `skip_llm`, `output_mode=none`, or `send_bot=false`.

## Action Matrix

| Action | Status | Auto-execute? | Draft only? | Human approval required? | Forbidden automation | External side effect? | Risk | Gate |
| --- | --- | ---:| ---:| ---:| ---:| ---:| --- | --- |
| Read public RSS/search sources | implemented | Yes | No | No | No | No | Stale or low-quality public evidence | Time window gate; Evidence Gate |
| Recall via RSS / Bocha / Tavily | implemented | Yes when configured | No | Provider key/config is human-owned | No | Provider API read only | Quota, outage, bad source mix | Tool permission gate; provider degradation gate |
| Draft report generation | implemented | Yes when not `skip_llm` | Yes | Prompt/provider changes need approval | No | No external write | Hallucination, stale event framing | Evidence Gate; source URL guardrail |
| Local artifact write | implemented | Yes | No | No for normal run artifacts | No | Local filesystem only | Private artifact leakage if committed/shared | Privacy gate |
| Lint and audit | implemented | Yes | No | No | No | No | False pass or overly broad warnings | report_lint gate; top_event_audit gate |
| Dry-run | implemented | Yes when requested | No | No | No | No | False confidence if treated as production | Publish Gate should stay blocked |
| `skip_llm` evidence-only run | implemented | Yes when requested | No | No | No | No | Evidence quality only, no report validation | Evidence Gate |
| Feishu docx/Drive publish | implemented | Yes after explicit trigger unless disabled | No | Yes, operational approval through trigger/ref and publish flags | No autonomous publish | Yes | Wrong ref/date/folder, duplicate publish | Publish Gate; approval gate |
| Feishu bot card send | implemented | Yes when configured and not blocked | No | Yes, operational approval through trigger/ref and bot flags | No autonomous new channel | Yes | Wrong audience/noisy card | Bot Gate; Publish Gate |
| GitHub workflow dispatch | implemented outside runtime | External caller triggers | No | Yes | No autonomous dispatch from docs/Codex tasks | Yes | Wrong ref, production side effect | Approval Gate |
| Config / secret handling | partial | Runtime reads configured env names | No | Humans own secret creation/rotation | Codex must not read/output values | Potentially | Secret exposure | Privacy gate |
| Delete / cleanup | partial | Temp Feishu source cleanup only | No | Required for any new cleanup | No user-data cleanup automation | Yes | Deleting wrong remote file | Rollback/destructive-action gate |
| Production ref change | planned/manual | No | No | Yes | Yes unless explicit task | Yes | Production drift | Approval Gate |
| Static eval checker | planned | Yes when implemented | No | No | No | No | Incomplete coverage | Eval gate |
| Read-only Artifact Workbench | planned P2 | Read only | No | No for sanitized demo artifacts | No writes or publishes | No | Accidental private artifact exposure | Privacy gate |

## Required Controls

- Secrets, `.env` values, webhooks, tokens, cookies, private logs, and private run outputs must not be read, printed, summarized, committed, or exported.
- `outputs/` may contain private run artifacts and Feishu URLs; treat it as private local storage unless artifacts are explicitly sanitized.
- Feishu publish and bot send must stay disabled for documentation, eval, and inspection tasks.
- New publish/delete behavior requires dry-run validation first and explicit human approval.

## Status Notes

- implemented: current runtime behavior exists in code/tests/docs.
- partial: behavior exists but lacks a formal approval artifact, manifest, or durable trace.
- planned: documented target only; not implemented by this Phase A docs task.

## Current Gaps

- No formal approval artifact before normal Feishu publish.
- No formal `RunManifest` showing approval/ref/date/publish decisions.
- No `ToolCall` trace artifact for external and local tool usage.
- Cross-run idempotency remains partial.

## P2 Future Work: Read-only Artifact Workbench

Status: planned.

If built later, it should inspect only sanitized artifacts and never trigger provider calls, Feishu publish, bot send, GitHub workflow dispatch, delete, or cleanup actions.
