# 00 Requirements

- Project: AI Radar Agent
- Agent Type: Intelligence / research / daily report publishing agent
- Status: Active
- Last Updated: 2026-06-27
- Owner: Unknown
- Source of Truth: Repository code, README, AGENTS.md, prompts/radar_prompt.md, .github/workflows/daily.yml
- Related Files: README.md, AGENTS.md, ai_radar_agent/__main__.py, ai_radar_agent/config.py, config/sources.yaml, prompts/radar_prompt.md, tests/

## AS-IS 当前实现

### Original Request

Unknown. The original product request is not stored as a single source-of-truth artifact in the repository.

### Cleaned Requirement

Build and maintain a daily AI radar agent that:

- Uses an exact Beijing natural-day window.
- Recalls broad public AI industry evidence from configured RSS and search providers.
- Sends evidence with URLs to DeepSeek.
- Generates a strict domestic and overseas AI radar report.
- Audits report structure and source links.
- Generates a compact brief for Feishu group cards.
- Publishes the full report to Feishu docx or Drive Markdown fallback.
- Records local artifacts for debugging and audit.

### Background

AI frontier events, product launches, adoption signals, and commercialization data are distributed across official sources, media, RSS feeds, and search APIs. The project reduces manual daily research and publishing work while enforcing source traceability.

### Target User

- Primary: project owner / maintainer who consumes a daily AI radar in Feishu.
- Secondary: operators who run or debug GitHub Actions, Feishu automation, and provider credentials.

### Primary Use Case

Generate a daily AI frontier radar for the previous complete Beijing natural day and publish it to Feishu with optional group-card notification.

### Constraints

- Do not ask the LLM to invent sources.
- Evidence URLs must come from collected evidence or report body.
- Do not store secrets in code.
- Keep Feishu Drive Markdown fallback when using Feishu docx import.
- Keep local debug modes safe: `dry_run`, `skip_llm`, and `output_mode=none`.
- Stable code baseline is `main` carrying the Week 2 standardized baseline; `single_card_v7.1` is retained as a previous-runtime rollback branch, and `week2/standardization` is retained as the Week 2 branch snapshot. Production dispatch on `main` requires `EVENT_HISTORY_COMMIT_REF=main`.

### MVP Scope

- CLI and GitHub Actions execution.
- RSS / Bocha / Tavily recall.
- DeepSeek report generation.
- Report lint.
- DeepSeek brief generation with parsing and repair.
- Feishu docx publish with Markdown fallback.
- Feishu bot card send.
- Local artifacts under `outputs/<date>/`.

### Explicit Non-goals

- General news aggregation.
- Investment advice.
- Job or career advice.
- Secret storage.
- Fully autonomous irreversible production changes without operator control.
- LLM web browsing or LLM-invented citations.

### Assumptions

- Feishu automation triggers production via GitHub `workflow_dispatch`.
- GitHub repository secrets and variables provide runtime credentials.
- `prompts/radar_prompt.md` remains the main report prompt source of truth.
- Current stable baseline is `main` / `week2_standardization`; previous v5.2 production state is preserved only by fixed rollback tag `v5.2.0-rollback`.

### Open Questions

- Whether dedicated failure notification is still planned or was removed; `.github/workflows/daily.yml` currently only uploads artifacts after the run.
- How far the Week 2 standardized Evidence Gate / event-history / final-top audit pipeline should be formalized in schemas and evals.
- Whether cross-run idempotency should be implemented through GitHub cache, committed state, or Feishu-side document lookup.

### Current Implementation Status

The main daily flow is implemented and tested. The standard project design docs were missing before this retrofit. Standard scaffold directories now exist for schemas, evals, runs, state, prompts, and skills, but formal runtime JSON schema validation, real eval datasets, and durable run manifests are not currently implemented.

## GAPS 当前缺口

- No original requirements artifact exists.
- Standard scaffold directories exist, but they are not wired into runtime validation, CI evals, or durable state handling.
- Production ref documentation was inconsistent before this update.
- README mentions some behavior that is not confirmed in code, such as failure notification through ops bot variables.
- Cross-run publish idempotency is incomplete.
- Evidence Gate / event-history / final-top audit behavior is implemented in code but not yet fully represented in formal schemas or evals.

## TO-BE 后续建议

- Add a short source-of-truth requirements note whenever major product behavior changes.
- Add formal schemas for `EvidenceItem`, `Brief`, `ReportLintResult`, `FeishuResult`, `BotResult`, and `RunManifest`.
- Add eval cases for source validity, duplicate rate, stale rate, hallucinated citation rate, and report explainability.
- Implement a real run manifest before adding more publishing autonomy.
- Reconcile README, CHANGELOG, code warnings, and GitHub workflow docs after production ref changes.
