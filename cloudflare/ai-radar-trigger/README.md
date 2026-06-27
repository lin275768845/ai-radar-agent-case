# Cloudflare AI Radar Trigger Pattern

This directory is included in the public mirror to show the Cloudflare Worker trigger pattern used by AI Radar-style deployments. It is documentation and review material for the sanitized portfolio mirror, not evidence that this public repository is connected to a live Cloudflare, Feishu, or GitHub production deployment.

Default mirror schedule in `wrangler.toml`:

```text
0 2 * * *
```

Cloudflare cron uses UTC, so this is 10:00 Asia/Shanghai.

## Mirror-Safe Defaults

The committed `wrangler.toml` uses mirror-safe defaults:

- `GITHUB_REPO = "ai-radar-agent-case"`
- `GITHUB_REF = "main"`
- `BOCHA_ENABLED = "false"`

Production deployments should override these values through private Cloudflare environment variables or private deployment configuration outside this public repository.

## Required Variables For A Private Deployment

Configure these in Cloudflare Worker settings:

- `GITHUB_OWNER`: defaults to `lin275768845`
- `GITHUB_REPO`: defaults to `ai-radar-agent-case` in this public mirror
- `GITHUB_WORKFLOW`: defaults to `daily.yml`
- `GITHUB_REF`: defaults to `main`

When `GITHUB_REF=main`, also set the GitHub repository variable
`EVENT_HISTORY_COMMIT_REF=main` so the workflow can write
`state/event_history.jsonl` back to the same ref.

Optional control variables. The workflow input `bocha_enabled` is always sent explicitly:

- `BOCHA_ENABLED`: set to `false` in the committed mirror config. A private production deployment may override it outside the repository if Bocha should be enabled.

Configure these as secrets:

- `GITHUB_TOKEN`: GitHub fine-grained token with Actions read/write for the repository.
- `MANUAL_TRIGGER_SECRET`: long random secret for manual `/trigger` calls.

Do not commit real tokens or secrets to this repository.
Keep `BOCHA_API_KEY` in GitHub Actions secrets only; do not store or print it in Worker docs or logs.
Manual `/trigger` bearer secrets are not included in this mirror.

## Manual Trigger

Use an Authorization header, not a query parameter:

```bash
curl -X GET \
  -H "Authorization: Bearer <MANUAL_TRIGGER_SECRET>" \
  https://<worker-name>.<account>.workers.dev/trigger
```

The Worker returns `202` quickly and dispatches GitHub in the background. In this public mirror, treat this as a pattern to review. A real deployment requires private Cloudflare, GitHub, Feishu, and provider secrets configured outside the repo.

## Notes

- GitHub API 429 / 5xx responses are retried up to three times.
- Logs include GitHub status and a short sanitized response body.
- Logs never print `GITHUB_TOKEN` or `MANUAL_TRIGGER_SECRET`.
- Bocha is controlled by the explicit `bocha_enabled` workflow input. Do not rely on GitHub repo variable `BOCHA_ENABLED` for manual or Cloudflare-triggered runs.
- This public mirror contains the Worker pattern only. Production deployment requires private Cloudflare, GitHub, Feishu, and provider environment variables/secrets configured outside the repository.
