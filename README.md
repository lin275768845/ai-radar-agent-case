# AI Radar Agent

Chinese mirror: [README.zh-CN.md](README.zh-CN.md).

## Public Mirror Note

This repository is a sanitized public mirror of a production AI Radar Agent. It is published for portfolio review, architecture review, workflow review, evidence-first intelligence-agent design review, safety/autonomy boundary review, and case-study review.

It is not a full production clone and is not connected to the live Cloudflare, Feishu, or GitHub production deployment. Production secrets, private configuration, raw production outputs, real Feishu publication history, private runtime state, and production `state/event_history.jsonl` are intentionally excluded. The private production repository remains separate.

For a concise scope summary, see [docs/PUBLIC_MIRROR_SCOPE.md](docs/PUBLIC_MIRROR_SCOPE.md).

## What This Mirror Is

- A sanitized portfolio mirror based on a real production AI intelligence agent.
- A review target for the agent workflow, architecture, safety boundaries, schema contracts, eval design, and demo artifacts.
- A case-study repository that shows how an evidence-first publishing agent is structured without exposing production state or credentials.

## What You Can Review

- Evidence-first workflow from recall to Evidence Gate, report generation, Publish Gate, and review artifacts.
- Autonomy and tool permission boundaries for local work, provider calls, GitHub Actions, Feishu publishing, and external notifications.
- `RunManifest` and `ToolCall` schema contracts for future runtime observability.
- No-side-effect eval cases and the local static checker under `evals/`.
- Sanitized simulated demo artifacts under `demo_run/`.
- Cloudflare plus GitHub Actions trigger pattern as a reviewable deployment pattern, not a live deployment.
- Key runtime reconciliation and safety logic, especially report reconciliation, linting, evidence gates, and publish/bot guardrails.

## What You Can Run Locally

These checks are local and require no secrets, no provider keys, and no external side effects:

```bash
python3 evals/check_ai_radar_week2_eval_cases.py
python3 -m json.tool demo_run/demo_manifest.json
python3 -m py_compile ai_radar_agent/report_reconcile.py tests/test_report_reconcile.py
```

This mirror does not promise clone-and-run reproduction of the private production pipeline.

## What Is Intentionally Excluded

- `.env`, `.env.*`, `.dev.vars`, token files, and webhook configuration.
- Production `state/event_history.jsonl`.
- Real Feishu document URLs and production publication history.
- Production outputs, raw run artifacts, private logs, private runtime state, and private operational notes.
- Cloudflare, GitHub, Feishu, search-provider, and LLM secrets.
- Private production prompts/configuration that would be required for an end-to-end production run.

## Runability Boundary

This mirror is optimized for reviewable architecture and safety patterns, not turnkey production deployment. End-to-end production execution requires private GitHub repository settings, Cloudflare Worker settings, Feishu app/bot credentials, provider keys, production prompts/configuration, and runtime state that are intentionally not included here.

## License

License not yet specified. This repository is published for portfolio review; reuse rights are not granted unless a license is later added.

## Project Name

AI Radar Agent

## One-liner

Daily AI frontier radar agent: recall-first public evidence collection, DeepSeek report generation, report/brief quality checks, and Feishu publishing.

## Agent Type

Intelligence / research / daily report publishing agent.

## Current Status

- Current stable code baseline is `main` carrying the Week 2 standardized baseline.
- `single_card_v7.1` is retained as a previous-runtime rollback branch; `week2/standardization` is retained as the Week 2 branch snapshot and should not be assumed to track `main` after `main` advances.
- Previous v5.2 production state is preserved by fixed rollback tag `v5.2.0-rollback`; the `single_card_v5.2` branch has been removed to reduce branch sprawl.
- App runtime version marker is `week2_standardization`.
- Historical v3.x and v0.2.x branch references in older release notes are rollback/history context, not the current production ref.

## Week 2 Standardization Status

AI Radar Agent is also documented as an evidence-first intelligence and publishing agent case. The Week 2 standardization work adds portfolio-grade docs, runtime schema contracts, no-side-effect eval definitions, a sanitized simulated demo run, and Obsidian-ready pattern notes without changing Cloudflare production routing.

| Area | Status | Notes |
| --- | --- | --- |
| Core workflow docs | implemented | Workflow, autonomy, tool permissions, gates, eval plan, observability, and runbook are documented. |
| `RunManifest` / `ToolCall` schema contracts | implemented | Contracts exist in `schemas/`; runtime emission remains planned. |
| Week 2 eval definitions and static checker | implemented | Local checker validates the Week 2 eval JSONL and schema JSON. |
| Runtime eval integration | planned | The checker validates definitions, not live runtime behavior. |
| Sanitized demo run | implemented | Demo artifacts are deterministic mock data and explicitly simulated. |
| zh-CN documentation mirrors | implemented | English docs remain canonical; Simplified Chinese mirrors live in `README.zh-CN.md` and `docs/zh-CN/`. |
| External publish / Feishu / bot send | implemented in runtime, human-gated | Real publish remains controlled by workflow inputs and explicit approval. Demo/eval docs do not publish. |
| Dashboard / polished screenshots | planned P2 / Week 7 Portfolio | Not part of Week 2 standardization. |

## Problem

AI industry signals are scattered across official feeds, media, search providers, research sources, and adoption-signal surfaces. This project automates the daily work of collecting public evidence, forcing source-aware analysis, and publishing a concise AI radar without asking the LLM to invent citations.

## Core Capabilities

- Build an exact Beijing natural-day window.
- Collect broad evidence from RSS, Bocha, and optional Tavily.
- Apply Evidence Gate filtering, source-tier checks, and optional primary-source enrichment.
- Use 5-day event history and final Top dedupe to reduce repeated events.
- Run final Top LLM audit for high-confidence duplicate review.
- Pass evidence with URLs into DeepSeek for strict daily radar generation.
- Save evidence, report, lint, brief, publish result, and summary artifacts locally.
- Generate structured brief data for Feishu group cards.
- Publish Feishu native docx when available, with Drive Markdown fallback.
- Send optional Feishu custom bot cards.
- Redact secrets in logs and summaries.
- Support safe debugging through `dry_run`, `skip_llm`, `output_mode=none`, and artifact review.

## Current Workflow Summary

```text
GitHub workflow_dispatch or CLI
  -> Beijing natural-day window
  -> RSS / Bocha / Tavily recall
  -> Evidence Gate + event history matching
  -> filtered evidence.json / evidence.md / evidence_gate.json
  -> DeepSeek daily radar report
  -> report_lint.json
  -> DeepSeek brief.json + deterministic repair/fallback
  -> final_top_dedupe.json + final_top_llm_audit.json + top_event_audit.json
  -> Feishu docx import or Drive Markdown fallback
  -> optional Feishu group card
  -> GitHub Summary and artifacts
```

## Inputs

- Target date, or blank for yesterday in `Asia/Shanghai`.
- RSS and search source configuration from `config/sources.yaml`.
- Environment variables / GitHub secrets for DeepSeek, search providers, and Feishu.
- Main report prompt from `prompts/radar_prompt.md`.

## Outputs

- `outputs/<date>/evidence.json`
- `outputs/<date>/evidence.md`
- `outputs/<date>/evidence_gate.json`
- `outputs/<date>/evidence_dropped.md`
- `outputs/<date>/AI_radar_<date>.md`
- `outputs/<date>/report_lint.json`
- `outputs/<date>/brief.json`
- `outputs/<date>/brief.md`
- `outputs/<date>/final_top_dedupe.json`
- `outputs/<date>/final_top_llm_audit.json`
- `outputs/<date>/top_event_audit.json`
- `outputs/<date>/publish_result.json`
- Feishu docx or Markdown URL when publishing is enabled.
- Feishu bot card result when group push is enabled.

## Week 2 Artifact Map

| Artifact | Purpose |
| --- | --- |
| [docs/03_WORKFLOW.md](docs/03_WORKFLOW.md) | Workflow stages from recall to artifacts and publish gate. |
| [docs/04_AUTONOMY_MATRIX.md](docs/04_AUTONOMY_MATRIX.md) | Autonomy boundaries and human-approval points. |
| [docs/06_TOOLS_AND_PERMISSIONS.md](docs/06_TOOLS_AND_PERMISSIONS.md) | Tool permission matrix and side-effect classes. |
| [docs/09_GATES_AND_GUARDRAILS.md](docs/09_GATES_AND_GUARDRAILS.md) | Evidence, report, brief, publish, privacy, and future manifest gates. |
| [docs/10_EVAL_PLAN.md](docs/10_EVAL_PLAN.md) | Eval strategy and Week 2 static checker status. |
| [docs/11_OBSERVABILITY.md](docs/11_OBSERVABILITY.md) | Current artifacts, observability gaps, and `RunManifest` direction. |
| [docs/12_RUNBOOK.md](docs/12_RUNBOOK.md) | Safe local modes, common failures, and emergency stop guidance. |
| [docs/13_RUNTIME_OBJECT_MAP.md](docs/13_RUNTIME_OBJECT_MAP.md) | Relationship between `RunManifest`, `ToolCall`, `EvidenceItem`, gates, evals, and demo artifacts. |
| [schemas/run_manifest.schema.json](schemas/run_manifest.schema.json) | Run-level schema contract for sanitized execution manifests. |
| [schemas/tool_call.schema.json](schemas/tool_call.schema.json) | Per-tool-call schema contract for sanitized tool metadata. |
| [evals/ai_radar_week2_eval_cases.jsonl](evals/ai_radar_week2_eval_cases.jsonl) | 10 local no-side-effect eval case definitions. |
| [evals/check_ai_radar_week2_eval_cases.py](evals/check_ai_radar_week2_eval_cases.py) | Local static checker for eval cases and schema JSON. |
| [demo_run/demo_output_report.md](demo_run/demo_output_report.md) | Sanitized simulated demo report. |
| [docs/case_study_ai_radar_week2.md](docs/case_study_ai_radar_week2.md) | Portfolio case study draft for Week 2 standardization. |
| [docs/obsidian_pattern_notes/AI_Radar_Week2_MOC.md](docs/obsidian_pattern_notes/AI_Radar_Week2_MOC.md) | Obsidian-ready map of content for sanitized Week 2 pattern notes. |

## Local Static Checks

```bash
python3 evals/check_ai_radar_week2_eval_cases.py
python3 -m json.tool demo_run/demo_manifest.json
python3 -m py_compile ai_radar_agent/report_reconcile.py tests/test_report_reconcile.py
```

Full production execution is intentionally out of scope for this public mirror.

## Environment Variables

Use variable names only in docs and code examples. Do not store real values in this repository.

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
- `TAVILY_MAX_QUERIES`
- `TAVILY_MAX_RESULTS_PER_QUERY`
- `TAVILY_MAX_CONSECUTIVE_CONNECT_FAILURES`
- `FEISHU_APP_ID`
- `FEISHU_APP_SECRET`
- `FEISHU_FOLDER_TOKEN`
- `FEISHU_TEMP_FOLDER_TOKEN`
- `FEISHU_KEEP_MD_ARCHIVE`
- `FEISHU_DOC_BASE_URL`
- `FEISHU_IMPORT_POLL_TIMEOUT_SECONDS`
- `FEISHU_IMPORT_POLL_INTERVAL_SECONDS`
- `PRINT_FEISHU_URL_IN_SUMMARY`
- `FEISHU_BOT_WEBHOOK_URL`
- `FEISHU_BOT_SECRET`
- `FEISHU_BOT_FALLBACK_TEXT`
- `FEISHU_CARD_MAX_BYTES`
- `FEISHU_CARD_WARN_BYTES`
- `FEISHU_CORE_JUDGMENT_MAX_CHARS`
- `FEISHU_WATCH_SIGNAL_MAX_CHARS`
- `FEISHU_EVENT_WHY_MAX_CHARS`
- `FEISHU_CARD_TITLE_MAX_CHARS`
- `FEISHU_OVERVIEW_WHY_MAX_CHARS`
- `RADAR_TIMEZONE`
- `OUTPUT_MODE`
- `SEND_BOT`
- `REPORT_LINT_POLICY`
- `BOT_BLOCK_ON_LINT_CRITICAL`
- `STRICT_REPORT_LINT`
- `MAX_SEARCH_QUERIES_PER_RUN`
- `MAX_SEARCH_RESULTS_PER_PROVIDER`
- `MAX_SEARCH_RESULTS_PER_QUERY`
- `MAX_EVIDENCE_ITEMS`
- `EVIDENCE_GATE_ENABLED`
- `EVENT_HISTORY_ENABLED`
- `EVENT_HISTORY_LOOKBACK_DAYS`
- `EVENT_HISTORY_PATH`
- `EVENT_HISTORY_WRITE_ENABLED`
- `EVENT_HISTORY_COMMIT_ENABLED`
- `EVENT_HISTORY_COMMIT_REF`
- `EVENT_HISTORY_FILTER_MODE`
- `FINAL_TOP_LLM_AUDIT_ENABLED`
- `FINAL_TOP_LLM_AUDIT_MAX_HISTORY_EVENTS`
- `FINAL_TOP_LLM_AUDIT_MAX_TOKENS`
- `PRIMARY_SOURCE_ENRICHMENT_ENABLED`
- `PRIMARY_SOURCE_MAX_QUERIES`
- `PRIMARY_SOURCE_MAX_RESULTS_PER_QUERY`
- `BRIEF_MAX_TOKENS`
- `BRIEF_REPAIR_MAX_TOKENS`
- `BRIEF_SECTION_MAX_TOKENS`

## Current Repository Structure

```text
.
├── ai_radar_agent/          # Python package and runtime logic
├── ai_radar_agent/fetchers/ # RSS, Bocha, Tavily fetchers
├── docs/                    # architecture and operations docs
├── schemas/                 # RunManifest / ToolCall schema contracts; runtime emission planned
├── evals/                   # Week 2 static eval definitions and checker; runtime integration planned
├── state/                   # sample event-history shape only; production state excluded
├── tests/                   # pytest suite
├── .github/workflows/       # GitHub Actions workflow
├── pyproject.toml
└── README.md
```

## Key Directories

- `ai_radar_agent/`: production Python package.
- `schemas/`: Week 2 `RunManifest` and `ToolCall` schema contracts; current runtime validation still lives in Python code and tests.
- `evals/`: Week 2 no-side-effect eval definitions and static checker; current CI/runtime does not execute runtime eval integration.
- `state/`: sanitized sample event-history shape. Production `state/event_history.jsonl` is excluded.
- `tests/`: regression tests for workflow, parsing, gates, Feishu, and bot behavior.
- `docs/`: recovered project design documents.
- `demo_run/`: sanitized simulated demo artifacts.

## Non-goals

- Not a general news crawler.
- Not an investment-advice agent.
- Not a job-search or career-advice agent.
- Not a system that asks the LLM to browse or invent URLs.
- Not a fully autonomous irreversible publisher; high-risk production changes require confirmation.
- Not a full production clone or turnkey deployment repository.

## Maintenance Notes

- Keep `prompts/radar_prompt.md` as the main report prompt source of truth.
- Add tests for date-window logic, parsing logic, source binding, report lint, Feishu output, and bot cards.
- Keep Drive Markdown fallback when changing Feishu docx behavior.
- Treat README branch/ref references as operationally sensitive; production automation ref changes require explicit confirmation.
- See `docs/12_RUNBOOK.md` for operational procedures and `docs/09_GATES_AND_GUARDRAILS.md` for gate behavior.

## Safety / Privacy Notes

- Never commit `.env`, secrets, tokens, cookies, webhooks, private logs, or real credentials.
- Do not paste real Feishu / GitHub / DeepSeek / Bocha / Tavily secrets into issues, docs, prompts, or chat.
- `outputs/` may contain Feishu URLs and local run state; treat it as private local artifact storage.
- Logs and summaries should stay redacted; do not emit full prompts, evidence payloads, LLM payloads, secrets, or webhook URLs.
- Sanitized demo artifacts are not production outputs and should not be described as live market intelligence.

## Operational Detail

The following sections keep project-specific setup and operating details from earlier README versions. Some older branch names are retained only when explicitly labeled as historical context.

当前稳定代码基线：`main`，承载 Week 2 standardized baseline。

`single_card_v7.1` 作为旧 runtime rollback branch 保留；`week2/standardization` 作为 Week 2 branch snapshot 保留。它们不再被假设会随着 `main` 自动前进。外部生产调度 ref 变更需要单独确认。生产 ref 使用 `main` 时，GitHub repository variable `EVENT_HISTORY_COMMIT_REF` 也应同步设为 `main`，否则 history 写回会被保护逻辑跳过。

Week 2 standardized baseline 基于已验收的 single-card 链路继续 hardening。它保留 single-card 产品形态、历史去重、最终 Top 去重、最终 Top LLM 复核和 Evidence Gate 策略，并把默认模型、最终 lint、Top 源绑定、主体地区归属、Bocha 控制面和标准化文档收紧到上线口径。

每天自动生成 AI 雷达日报：Recall-first 搜索 -> DeepSeek 生成 -> 保存 Markdown / 飞书原生文档 -> 生成 brief -> 可选推送飞书群卡片。

这个仓库的目标是：你不需要使用 CLI。日常部署和运行只通过 GitHub 网页、Codex 客户端、飞书开放平台后台完成。

## 自动生成什么

- 默认时间口径：北京时间昨天 00:00-23:59。
- 默认输出：同一份 Markdown 中包含国内版和海外版 AI 雷达日报。
- 核心 prompt：`prompts/radar_prompt.md`，程序会原文读取作为系统 prompt，不压缩、不改写、不删减。
- 证据文件：
  - `outputs/<date>/evidence.json`
  - `outputs/<date>/evidence.md`
  - `outputs/<date>/evidence_gate.json`
  - `outputs/<date>/evidence_dropped.md`
- 日报文件：
  - `outputs/<date>/AI_radar_<date>.md`
- 简报文件：
  - `outputs/<date>/brief.json`
  - `outputs/<date>/brief.md`
  - `domestic_top` / `overseas_top` 的每条 item 都包含 `sources` 数组；群卡片会展示其中 1-2 个来源链接。
- 去重和质量审计文件：
  - `outputs/<date>/final_top_dedupe.json`
  - `outputs/<date>/final_top_llm_audit.json`
  - `outputs/<date>/top_event_audit.json`
- 报告质量检查：
  - `outputs/<date>/report_lint.json`
- 发布状态：
  - `outputs/<date>/publish_result.json`
- 飞书输出：
  - `feishu_drive_md`：上传 Markdown 文件。
  - `feishu_docx_import`：推荐，导入为飞书原生在线文档；成功时目标日报文件夹默认只保留原生文档，失败时 fallback 到 Markdown 上传。
  - `none`：只生成 GitHub artifact，不调用飞书。

## 你需要准备的账号和密钥

### DeepSeek

在 DeepSeek 后台创建 API Key。GitHub Actions 会读取：

- `DEEPSEEK_API_KEY`
- `DEEPSEEK_BASE_URL`
- `DEEPSEEK_MODEL`

### 搜索 Provider

搜索证据由 RSS / Bocha / Tavily 这类 provider 提供。DeepSeek 只负责分析和生成日报，不直接替代搜索 API，也不会被要求自己编造来源。

默认推荐低成本配置：

```text
SEARCH_PROVIDERS=rss,bocha
TAVILY_ENABLED=false
```

Bocha 用于补充国产网页搜索召回：

- `BOCHA_API_KEY`

如果暂时没有 Bocha key，可以只用 RSS：

```text
SEARCH_PROVIDERS=rss
```

Tavily 现在只是可选补充，不是必须项。若想继续少量使用 Tavily：

```text
SEARCH_PROVIDERS=rss,bocha,tavily
TAVILY_ENABLED=true
TAVILY_MAX_QUERIES=5
```

Tavily 相关 secret：

- `TAVILY_API_KEY`

Bocha / Tavily 请求默认使用快速超时和有限重试；400、401、403 不重试，429 / 5xx 只做轻量重试。任一 provider 失败只会 warning，不阻断 RSS 和主流程。

### Evidence Gate（single_card_v4 / v4.1 / v4.2 / v5）

`single_card_v4` 在 RSS / Bocha / Tavily 返回 raw evidence 后、DeepSeek 生成正式日报前新增 Evidence Gate；`single_card_v4.1` 又在 Evidence Gate 之后、DeepSeek 生成正式日报前增加历史去重；`single_card_v4.2` 把默认窗口改为最近 5 日，开启 history commit，并在 `brief.json` 生成后对最终 Top 再做一次历史去重；`single_card_v5` 在此基础上收紧语义去重，避免只按标题比较，也避免 content 中的杂散实体造成误杀；`single_card_v5.2` 增加最终 Top LLM 复核，用于在 deterministic 去重之后再审计高置信重复事件：

```text
raw evidence -> evidence_gate -> filtered evidence -> DeepSeek report
single_card_v5.2: filtered evidence -> event_history matching -> DeepSeek report -> brief -> final_top_dedupe -> final_top_llm_audit -> card/history
```

它的目标是提高及时性和来源质量：

- 减少旧新闻、转载、回顾、盘点在连续几天日报里重复出现。
- 降低聚合页、移动端转载页、搜索结果页的权重。
- 优先保留官方源、权威媒体和数据源。
- 尝试为高潜事件补一手官方来源。

Evidence Gate 会为每条证据补充：

- `date_status`：
  - `in_window`：证据发布时间在目标北京时间自然日内。
  - `new_signal`：事件可能前延，但目标日出现新价格、新调用量、新上线、新披露等新增信号。
  - `old_repeated`：旧事件回顾、盘点、转载，没有新增事实。
  - `out_of_window`：明显不在目标日期，且没有新增信号。
  - `unknown`：日期无法判断。
- `source_tier`：
  - `S1`：官方源，如公司博客、release note、docs、GitHub release、pricing page、IR / SEC / 财报、官方新闻稿。
  - `S2`：权威媒体，如 Reuters、Bloomberg、FT、WSJ、The Information、TechCrunch、The Verge、证券时报、第一财经、财联社、机器之心、量子位、36氪、IT之家等。
  - `S3`：数据源，如 OpenRouter、Artificial Analysis、Chatbot Arena、SWE-bench、Aider、GitHub、Hugging Face、Similarweb、Sensor Tower 等。
  - `S4/S5`：社群、自媒体、聚合页、快讯转载、搜索结果页、移动端聚合、来源不明页面。
- `source_fit`：
  - `high` / `medium` / `low`。`source_fit=low` 默认不会进入 filtered evidence。
- `not_core_eligible`：
  - 对日期不明、旧事件或 observation-only 证据做标记，提示 DeepSeek 不要把它强行写成当天核心事件。

Evidence Gate 新增 artifact：

- `evidence_gate.json`：记录 raw / filtered / dropped 数量、source tier 统计、primary source enrichment 结果、event history 命中情况。
- `evidence_dropped.md`：列出被剔除的旧新闻、窗口外新闻、低质量来源和重复证据，包含 `source_tier`、`date_status`、`reason` 和完整 URL，并汇总 dropped reason 分布。
- `top_event_audit.json`：只审计最终 `brief.json` 的 `domestic_top` / `overseas_top`，记录每条 Top 事件是否有一手来源、S1/S2 来源、低质量来源或日期异常；它不改变 report / brief / card 输出。
- `evidence.md` 顶部会增加 Evidence Gate 审计表。注意：artifact 里会展示 dropped evidence 方便人工排查，但 DeepSeek 只会收到 filtered evidence。

Event history 用于避免同一事件连续几天重复写入。它只存结构化 Top 事件摘要，不存完整日报，也不存 secrets：

- 默认 `EVENT_HISTORY_ENABLED=true`。
- 默认回看 `EVENT_HISTORY_LOOKBACK_DAYS=5`。
- 本地历史文件是 `state/event_history.jsonl`。
- 如果同一事件过去 5 天已写过，且今天没有新价格、新调用量、新上线、新官方披露等新增信号，会被标记为 `old_repeated` / `not_core_eligible=true`，提示 DeepSeek 不要再写入核心 Top。
- 如果今天有新信号，会标记为 `new_signal` 并保留。
- 默认 `EVENT_HISTORY_FILTER_MODE=mark`：历史命中的旧证据会标记为 `not_core_eligible=true`，仍随 evidence context 交给 DeepSeek 作为背景；最终 Top 仍会经过 `final_top_dedupe`。
- 可选 `EVENT_HISTORY_FILTER_MODE=drop`：历史命中的旧证据若没有新增信号，会在进入 DeepSeek 前移除；`event_history_matches.json` / `event_history_context.md` 仍会保留审计记录。drop 模式更激进，可能误杀前延背景，建议谨慎开启。
- `dry_run=true` 时不会写 history。
- `dry_run=false`、`skip_llm=false`、docx / canonical URL 存在且主流程成功后，才会把最终 `brief.json` 的 `domestic_top` / `overseas_top` 追加写入 `state/event_history.jsonl`。
- 默认 `EVENT_HISTORY_COMMIT_ENABLED=true`。workflow 会 checkout 当前 `github.ref_name`，并显式 push 到 `HEAD:${GITHUB_REF_NAME}`；commit message 带 `[skip ci]`。tag ref 或空 ref 不会尝试 push，push 失败只会 warning，不阻断日报发布。
- 默认 `EVENT_HISTORY_COMMIT_REF=main`。只有当前 `GITHUB_REF_NAME` 与该值一致时才允许写回 `state/event_history.jsonl`；手动测试其他分支或 rollback ref 时会在 Summary 记录 `ref_not_allowed_for_history_commit`，但不会失败，除非显式覆盖该变量。
- `final_top_dedupe.json` 会记录最终 Top 层面的历史命中、被删除的重复 Top、允许保留的 `new_signal` Top；这一步会改变 `brief.json` / 卡片 / history 写入，但不改变完整日报正文。
- `final_top_llm_audit.json` 会记录最终 Top 的 LLM 复核结果。该复核只接受 action=drop、confidence=high、`new_signal=false` 且明确指向重复对象的删除决策；如果 LLM 输出异常，会尝试修复 JSON 一次。复核失败不会阻断日报发布，只会在 Summary 中记录 `final_top_llm_audit_failed=true`。
- 如果生产 ref 是稳定分支，开启 commit 前要确认 workflow 有权限 push 到对应分支，或改用单独 state branch。

Primary Source Enrichment 用于尝试补官方源：

- 默认 `PRIMARY_SOURCE_ENRICHMENT_ENABLED=true`。
- 默认最多 `PRIMARY_SOURCE_MAX_QUERIES=8` 个官方源 query。
- 默认每个 query 最多 `PRIMARY_SOURCE_MAX_RESULTS_PER_QUERY=3` 条结果。
- 官方源补强会先跳过明显 `out_of_window`、`old_repeated` 和 `source_fit=low` 的证据，避免浪费 Bocha query。
- 找不到官方源不会失败，只会在 `evidence_gate.json` 和 Summary 里记录。

Summary 会新增：

- `raw_evidence_count`
- `filtered_evidence_count`
- `evidence_gate_dropped_count`
- `dropped_old_repeated_count`
- `dropped_out_of_window_count`
- `dropped_low_source_fit_count`
- `primary_sources_count`
- `official_sources_count`
- `authoritative_media_count`
- `aggregator_sources_count`
- `primary_source_enrichment_attempted`
- `primary_source_enrichment_added_count`
- `evidence_gate_relaxed`
- `event_history_enabled`
- `event_history_write_enabled`
- `event_history_path`
- `event_history_lookback_days`
- `event_history_filter_mode`
- `event_history_events_loaded`
- `event_history_matches_count`
- `event_history_old_repeated_count`
- `event_history_new_signal_count`
- `event_history_dropped_from_core_count`
- `event_history_observe_only_count`
- `event_history_pre_llm_dropped_count`
- `event_history_write_succeeded`
- `event_history_write_error`
- `final_top_dedupe_matches_count`
- `final_top_dedupe_dropped_count`
- `final_top_dedupe_new_signal_count`
- `final_top_dedupe_dropped_titles_sample`
- `final_top_llm_audit_attempted`
- `final_top_llm_audit_succeeded`
- `final_top_llm_audit_failed`
- `final_top_llm_audit_decisions_count`
- `final_top_llm_audit_dropped_count`
- `final_top_llm_audit_rejected_count`
- `final_top_llm_audit_dropped_titles_sample`
- `top_events_count`
- `top_events_with_primary_source_count`
- `top_events_with_s1_source_count`
- `top_events_with_s1_or_s2_source_count`
- `top_events_with_low_source_count`
- `top_events_out_of_window_count`
- `top_events_old_repeated_count`
- `top_events_new_signal_count`
- `top_event_audit_warnings_count`

Top 事件质量验收建议：

- `top_events_with_low_source_count` 尽量为 0。
- `top_events_old_repeated_count` 尽量为 0。
- `top_events_out_of_window_count` 尽量为 0。
- `top_events_with_s1_or_s2_source_count` 越高越好。

本地三日重合率回测可以使用：

```bash
python scripts/compare_top_events.py \
  outputs/2026-06-01/brief.json \
  outputs/2026-06-02/brief.json \
  outputs/2026-06-03/brief.json
```

脚本只读 `brief.json`，输出每日 Top 数量、两两 Jaccard、重复事件簇、连续多日重复事件和总重复簇占比。

### 飞书开放平台

在飞书开放平台创建一个自建应用，并准备：

- `FEISHU_APP_ID`
- `FEISHU_APP_SECRET`
- `FEISHU_FOLDER_TOKEN`
- `FEISHU_TEMP_FOLDER_TOKEN`，可选，用于放置 docx 导入所需的临时 Markdown 源文件
- `FEISHU_DOC_BASE_URL`，可选，默认 `https://my.feishu.cn`，用于飞书只返回 docx token 时构造原生文档链接

飞书侧需要完成：

1. 创建自建应用。
2. 开通云空间文件上传权限。
3. 如果使用 `feishu_docx_import`，开通导入云文档、Docx / 云文档创建或编辑相关权限。
4. 发布或启用应用，使权限生效；权限变更后也需要发布新版并完成审核。
5. 创建一个用于接收日报的飞书文件夹。
6. 确保该应用身份对这个文件夹有编辑权限。
7. 从文件夹 URL 中复制 folder token，填入 `FEISHU_FOLDER_TOKEN`。

`feishu_docx_import` 需要先上传一个临时 Markdown 源文件以创建导入任务。默认会优先上传到 `FEISHU_TEMP_FOLDER_TOKEN` 指定的临时文件夹；如果没有配置，就临时上传到 `FEISHU_FOLDER_TOKEN`。导入成功后程序会尝试删除这个临时源文件；删除失败只会 warning，不会让日报失败。

飞书导入是异步任务：`job_status=0` 才表示导入完成，`job_status=1` 或 `2` 表示仍在处理中，程序会继续轮询等待。默认最多等待 `FEISHU_IMPORT_POLL_TIMEOUT_SECONDS=180` 秒；超时仍未完成时会 fallback 上传 Markdown，此时群卡片链接 Markdown 是预期 fallback 行为。

日志和 Summary 会脱敏：不会打印 `docx_token`、`md_token`、临时源文件 token、tenant access token、app secret、webhook、API key。默认 Summary 会显示最终飞书链接；如果希望只显示链接是否存在，可把 repository variable `PRINT_FEISHU_URL_IN_SUMMARY` 设为 `false`。

### 飞书群自定义机器人

如果要把 brief 推送到飞书群，另外创建群自定义机器人，并准备：

- `FEISHU_BOT_WEBHOOK_URL`
- `FEISHU_BOT_SECRET`，可选
- `FEISHU_BOT_FALLBACK_TEXT`，默认 `true`。卡片消息被判定为 payload 格式类错误时，会再尝试发送一条 1000 字以内的纯文本消息。

注意区分两类身份：

- 飞书自建应用 / 应用身份：负责 Drive 文件上传和 Docx 导入。
- 群自定义机器人 webhook：只负责往群里推送消息卡片。

`FEISHU_BOT_SECRET` 是群自定义机器人「安全设置」里的签名密钥，不是 `FEISHU_APP_SECRET`。如果机器人没有开启签名校验，就不要配置 `FEISHU_BOT_SECRET`；配置后程序会按飞书规则添加秒级 `timestamp` 和 `sign`，但不会把 sign 写入日志或 Summary。

不要把任何密钥发给 Codex 或写进仓库文件；只放在 GitHub repository secrets 里。

## 飞书群卡片版本

当前稳定基线已更新为 `main` / `week2_standardization`。`single_card_v7.1` 作为旧 runtime rollback branch 保留；`week2/standardization` 作为 Week 2 branch snapshot 保留，不再要求与 `main` 同步。早期 `single_card_v3.1` / `three_card_v3.1` 只作为历史分支口径保留在旧 release 或回滚说明中，不再作为当前生产建议。

| 分支 | 卡片形态 | 适合场景 |
|---|---|---|
| `main` | 当前稳定 Week 2 standardized baseline | 推荐生产 ref；runtime marker 为 `week2_standardization`。 |
| `single_card_v7.1` | v7.1 回滚分支 | 旧 runtime rollback branch；不再代表当前稳定基线。 |
| `week2/standardization` | Week 2 branch snapshot | 保留 Week 2 standardization 合入前后的分支快照，便于回看或回滚标准化工作。 |
| `v5.2.0-rollback` | v5.2 固定回滚 tag | 仅作为 tag 保留；如需测试 v5.2，可从该 tag 临时建分支。 |

当前卡片链路共同点：

- 搜索召回、DeepSeek 日报生成、飞书 docx 导入、`brief.json` 生成逻辑保持一致。
- 卡片标题会带分支名，例如 `AI Radar｜2026-06-27｜main`，方便区分测试结果。
- 都会展示国内 / 海外 Top events，按 `P1` > `P2` > `观察` 排序。
- 每条事件最多展示 2 个来源链接；来源来自 `evidence.json`，不会让 LLM 编造 URL。
- 卡片文案会使用 card 专用短字段，避免把完整日报里的长段落、表格残片或 Markdown 标题直接塞进群消息。

当前 Summary 可重点看 `bot_cards_sent_count`、`bot_overview_card_sent`、`bot_domestic_detail_card_sent`、`bot_overseas_detail_card_sent`、`bot_domestic_items_rendered_count`、`bot_overseas_items_rendered_count`、`bot card title`、`bot sent`。

切换方式：

- 飞书自动化触发时，在 workflow dispatch body 里把 `"ref"` 设为确认后的生产 ref。新配置建议使用 `main`，并同步设置 `EVENT_HISTORY_COMMIT_REF=main`；既有配置如果仍使用 `single_card_v7.1`，需要确认后再切换。
- GitHub 网页手动测试时，在 `Run workflow` 的 branch 下拉框选择目标分支。
- 不要在未确认外部调度器和回滚方案前改生产 ref。

## GitHub 网页部署步骤

### 1. 打开仓库设置

在 GitHub 网页进入你的仓库：

`lin275768845/ai-radar-agent`

依次打开：

`Settings` -> `Secrets and variables` -> `Actions`

### 2. 添加 Repository secrets

在 `Secrets` 里添加：

- `DEEPSEEK_API_KEY`
- `DEEPSEEK_BASE_URL`
- `DEEPSEEK_MODEL`
- `BOCHA_API_KEY`
- `TAVILY_API_KEY`
- `FEISHU_APP_ID`
- `FEISHU_APP_SECRET`
- `FEISHU_FOLDER_TOKEN`
- `FEISHU_TEMP_FOLDER_TOKEN`
- `FEISHU_BOT_WEBHOOK_URL`
- `FEISHU_BOT_SECRET`

如果你暂时不用 Bocha，可以不填 `BOCHA_API_KEY`，并把 repository variable `SEARCH_PROVIDERS` 设为 `rss`。如果你暂时不用 Tavily，可以先不填 `TAVILY_API_KEY`。
如果你暂时不推送群卡片，可以先不填飞书机器人相关 secrets。

可选 repository variable：

- `FEISHU_KEEP_MD_ARCHIVE`：默认 `false`。只有设为 `true` 时，`feishu_docx_import` 成功后才会额外上传一份 Markdown 归档；即使开启，群卡片和 `brief.json.doc_url` 仍优先使用原生文档链接。
- `FEISHU_DOC_BASE_URL`：默认 `https://my.feishu.cn`。如果你的飞书文档域名不是这个值，可以设为自己的租户域名，例如 `https://example.feishu.cn`。
- `FEISHU_IMPORT_POLL_TIMEOUT_SECONDS`：默认 `180`。飞书 docx 导入任务最长等待时间。
- `FEISHU_IMPORT_POLL_INTERVAL_SECONDS`：默认 `3`。导入任务前几次轮询间隔；后续会放宽到 5 秒。
- `PRINT_FEISHU_URL_IN_SUMMARY`：默认 `true`。设为 `false` 时，Summary 不打印具体飞书 URL，只打印是否存在。
- `FEISHU_BOT_FALLBACK_TEXT`：默认 `true`。飞书卡片 payload 被拒绝时尝试发送纯文本 fallback，用来区分 webhook 通道坏了，还是卡片格式不被接受。
- `FEISHU_CARD_MAX_BYTES`：默认 `28000`。单张飞书卡片 JSON payload 的安全上限，超过后会压缩详情卡内容。
- `FEISHU_CARD_WARN_BYTES`：默认 `24000`。预留的卡片体积告警阈值。
- `FEISHU_CORE_JUDGMENT_MAX_CHARS`：默认 `56`。总览卡每条「今日核心判断」的最大字符数。
- `FEISHU_WATCH_SIGNAL_MAX_CHARS`：默认 `56`。总览卡每条「观察信号」的最大字符数。
- `FEISHU_EVENT_WHY_MAX_CHARS`：默认 `72`。详情卡里每条事件 why 的最大字符数。
- `FEISHU_CARD_TITLE_MAX_CHARS`：默认 `28`。群卡片事件短标题的最大字符数。
- `FEISHU_OVERVIEW_WHY_MAX_CHARS`：默认 `0`。总览卡默认不展示 why，只展示 title + priority。
- `REPORT_LINT_POLICY`：默认 `block_bot`。报告 lint errors / critical errors 会阻断群卡片，但不阻断 Feishu docx 发布；显式选择 `warn` 时才会继续推群。
- `BOT_BLOCK_ON_LINT_CRITICAL`：默认 `false`。设为 `true` 时，`REPORT_LINT_POLICY=warn` 下 critical errors 也会阻断群卡片。
- `STRICT_REPORT_LINT`：默认 `false`。设为 `true` 时，报告 lint 有 errors 会直接让 workflow 失败，效果接近 `report_lint_policy=strict`。
- `SEARCH_PROVIDERS`：默认 `rss,bocha`。支持 `rss`、`bocha`、`tavily`，RSS 会始终保留。
- `BOCHA_ENABLED`：默认 `false`；通常不需要单独设置，是否跑 Bocha 由 `SEARCH_PROVIDERS` 决定。
- `BOCHA_BASE_URL`：默认 `https://api.bochaai.com`。
- `BOCHA_MAX_QUERIES`：默认 `20`。
- `BOCHA_MAX_RESULTS_PER_QUERY`：默认 `5`。
- `BOCHA_CONNECT_TIMEOUT`：默认 `5`。
- `BOCHA_READ_TIMEOUT`：默认 `15`。
- `MAX_SEARCH_QUERIES_PER_RUN`：默认 `30`，所有搜索 provider 合计 query 上限。
- `MAX_SEARCH_RESULTS_PER_PROVIDER`：默认 `80`，单个 provider 返回结果上限。
- `MAX_EVIDENCE_ITEMS`：默认 `80`，最终去重后 evidence 上限。
- `EVIDENCE_GATE_ENABLED`：默认 `true`。控制是否启用 Evidence Gate。
- `EVENT_HISTORY_ENABLED`：默认 `true`。控制是否读取 / 写入 `state/event_history.jsonl`。
- `EVENT_HISTORY_LOOKBACK_DAYS`：默认 `5`。重复事件历史回看天数。
- `EVENT_HISTORY_PATH`：默认 `state/event_history.jsonl`。
- `EVENT_HISTORY_WRITE_ENABLED`：默认 `true`。控制成功运行后是否写入本地 history；`dry_run=true` 时仍不会写。
- `EVENT_HISTORY_COMMIT_ENABLED`：默认 `true`。控制 workflow 是否把 `state/event_history.jsonl` commit / push 回 GitHub。
- `EVENT_HISTORY_COMMIT_REF`：默认 `main`。只允许这个 ref 写回 history，避免非生产分支手动运行污染 state。
- `EVENT_HISTORY_FILTER_MODE`：默认 `mark`。`mark` 只标记历史旧证据，`drop` 会在进入 DeepSeek 前移除旧重复且无新增信号的证据。
- `FINAL_TOP_LLM_AUDIT_ENABLED`：默认 `true`。控制是否在 deterministic final Top 去重后调用 DeepSeek 做高置信重复复核。
- `FINAL_TOP_LLM_AUDIT_MAX_HISTORY_EVENTS`：默认 `30`。传给最终 Top LLM 复核的历史 Top 数量上限。
- `FINAL_TOP_LLM_AUDIT_MAX_TOKENS`：默认 `1200`。最终 Top LLM 复核返回 token 上限。
- `PRIMARY_SOURCE_ENRICHMENT_ENABLED`：默认 `true`。控制是否尝试补官方源。
- `PRIMARY_SOURCE_MAX_QUERIES`：默认 `8`。官方源补强 query 上限。
- `PRIMARY_SOURCE_MAX_RESULTS_PER_QUERY`：默认 `3`。官方源补强每个 query 的结果上限。
- `TAVILY_ENABLED`：默认 `false`。只有 `SEARCH_PROVIDERS` 包含 `tavily` 且该值为 `true` 时才会调用 Tavily。
- `TAVILY_CONNECT_TIMEOUT`：默认 `5`。
- `TAVILY_READ_TIMEOUT`：默认 `15`。
- `TAVILY_MAX_QUERIES`：默认 `8`。
- `TAVILY_MAX_RESULTS_PER_QUERY`：默认 `3`。
- `TAVILY_MAX_CONSECUTIVE_CONNECT_FAILURES`：默认 `2`。
### 3. 确认 Actions 已开启

打开仓库的 `Actions` 页面。如果 GitHub 提示需要启用 workflow，选择启用。

本仓库的 workflow 文件是：

`.github/workflows/daily.yml`

Workflow 已按 GitHub JavaScript Actions Node 24 迁移做兼容：`checkout` / `setup-python` 使用新版 action，并设置 `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true`。`upload-artifact` 暂保留 v4，等 v6 可用后再升级。

## 运行方式

### 定时触发

本仓库不使用 GitHub Actions 原生 `schedule`，只保留 `workflow_dispatch`。生产定时由外部调度器（例如 Cloudflare Worker 或飞书自动化）调用 GitHub workflow dispatch API。当前生产配置建议把 `ref` 指向 `main`，并把 GitHub repository variable `EVENT_HISTORY_COMMIT_REF` 设为 `main`；既有配置如果仍指向 `single_card_v7.1`，应视为旧回滚配置，需要确认后再切换。如果需要 branch rollback，可选择 `single_card_v7.1` 或 `week2/standardization`；如果必须回看 v5.2，可从 `v5.2.0-rollback` 临时建分支，并同步修改对应调度器的 ref。

不填写 `date` 时，workflow 仍然生成北京时间“昨天 00:00-23:59”的完整自然日日报，不会改成今天。

### Cloudflare 定时触发

`cloudflare/ai-radar-trigger/` 收录了已经跑通链路的 Worker 模板，便于审计和迁移。它不会自动修改 Cloudflare 控制台中已部署的 Worker；需要手动复制或用 Wrangler 部署。

Worker 默认配置：

- `GITHUB_OWNER=lin275768845`
- `GITHUB_REPO=ai-radar-agent`
- `GITHUB_WORKFLOW=daily.yml`
- `GITHUB_REF=main`
- GitHub repository variable: `EVENT_HISTORY_COMMIT_REF=main`
- cron: `0 2 * * *`，即北京时间每天 10:00。

需要配置为 Cloudflare secrets：

- `GITHUB_TOKEN`
- `MANUAL_TRIGGER_SECRET`

手动触发使用 Authorization header，不再建议把 secret 放到 URL query 中：

```bash
curl -H "Authorization: Bearer <MANUAL_TRIGGER_SECRET>" \
  https://<worker-name>.<account>.workers.dev/trigger
```

Worker 只打印 GitHub dispatch 的 status 和脱敏后的短 body，不打印 `GITHUB_TOKEN` 或 `MANUAL_TRIGGER_SECRET`。

### 日志安全

即使 workflow 使用 `--verbose`，`openai`、`openai._base_client`、`httpx`、`httpcore`、`urllib3` 这些第三方 SDK logger 也会保持 `WARNING` 级别，避免完整 prompt、evidence 或 LLM payload 出现在 GitHub Actions log。`--verbose` 只用于 `ai_radar_agent` 自身的应用层摘要日志。

### 手动运行

Run workflow 页面默认就是正式运行：不填写日期时生成北京时间昨天的完整日报，默认发布 Feishu docx，并在发布成功后发送飞书群卡片。`dry_run` 只用于调试，`skip_llm` 只用于 evidence-only 召回测试。

在 GitHub 网页：

1. 打开 `Actions`。
2. 选择 `Daily AI Radar`。
3. 点击 `Run workflow`。
4. 直接点击运行即可正式生成昨天日报、发布 Feishu docx、发送群卡片。
5. 可选填写 `date`，格式是 `YYYY-MM-DD`。
6. 可选勾选 `dry_run`，只生成 artifact，不上传飞书、不发送群卡片。
7. 可选勾选 `skip_llm`，只生成 `evidence.json` / `evidence.md`，用于测试召回。
8. 可选开启 `tavily_enabled`，把 Tavily 作为额外搜索补充；默认不启用，避免消耗 Tavily 额度。
9. 可选勾选 `force_republish`，忽略本地 `publish_result.json` 并重新发布飞书文档。
10. 可选选择 `report_lint_policy`：
   - `block_bot`：默认。errors 或 critical errors 会阻断群推送，但不阻断飞书发布。
   - `warn`：warnings / errors / critical errors 继续发布和推群，只在 Summary 提示。
   - `strict`：errors 或 critical errors 会阻断发布和群推送，适合调试。
   - `off`：只生成 `report_lint.json`，lint 不影响流程。
11. 可选勾选 `bot_block_on_lint_critical`，让 `warn` 模式下的 critical errors 也阻断群推送。

高级调试时可以改 `output_mode`：
   - `none`
   - `feishu_drive_md`
   - `feishu_docx_import`

不填写 `date` 时，仍然默认生成北京时间昨天的日报。

推荐测试顺序：

1. 正式运行：直接点 `Run workflow`。
2. 只看 artifact：勾选 `dry_run`。
3. 只测召回：勾选 `skip_llm`。
4. 临时使用 Tavily：勾选 `tavily_enabled`，或把 `SEARCH_PROVIDERS` 临时设为 `rss,bocha,tavily` 并设置 `TAVILY_ENABLED=true`。

## 查看结果

每次 workflow 结束后：

- 本地 artifact 中始终保留 Markdown 日报。
- 飞书主阅读入口默认是原生在线文档，也就是 `output_mode=feishu_docx_import` 成功后的 docx 链接。
- `output_mode=feishu_docx_import` 且导入成功时，飞书目标日报文件夹默认只保留原生在线文档。
- 如果 `feishu_docx_import` 失败，程序会 fallback 上传 Markdown；此时 Summary 会显示 `docx_error_summary` 和 `fallback_reason`。
- 如果 Summary 显示 `docx_last_job_status: 1` 或 `2` 且 fallback 到 Markdown，通常表示导入任务等待超时，任务仍在飞书侧处理中。
- 如果 Summary 显示 `docx_url exists: false`、`fallback_used: true`、`canonical_type: md`，说明 docx import 没成功，群卡片链接 Markdown 是 fallback 行为。
- Markdown 只会在三种情况下上传到飞书：`output_mode=feishu_drive_md`、docx 导入失败 fallback、显式设置 `FEISHU_KEEP_MD_ARCHIVE=true`。
- GitHub Actions run 页面会有 `ai-radar-outputs` artifact，里面包含 report、`evidence.json`、`evidence.md`、`evidence_gate.json`、`evidence_dropped.md`、`event_history_matches.json`、`event_history_context.md`、`final_top_dedupe.json`、`final_top_llm_audit.json`、`top_event_audit.json`、`brief.json`、`brief.md`。
- `evidence.md` 顶部有「召回审计」，包含 provider audit 表，逐项显示 RSS、Bocha、Tavily 的 enabled、status、queries_used、results_count、evidence_count 和 error_summary；同时保留 RSS per-source audit。单个 RSS 源或搜索 provider timeout / 失败只会 warning，不影响其他源。
- `evidence_gate.json` 用来验收召回质量：重点看 `raw_evidence_count`、`filtered_evidence_count`、`dropped_old_repeated_count`、`dropped_out_of_window_count`、`dropped_low_source_fit_count`、`primary_sources_count` 和 `primary_source_enrichment_added_count`。`evidence_dropped.md` 用来人工检查哪些旧新闻、窗口外新闻或低质量来源被剔除。
- `event_history_matches.json` 用来验收证据层 5 日去重：重点看 `history_events_loaded`、`matched_candidates_count`、`old_repeated_count`、`new_signal_repeat_count`、`filter_mode`、`pre_llm_dropped_count` 和每条 match 的 `action`。`event_history_context.md` 会优先列出当天命中的历史事件，其余按日期新到旧和 `P1` > `P2` > `观察` 排序。
- `final_top_dedupe.json` 用来验收最终 Top 去重：重点看 `matches_count`、`dropped_count`、`new_signal_count` 和 `dropped_titles`。如果某条 Top 已在最近 5 日出现且没有强新增信号，它会从 `brief.json` / 卡片 / history 中删除。
- `final_top_llm_audit.json` 用来验收最终 Top LLM 复核：重点看 `attempted`、`succeeded`、`failed`、`decisions`、`dropped_titles` 和 `error`。如果 deterministic 去重把某条重复事件误判成 `new_signal` 放过，LLM 复核仍可能把它从最终卡片里删除。
- `top_event_audit.json` 用来验收最终 Top 事件质量：重点看 `top_events_with_s1_or_s2_source_count`、`top_events_with_low_source_count`、`top_events_old_repeated_count`、`top_events_out_of_window_count` 和每条 event 的 `warnings`。
- 如果 DeepSeek 生成的报告正文没有任何可识别 URL，程序会在报告末尾追加 `附录：本次证据来源索引`，最多列出 30 条 evidence URL，作为来源链接兜底；这不会替代正文里的“来源”字段，只是保证 docx、lint 和 brief source links 有可追溯 URL。
- `report_lint.json` 会记录报告质量检查结果，字段包括 `warnings`、`errors`、`critical_errors` 和计数 summary。默认 `REPORT_LINT_POLICY=block_bot` 时，errors / critical errors 会阻断群卡片但不阻断 Feishu docx 发布，Summary 会显示 `bot skipped/reason=report_lint_errors` 或 `report_lint_critical_errors`。显式选择 `warn` 时才会继续推群，并显示 `bot lint action: ignored_by_policy_warn` 或 `ignored_critical_by_policy_warn`。
- Summary 会显示 `report_lint critical_errors summary`，用于直接看前 3 条 critical 原因；完整内容仍保留在 artifact 的 `report_lint.json`。
- `brief.json` 会显示 `brief_generation_status`：`ok` 表示结构化 brief 正常生成，`repaired` 表示通过 section-level retry、partial JSON salvage 或 report_core_events deterministic fallback 修复，`fallback` 只表示 salvage 和 report fallback 都失败、只能提示查看完整日报。fallback brief 不影响 docx 发布和 bot 推送。
- v5.2 runtime 会优先用正式雷达 section 抽取 `report_core_events` 作为骨架，再让 LLM 压缩 `card_title` / `why`；如果 DeepSeek 返回 JSON 被截断，会尝试 partial JSON salvage；如果 salvage 不足但正式雷达事件可提取，会用 deterministic fallback 补齐 `domestic_top` / `overseas_top`。当前 main 已合入该 v5.2 行为：每个 core event 都携带稳定 `event_id`、table row、deep dive block、binding status、source URLs 和自然语言 why，避免标题、why、sources 按 index 错配。
- brief source links 采用两阶段生成：DeepSeek 只返回 `source_ids`，代码再从完整 `evidence.json` 映射成最终 `sources.url`，避免 LLM 编造 URL；compact evidence catalog 只影响提示长度，不限制解析器读取 E78 这类后段证据。若 `sources=[]`，该条新闻仍会保留并展示，只是不显示“来源：”。“无强核心事件”只会在对应 Top list 为空时显示。
- 群卡片标题固定为 `AI Radar｜YYYY-MM-DD`，不会使用第一条新闻标题。Summary 里可用 `brief_finish_reason`、`brief_parse_stage`、`brief_salvage_succeeded`、`brief_json_parse_error`、`brief_normalization_error` 判断问题发生在 length 截断、raw JSON 解析、repair、salvage 还是 normalization；用 `brief_llm_domestic_items_count` / `brief_llm_overseas_items_count` 判断 LLM 生成了多少 items，用 `brief_final_domestic_items_count` / `brief_final_overseas_items_count` 判断 normalization 后保留了多少 items，用 `brief_source_ids_requested_count`、`brief_source_ids_resolved_count`、`brief_source_ids_unresolved_count` 和 `brief_unresolved_source_ids_sample` 判断 source_ids 解析成功多少。source_ids 解析失败只影响来源链接，不会触发 fallback 或删除新闻摘要。
- brief 会先从完整日报的国内 / 海外正式雷达提取 expected count，不从候选事件表提取 Top events；支持 `AI 前沿能力与应用雷达 - 国内版`、`AI 前沿能力与应用雷达-国内版`、`国内版正式雷达`、`国内版`、海外版对应标题。优先读取“今日总览”表格，其次读取“逐条深度解读”编号标题。日报模式每侧最多保留 6 条正式核心事件，若正式雷达超过 6 条，会按 `P1` > `P2` > `观察` 保留前 6 条，并在 Summary 显示 `report_*_core_events_count_raw`、`report_*_core_events_count_capped` 和 `*_core_events_truncated=true`。国内 / 海外无核心事件时，`brief.json` 保持 `domestic_top=[]` / `overseas_top=[]`，不会创建“今日无强核心事件”fake item。若 LLM brief 少生成正式核心事件，系统会尝试 count repair；仍不足时用正式雷达清单 deterministic fallback 补齐。Summary 会区分 `brief_count_mismatch_initial` 和 `brief_count_mismatch_final`：如果初始 LLM 输出 too_few，但最终已经由正式雷达补齐，则 `brief_count_mismatch=false`、`brief_count_mismatch_final=false`、`brief_count_mismatch_handled=true`，并显示 `brief_count_filled_from_core_events=true`、expected / actual count。Summary 可用 `report_domestic_core_events_count`、`report_overseas_core_events_count`、`report_*_section_found`、`report_*_extraction_method`、`section_detection_error`、`report_*_zero_core_explicit`、`report_*_extraction_suspect`、`brief_count_mismatch_initial`、`brief_count_mismatch_final`、`brief_count_mismatch_handled` 验收：`zero_core_explicit=true` 只表示该侧正式雷达明确没有核心事件，且该侧 count 必须为 0；如果同一 section 既有无核心文案又抽到事件，事件优先，Summary 会显示 `report_*_zero_core_conflict_resolved=events_found`。`extraction_suspect=true` 表示 section 找到了但 parser 未抽到事件，可能需要查看完整报告结构。
- 卡片详情 `why` 优先使用 `card_why`，其次来自逐条深度解读里的「影响 / So what / 概述 / 重要性判断」等自然语言，不使用 report table row、`L1 | P1 | 高 | ...`、纯编号、Markdown heading、a./b. subbullet 或标题复述。卡片文案会做语义压缩和安全截断，默认尽量不用省略号，避免出现“用户入口争”“C端A”“后续应”“Agent商业化的核心平”“状态”这类吞字残片；总览卡的核心判断 / 观察信号默认每条最多 56 字，详情卡 why 默认最多 72 字。来源链接必须与事件主体绑定；低可信、跨实体或只靠同日期/provider 的匹配会被丢弃，宁可 `sources=[]` 也不乱配。Summary 可用 `report_core_event_*`、`source_binding_*`、`brief_items_*`、`bot_why_cleaned_count`、`bot_why_truncated_count`、`bot_detail_why_fallback_count`、`bot_card_text_quality_passed`、`bot_card_bad_fragment_count` 和 `card_text_issue_source` 查看绑定和清洗情况。
- `publish_result.json` 会记录本地发布结果。若同一输出目录里已存在该文件且 `force_republish=false`，程序会复用 `canonical_url`，不再创建飞书 docx 或上传 md，但仍可发送群卡片。GitHub Actions artifact 默认是临时的，跨 run 幂等后续需要接 GitHub cache、提交状态文件，或按飞书标题查找已有文档。
- 群卡片链接优先级固定为：`docx_url` > `md_url` > 无按钮。
- 群推送采用多卡片策略，避免一张卡片过长导致尾部 section 被飞书丢弃：卡片 1 是总览卡，永远优先展示标题、最多 3 条「今日核心判断」、最多 3 条「观察信号」、国内 / 海外 Top 简表和「查看完整日报」按钮；卡片 2 是国内详情卡；卡片 3 是海外详情卡。若 LLM 生成的 `brief.core_judgments` 或 `brief.watch_signals` 为空，程序会从完整报告的「今日核心判断 / 本周核心判断 / 本月核心判断 / 核心判断」和「观察信号」section 兜底提取 bullet list，并在 Summary 显示 `core_judgments_filled_from_report`、`watch_signals_filled_from_report` 和提取错误原因。详情卡每侧最多展示 6 条完整日报正式雷达里的 Top events，展示顺序为 `P1` > `P2` > `观察`，同一优先级内保持 brief 原始顺序。如果输入超过 6 条，卡片会裁剪到 6 条并提示“更多详情见完整日报”，Summary 会显示 `bot_*_items_input_count`、`bot_*_items_rendered_count`、`bot_*_items_truncated` 和 `bot_card_truncated_reason=max_6_per_region`。总览卡只列 title + priority，不展示 why / sources；详情卡展示 why 和每条最多 2 个真实原始来源链接。总览卡优先使用 `core_judgments[].card` / `watch_signals[].card`，详情卡优先使用 `card_why`，并在发送前做卡片文本质量校验；若详情卡中“详见完整日报。”超过 2 条，Summary 显示 `bot_detail_why_fallback_warning=true`。来源 URL 只允许来自 `evidence.json` 或报告正文已有 URL，不会编造；source label 会优先显示真实媒体 / 官方来源名并按 URL 和显示名去重，`Tavily` / `RSS` provider 名只作为内部字段，不会作为用户可见来源，`tavily.tavily` 这类 label 会被清洗或丢弃。如果某侧正式雷达明确没有核心事件，对应 section 显示“今日无强核心事件，不强行凑数”，不显示来源。若卡片过长，系统会优先缩短详情卡 why，再减少 sources；仍超限才截断事件，并在 Summary 显示 `bot_card_items_truncated=true` 和原因。完整日报按钮仍然链接 docx / md。验收时对比 `report_*_core_events_count`、`brief_final_*_items_count`、`bot_*_items_rendered_count`、`bot_cards_sent_count`、`bot_card_split_used`、`bot_core_judgments_rendered_count`、`bot_watch_signals_rendered_count`、`bot_card_text_quality_passed` 和 `bot_card_bad_fragment_count`。
- 群卡片是否推送主要看 `send_bot`、`FEISHU_BOT_WEBHOOK_URL`、`doc_url`、`report_lint_policy` 和 `bot_block_on_lint_critical`。如果 Summary 显示 `bot skipped/reason=report_lint_errors`，说明当前 policy 是 `block_bot` / `strict`；如果显示 `report_lint_critical_errors`，说明选择了 `block_bot` / `strict` 或打开了 `bot_block_on_lint_critical=true`。
- `bot sent=false / reason=failed` 已废弃。新的 Summary 会显示 `bot attempted`、`bot status_code`、`bot response_code`、`bot response_msg`、`bot error_summary`、`bot response_body_summary`、`bot cards attempted/sent`、`bot overview/detail card sent`、`bot_card_*_bytes`、`bot_card_split_used`、`bot_card_text_compacted`、`bot_core_judgments_original_count`、`bot_core_judgments_rendered_count`、`bot_core_judgments_truncated_count`、`bot_watch_signals_original_count`、`bot_watch_signals_rendered_count`、`bot_watch_signals_truncated_count`、`bot_text_truncation_examples`、`bot_why_cleaned_count`、`bot_why_truncated_count`、`bot_why_fallback_count`、`bot_why_cleaned_examples`、`bot text fallback attempted/sent` 等字段，响应 body 会脱敏截断。
- `bot attempted=false` 表示 webhook 没有被调用，通常是 dry_run、skip_llm、send_bot=false、missing_webhook、missing_doc_url 或 lint policy 阻断。`bot attempted=true` 但 `bot sent=false` 才需要查看 webhook 的 `response_code`、`response_msg` 和 body summary。
- 生产日志默认降噪和脱敏：不会输出完整 prompt、完整 evidence、完整 LLM payload、HTTP headers、Authorization、webhook、access token、app secret 或 API key；`openai`、`httpx`、`httpcore`、`urllib3` 等第三方 SDK 即使在 `--verbose` 下也保持 WARNING 级别。Summary 中的错误 body 只保留脱敏后的截断摘要。
- 当前 `.github/workflows/daily.yml` 未确认存在独立失败通知步骤；Summary 中的 `failure_notification_*` 字段当前按成功路径写为 false/成功说明。若需要失败告警，应作为后续功能单独实现和测试。
- 不要在日志、README、issue、群消息里粘贴 token、webhook、完整 prompt、完整 evidence 或未脱敏 LLM payload。
- 常见 bot 失败：如果总览卡发送失败，Summary 的 `bot skipped/reason` 会显示 `overview_card_failed`，原始分类会保留在 `bot error_summary` 里，例如：
  - `missing_webhook`：没有配置 `FEISHU_BOT_WEBHOOK_URL`。
  - `signature_error`：签名错误；确认 `FEISHU_BOT_SECRET` 是机器人签名密钥，不是 `FEISHU_APP_SECRET`，也可以临时关闭机器人签名校验验证。
  - `keyword_mismatch`：机器人开启了关键词校验，但消息没有命中关键词；可临时关闭关键词或把 `AI Radar` 加入关键词。
  - `ip_not_allowed`：机器人开启了 IP 白名单，GitHub Actions 出口 IP 不在白名单；可临时关闭 IP 白名单验证。
  - `payload_invalid`：卡片 payload 格式或字段不被飞书接受；若 `FEISHU_BOT_FALLBACK_TEXT=true`，程序会尝试纯文本 fallback。
  - `webhook_http_status`：webhook 返回非 200，看 `bot status_code` 和 `bot response_body_summary`。
  - `webhook_http_error`：网络错误，看 `bot error_summary`。
- 排查 bot 时，优先看 Summary 的 `bot response_msg`。若无法判断，临时关闭签名、关键词和 IP 白名单分别测试；如果纯文本 fallback 成功，说明 webhook 通道可用，问题更可能在卡片 payload。
- 排查失败时，先看 GitHub run URL、失败步骤日志、Summary 和 Actions artifact 的 `outputs/`。独立失败告警能力当前不是已确认实现。
- 群卡片不展示 evidence 数量；`evidence_count` 只保留在 artifact 和 workflow summary 里。
- GitHub Actions summary 会显示 `app_version`（当前为 `week2_standardization`）、`github_sha`、`github_ref`、`github_event_name`、`trigger_source`、`scheduler`、`production_ref_warning`、`expected_external_trigger_time`、`actual_run_started_at_utc`、`actual_run_started_at_asia_shanghai`、`dry_run`、`skip_llm`、`output_mode`、`send_bot`、`search_providers`、`tavily_enabled`、target date、evidence count、RSS count、Bocha count、Tavily count、provider status / error summary、search query budget、provider queries/results count、RSS fallback used、report path、brief path、docx/md URL 是否存在、`canonical_type`、`bot link target`、fallback 状态、Markdown 归档状态、`temp_file_token exists`、`temp_file_deleted`、`temp_file_delete_error`、bot sent/skipped。
- 如果飞书目标文件夹里还有历史生成的 `AI_radar_<date>.md`，程序不会自动删除，避免误删用户文件；需要你在飞书里手动删除，或以后单独加 cleanup workflow。
- `.tmp_AI_radar_*.md` 是导入 docx 的临时源文件，不是正式日报。如果它留在飞书目录，可能是导入任务超时仍在处理中，或临时文件删除失败；可以手动删除、给应用补充删除文件权限，或配置 `FEISHU_TEMP_FOLDER_TOKEN` 把临时源文件放到单独临时文件夹。目标日报文件夹默认只应保留 docx。
- 手动测试前建议先删除飞书里同日期的旧 Markdown 和旧 `.tmp_AI_radar_*.md`，避免把历史遗留误判成新运行产物；新运行是否又生成 Markdown 或残留临时文件，以 Summary 的 `md_archive_used` 和 `temp_file_deleted` 为准。

如果 workflow 失败，先看 Actions 页面里的失败步骤日志。常见原因：

- GitHub secrets 名称拼错。
- DeepSeek key、base URL 或 model 不可用。
- 飞书应用没有文件夹权限。
- 飞书 folder token 填错。
- 飞书 Docx 导入权限未开通；此时会尝试 fallback 到 Markdown 上传。
- 群机器人 webhook 或签名配置不正确；这只会 warning，不会让主流程失败。
- RSS / Bocha / Tavily 都没有召回到任何证据。
- 报告 lint errors / critical errors。workflow 默认 `block_bot` 下 lint 会阻断群推送但不阻断 Feishu docx 发布；如果选择 `strict`，会阻断发布和群推送；显式选择 `warn` 时不会阻断群推送。

## Release / 历史回滚点

历史 release notes 保留在 `docs/release/v0.2.1.md`。当前稳定基线为 `main` / `week2_standardization`；rollback refs 为 `single_card_v7.1`、`week2/standardization` 和固定 tag `v5.2.0-rollback`。

如果后续要把某个卡片分支重新固定成新的 release/tag，可在 GitHub 网页创建 release：

1. 打开仓库的 `Releases` 页面。
2. 点击 `Draft a new release`。
3. Tag 填新版本号。
4. Release title 填对应版本名。
5. Release notes 说明该版本使用 `single_card` 还是 `three_card` 卡片形态。

## 用 Codex 客户端维护

你可以在 Codex 客户端里提出维护需求，例如：

- “帮我调整搜索源”
- “帮我修改日报格式”
- “帮我检查 GitHub Actions 失败原因”
- “帮我更新飞书上传逻辑”

Codex 可以修改仓库文件并帮你验证，但密钥仍然只在 GitHub 网页和飞书后台配置，不要发给 Codex。

## 关键文件

- `prompts/radar_prompt.md`: 核心分析 prompt，程序原文读取。
- `config/sources.yaml`: RSS、Bocha、Tavily Recall-first 搜索源配置。
- `ai_radar_agent/__main__.py`: 主流程入口。
- `ai_radar_agent/llm.py`: DeepSeek 调用。
- `ai_radar_agent/feishu.py`: 飞书文件上传。
- `ai_radar_agent/feishu_docx.py`: 飞书原生文档导入。
- `ai_radar_agent/report_lint.py`: 日报质量检查。
- `ai_radar_agent/brief.py`: brief.json / brief.md 生成。
- `ai_radar_agent/feishu_bot.py`: 飞书群卡片推送。
- `.github/workflows/daily.yml`: GitHub Actions 自动运行配置。
