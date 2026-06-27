# 05 Data Model

- Project: AI Radar Agent
- Agent Type: Intelligence / research / daily report publishing agent
- Status: Active
- Last Updated: 2026-06-11
- Owner: Unknown
- Source of Truth: Repository code and tests
- Related Files: ai_radar_agent/models.py, ai_radar_agent/config.py, ai_radar_agent/report_lint.py, ai_radar_agent/feishu_result.py, ai_radar_agent/feishu_bot.py, ai_radar_agent/evidence_gate.py, ai_radar_agent/event_history.py, ai_radar_agent/top_event_audit.py, tests/

## AS-IS 当前实现

### Data Model Overview

Current data models are implemented with dataclasses, Pydantic settings, dictionaries normalized by code, and tests. A standard `schemas/` scaffold exists, but those JSON Schema files are not wired into runtime validation.

### Core Objects

| Object | Field | Type | Required | Source | Used In | Validation | Notes |
|---|---|---|---:|---|---|---|---|
| `TimeWindow` | `target_date` | date | Yes | CLI/default date | all run stages | `window_for_date` | Beijing natural day target |
| `TimeWindow` | `start` / `end` | datetime | Yes | `dates.py` | fetch filters, prompt | tests | timezone-aware |
| `EvidenceItem` | `title` | str | Yes | RSS/search/replay | evidence, report prompt, brief matching | dataclass defaults in replay | may be empty if provider returns empty |
| `EvidenceItem` | `url` | str | Yes | RSS/search/replay | report source, brief sources | URL normalization in lint/brief | key for dedupe |
| `EvidenceItem` | `content` | str | Yes | RSS/search/replay | evidence Markdown | length capped in Markdown | raw-ish snippet |
| `EvidenceItem` | `source` | str | No | provider result | source label | label cleanup | provider/source name |
| `EvidenceItem` | `published_at` | str | No | provider result | time filter/prompt | best-effort parse | can be missing |
| `EvidenceItem` | `provider` | str | No | fetcher | audit/debug | none | e.g. bocha/tavily |
| `EvidenceItem` | `region_hint` | literal | No | config basket | prompt context | type hint only | domestic/overseas/global/unknown |
| `EvidenceItem` | `source_basket` | str | No | config basket | evidence audit | none | source category |
| `RecallAudit` | `target_date` | str | Yes | window | evidence Markdown/Summary | dataclass | per-run recall metadata |
| `RecallAudit` | `total_evidence_count` | int | Yes | collector | gates/Summary | computed | no evidence blocks run |
| `RecallAudit` | `provider_audits` | list | No | collector | evidence Markdown | dataclass list | provider status table |
| `ProviderAudit` | `provider` | str | Yes | collector | audit | dataclass | rss/bocha/tavily |
| `ProviderAudit` | `enabled` | bool | Yes | settings/provider list | audit | dataclass | distinguishes disabled/missing key |
| `ReportLintResult` | `warnings` | list[str] | Yes | lint checks | report_lint.json/Summary | `finalize` | non-blocking by default |
| `ReportLintResult` | `errors` | list[str] | Yes | lint checks | policy gate | `finalize` | can block bot or strict publish |
| `ReportLintResult` | `critical_errors` | list[str] | Yes | lint checks | policy gate | `finalize` | can block based on policy |
| `Brief` | `domestic_top` / `overseas_top` | list[dict] | Yes | LLM + normalization | brief/card | normalization tests | dict schema, no formal class |
| `Brief` | `source_ids` | list[str] | No | LLM brief output | source resolution | evidence catalog matching | converted to `sources` |
| `Brief` | `sources` | list[dict] | No | normalization | brief/card | URL allowlist/source binding | max 2 per item in card |
| `FeishuResult` | `canonical_url` | str | No | publish | brief/Summary | `finalize` | docx preferred over md |
| `FeishuResult` | `canonical_type` | str | Yes | publish | brief/Summary | `finalize` | `docx`, `md`, or `none` |
| `FeishuResult` | `fallback_used` | bool | Yes | docx import | Summary | dataclass | true when MD fallback |
| `BotResult` | `attempted` / `sent` / `skipped` | bool | Yes | bot send | Summary | dataclass | webhook status |
| `BotResult` | `response_code` / `response_msg` | optional | No | Feishu webhook | Summary | sanitized | no secret values |
| `EvidenceGateAudit` / event-history audits | counts/status fields | dict/dataclass | Yes | v5.2 gate/dedupe/audit modules | artifacts/Summary | tests | evidence quality and repeat-event audit |

### Object Fields

Fields are defined in:

- `ai_radar_agent/models.py`
- `ai_radar_agent/report_lint.py`
- `ai_radar_agent/feishu_result.py`
- `ai_radar_agent/feishu_bot.py`
- `ai_radar_agent/evidence_gate.py`
- `ai_radar_agent/event_history.py`
- `ai_radar_agent/top_event_audit.py`
- dictionary-normalization code in `ai_radar_agent/brief.py`

### Source of Each Field

- Date fields: CLI/default in `dates.py`.
- Evidence fields: RSS / Bocha / Tavily / replay file.
- Report fields: DeepSeek output plus deterministic appendix.
- Brief fields: DeepSeek output plus normalization and fallback extraction.
- Feishu fields: Feishu API responses and fallback logic.
- Bot fields: card renderer and webhook response.

### Required vs Optional

Dataclasses provide defaults for many optional fields. Runtime requiredness is mostly enforced through settings validation, no-evidence checks, lint policy, and normalization logic.

### Validation Rules

- Settings: Pydantic `BaseSettings`.
- Report: `lint_report`.
- Brief: JSON parse, schema subset validation, normalization, source ID resolution.
- Sources: URL allowlist from evidence/report.
- Feishu: required env validation for publish.
- Bot card: text quality validation and payload-size controls.

### State Objects

- `publish_result.json` with date, output mode, canonical URL/type, docx/md URL, publish timestamp, GitHub run ID, fallback flag.
- `evidence_gate.json`, `event_history_matches.json`, `final_top_dedupe.json`, `final_top_llm_audit.json`, and `top_event_audit.json` in v5.2 runs.

### Audit Objects

- `RecallAudit`.
- `ProviderAudit`.
- `RssSourceAudit`.
- `ReportLintResult`.
- Evidence Gate / event-history / final-top audit objects.
- `BotResult`.

### Schema Files

Scaffold schema files now exist:

- `schemas/input.schema.json`
- `schemas/output.schema.json`
- `schemas/state.schema.json`
- `schemas/audit_result.schema.json`

These files are draft scaffolds only. Current runtime validation still lives in Python code and tests.

### Current Schema Coverage

Strongest coverage is in tests and normalization code. The scaffold schema files are not authoritative for current runtime behavior.

## GAPS 当前缺口

- Scaffold JSON Schema files exist, but there is no formal runtime JSON Schema / Pydantic model for `Brief`.
- No formal `RunManifest`.
- No runtime-enforced formal schema for `evidence.json` despite dataclass source.
- No migration/version field in artifacts.

## TO-BE 后续建议

- Proposed: replace/extend scaffold schemas with runtime-reviewed schemas for evidence, brief, audit result, output, and run manifest.
- Proposed: add artifact version fields.
- Keep these proposed schemas backward-compatible with current `outputs/<date>/` artifacts.
