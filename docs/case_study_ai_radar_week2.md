# AI Radar Week 2 Case Study

Chinese mirror: [docs/zh-CN/case_study_ai_radar_week2.md](zh-CN/case_study_ai_radar_week2.md).

## 1. Title

AI Radar Agent: evidence-first intelligence and publishing agent standardization.

## 2. Context

AI Radar started as a daily AI-industry radar workflow: collect public signals, bind claims to evidence, generate a concise report, audit the output, and publish only when the configured gates allow it. Week 2 standardization turns that project into a clearer agent-product case by documenting the workflow, defining runtime contracts, adding no-side-effect eval cases, and producing a sanitized demo run.

This case study covers the local Week 2 branch only. It does not claim that the demo artifacts are production outputs or live market intelligence.

## 3. Problem

AI news and product signals are noisy. A useful intelligence agent needs more than a prompt: it needs a workflow that can separate evidence collection, evidence qualification, narrative drafting, quality checks, publishing decisions, and observability.

The main risk is overclaiming. Without explicit gates and traceable artifacts, an agent can turn stale, weak, duplicated, or unsupported signals into confident narrative. For a publishing workflow, a second risk is side effects: document creation, bot messages, workflow dispatch, or provider calls must remain under human control.

## 4. Design Goal

The Week 2 goal was to standardize AI Radar as an evidence-first agent case:

- Make the workflow legible from recall to publish gate.
- Document autonomy boundaries and tool permissions.
- Define RunManifest and ToolCall contracts for future runtime observability.
- Add local eval definitions that forbid external side effects.
- Produce a sanitized demo run that shows the artifact shape without production execution.
- Keep all work local and reviewable.

## 5. Constraints

- No production pipeline execution.
- No RSS, Bocha, Tavily, LLM, Feishu, webhook, GitHub workflow, or external publish calls.
- No business-code or prompt-source changes.
- No reading of secrets, `.env` values, tokens, webhooks, cookies, private logs, localStorage, private notes, private runtime outputs, or private artifacts.
- Demo output must be deterministic mock data or derived from Week 2 docs.
- External publishing remains intentionally disabled for Week 2.

## 6. Architecture

```text
Sources
  -> Evidence Collection
  -> Evidence Gate
  -> Intelligence Draft
  -> Report / Brief / Top Event Audits
  -> Publish Gate
  -> Local Artifacts / Optional Future Publishing
```

The architecture is organized around gates rather than a single autonomous generation step. Source recall and local artifact writing can be automated in safe contexts; external publishing and workflow dispatch are treated as high-risk side effects.

## 7. Evidence-First Workflow

The workflow begins with a Beijing natural-day window, then collects public signals through configured recall sources in the real system. Evidence is filtered, deduped, checked against history, and carried into report and brief generation through source-bound artifacts.

Week 2 documents the workflow in [docs/03_WORKFLOW.md](03_WORKFLOW.md). It also records existing artifacts such as evidence, report lint, brief, top event audit, and publish result files in [docs/11_OBSERVABILITY.md](11_OBSERVABILITY.md).

In the sanitized demo, evidence items are mock records in [demo_run/demo_evidence_items.jsonl](../demo_run/demo_evidence_items.jsonl). They are not live data and were not fetched from the network.

## 8. Safety And Autonomy Model

The autonomy model distinguishes low-risk local actions from external side effects:

- Local/static checks are allowed.
- Demo artifacts are local and simulated.
- Eval definitions forbid Feishu, webhook, GitHub workflow dispatch, external publish, provider calls, and production pipeline execution.
- Publish and bot-send paths remain gated and require explicit human approval outside the Week 2 demo/eval context.

The main references are [docs/04_AUTONOMY_MATRIX.md](04_AUTONOMY_MATRIX.md), [docs/06_TOOLS_AND_PERMISSIONS.md](06_TOOLS_AND_PERMISSIONS.md), and [docs/09_GATES_AND_GUARDRAILS.md](09_GATES_AND_GUARDRAILS.md).

## 9. Schema Contracts

Phase B adds two schema contracts:

- [schemas/run_manifest.schema.json](../schemas/run_manifest.schema.json) defines a sanitized run-level manifest shape.
- [schemas/tool_call.schema.json](../schemas/tool_call.schema.json) defines a sanitized per-tool-call record shape.

These are implemented schema contracts, not proof of runtime emission. Runtime generation of RunManifest and ToolCall records remains planned.

## 10. Eval Suite

Phase C adds 10 local eval case definitions in [evals/ai_radar_week2_eval_cases.jsonl](../evals/ai_radar_week2_eval_cases.jsonl). The cases cover evidence gates, publish gates, tool permissions, safety mode, schema contracts, observability, redaction, failure handling, static eval checks, and emergency stop.

The static checker [evals/check_ai_radar_week2_eval_cases.py](../evals/check_ai_radar_week2_eval_cases.py) validates the case file and Phase B schema JSON. It is local-only: it does not import production code, call external APIs, invoke LLMs, trigger Feishu or GitHub, or run the production pipeline.

Runtime eval integration remains planned.

## 11. Sanitized Demo Run

Phase D adds a deterministic local demo under [demo_run/](../demo_run/). The manifest explicitly uses:

```json
{
  "execution_mode": "demo_sandbox",
  "runtime_status": "simulated"
}
```

The demo includes:

- `demo_manifest.json`: simulated run-level manifest.
- `demo_tool_calls.jsonl`: simulated ToolCall records.
- `demo_evidence_items.jsonl`: simulated evidence items.
- `demo_output_report.md`: human-readable sanitized demo report.

The demo is not production execution, not live recall, not external model output, and not externally published.

## 12. Implemented Vs Partial Vs Planned

| Area | Status | Notes |
| --- | --- | --- |
| Phase A workflow docs | implemented | Core workflow, autonomy, tools, gates, eval plan, observability, and runbook are documented. |
| Phase B schema contracts | implemented | RunManifest and ToolCall schemas exist. |
| Runtime RunManifest / ToolCall emission | planned | Runtime integration is not fully implemented. |
| Phase C eval definitions | implemented | 10 no-side-effect cases exist. |
| Phase C static checker | implemented | Local checker validates eval definitions and schema JSON. |
| Runtime eval execution | planned | The checker validates definitions, not real runtime behavior. |
| Phase D sanitized demo run | implemented | Demo artifacts are deterministic mock data. |
| External publishing during Week 2 | intentionally disabled | No Feishu, webhook, workflow dispatch, or external publish action was triggered. |
| Dashboard and screenshots | planned P2 / Week 7 Portfolio | Not included in this curated public mirror. |
| Obsidian-ready pattern notes | private/omitted | Pattern-note exports are not part of the curated public showcase. |

## 13. Lessons Learned

- Workflow design should precede agent autonomy.
- Evidence quality and source binding need explicit gates before narrative generation.
- Publishing agents need side-effect boundaries, not just output formatting.
- Schema contracts can clarify intended observability before runtime integration is built.
- Static eval definitions are useful only when they clearly state what they do not execute.
- A sanitized demo can make an agent case reviewable without exposing private artifacts or triggering external systems.

## 14. Next Steps

- Pattern notes and private knowledge-base material remain outside this curated public showcase.
- Future runtime work: emit RunManifest and ToolCall records from real runs.
- Future eval work: validate emitted manifests and selected runtime outputs locally.
- Portfolio work: optional read-only dashboard/screenshots from sanitized artifacts.
- Optional PR/review after explicit approval.
