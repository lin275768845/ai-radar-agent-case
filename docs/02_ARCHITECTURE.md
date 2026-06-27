# 02 Architecture

- Project: AI Radar Agent
- Agent Type: Intelligence / research / daily report publishing agent
- Status: Active
- Last Updated: 2026-06-11
- Owner: Unknown
- Source of Truth: Repository code, README, AGENTS.md, prompts/radar_prompt.md, .github/workflows/daily.yml
- Related Files: ai_radar_agent/__main__.py, ai_radar_agent/config.py, ai_radar_agent/models.py, ai_radar_agent/collector.py, ai_radar_agent/llm.py, ai_radar_agent/brief.py, ai_radar_agent/report_lint.py, ai_radar_agent/feishu.py, ai_radar_agent/feishu_docx.py, ai_radar_agent/feishu_bot.py

## AS-IS 当前实现

### System Overview

AI Radar Agent is a Python package run by CLI or GitHub Actions. It collects public evidence, generates a DeepSeek report, validates/report-lints the output, creates a compact brief, publishes to Feishu, and records local artifacts under `outputs/<date>/`.

### Current Repository Structure

```text
ai_radar_agent/
  __main__.py          # orchestration entrypoint
  config.py            # Pydantic settings from env vars
  models.py            # core dataclasses
  collector.py         # recall orchestration
  fetchers/            # RSS, Bocha, Tavily
  llm.py               # DeepSeek report generation
  brief.py             # brief generation, parsing, repair, source binding
  report.py            # report save and source appendix fallback
  report_lint.py       # report checks
  feishu.py            # Drive token/upload/delete
  feishu_docx.py       # docx import workflow
  feishu_result.py     # publish result dataclass
  feishu_bot.py        # bot cards and webhook send
  event_history.py     # v5.2 event history and final Top dedupe
config/sources.yaml
prompts/radar_prompt.md
.github/workflows/daily.yml
tests/
outputs/
```

### Architecture Diagram

```text
Feishu automation or manual workflow_dispatch
  -> GitHub Actions daily.yml
  -> python -m ai_radar_agent
  -> Settings / CLI args
  -> TimeWindow gate
  -> RSS / Bocha / Tavily recall
  -> evidence dedupe and cap
  -> evidence.json + evidence.md
  -> Evidence Gate / event history matching
  -> DeepSeek report generation
  -> report source URL appendix fallback
  -> report_lint.json
  -> DeepSeek brief generation
  -> brief parse / repair / source binding
  -> Feishu docx import
       -> fallback to Drive Markdown
  -> publish_result.json
  -> optional Feishu bot cards
  -> GitHub Summary and uploaded artifact
```

### Entry Points

- CLI: `python -m ai_radar_agent`
- Console script: `ai-radar-agent`
- GitHub Actions: `.github/workflows/daily.yml`
- Docker: `Dockerfile` runs `python -m ai_radar_agent`

### Core Modules

| Module / File | Current Role | Inputs | Outputs | Notes |
|---|---|---|---|---|
| `ai_radar_agent/__main__.py` | Main orchestration | CLI args, env settings | artifacts, publish/send results | Controls dry-run, skip-LLM, replay, publish, summary |
| `ai_radar_agent/config.py` | Runtime settings | environment variables | `Settings` | Pydantic BaseSettings |
| `ai_radar_agent/dates.py` | Date-window logic | date or current time | `TimeWindow` | Beijing natural-day exactness |
| `ai_radar_agent/models.py` | Core dataclasses | n/a | data objects | Scaffold JSON Schemas exist but are not runtime validators |
| `ai_radar_agent/collector.py` | Recall orchestration | settings, sources, window | evidence, recall audit | Always keeps RSS in provider list |
| `ai_radar_agent/fetchers/rss.py` | RSS fetch | RSS URLs | `EvidenceItem` list, RSS audit | Missing dates are retained |
| `ai_radar_agent/fetchers/bocha_search.py` | Bocha search | queries, API key | `EvidenceItem` list | Handles auth/rate/server errors |
| `ai_radar_agent/fetchers/tavily_search.py` | Tavily search | queries, API key | `EvidenceItem` list | Optional, quota-consuming |
| `ai_radar_agent/llm.py` | Full report generation | prompt, evidence Markdown | report Markdown | DeepSeek/OpenAI-compatible client |
| `ai_radar_agent/report.py` | Report save/source appendix | report, evidence | Markdown file | Appends evidence URLs if report lacks URLs |
| `ai_radar_agent/report_lint.py` | Report quality checks | report, evidence | `ReportLintResult` | Can warn, block bot, or strict-block publish |
| `ai_radar_agent/brief.py` | Brief generation and normalization | report, audit, evidence | `brief.json`, `brief.md` | Includes LLM calls and deterministic fallback |
| `ai_radar_agent/feishu.py` | Feishu Drive API | credentials, file path | upload/delete result | Gets tenant access token |
| `ai_radar_agent/feishu_docx.py` | Feishu docx import | Markdown report | `FeishuResult` | Uploads temp MD, creates/polls import task, deletes temp file |
| `ai_radar_agent/feishu_result.py` | Publish result object | publish fields | safe summaries | Redacts token presence via boolean fields |
| `ai_radar_agent/feishu_bot.py` | Group card rendering/sending | brief, settings | `BotResult` | Multi-card, text fallback, signature support |
| `ai_radar_agent/evidence_gate.py` | Evidence quality gate | raw evidence, window, settings | filtered/dropped evidence audit | v5.2 runtime |
| `ai_radar_agent/event_history.py` | 5-day event history and final Top dedupe | brief, history state, evidence | history matches, dedupe audit, updated brief | v5.2 runtime |
| `ai_radar_agent/final_top_auditor.py` | Final Top LLM duplicate audit | brief, history context | LLM audit payload and decisions | v5.2 runtime |
| `ai_radar_agent/top_event_audit.py` | Final Top quality audit | brief, evidence, window | source/date quality audit | v5.2 runtime |

### Data Flow

Evidence flows from fetchers into `EvidenceItem`, then into Markdown context for DeepSeek. The generated report is linted, parsed into core events, compressed into brief items, source-bound to evidence IDs/URLs, then rendered into Feishu cards.

### State Flow

The only current state-like mechanism is local `outputs/<date>/publish_result.json`, reused within the same output directory unless `--force-republish` is set. There is no durable cross-run state database.

### LLM Call Sites

- `DeepSeekGenerator.generate()` in `llm.py`.
- `DeepSeekBriefGenerator._call()` and section/recovery methods in `brief.py`.

### Tool Call Sites

- RSS HTTP GET.
- Bocha search HTTP POST.
- Tavily search HTTP POST.
- Feishu tenant token/upload/delete/import/poll.
- Feishu bot webhook POST.

### Storage

- Local filesystem under `outputs/<date>/`.
- GitHub Actions uploaded artifact.
- Feishu Drive / docx as external storage.

### External Services

- DeepSeek API compatible with OpenAI SDK.
- RSS hosts configured in `config/sources.yaml`.
- Bocha.
- Tavily.
- Feishu Open Platform.
- GitHub Actions.

### Error Boundaries

- Provider failures warn and continue when possible.
- No evidence raises runtime error.
- Report lint can be warn, block bot, strict, or off.
- Feishu docx import falls back to Drive Markdown.
- Feishu bot failures usually do not fail the main report publish.
- Final Top LLM audit failures are recorded and do not block publish by default.

### Deployment Shape

Primary deployment is GitHub Actions `workflow_dispatch`, triggered manually or by Feishu automation. Docker and docker-compose exist for local/container execution.

## GAPS 当前缺口

- No formal architecture doc existed before this file.
- `schemas/` exists as scaffold only; runtime still uses dataclasses, Pydantic settings, normalization code, and tests for validation.
- No durable run manifest or trace file.
- No cross-run idempotency beyond local `publish_result.json`.
- Formal schemas/evals for Evidence Gate, event history, and final Top audit remain incomplete.
- README mentions ops failure notification, but current workflow does not contain a visible notify-failure step.

## TO-BE 后续建议

### Architecture Risks

- LLM report format drift can break brief extraction.
- Feishu API permission drift can break docx import.
- Search provider outages can reduce evidence quality.
- Local-only state can cause duplicate publishes across GitHub runs.

### Proposed Architecture Improvements

- Add a `RunManifest` artifact for every run.
- Add formal JSON schemas for artifacts.
- Add explicit publish approval or dry-run gate for any new irreversible action.
- Implement cross-run idempotency deliberately.
- Add formal evals and schemas for Evidence Gate, event history, final Top dedupe, and final Top LLM audit.
