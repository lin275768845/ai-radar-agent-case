---
type: pattern-note
project: AI Radar Agent
phase: Week 2
status: implemented
privacy: sanitized
external_side_effects: none
tags:
  - ai-radar
  - autonomy
  - permissions
  - pattern-note
---

# Agent Autonomy and Permission Boundaries

## Pattern

Agent autonomy should be described as a permission model, not only as a prompt instruction. AI Radar separates safe local actions from external side effects and human-owned commitments.

## Autonomy Levels

| Level | Status | Examples |
| --- | --- | --- |
| Read-only or static inspection | implemented | Read docs, schemas, eval definitions, and sanitized demo artifacts. |
| Local artifact generation | implemented for Week 2 artifacts | Create docs, schema contracts, eval definitions, and sanitized demo artifacts. |
| Provider or LLM calls | not used in Week 2 | Must not occur during docs/eval/demo phases. |
| External publish or notification | blocked for Week 2 | Feishu publish, bot send, webhooks, and workflow dispatch are not triggered. |
| Irreversible or production actions | human-owned | Requires explicit approval outside the Week 2 standardization artifacts. |

## Allowed Actions In Week 2

- Create sanitized documentation.
- Define schema contracts.
- Define no-side-effect eval cases.
- Run local static validation.
- Create deterministic mock demo artifacts.
- Create Obsidian-ready export notes inside the repo.

## Forbidden Actions In Week 2

- No external publish.
- No Feishu call.
- No webhook call.
- No GitHub workflow dispatch.
- No external provider call.
- No LLM invocation.
- No production pipeline execution.
- No reading of secrets, private notes, private logs, or private runtime outputs.

## Boundary Principle

If an action can write outside the local repo, send a message, publish a document, trigger a workflow, change production state, or expose private data, it belongs behind a human approval gate.

## Status Notes

| Boundary | Status |
| --- | --- |
| Autonomy matrix | implemented |
| Tool permission matrix | implemented |
| Week 2 no external side effects | implemented |
| Runtime approval artifact | partial |
| Automated external publishing in this case | planned/manual, not enabled by Week 2 artifacts |

## Source References

- [Autonomy Matrix](../04_AUTONOMY_MATRIX.md)
- [Tools And Permissions](../06_TOOLS_AND_PERMISSIONS.md)
- [Runbook](../12_RUNBOOK.md)
- [Case Study](../case_study_ai_radar_week2.md)

## Related Notes

- [[Publishing_Gates_and_Safety_Model]]
- [[No_Side_Effect_Eval_Suite]]
- [[Sanitized_Demo_Run_Pattern]]
