# 08 Prompts

- Project: AI Radar Agent
- Agent Type: Intelligence / research / daily report publishing agent
- Status: Active
- Last Updated: 2026-06-11
- Owner: Unknown
- Source of Truth: prompts/radar_prompt.md and LLM call sites in code
- Related Files: prompts/radar_prompt.md, ai_radar_agent/llm.py, ai_radar_agent/brief.py, tests/test_brief.py

## AS-IS 当前实现

### Prompt Inventory

| Prompt | Current Location | Call Site | Purpose | Input Variables | Output Format | Schema Validation | Risk | Migration Notes |
|---|---|---|---|---|---|---:|---|---|
| Main Radar System Prompt | `prompts/radar_prompt.md` | `DeepSeekGenerator.generate()` in `llm.py` | Define AI radar analyst role, source tiers, time rules, candidate tables, report format, red lines | loaded as full system prompt | Markdown report | No formal schema; report lint checks structure/URLs | prompt length and report format drift | Keep as file source of truth |
| Prompt Scaffold Slots | `prompts/system.md`, `parser.md`, `judge.md`, `writer.md`, `auditor.md` | Not wired | Standard project prompt slots for future migration | n/a | n/a | No | may be mistaken for current runtime prompts | Keep clearly marked scaffold until explicit migration |
| Main Radar User Prompt | `llm.py` | `DeepSeekGenerator.generate()` | Inject date window and evidence list | `window.display_range`, `window.zh_date`, `evidence_md` | Markdown report | Report lint | hardcoded in code | Could move to prompt template later |
| Brief JSON Prompt | `brief.py` | `DeepSeekBriefGenerator._prompt()` | Convert full report into card-ready brief JSON | window, report, audit, evidence catalog, core events | JSON object | parse + normalize + repair | hardcoded, can drift from tests | Proposed future prompt template |
| Brief Repair Prompt | `brief.py` | `_repair_prompt()` | Repair invalid JSON without new facts | raw response, parse error | JSON object | parse + normalize | repair may still fail | Keep tests before migration |
| Count Repair Prompt | `brief.py` | `_count_repair_prompt()` | Repair missing top items against extracted core events | raw response, core events, evidence catalog | JSON object | normalize + count checks | may overfit to report extraction | Template only after schemas exist |
| Section Items Prompt | `brief.py` | `_section_items_prompt()` | Retry domestic/overseas top items separately | region, report, catalog, core events | JSON object | normalize | may duplicate logic | Proposed template |
| Signals Prompt | `brief.py` | `_signals_prompt()` | Extract core judgments and watch signals | report excerpt | JSON object | parse | may include candidate table text | Proposed template |
| Core Extractor Prompt | `brief.py` | `_core_extractor_prompt()` | Fallback extraction when deterministic report parsing is suspect | report, existing core event state | JSON object | normalize | LLM fallback may miss events | Proposed eval coverage |

### Prompt Name

The only standalone named prompt file is the main radar prompt. Other prompts are function-local prompt templates in `brief.py` and `llm.py`.

### File Location

- `prompts/radar_prompt.md`: main report system prompt.
- `prompts/system.md`, `parser.md`, `judge.md`, `writer.md`, `auditor.md`: scaffold-only prompt slots, not wired into runtime.
- `ai_radar_agent/llm.py`: user prompt for report generation.
- `ai_radar_agent/brief.py`: brief and repair prompts.

### Call Site

All LLM calls use OpenAI-compatible `chat.completions.create` through DeepSeek settings.

### Purpose

Prompts enforce recall-first analysis, source tiers, no invented citations, domestic/overseas separation, candidate-event screening, and card-safe brief generation.

### Input Variables

- `window.display_range`
- `window.zh_date`
- `evidence_md`
- `report_md`
- `audit`
- `doc_url`
- `evidence catalog`
- `core_events`

### Output Format

- Main report: Markdown with candidate event tables, domestic/overseas radar sections, source links, and self-check.
- Brief: JSON object with `domestic_top`, `overseas_top`, `core_judgments`, `watch_signals`, and `source_ids`.

### Schema Validation

No formal external schema. Main report uses `report_lint.py`. Brief uses parse, salvage, normalization, source binding, and tests.

### Few-shot Examples

No few-shot example file exists. The main prompt contains detailed format instructions rather than explicit example completions.

### Version

No prompt version metadata exists in `prompts/radar_prompt.md`. README references a radar prompt version phrase inside prompt text, but it is not formalized as artifact metadata.

### Risks

- Main report prompt is long and can be hard to diff/review.
- Brief prompts are hardcoded in code, making prompt-only review harder.
- LLM JSON mode fallback can still produce parse drift.
- Report prompt and parser expectations must stay aligned.

### Migration Notes

Do not migrate prompts during documentation work. A future prompt migration should add tests first, preserve source-ID constraints, and keep `prompts/radar_prompt.md` as source of truth until replacement is explicit.

## GAPS 当前缺口

- Scaffold prompt slots exist, but there is no prompt registry with version/owner/change notes.
- No prompt eval set.
- Brief prompts are hardcoded in `brief.py`.
- Scaffold schemas exist, but no runtime-enforced formal schema file for brief output.

## TO-BE 后续建议

- Add prompt metadata block to `prompts/radar_prompt.md`.
- Move brief prompts to `prompts/` only after tests and schema coverage are ready.
- Add prompt change checklist to runbook.
- Add golden prompt evals for source hallucination, stale events, duplicate events, and report parsing.
