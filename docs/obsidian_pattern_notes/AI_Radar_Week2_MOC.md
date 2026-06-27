---
type: pattern-note
project: AI Radar Agent
phase: Week 2
status: implemented
privacy: sanitized
external_side_effects: none
tags:
  - ai-radar
  - agent-engineering
  - moc
  - pattern-note
---

# AI Radar Week2 MOC

Chinese mirror: [zh-CN/AI_Radar_Week2_MOC.md](zh-CN/AI_Radar_Week2_MOC.md).

## Summary

AI Radar Week 2 standardizes an evidence-first intelligence and publishing agent case. The work turns the agent into a reviewable portfolio artifact by documenting workflow, autonomy boundaries, gates, schema contracts, eval definitions, and a sanitized simulated demo run.

This folder contains Obsidian-ready export notes only. These notes were created inside the repo and were not imported into any vault.

## Pattern Notes

- [[Evidence_First_Intelligence_Agent]]
- [[Agent_Autonomy_and_Permission_Boundaries]]
- [[RunManifest_and_ToolCall_Contracts]]
- [[No_Side_Effect_Eval_Suite]]
- [[Sanitized_Demo_Run_Pattern]]
- [[Publishing_Gates_and_Safety_Model]]

## Snapshot

| Area | Status | Notes |
| --- | --- | --- |
| Phase A docs | implemented | Workflow, autonomy, tools, gates, eval plan, observability, and runbook are documented. |
| Phase B schema contracts | implemented | RunManifest and ToolCall contracts exist. |
| Phase C eval cases and static checker | implemented | 10 local no-side-effect eval cases and a checker exist. |
| Phase D sanitized demo run | implemented | Demo artifacts are deterministic and simulated. |
| Phase E README and case study | implemented | Portfolio README and case study draft exist. |
| Phase F Obsidian-ready notes | implemented | Repo-local sanitized notes are export-ready. |
| Runtime RunManifest and ToolCall emission | planned | Schema contracts exist, but runtime emission remains future work. |
| Runtime eval integration | planned | Static checker validates definitions, not live runtime behavior. |
| External publish integration | partial | Runtime has publishing paths, but Week 2 notes and demo do not enable external publishing. |
| Feishu publish and GitHub workflow dispatch | planned/manual for this case | Not triggered or enabled by Week 2 standardization artifacts. |
| Dashboard and screenshots | planned | P2 / Week 7 Portfolio. |

## Repo Artifact Map

- [README](../../README.md)
- [Case Study](../case_study_ai_radar_week2.md)
- [Workflow](../03_WORKFLOW.md)
- [Autonomy Matrix](../04_AUTONOMY_MATRIX.md)
- [Tools And Permissions](../06_TOOLS_AND_PERMISSIONS.md)
- [Gates And Guardrails](../09_GATES_AND_GUARDRAILS.md)
- [Eval Plan](../10_EVAL_PLAN.md)
- [Observability](../11_OBSERVABILITY.md)
- [Runbook](../12_RUNBOOK.md)
- [Runtime Object Map](../13_RUNTIME_OBJECT_MAP.md)
- [RunManifest Schema](../../schemas/run_manifest.schema.json)
- [ToolCall Schema](../../schemas/tool_call.schema.json)
- [Eval Cases](../../evals/ai_radar_week2_eval_cases.jsonl)
- [Eval Checker](../../evals/check_ai_radar_week2_eval_cases.py)
- [Sanitized Demo Report](../../demo_run/demo_output_report.md)
- [Sanitized Demo Manifest](../../demo_run/demo_manifest.json)

## Export Boundary

These notes are sanitized and portfolio-safe. They do not contain secrets, private note contents, private paths, private runtime outputs, or raw production artifacts.
