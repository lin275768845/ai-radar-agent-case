---
type: pattern-note
project: AI Radar Agent
phase: Week 2
status: implemented
privacy: sanitized
external_side_effects: none
tags:
  - ai-radar
  - runmanifest
  - toolcall
  - schema-contract
  - pattern-note
---

# RunManifest and ToolCall Contracts

## Pattern

Schema contracts make agent behavior reviewable before full runtime integration exists. AI Radar uses RunManifest and ToolCall schemas to describe the intended shape of sanitized run-level and per-tool-call traces.

## RunManifest Purpose

RunManifest is the intended run-level object for:

- execution mode and safety mode
- input summary
- source and evidence summary
- ToolCall references
- gate results
- artifact references
- publish decisions
- external side effect records
- warnings, errors, metrics, and redaction status

## ToolCall Purpose

ToolCall is the intended per-tool-call record for:

- tool name and category
- permission class
- purpose
- status
- redacted input and output summaries
- evidence, artifact, and gate references
- network access
- external_side_effects classification
- dry-run and sensitive-data policy

## Contract Vs Runtime Emission

| Item | Status | Meaning |
| --- | --- | --- |
| RunManifest schema | implemented | Contract exists in the repo. |
| ToolCall schema | implemented | Contract exists in the repo. |
| Runtime RunManifest emission | planned | Current runtime does not emit a formal manifest artifact. |
| Runtime ToolCall trace emission | planned | Current runtime does not emit a formal tool-call trace artifact. |
| Demo manifest alignment | partial | Phase D demo conceptually follows the contract with simulated data. |

## Redaction And Sensitive Data Handling

The contracts require redacted summaries and references. They must not store raw secrets, tokens, webhook URLs, cookies, credentials, private logs, private note contents, localStorage dumps, or private runtime outputs.

## Source References

- [Runtime Object Map](../13_RUNTIME_OBJECT_MAP.md)
- [RunManifest Schema](../../schemas/run_manifest.schema.json)
- [ToolCall Schema](../../schemas/tool_call.schema.json)
- [Observability](../11_OBSERVABILITY.md)
- [Sanitized Demo Manifest](../../demo_run/demo_manifest.json)

## Related Notes

- [[Evidence_First_Intelligence_Agent]]
- [[No_Side_Effect_Eval_Suite]]
- [[Sanitized_Demo_Run_Pattern]]
