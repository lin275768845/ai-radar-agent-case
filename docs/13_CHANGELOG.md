# 13 Changelog

- Project: AI Radar Agent
- Agent Type: Intelligence / research / daily report publishing agent
- Status: Active
- Last Updated: 2026-06-27
- Owner: Unknown
- Source of Truth: Documentation retrofit in this repository
- Related Files: README.md, AGENTS.md, docs/00_REQUIREMENTS.md, docs/01_PRD.md, docs/02_ARCHITECTURE.md, docs/03_WORKFLOW.md, docs/04_AUTONOMY_MATRIX.md, docs/05_DATA_MODEL.md, docs/06_TOOLS_AND_PERMISSIONS.md, docs/07_SKILLS.md, docs/08_PROMPTS.md, docs/09_GATES_AND_GUARDRAILS.md, docs/10_EVAL_PLAN.md, docs/11_OBSERVABILITY.md, docs/12_RUNBOOK.md

## v0.1.4-week2-baseline-marker - 2026-06-27

### Version

`v0.1.4-week2-baseline-marker`

### Date

2026-06-27

### Change Type

Runtime marker and documentation baseline correction.

### Summary

Updated the current stable baseline label from `single_card_v7.1` / `v7.1.0` to `main` / `week2_standardization`, while preserving `single_card_v7.1` and `week2/standardization` as rollback refs.

### Impact

GitHub Actions Summary now reports `app_version: week2_standardization`. Default event-history commit ref examples now point to `main`. No prompt source, provider behavior, Feishu behavior, Cloudflare ref, or production scheduler was changed.

### Rollback Plan

Revert this marker/documentation sync commit if the production baseline is intentionally moved back to a v7.1 rollback ref.

## v0.1.3-rollback-branch-sync - 2026-06-27

### Version

`v0.1.3-rollback-branch-sync`

### Date

2026-06-27

### Change Type

Documentation ref / rollback sync.

### Summary

Updated documentation to treat `single_card_v7.1` and `week2/standardization` as branch rollback points, and to preserve v5.2 only through fixed tag `v5.2.0-rollback` after deleting the `single_card_v5.2` branch.

### Impact

No runtime behavior, workflow trigger, production dispatcher, prompt source, schema, state, or external service was changed.

### Rollback Plan

Revert this documentation-only sync commit.

## v0.1.2-ref-doc-sync - 2026-06-27

Superseded by `v0.1.3-rollback-branch-sync` above for the current rollback branch policy.

### Version

`v0.1.2-ref-doc-sync`

### Date

2026-06-27

### Change Type

Documentation ref / rollback sync.

### Summary

Updated documentation to reflect that `main` and `single_card_v7.1` now point to the same stable v7.1 baseline, fixed as tag `v7.1.0`, and that the v5.2 rollback point is fixed as tag `v5.2.0-rollback`.

### Impact

No runtime behavior, workflow trigger, production dispatcher, prompt source, schema, state, or external service was changed.

### Rollback Plan

Revert this documentation-only sync commit.

## AS-IS 当前实现

This file tracks documentation, scaffold, and architecture-recovery changes for the standardized Agent project design set. The root `CHANGELOG.md` remains the historical product changelog.

## v0.1.1-standard-scaffold - 2026-06-11

### Version

`v0.1.1-standard-scaffold`

### Date

2026-06-11

### Change Type

Documentation scaffold / test contract sync.

### Summary

Added the standard Agent project directory scaffold and synchronized brief tests with the current `brief.py` contract.

### Files Changed

- `schemas/input.schema.json`
- `schemas/output.schema.json`
- `schemas/state.schema.json`
- `schemas/audit_result.schema.json`
- `prompts/system.md`
- `prompts/parser.md`
- `prompts/judge.md`
- `prompts/writer.md`
- `prompts/auditor.md`
- `skills/example.skill.md`
- `evals/golden_cases.jsonl`
- `evals/failure_cases.jsonl`
- `evals/edge_cases.jsonl`
- `evals/regression_cases.jsonl`
- `runs/.gitkeep`
- `state/.gitkeep`
- `tests/.gitkeep`
- `tests/test_brief.py`

### Added

- Added scaffold-only schema, prompt, skill, eval, runs, and state files.
- Marked scaffold files as not wired into runtime.

### Changed

- Updated brief tests to assert the current initial/final mismatch contract.

### Impact

Runtime behavior is unchanged. Tests now match the current deterministic brief repair/fill behavior.

### Breaking Change

No.

### Rollback Plan

Revert the scaffold/test-sync commit if the project owner decides to keep only the documentation retrofit.

## v0.1.0-docs-retrofit - 2026-06-11

### Version

`v0.1.0-docs-retrofit`

### Date

2026-06-11

### Change Type

Documentation / architecture recovery.

### Summary

Added standardized Agent project documentation based on repository inspection. The docs distinguish current implementation facts from gaps and future recommendations.

### Files Changed

- `README.md`
- `AGENTS.md`
- `docs/00_REQUIREMENTS.md`
- `docs/01_PRD.md`
- `docs/02_ARCHITECTURE.md`
- `docs/03_WORKFLOW.md`
- `docs/04_AUTONOMY_MATRIX.md`
- `docs/05_DATA_MODEL.md`
- `docs/06_TOOLS_AND_PERMISSIONS.md`
- `docs/07_SKILLS.md`
- `docs/08_PROMPTS.md`
- `docs/09_GATES_AND_GUARDRAILS.md`
- `docs/10_EVAL_PLAN.md`
- `docs/11_OBSERVABILITY.md`
- `docs/12_RUNBOOK.md`
- `docs/13_CHANGELOG.md`

### Added

- Added standardized Agent project documentation set.
- Added AS-IS / GAPS / TO-BE structure.
- Added project architecture, workflow, autonomy, data model, tools, skills, prompts, gates, eval, observability, and runbook docs.

### Changed

- Updated README with a concise external-facing project overview.
- At that time, updated README production ref language to `single_card_v5.2`.
- Updated AGENTS.md with project-level Codex development rules.

### Impact

No business logic, prompt source files, schemas, workflow files, state, logs, or external services were intentionally changed.

### Breaking Change

No.

### Risks

- Documentation is based on repository inspection and may require human verification.
- Some historical branch/ref references remain in root `CHANGELOG.md`, release notes, tests, or code warning strings because this documentation-only phase did not modify business code or non-target files.
- After merging v5.2 back to main, Evidence Gate, event history, final Top dedupe, and final Top LLM audit are the current runtime path.

### Rollback Plan

Revert documentation retrofit commit.

### Notes

At the time of this documentation recovery workflow, the production ref was confirmed by the user as `single_card_v5.2`. This is historical context; current stable baseline and rollback refs are tracked in the newer entries above.

## GAPS 当前缺口

- Root `CHANGELOG.md` still contains older production-ref language.
- Code-level production warning still mentions an older stable ref.
- No formal release process exists for doc-only architecture recovery.

## TO-BE 后续建议

- Add future entries when prompt, schema, workflow, or production-ref behavior changes.
- Keep this docs changelog separate from runtime release notes unless the project owner merges them deliberately.
