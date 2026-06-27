# Public Mirror Scope

This repository is a sanitized public mirror of a private production AI Radar Agent. It is intended for portfolio and case-study review, not for reproducing the private production deployment end to end.

## Purpose

- Review the evidence-first intelligence-agent architecture.
- Review workflow design, autonomy boundaries, gates, schemas, evals, and sanitized demo artifacts.
- Show the Cloudflare plus GitHub Actions trigger pattern without exposing live deployment state.

## Included

- Core Python package modules needed to understand the runtime design.
- Architecture, workflow, gate, runbook, observability, and case-study documentation.
- `RunManifest` and `ToolCall` schema contracts.
- No-side-effect eval definitions and static checker.
- Sanitized simulated demo artifacts.
- Mirror-safe Cloudflare Worker pattern files.

## Excluded

- `.env`, `.env.*`, `.dev.vars`, tokens, webhook configs, and secrets.
- Production `state/event_history.jsonl`.
- Real Feishu document URLs and publication history.
- Production outputs, raw run artifacts, private logs, private runtime state, and private operational notes.
- Private production prompts/configuration required for end-to-end production execution.

## Local Checks

```bash
python3 evals/check_ai_radar_week2_eval_cases.py
python3 -m json.tool demo_run/demo_manifest.json
python3 -m py_compile ai_radar_agent/report_reconcile.py tests/test_report_reconcile.py
```

## Runability Boundary

This mirror is optimized for architecture and safety review. A real production deployment requires private GitHub settings, Cloudflare settings, Feishu app/bot credentials, provider keys, production prompts/configuration, and runtime state outside this public repository.
