---
type: pattern-note
project: AI Radar Agent
phase: Week 2
status: implemented
privacy: sanitized
external_side_effects: none
tags:
  - ai-radar
  - evidence-first
  - intelligence-agent
  - pattern-note
---

# Evidence First Intelligence Agent

## Pattern

An evidence-first intelligence agent binds claims to source records before writing narrative. The agent should collect signals, apply an Evidence Gate, record uncertainty, and only then draft a report or brief.

In AI Radar, this pattern is documented as:

```text
Sources
  -> Evidence Collection
  -> Evidence Gate
  -> Intelligence Draft
  -> Report / Brief / Top Event Audits
  -> Publish Gate
  -> Local Artifacts / Optional Future Publishing
```

## Why Evidence Gates Matter

Evidence Gate prevents weak, stale, duplicated, or unsupported items from becoming confident narrative. It also gives reviewers an artifact trail for why an item was accepted, warned, dropped, or blocked.

Implemented examples:

- Phase A documents the Evidence Gate and source quality guardrails.
- Phase C includes eval cases for sufficient evidence, insufficient evidence, conflicting sources, and source fetch failure.
- Phase D demo evidence uses deterministic mock records only.

## Uncertainty And No Overclaiming

The agent should keep uncertainty visible when source quality is mixed or an item resembles earlier history. In the sanitized demo, one mock evidence item is retained as supportive context rather than framed as a fresh top event.

No overclaiming means:

- Do not invent official sources.
- Do not turn old events into today events.
- Do not treat mock demo records as live data.
- Do not publish narrative when the Publish Gate is blocked.

## Status Notes

| Capability | Status |
| --- | --- |
| Evidence Gate documentation | implemented |
| Evidence-first workflow docs | implemented |
| Static eval cases for evidence risks | implemented |
| Runtime eval integration | planned |
| Runtime RunManifest emission | planned |

## Source References

- [Workflow](../03_WORKFLOW.md)
- [Gates And Guardrails](../09_GATES_AND_GUARDRAILS.md)
- [Eval Plan](../10_EVAL_PLAN.md)
- [Eval Cases](../../evals/ai_radar_week2_eval_cases.jsonl)
- [Sanitized Demo Report](../../demo_run/demo_output_report.md)

## Related Notes

- [[Publishing_Gates_and_Safety_Model]]
- [[No_Side_Effect_Eval_Suite]]
- [[Sanitized_Demo_Run_Pattern]]
