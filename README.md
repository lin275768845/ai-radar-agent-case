# AI Radar Agent

Chinese mirror: [README.zh-CN.md](README.zh-CN.md).

## At a glance

AI Radar Agent is an evidence-first intelligence agent for tracking AI
industry signals. It collects public signals such as model releases, agent
products, enterprise adoption, infrastructure changes, policy developments,
and funding events; then filters them through source-quality checks, reporting
windows, recent-history deduplication, and an Evidence Gate before generating a
source-bound daily radar report.

Its value is not simply "writing a daily newsletter automatically." The system
separates evidence collection, evidence gating, LLM-based synthesis, report
linting, top-event auditing, publish gating, and human-owned external actions.

The LLM participates in three bounded parts of the workflow:

- Report generation: turning accepted, source-bound evidence into the daily
  radar report.
- Brief/card generation and repair: producing structured brief content and
  resolving it back to the evidence catalog when possible.
- Optional final-top audit: reviewing final top candidates against recent
  history for high-confidence duplicate signals after deterministic dedupe.

The LLM is used to summarize, structure, rank, and explain evidence-bound
signals. It is not treated as the source of truth, does not collect sources,
does not own the main deduplication logic, and cannot decide whether publishing
is allowed.

In short, this mirror shows how a real AI information workflow can be
standardized into an auditable intelligence Agent: one that can explain why an
event was selected, trace the evidence behind it, evaluate output quality, and
control when publishing is allowed.

## Public Case-Study Mirror

This repository is a sanitized public mirror of a production AI Radar Agent.
It is published for portfolio review, architecture review, workflow review,
evidence-first intelligence-agent design review, safety/autonomy boundary
review, eval/schema/demo review, and case-study review.

It is not a full production clone. It is not connected to the live Cloudflare,
Feishu, or GitHub production deployment. The private production repository
remains separate.

Production secrets, private configuration, raw production outputs, real Feishu
publication history, private runtime state, and production
`state/event_history.jsonl` are intentionally excluded.

For the concise scope statement, see
[docs/PUBLIC_MIRROR_SCOPE.md](docs/PUBLIC_MIRROR_SCOPE.md).

Visual architecture guide:
[docs/ARCHITECTURE_OVERVIEW.md](docs/ARCHITECTURE_OVERVIEW.md).

Agent strategy panel:
[docs/STRATEGY_PANEL.md](docs/STRATEGY_PANEL.md).

## What This Mirror Is

- A sanitized portfolio mirror based on a real production AI intelligence
  agent.
- A case-study repository for evidence-first intelligence-agent architecture.
- A review target for workflow design, gates, autonomy boundaries, schema
  contracts, evals, demo artifacts, and public safety posture.
- A curated public artifact that shows the shape of the system without
  exposing credentials, private runtime state, or production publishing
  history.

## What This Mirror Is Not

- Not a turnkey deployment repository.
- Not a full clone of the private production repo.
- Not connected to live Cloudflare, Feishu, provider, or GitHub production
  settings.
- Not intended to reproduce the private production pipeline end to end after
  clone.
- Not a place where production secrets, raw outputs, webhook configs, or
  private operational notes are stored.
- Not a complete source export; production-only modules and tests are omitted
  to keep the public review surface focused.

## What You Can Review

- Evidence-first workflow from public-source recall to Evidence Gate, report
  generation, report linting, Publish Gate, and review artifacts.
- Safety and autonomy boundaries for local work, provider calls, GitHub
  Actions, Feishu publishing, and external notifications.
- `RunManifest` and `ToolCall` schema contracts for future runtime
  observability.
- No-side-effect eval definitions and the local static checker under
  `evals/`.
- Sanitized simulated demo artifacts under `demo_run/`.
- Cloudflare plus GitHub Actions trigger pattern as a reviewable deployment
  pattern, not as a live deployment.
- Selected runtime code slices, especially report reconciliation logic and the
  Cloudflare trigger pattern.

## What You Can Run Locally

These checks are local. They require no secrets, no provider keys, and no
external side effects:

```bash
python3 evals/check_ai_radar_week2_eval_cases.py
python3 -m json.tool demo_run/demo_manifest.json
python3 -m py_compile \
  ai_radar_agent/dates.py \
  ai_radar_agent/models.py \
  ai_radar_agent/report_reconcile.py \
  tests/test_report_reconcile.py \
  tests/test_cloudflare_trigger.py
```

The full private production pipeline is intentionally out of scope for this
mirror.

## What Is Intentionally Excluded

- `.env`, `.env.*`, `.dev.vars`, token files, webhook configs, and secrets.
- Production `state/event_history.jsonl`.
- Real Feishu document URLs and publication history.
- Production outputs, raw run artifacts, private logs, private runtime state,
  and private operational notes.
- Cloudflare, GitHub, Feishu, search-provider, and LLM secrets.
- Private production source configuration.
- Private production prompts.
- Private deployment settings and account-level configuration.
- Production-only Python modules, provider integrations, Feishu publishing
  implementation, full regression tests, packaging metadata, and raw state.

In the private production repo, source configuration and report prompts are
kept in files such as `config/sources.yaml` and `prompts/radar_prompt.md`.
Those files are intentionally excluded from this public mirror.

## Runability Boundary

This mirror is optimized for reviewable architecture and safety patterns, not
for clone-and-run production deployment.

End-to-end production execution requires private GitHub repository settings,
Cloudflare Worker settings, Feishu app/bot credentials, provider keys,
production prompts/configuration, production state, and deployment controls
that are not included here.

## Project Overview

AI Radar Agent is an evidence-first intelligence and publishing agent. It
collects public AI industry signals, filters them through evidence and quality
gates, generates a source-aware daily radar report, and publishes only when
human-controlled publish gates allow it.

The public mirror focuses on the agent design:

- Recall before generation.
- Evidence before narrative.
- Schema contracts before runtime observability.
- Gates before publish.
- Local evals before broader automation.
- Redacted artifacts before public storytelling.

## Current Status

| Area | Public mirror status | Notes |
| --- | --- | --- |
| Core workflow docs | Implemented | Workflow, autonomy, tools, gates, eval plan, observability, and runbook are documented. |
| `RunManifest` / `ToolCall` schemas | Implemented | Contracts exist in `schemas/`; runtime emission remains planned. |
| Static eval definitions | Implemented | 10 no-side-effect eval cases are defined in JSONL. |
| Static eval checker | Implemented | Local checker validates eval definitions and schema JSON. |
| Runtime eval integration | Planned | The checker validates definitions, not live runtime behavior. |
| Sanitized demo run | Implemented | Demo artifacts are deterministic mock data and explicitly simulated. |
| Chinese docs | Implemented | Chinese mirror docs live in `README.zh-CN.md` and `docs/zh-CN/`. |
| Selected code slices | Implemented | The mirror keeps representative report reconciliation and trigger-pattern code, not the full production codebase. |
| External publish | Private/human-gated | Real publish controls belong to the private production environment. |
| Dashboard/screenshots | Planned | Not included in this curated showcase mirror. |

## Workflow Sketch

```text
Trigger pattern or local operator
  -> Beijing natural-day window
  -> public-source recall
  -> Evidence Gate and event-history checks
  -> filtered evidence artifacts
  -> report generation path
  -> report lint and brief validation
  -> final top-event reconciliation
  -> Publish Gate
  -> local artifacts or private production publish path
```

The public mirror includes selected code slices, docs, schemas, evals, and
sanitized demo artifacts that make this workflow reviewable. It does not
include the private configuration or complete production implementation
required to run the production path end to end.

## Review Map

| Artifact | Purpose |
| --- | --- |
| [docs/PUBLIC_MIRROR_SCOPE.md](docs/PUBLIC_MIRROR_SCOPE.md) | Scope and runability boundary for this public mirror. |
| [docs/STRATEGY_PANEL.md](docs/STRATEGY_PANEL.md) | High-level operating doctrine for signal selection, evidence gates, publish gates, and human control. |
| [docs/ARCHITECTURE_OVERVIEW.md](docs/ARCHITECTURE_OVERVIEW.md) | Visual workflow, trigger, observability, and public/private boundary guide. |
| [docs/03_WORKFLOW.md](docs/03_WORKFLOW.md) | Workflow stages from recall to artifacts and publish gate. |
| [docs/04_AUTONOMY_MATRIX.md](docs/04_AUTONOMY_MATRIX.md) | Autonomy boundaries and human-approval points. |
| [docs/06_TOOLS_AND_PERMISSIONS.md](docs/06_TOOLS_AND_PERMISSIONS.md) | Tool permission matrix and side-effect classes. |
| [docs/09_GATES_AND_GUARDRAILS.md](docs/09_GATES_AND_GUARDRAILS.md) | Evidence, report, brief, publish, privacy, and manifest gates. |
| [docs/10_EVAL_PLAN.md](docs/10_EVAL_PLAN.md) | Eval strategy and static checker status. |
| [docs/11_OBSERVABILITY.md](docs/11_OBSERVABILITY.md) | Current artifacts, observability gaps, and manifest direction. |
| [docs/12_RUNBOOK.md](docs/12_RUNBOOK.md) | Safe local modes, common failures, and emergency stop guidance. |
| [docs/13_RUNTIME_OBJECT_MAP.md](docs/13_RUNTIME_OBJECT_MAP.md) | Relationship between manifests, tool calls, gates, evals, and demos. |
| [schemas/run_manifest.schema.json](schemas/run_manifest.schema.json) | Run-level schema contract for sanitized execution manifests. |
| [schemas/tool_call.schema.json](schemas/tool_call.schema.json) | Per-tool-call schema contract for sanitized tool metadata. |
| [evals/ai_radar_week2_eval_cases.jsonl](evals/ai_radar_week2_eval_cases.jsonl) | No-side-effect eval case definitions. |
| [evals/check_ai_radar_week2_eval_cases.py](evals/check_ai_radar_week2_eval_cases.py) | Local static checker. |
| [demo_run/demo_output_report.md](demo_run/demo_output_report.md) | Sanitized simulated demo report. |
| [docs/case_study_ai_radar_week2.md](docs/case_study_ai_radar_week2.md) | Public case-study draft. |
| [ai_radar_agent/report_reconcile.py](ai_radar_agent/report_reconcile.py) | Representative runtime code slice for report/brief reconciliation. |
| [cloudflare/ai-radar-trigger/src/index.js](cloudflare/ai-radar-trigger/src/index.js) | Mirror-safe Worker trigger-pattern code. |

## Public Repository Structure

```text
.
├── ai_radar_agent/          # Selected Python code slices for review
├── cloudflare/              # Mirror-safe Worker trigger pattern
├── demo_run/                # Sanitized simulated demo artifacts
├── docs/                    # Curated architecture, workflow, and safety docs
├── evals/                   # Static no-side-effect eval cases and checker
├── schemas/                 # RunManifest / ToolCall schema contracts
├── tests/                   # Representative tests for retained code slices
├── .github/workflows/       # Manual workflow pattern
└── README.md
```

## Demo Artifacts

The `demo_run/` directory contains deterministic, sanitized, simulated
artifacts. They are designed to show artifact shape and safety posture without
using production data.

Included demo artifacts:

- `demo_manifest.json`
- `demo_tool_calls.jsonl`
- `demo_evidence_items.jsonl`
- `demo_output_report.md`

They are not live market intelligence and should not be described as production
outputs.

## Cloudflare And GitHub Actions Pattern

The mirror includes a Cloudflare Worker trigger pattern under
`cloudflare/ai-radar-trigger/` and a manual GitHub Actions static-check
workflow under `.github/workflows/`.

These files are included for architecture and safety review. They are not
evidence that this public repository is deployed to Cloudflare or connected to
live Feishu/provider credentials.

The committed mirror defaults are safe for public review:

- `GITHUB_REPO = "ai-radar-agent-case"`
- `GITHUB_REF = "main"`
- `BOCHA_ENABLED = "false"`

Private production deployments must override deployment settings and secrets
outside this public repository.

## Safety And Privacy Notes

- Do not commit `.env`, secrets, tokens, cookies, webhooks, private logs, or
  real credentials.
- Do not paste real Feishu, GitHub, DeepSeek, Bocha, Tavily, Cloudflare, or
  provider secrets into issues, docs, prompts, logs, or chat.
- Treat production `outputs/` and production `state/event_history.jsonl` as
  private operational artifacts.
- Logs and summaries should stay redacted. They should not emit full prompts,
  full evidence payloads, LLM payloads, HTTP headers, secrets, or webhook URLs.
- External publishing, workflow dispatch, Feishu bot sends, and deployment
  changes remain human-owned production actions.

## Maintenance Notes

- Keep this public README focused on architecture, workflow, safety, evals,
  schemas, and sanitized demos.
- Keep private production runbooks, prompts, source configs, and state outside
  the public mirror.
- Keep production-only implementation files out of the public showcase unless
  they materially improve architecture review.
- When updating docs, preserve the distinction between implemented, partial,
  planned, simulated, and private-production-only behavior.
- When updating Cloudflare examples, keep defaults mirror-safe and avoid real
  account IDs, tokens, worker URLs, webhook URLs, or secrets.

## License

License not yet specified. This repository is published for portfolio review;
reuse rights are not granted unless a license is later added.
