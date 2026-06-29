# Public Mirror Scope

This repository is a sanitized public mirror of a private production AI Radar
Agent.

It is intended for portfolio and case-study review. It is not intended to
reproduce the private production deployment end to end.

For visual workflow and boundary diagrams, see
[docs/ARCHITECTURE_OVERVIEW.md](ARCHITECTURE_OVERVIEW.md).

For high-level operating principles, see
[docs/STRATEGY_PANEL.md](STRATEGY_PANEL.md).

## Purpose

- Review the evidence-first intelligence-agent architecture.
- Review workflow design, autonomy boundaries, gates, schemas, evals,
  selected code slices, and sanitized demo artifacts.
- Show the Cloudflare plus GitHub Actions trigger pattern without exposing live
  deployment state.
- Make the public safety posture inspectable without publishing private runtime
  data.

## Included

- Selected Python code slices needed to understand representative runtime
  design choices.
- Architecture, workflow, gate, runbook, observability, and case-study
  documentation.
- `RunManifest` and `ToolCall` schema contracts.
- No-side-effect eval definitions and the static checker.
- Sanitized simulated demo artifacts.
- Mirror-safe Cloudflare Worker pattern files.
- A manual static-check workflow for public mirror validation.

## Excluded

- `.env`, `.env.*`, `.dev.vars`, tokens, webhook configs, and secrets.
- Production `state/event_history.jsonl`.
- Real Feishu document URLs and publication history.
- Production outputs, raw run artifacts, private logs, private runtime state,
  and private operational notes.
- Private production prompts and source configuration.
- Private Cloudflare, GitHub, Feishu, provider, and account settings.
- Production-only Python modules, provider integrations, Feishu publishing
  implementation, full regression tests, packaging metadata, and raw state.

In the private production repo, source configuration and report prompts are
kept in files such as `config/sources.yaml` and `prompts/radar_prompt.md`.
Those files are intentionally excluded from this public mirror.

## What Can Be Reviewed

- Evidence Gate and Publish Gate design.
- Autonomy and tool-permission boundaries.
- Redaction and no-side-effect posture.
- Runtime schema direction.
- Static eval methodology.
- Sanitized demo artifact shape.
- Representative report reconciliation code.
- Cloudflare/GitHub trigger pattern as architecture, not live deployment.

## Local Checks

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

## Runability Boundary

This mirror is optimized for architecture and safety review.

A real production deployment requires private GitHub settings, Cloudflare
settings, Feishu app/bot credentials, provider keys, production
prompts/configuration, and runtime state outside this public repository.

## Public Safety Posture

- The checked-in demo is simulated and sanitized.
- The checked-in evals are local and no-side-effect.
- The checked-in Cloudflare config is mirror-safe by default.
- Production secrets, raw outputs, webhook configs, and state are not included.
