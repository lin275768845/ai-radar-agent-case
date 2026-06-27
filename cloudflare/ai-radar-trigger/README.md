# Cloudflare AI Radar Trigger

This Worker triggers GitHub Actions `workflow_dispatch` for the single-card AI Radar workflow.

Default schedule in `wrangler.toml`:

```text
0 2 * * *
```

Cloudflare cron uses UTC, so this is 10:00 Asia/Shanghai.

## Required Variables

Configure these in Cloudflare Worker settings:

- `GITHUB_OWNER`: defaults to `lin275768845`
- `GITHUB_REPO`: defaults to `ai-radar-agent`
- `GITHUB_WORKFLOW`: defaults to `daily.yml`
- `GITHUB_REF`: defaults to `main`

When `GITHUB_REF=main`, also set the GitHub repository variable
`EVENT_HISTORY_COMMIT_REF=main` so the workflow can write
`state/event_history.jsonl` back to the same ref.

Optional control variables. The workflow input `bocha_enabled` is always sent explicitly:

- `BOCHA_ENABLED`: set to `true` in the committed Worker config so Cloudflare cron uses Bocha by default and passes workflow input `bocha_enabled=true`. Set to `false` or remove it to pass `bocha_enabled=false`.

Configure these as secrets:

- `GITHUB_TOKEN`: GitHub fine-grained token with Actions read/write for the repository.
- `MANUAL_TRIGGER_SECRET`: long random secret for manual `/trigger` calls.

Do not commit real tokens or secrets to this repository.
Keep `BOCHA_API_KEY` in GitHub Actions secrets only; do not store or print it in Worker docs or logs.

## Manual Trigger

Use an Authorization header, not a query parameter:

```bash
curl -X GET \
  -H "Authorization: Bearer <MANUAL_TRIGGER_SECRET>" \
  https://<worker-name>.<account>.workers.dev/trigger
```

The Worker returns `202` quickly and dispatches GitHub in the background. Check GitHub Actions for the actual run.

## Notes

- GitHub API 429 / 5xx responses are retried up to three times.
- Logs include GitHub status and a short sanitized response body.
- Logs never print `GITHUB_TOKEN` or `MANUAL_TRIGGER_SECRET`.
- Bocha is controlled by the explicit `bocha_enabled` workflow input. Do not rely on GitHub repo variable `BOCHA_ENABLED` for manual or Cloudflare-triggered runs.
- This public mirror contains the Worker pattern only. Production deployment requires private Cloudflare and GitHub environment variables/secrets configured outside the repository.
