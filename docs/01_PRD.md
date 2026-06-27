# 01 PRD

- Project: AI Radar Agent
- Agent Type: Intelligence / research / daily report publishing agent
- Status: Active
- Last Updated: 2026-06-27
- Owner: Unknown
- Source of Truth: Repository code, README, AGENTS.md, prompts/radar_prompt.md, .github/workflows/daily.yml
- Related Files: ai_radar_agent/__main__.py, ai_radar_agent/collector.py, ai_radar_agent/llm.py, ai_radar_agent/brief.py, ai_radar_agent/report_lint.py, ai_radar_agent/feishu_docx.py, ai_radar_agent/feishu_bot.py

## AS-IS 当前实现

### One-liner

AI Radar Agent generates a source-constrained daily AI industry radar and publishes it to Feishu.

### Agent Category

Research automation agent with publishing and notification capabilities.

### Target User

- Daily reader: wants a concise domestic / overseas AI frontier radar.
- Maintainer: manages source configuration, prompts, GitHub Actions, Feishu credentials, and release refs.

### Scenario

Every day, Feishu automation calls GitHub Actions. The workflow runs the agent for the previous complete Beijing natural day, collects evidence, generates a DeepSeek report, lints it, derives a brief, publishes a Feishu docx or fallback Markdown, and optionally sends group cards.

### Pain Points

- Manual AI news scanning is time-consuming.
- AI industry signal quality varies widely.
- LLMs can hallucinate URLs if not constrained by evidence.
- Feishu publishing has multiple fragile API and permission steps.
- Bot cards can become too long or contain bad fragments without cleanup.

### Goals

- Maintain exact date-window correctness.
- Maximize recall while enforcing strict evidence review.
- Preserve source URLs and source IDs.
- Produce a publishable daily report and concise card brief.
- Keep publishing fallbacks safe and observable.
- Make failures diagnosable through artifacts and GitHub Summary.

### Non-goals

- Cover every AI-related news item.
- Produce investment recommendations.
- Produce career advice.
- Replace human approval for high-risk operational changes.
- Automatically clean old Feishu documents beyond temporary import source deletion.

### Inputs

- `date` workflow input or CLI `--date`.
- `config/sources.yaml`.
- `prompts/radar_prompt.md`.
- Environment variables / GitHub secrets.
- Optional safe debug modes such as `dry_run`, `skip_llm`, and `output_mode=none`.

### Outputs

- Evidence artifacts.
- Markdown radar report.
- Report lint JSON.
- Brief JSON and Markdown.
- Feishu publish result.
- Feishu bot card result.
- GitHub Step Summary.

### User Journey

1. Operator configures GitHub secrets, repository variables, and Feishu automation.
2. Feishu automation triggers GitHub workflow dispatch for the confirmed production ref. Current production configurations should use `main` with `EVENT_HISTORY_COMMIT_REF=main`; existing configurations that still use `single_card_v7.1` are rollback/manual-only until explicitly switched.
3. Agent runs for the target Beijing natural day.
4. User reads the Feishu docx and optional group card.
5. Maintainer checks GitHub Summary and artifacts when anything looks wrong.

### Success Metrics

- Report generated for the correct Beijing natural day.
- Evidence count is nonzero.
- Core source URLs resolve to collected evidence or allowed report URLs.
- Report lint has no critical errors under production policy.
- Feishu docx URL or Markdown fallback exists.
- Bot card sends or provides clear skipped/failure reason.
- No secrets appear in logs or summaries.

### MVP Scope

Implemented:

- CLI and GitHub Actions entry.
- RSS / Bocha / Tavily recall.
- DeepSeek report generation.
- Report lint.
- Brief generation with repair and fallback.
- Feishu docx import and Drive Markdown fallback.
- Feishu group-card generation and send.
- Local artifact write.

### Current Version Capabilities

- Current stable code baseline: `main` / `week2_standardization`; runtime marker is `week2_standardization`.
- Rollback refs: `single_card_v7.1`, `week2/standardization`, and fixed tag `v5.2.0-rollback`.
- Safe debug modes include `dry_run`, `skip_llm`, and `output_mode=none`.
- Week 2 standardized Evidence Gate / event-history / final-top audit behavior is implemented in code.

## GAPS 当前缺口

- No explicit product requirements artifact existed before this PRD.
- No formal eval acceptance threshold exists.
- No persisted run manifest exists.
- No complete cross-run idempotency.
- Production ref references were split across README, CHANGELOG, and code warning strings.

## TO-BE 后续建议

### v1 Roadmap

- Formalize run manifest and artifact schema.
- Add source validity and stale-rate evals.
- Add cross-run idempotency through a deliberate state mechanism.
- Reconcile production-ref messaging in code and docs.

### v2 Roadmap

- Add formal schemas and evals for Evidence Gate, event history, final Top dedupe, and final Top LLM audit.
- Add dashboard-style observability over runs.
- Add formal approval workflow before irreversible cleanup or production ref changes.

### Risks

- Search providers may miss important events or return stale results.
- LLM output can drift from the expected report structure.
- Feishu API permission changes can break publishing.
- Local `outputs/` may contain private URLs and should remain untracked.
