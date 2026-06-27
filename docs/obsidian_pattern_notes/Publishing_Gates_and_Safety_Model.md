---
type: pattern-note
project: AI Radar Agent
phase: Week 2
status: implemented
privacy: sanitized
external_side_effects: none
tags:
  - ai-radar
  - gates
  - publish-safety
  - pattern-note
---

# Publishing Gates and Safety Model

## Pattern

Publishing agents need separate gates for evidence quality and external side effects. Evidence Gate protects narrative quality. Publish Gate protects external systems and human-owned commitments.

## Evidence Gate

Evidence Gate checks whether recalled items are usable for narrative. It should detect missing evidence, weak source fit, repeated history, stale events, and unsupported source references.

Status: implemented in docs and current runtime behavior. Runtime manifest integration remains planned.

## Publish Gate

Publish Gate decides whether document publication, bot cards, workflow dispatch, or other external side effects can proceed.

For Week 2 standardization:

- Feishu publish is blocked.
- GitHub workflow dispatch is blocked.
- Webhook calls are blocked.
- External publish is blocked.
- Demo artifacts are local and simulated.

## Safety Modes

| Mode | Purpose | Week 2 status |
| --- | --- | --- |
| dry_run | local validation without publishing | implemented |
| skip_llm | evidence-only debugging | implemented |
| output_mode=none | no-publish local or workflow validation | implemented |
| eval/static check | local definition validation | implemented for Phase C checker, runtime integration planned |
| emergency stop | block external actions during review | documented and planned for stronger runtime artifacting |

## No External Boundary

The Week 2 case is intentionally no external. It does not trigger Feishu, GitHub workflow dispatch, webhooks, external publish, provider calls, or LLM calls.

## Status Notes

| Area | Status |
| --- | --- |
| Evidence Gate docs | implemented |
| Publish Gate docs | implemented |
| No external side effects in eval/demo phases | implemented |
| Formal runtime approval artifact | partial |
| Runtime RunManifest gate | planned |
| Dashboard/screenshots | planned P2 / Week 7 Portfolio |

## Source References

- [Gates And Guardrails](../09_GATES_AND_GUARDRAILS.md)
- [Runbook](../12_RUNBOOK.md)
- [Autonomy Matrix](../04_AUTONOMY_MATRIX.md)
- [Sanitized Demo Report](../../demo_run/demo_output_report.md)

## Related Notes

- [[Agent_Autonomy_and_Permission_Boundaries]]
- [[Evidence_First_Intelligence_Agent]]
- [[Sanitized_Demo_Run_Pattern]]
