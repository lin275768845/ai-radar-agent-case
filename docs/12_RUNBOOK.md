# 12 Runbook

- Project: AI Radar Agent
- Agent Type: Intelligence / research / daily report publishing agent
- Status: Active
- Last Updated: 2026-06-27
- Owner: Unknown
- Source of Truth: README, `.github/workflows/daily.yml`, evals, schemas, demo artifacts
- Related Files: README.md, `.github/workflows/daily.yml`, `evals/`, `schemas/`, `demo_run/`
- Public Mirror Note: this curated mirror omits production CLI, packaging,
  prompt/config files, provider integrations, Feishu publishing code, and raw
  runtime state.

## AS-IS 当前实现

### Operating Rule

Prefer the safest mode that answers the question:

1. Static/read-only inspection.
2. Week 2 static checker when validating eval/schema artifacts.
3. `--skip-llm` for recall only.
4. `--dry-run --output-mode none` for no-publish validation.
5. `--dry-run` for report/brief artifacts without Feishu publish or bot send.
6. Production publish only after explicit human approval.

Do not trigger Feishu, GitHub workflow dispatch, provider writes, bot send, or production publish during documentation, planning, or inspection tasks.

### Public Mirror Local Checks

This curated public mirror is not a production run repository. Run only local
static checks:

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

### Production Run

Production is triggered by Feishu automation calling GitHub Actions `workflow_dispatch` for `.github/workflows/daily.yml`. Current stable code baseline is `main` / `week2_standardization`; `single_card_v7.1` is retained as a previous-runtime rollback branch, and `week2/standardization` is retained as the Week 2 branch snapshot. Production dispatch on `main` requires GitHub repository variable `EVENT_HISTORY_COMMIT_REF=main` so event history writes are allowed.

Recommended production inputs:

```json
{
  "ref": "main",
  "inputs": {
    "date": "",
    "dry_run": "false",
    "skip_llm": "false",
        "send_bot": "true",
        "output_mode": "feishu_docx_import",
        "tavily_enabled": "false",
        "bocha_enabled": "true",
        "force_republish": "false",
        "report_lint_policy": "warn",
        "bot_block_on_lint_critical": "false"
  }
}
```

Bocha is controlled per run by workflow input `bocha_enabled`. Manual and Cloudflare-triggered runs must pass `bocha_enabled=true` intentionally to set `BOCHA_ENABLED=true`; do not rely on a silent repository-variable override.

Production publish requires human approval through ref/input selection. Documentation, local validation, and no-publish workflow validation do not authorize publish.

### Environment Variables

Use variable names only:

- `DEEPSEEK_API_KEY`
- `DEEPSEEK_BASE_URL`
- `DEEPSEEK_MODEL`
- `SEARCH_PROVIDERS`
- `BOCHA_API_KEY`
- `BOCHA_ENABLED`
- `BOCHA_BASE_URL`
- `BOCHA_MAX_QUERIES`
- `BOCHA_MAX_RESULTS_PER_QUERY`
- `BOCHA_CONNECT_TIMEOUT`
- `BOCHA_READ_TIMEOUT`
- `TAVILY_API_KEY`
- `TAVILY_ENABLED`
- `TAVILY_CONNECT_TIMEOUT`
- `TAVILY_READ_TIMEOUT`
- `FEISHU_APP_ID`
- `FEISHU_APP_SECRET`
- `FEISHU_FOLDER_TOKEN`
- `FEISHU_TEMP_FOLDER_TOKEN`
- `FEISHU_BOT_WEBHOOK_URL`
- `FEISHU_BOT_SECRET`
- `RADAR_TIMEZONE`
- `OUTPUT_MODE`
- `SEND_BOT`
- `REPORT_LINT_POLICY`
- `BOT_BLOCK_ON_LINT_CRITICAL`
- `STRICT_REPORT_LINT`
- `MAX_SEARCH_QUERIES_PER_RUN`
- `MAX_SEARCH_RESULTS_PER_PROVIDER`
- `MAX_EVIDENCE_ITEMS`
- `STABILITY_PIPELINE_ENABLED`
- `STABILITY_PIPELINE_MODE`

See `.env.example` and `README.md` for the longer list.

### No Feishu / No Workflow Dispatch Safety Mode

Use these controls for safety:

- `--dry-run`
- `--skip-llm`
- `--output-mode none`
- `SEND_BOT=false`
- `REPORT_LINT_POLICY=block_bot` when bot sending must be blocked on critical lint

Do not call GitHub workflow dispatch, Feishu API, Cloudflare API, or bot webhook from Codex unless the user explicitly asks for that external side effect in the current task.

### Common Failures

| Symptom | Likely Cause | Safe Check | Recovery |
|---|---|---|---|
| Missing `DEEPSEEK_API_KEY` | secret not configured | GitHub Actions env/secrets | add secret and rerun |
| No evidence | all providers empty/failed | inspect `evidence.md` provider audit | rerun, enable Bocha/Tavily, check sources |
| Report lint errors | report format/source mismatch | inspect `report_lint.json` | adjust prompt or rerun after evidence check |
| Feishu docx fallback to MD | import permission/timeout/API error | Summary `docx_error_summary` | check Feishu app permissions; MD fallback is expected |
| Bot skipped | dry-run, output none, missing webhook, send false, lint policy | Summary bot fields | configure webhook or adjust policy |
| Bot signature error | wrong `FEISHU_BOT_SECRET` | Summary `response_msg` | use bot signing secret, not app secret |
| Duplicate publish | cross-run state missing | check Feishu folder and `publish_result.json` | use `force_republish=false`; manual cleanup if needed |
| Source ID mismatch | brief source IDs not in evidence catalog | inspect `brief.json` counters and unresolved samples | keep `sources=[]` rather than invent URLs; fix source binding later |
| Final Top duplicate or stale event | recent history or weak same-day signal | inspect `final_top_dedupe.json`, `final_top_llm_audit.json`, `top_event_audit.json` | confirm new signal or let gate drop/demote |

### Retry Policy

- RSS failures: warn and continue.
- Bocha/Tavily: limited retry for transient/rate/server errors; auth/bad request stops or skips.
- DeepSeek report call: tenacity retry.
- Feishu token/upload/import/poll: retry for transient errors.
- Feishu bot: posts cards; payload invalid can try text fallback.

### Rerun Procedure

1. Inspect GitHub Summary.
2. Download or inspect `ai-radar-outputs`.
3. If publish happened and should not duplicate, leave `force_republish=false`.
4. If only evidence needs debugging, rerun with `skip_llm=true`.
5. If publish should be skipped, rerun with `dry_run=true` or `output_mode=none`.
6. If a confirmed publish should be replaced, use `force_republish=true` deliberately.

### Eval / Static Check Procedure

Week 2 static checks are implemented for eval definitions and schema JSON. Runtime eval integration remains planned.

1. Run `python3 evals/check_ai_radar_week2_eval_cases.py`.
2. Run `python3 -m json.tool demo_run/demo_manifest.json >/dev/null`.
3. Confirm no external side effects are triggered.
4. Do not treat static checker success as proof that a live production publish is safe without workflow validation.

### Rollback Procedure

Current rollback is manual by selecting a known good GitHub ref/tag/branch in workflow dispatch or Feishu automation. Confirm the target ref with the project owner before changing production automation. Current stable baseline is `main` / `week2_standardization`; rollback refs are `single_card_v7.1`, `week2/standardization`, and fixed tag `v5.2.0-rollback`; create a temporary branch from the v5.2 tag only if v5.2 must be exercised.

### Duplicate Prevention

Current duplicate prevention is local to `outputs/<date>/publish_result.json`. It does not fully prevent duplicates across separate GitHub Action runs because artifacts are temporary.

### Prompt Change Procedure

Production prompt files are intentionally excluded from this public mirror.
Prompt changes belong in the private production repository and require human
authorization, relevant tests, dry-run validation, and publish-gate review.

### Schema Change Procedure

Scaffold schemas exist under `schemas/`, but runtime validation has not migrated to them. For model/normalization changes:

1. Update tests first or alongside code.
2. Preserve current artifact compatibility.
3. Update `docs/05_DATA_MODEL.md`.
4. Validate with focused pytest targets.

### Deployment Checklist

- Production ref has been confirmed in the external dispatcher. Current production configurations should use `main` with `EVENT_HISTORY_COMMIT_REF=main`; existing `single_card_v7.1` dispatchers are rollback/manual-only until explicitly switched.
- GitHub Actions enabled.
- Required secrets present.
- Feishu app has folder and docx import permissions.
- Feishu folder token points to the intended folder.
- `OUTPUT_MODE=feishu_docx_import`.
- `SEARCH_PROVIDERS` set intentionally.
- `TAVILY_ENABLED=false` unless quota use is intended.
- `dry_run=false` only for real publish.
- `send_bot=true` only when webhook is configured and intended.

### Emergency Stop

- Disable Feishu automation trigger, or change it to a safe ref/input.
- Set `dry_run=true`, `output_mode=none`, or `send_bot=false` for manual runs.
- Remove/disable Feishu bot webhook secret if message sending must stop.
- Do not delete Feishu documents automatically; use manual cleanup unless a cleanup workflow is explicitly approved.
- Do not trigger Cloudflare Worker dispatch during emergency review unless explicitly approved.

### Safe Debug Procedure

Use this order:

1. `--skip-llm` for recall only.
2. `--dry-run --output-mode none` or `--skip-llm` for safe local validation.
3. `--dry-run` for report/brief without publish.
4. `output_mode=none` if GitHub run should skip Feishu publish.

## GAPS 当前缺口

- No formal rollback automation.
- No cross-run publish dedupe.
- `RunManifest` / `ToolCall` contracts exist, but runtime emission is not implemented.
- Failure notification behavior in README is not confirmed by current workflow file.

## TO-BE 后续建议

- Add `run_manifest.json` and a clear run-state store.
- Add a non-publishing eval workflow.
- Add production-ref validation in docs and eventually code.
- Add a controlled cleanup procedure only after approval gates exist.
