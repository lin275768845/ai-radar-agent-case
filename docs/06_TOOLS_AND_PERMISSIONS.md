# 06 Tools And Permissions

- Project: AI Radar Agent
- Agent Type: evidence-first intelligence and publishing agent
- Status: active
- Last Updated: 2026-06-19
- Source of Truth: repository code, `README.md`, `.github/workflows/daily.yml`, tests
- Related Files: selected public code slices, schemas, evals, demo artifacts;
  full provider, LLM, Feishu, bot, report-lint, and brief-generation
  implementation files are omitted from this curated mirror.

## Permission Principle

Tools that read public information or write local sanitized artifacts are lower risk. Tools that publish, send messages, delete remote temporary files, dispatch workflows, or require secrets are high risk and must be gated.

Do not read or output real secrets, `.env` values, tokens, webhooks, cookies, private logs, or private run outputs.

## Tool Permission Matrix

| Tool | Status | Type | Input | Output | Side effect | Idempotent? | Requires secret? | Risk | Gate |
| --- | --- | --- | --- | --- | ---:| ---:| ---:| --- | --- |
| RSS fetch | implemented | public read/recall | RSS URLs, target Beijing window | Evidence items, RSS audit | No | Mostly | No | Timeout, stale item, missing dates | Time window gate; provider degradation gate |
| Bocha search | implemented | public search/read | Queries, target window, API key | Evidence items, provider audit | No external write | Mostly | Yes | Quota, auth failure, irrelevant results | Tool permission gate; Evidence Gate |
| Tavily search | implemented | public search/read | Queries, target window, enabled flag, API key | Evidence items, provider audit | No external write | Mostly | Yes | Optional provider cost/quota, stale results | Cost gate; provider degradation gate |
| LLM provider: report generation | implemented | compute/LLM | Prompt ref, evidence Markdown, target window | Report Markdown | No external write | No | Yes | Hallucination, unsupported claims | Evidence Gate; source URL guardrail |
| LLM provider: brief generation/repair | implemented | compute/LLM | Report, core events, evidence catalog | Brief JSON text | No external write | No | Yes | Invalid JSON, source ID mismatch | Brief schema/source_ids gate |
| LLM provider: final top audit | implemented | compute/LLM | Final top candidates, history context | Duplicate-drop decisions | No external write | No | Yes | False duplicate decision | final_top_llm_audit gate |
| Filesystem artifact read | implemented | local read | Project prompt/config/test files; operator-supplied replay paths | Strings/JSON | No | Yes | No | Reading private local artifact if pointed there | Privacy gate |
| Filesystem artifact write | implemented | local write/storage | Evidence, report, lint, brief, audit, publish result | `outputs/<date>/...` | Yes, local only | Partially | No | Committing/sharing private artifacts | Privacy gate; observability gate |
| Event history state | implemented | local state | Final top events, configured history path | `state/event_history.jsonl` when enabled | Yes | Partially | No | Duplicate or stale history state | History gate; state gate |
| GitHub Actions workflow | implemented outside runtime | scheduler/external trigger | `workflow_dispatch` ref and inputs | GitHub run, Summary, artifact bundle | Yes | No | External trigger needs GitHub auth | Wrong ref/date, production run | Approval Gate; Publish Gate |
| Feishu tenant token | implemented | auth | App id/secret from env/GitHub secrets | Tenant token | Auth side effect only | Cached per client | Yes | Secret leakage | Privacy gate |
| Feishu docx import | implemented | external publish/write | Report file, folder token, import settings | Docx URL/token or failure/fallback | Yes | No | Yes | Wrong folder, duplicate doc, timeout | Publish Gate |
| Feishu Drive Markdown upload | implemented | external publish/write | Report Markdown, folder token | File URL/token | Yes | No | Yes | Duplicate upload, wrong folder | Publish Gate |
| Feishu temporary source delete | partial | external delete/cleanup | Temporary file token | Delete result | Yes | Mostly | Yes | Wrong token deletion | Destructive-action gate; rollback gate |
| Feishu bot card webhook | implemented | notification/send | Brief, doc URL, webhook, optional signing secret | Bot response/result | Yes | No | Yes | Wrong audience, leaked URL, noisy card | Bot Gate; Publish Gate |
| `pytest` | implemented | local verification | Test targets | Test result | No external side effect expected | Yes | No | Tests may be incomplete | Test gate |
| Eval/static checker | planned | local verification | `evals/*.jsonl`, schemas, sanitized fixtures | Eval/static check result | No | Yes | No | False confidence if coverage is thin | Eval gate |
| RunManifest schema validation | planned | local verification | Planned `run_manifest.schema.json` and run manifest | Validation result | No | Yes | No | Schema drift | Future RunManifest gate |

## Side-effect Classes

| Class | Status | Examples | Default policy |
| --- | --- | --- | --- |
| Read-only public | implemented | RSS, search result recall | Allowed when configured; audit provider degradation |
| Local artifact write | implemented | `outputs/<date>/*.json`, report Markdown | Allowed for runs; do not commit private artifacts |
| External publish | implemented | Feishu docx/import/Drive upload | Requires explicit trigger and no-publish controls must be honored |
| External notification | implemented | Feishu bot card | Requires send flag/webhook and publish gate |
| External workflow | implemented outside runtime | GitHub `workflow_dispatch` | Human-triggered only |
| External delete/cleanup | partial | Feishu temporary source delete | No new cleanup automation without explicit approval |
| Eval/static check | planned | JSONL and schema checks | Must have no external side effect |

## Required Secrets

Status: implemented as environment/GitHub-secret configuration. Names only:

- `DEEPSEEK_API_KEY`
- `BOCHA_API_KEY`
- `TAVILY_API_KEY`
- `FEISHU_APP_ID`
- `FEISHU_APP_SECRET`
- `FEISHU_FOLDER_TOKEN`
- `FEISHU_TEMP_FOLDER_TOKEN`
- `FEISHU_BOT_WEBHOOK_URL`
- `FEISHU_BOT_SECRET`

Never print, quote, commit, or summarize real values.

## Current Gaps

- No formal `ToolCall` trace artifact.
- No machine-readable tool permission manifest.
- No formal run-level cost ledger.
- No formal approval artifact before external publish.
- Eval/static checker is planned but not implemented in this Phase A task.
