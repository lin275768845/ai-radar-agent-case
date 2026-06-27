# Cloudflare AI Radar Trigger Pattern

This directory is included to show the Cloudflare Worker trigger pattern used
by AI Radar-style deployments.

It is public review material for the sanitized portfolio mirror. It is not the
live production Worker config, and this public repository is not connected to a
live Cloudflare, Feishu, provider, or GitHub production deployment.

## Mirror-Safe Defaults

The committed `wrangler.toml` and Worker source use public-mirror defaults:

- `GITHUB_REPO = "ai-radar-agent-case"`
- `GITHUB_REF = "main"`
- `BOCHA_ENABLED = "false"`

These values are safe for public review. Private production deployments should
override runtime settings through private Cloudflare environment variables or
private deployment configuration outside this repository.

Do not commit real account IDs, tokens, webhook URLs, bearer secrets, provider
keys, or Feishu/GitHub/Cloudflare secrets.

## Schedule Example

The mirror schedule in `wrangler.toml` is:

```text
0 2 * * *
```

Cloudflare cron uses UTC, so this corresponds to 10:00 Asia/Shanghai.

This schedule is included as a pattern example. It does not mean this public
mirror is deployed or connected to production.

## Public Mirror Dispatch Inputs

The Worker source dispatches the public mirror workflow with a small,
no-side-effect input set:

- `date`
- `dry_run`
- `bocha_enabled`

The workflow in this repository runs static checks only. It does not call
provider APIs, LLMs, Feishu, webhooks, or production pipeline code.

## Private Deployment Variables

A private deployment would configure these outside the public repo:

- `GITHUB_OWNER`
- `GITHUB_REPO`
- `GITHUB_WORKFLOW`
- `GITHUB_REF`
- `BOCHA_ENABLED`

Secrets must also be configured outside the public repo:

- `GITHUB_TOKEN`
- `MANUAL_TRIGGER_SECRET`
- Provider API keys
- Feishu app or bot secrets

Manual `/trigger` bearer secrets are not included in this mirror.

## Manual Trigger Pattern

The Worker expects an Authorization header, not a query parameter:

```bash
curl -X GET \
  -H "Authorization: Bearer <MANUAL_TRIGGER_SECRET>" \
  https://<worker-name>.<account>.workers.dev/trigger
```

Treat this as an interface pattern only. A real deployment requires private
Cloudflare, GitHub, Feishu, and provider secrets configured outside this public
repository.

## Review Notes

- The Worker dispatches GitHub Actions in the background.
- GitHub API 429 and 5xx responses are retried up to three times.
- Logs are intended to include status and short sanitized response summaries.
- Logs must not print `GITHUB_TOKEN` or `MANUAL_TRIGGER_SECRET`.
- Bocha is controlled by the explicit `bocha_enabled` workflow input.
- This public mirror contains the Worker pattern only, not the production
  Worker deployment state.
