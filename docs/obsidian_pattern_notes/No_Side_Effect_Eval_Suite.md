---
type: pattern-note
project: AI Radar Agent
phase: Week 2
status: implemented
privacy: sanitized
external_side_effects: none
tags:
  - ai-radar
  - evals
  - no-side-effect
  - pattern-note
---

# No Side Effect Eval Suite

## Pattern

A no-side-effect eval suite validates definitions and safety expectations without calling production systems. It should prove the evaluation inputs are shaped correctly before any runtime integration is attempted.

## Week 2 Eval Suite

Phase C implements 10 local eval case definitions covering:

- evidence_gate
- publish_gate
- tool_permission
- safety_mode
- schema_contract
- observability
- redaction
- failure_handling
- eval_static_check
- emergency_stop

Every case sets `no_external_side_effects` to true and forbids external publish, workflow dispatch, webhook calls, provider calls, LLM calls, and production pipeline execution.

## Static Checker

The checker validates:

- exactly 10 JSONL records
- required fields
- expected case ids
- unique case ids
- category coverage
- forbidden external-risk actions
- related docs and schemas
- Phase B schema JSON validity

The checker is local/static. It does not import production code, call external APIs, invoke LLMs, trigger Feishu or GitHub, or run the production pipeline.

## What Remains Planned

| Item | Status |
| --- | --- |
| Eval case definitions | implemented |
| Static checker | implemented |
| Runtime eval execution | planned |
| Validation of emitted RunManifest artifacts | planned |
| Metric reporting for stale rate or source validity | planned |

## Source References

- [Eval Plan](../10_EVAL_PLAN.md)
- [Eval Cases](../../evals/ai_radar_week2_eval_cases.jsonl)
- [Eval Checker](../../evals/check_ai_radar_week2_eval_cases.py)
- [Runtime Object Map](../13_RUNTIME_OBJECT_MAP.md)

## Related Notes

- [[Evidence_First_Intelligence_Agent]]
- [[RunManifest_and_ToolCall_Contracts]]
- [[Publishing_Gates_and_Safety_Model]]
