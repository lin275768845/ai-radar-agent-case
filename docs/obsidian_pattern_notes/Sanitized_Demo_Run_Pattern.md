---
type: pattern-note
project: AI Radar Agent
phase: Week 2
status: implemented
privacy: sanitized
external_side_effects: none
tags:
  - ai-radar
  - demo-run
  - sanitized-artifact
  - pattern-note
---

# Sanitized Demo Run Pattern

## Pattern

A sanitized demo run gives reviewers a concrete artifact set without exposing private runtime outputs or triggering external systems. It should be deterministic, labeled as simulated, and separated from production execution.

## Phase D Demo

The AI Radar demo run is stored under `demo_run/` and includes:

- `demo_manifest.json`
- `demo_tool_calls.jsonl`
- `demo_evidence_items.jsonl`
- `demo_output_report.md`

The manifest includes:

```json
{
  "execution_mode": "demo_sandbox",
  "runtime_status": "simulated"
}
```

## How It Differs From Production Execution

| Dimension | Sanitized demo | Production execution |
| --- | --- | --- |
| Data | deterministic mock data | real runtime evidence |
| Network | none | may use configured providers |
| LLM | skipped or simulated | may call configured model |
| Publish | blocked | requires approval and configured gates |
| Artifacts | portfolio-safe demo files | private runtime outputs that require review |

## Status Notes

| Capability | Status |
| --- | --- |
| Sanitized demo manifest | implemented |
| Simulated ToolCall records | implemented |
| Simulated evidence items | implemented |
| Human-readable demo report | implemented |
| Dashboard/screenshots | planned P2 / Week 7 Portfolio |

## Safety Notes

- Demo artifacts are not production outputs.
- Demo evidence is not live data.
- No external publish happened.
- No actual Obsidian vault was read or modified.

## Source References

- [Sanitized Demo Report](../../demo_run/demo_output_report.md)
- [Sanitized Demo Manifest](../../demo_run/demo_manifest.json)
- [Runtime Object Map](../13_RUNTIME_OBJECT_MAP.md)
- [Case Study](../case_study_ai_radar_week2.md)

## Related Notes

- [[Evidence_First_Intelligence_Agent]]
- [[RunManifest_and_ToolCall_Contracts]]
- [[Publishing_Gates_and_Safety_Model]]
