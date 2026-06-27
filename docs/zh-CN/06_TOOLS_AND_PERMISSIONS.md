# 06 工具与权限中文镜像

英文权威版本见 [../06_TOOLS_AND_PERMISSIONS.md](../06_TOOLS_AND_PERMISSIONS.md)。

- 项目： AI Radar Agent
- 代理类型： 证据优先的情报与发布代理
- 状态： active
- 事实来源： repository code, `README.md`, `.github/workflows/daily.yml`, tests

## 权限原则

读取 public information 或写入 local sanitized artifacts 的 tools 风险较低。会 publish、send messages、delete remote temporary files、dispatch workflows 或 require secrets 的 tools 是 high risk，必须经过 gates。

不得读取或输出真实 secrets、`.env` values、tokens、webhooks、cookies、private logs 或 private run outputs。

## 工具权限矩阵

| 工具 | 状态 | 类型 | 输入 | 输出 | 副作用 | 是否幂等 | 是否需要密钥 | 风险 | 门禁 |
| --- | --- | --- | --- | --- | ---:| ---:| ---:| --- | --- |
| RSS fetch | 已实现（implemented） | public read/recall | RSS URLs, target Beijing window | Evidence items, RSS audit | No | Mostly | No | timeout、stale item、missing dates | Time window gate；provider degradation gate |
| Bocha search | 已实现（implemented） | public search/read | queries, target window, API key | Evidence items, provider audit | No external write | Mostly | Yes | quota、auth failure、irrelevant results | Tool permission gate；Evidence Gate |
| Tavily search | 已实现（implemented） | public search/read | queries, target window, enabled flag, API key | Evidence items, provider audit | No external write | Mostly | Yes | optional provider cost/quota、stale results | Cost gate；provider degradation gate |
| LLM provider: report generation | 已实现（implemented） | compute/LLM | prompt ref, evidence Markdown, target window | Report Markdown | No external write | No | Yes | hallucination、unsupported claims | Evidence Gate；source URL guardrail |
| LLM provider: brief generation/repair | 已实现（implemented） | compute/LLM | report, core events, evidence catalog | Brief JSON text | No external write | No | Yes | invalid JSON、source ID mismatch | Brief schema/source_ids gate |
| LLM provider: final top audit | 已实现（implemented） | compute/LLM | final top candidates, history context | duplicate-drop decisions | No external write | No | Yes | false duplicate decision | final_top_llm_audit gate |
| Filesystem artifact read | 已实现（implemented） | local read | project prompt/config/test files; operator-supplied replay paths | strings/JSON | No | Yes | No | 指向 private local artifact 时可能误读 | Privacy gate |
| Filesystem artifact write | 已实现（implemented） | local write/storage | evidence, report, lint, brief, audit, publish result | `outputs/<date>/...` | Yes, local only | Partially | No | committing/sharing private artifacts | Privacy gate；observability gate |
| Event history state | 已实现（implemented） | local state | final top events, configured history path | `state/event_history.jsonl` when enabled | Yes | Partially | No | duplicate or stale history state | History gate；state gate |
| GitHub Actions workflow | 运行时外已实现（implemented outside runtime） | scheduler/external trigger | `workflow_dispatch` ref and inputs | GitHub run, Summary, artifact bundle | Yes | No | external trigger needs GitHub auth | wrong ref/date, production run | Approval Gate；Publish Gate |
| Feishu tenant token | 已实现（implemented） | auth | app id/secret from env/GitHub secrets | tenant token | auth side effect only | cached per client | Yes | secret leakage | Privacy gate |
| Feishu docx import | 已实现（implemented） | 外部发布/write | report file, folder token, import settings | docx URL/token or failure/fallback | Yes | No | Yes | wrong folder, duplicate doc, timeout | Publish Gate |
| Feishu Drive Markdown upload | 已实现（implemented） | 外部发布/write | report Markdown, folder token | file URL/token | Yes | No | Yes | duplicate upload, wrong folder | Publish Gate |
| Feishu temporary source delete | 部分实现（partial） | external delete/cleanup | temporary file token | delete result | Yes | Mostly | Yes | wrong token deletion | Destructive-action gate；rollback gate |
| Feishu bot card webhook | 已实现（implemented） | notification/send | brief, doc URL, webhook, optional signing secret | bot response/result | Yes | No | Yes | wrong audience, leaked URL, noisy card | Bot Gate；Publish Gate |
| `pytest` | 已实现（implemented） | local verification | test targets | test result | No 外部副作用（external_side_effects） expected | Yes | No | tests may be incomplete | Test gate |
| Eval/静态检查器 | 计划中（planned） | local verification | `evals/*.jsonl`, schemas, sanitized fixtures | eval/static check result | No | Yes | No | coverage thin 时可能 false confidence | Eval gate |
| RunManifest schema validation | 计划中（planned） | local verification | planned `run_manifest.schema.json` and run manifest | validation result | No | Yes | No | schema drift | Future RunManifest gate |

## 副作用类型

| 类型 | 状态 | 示例 | 默认策略 |
| --- | --- | --- | --- |
| Read-only public | 已实现（implemented） | RSS, search result recall | 配置允许时可以执行；需要审计 provider 降级 |
| Local artifact write | 已实现（implemented） | `outputs/<date>/*.json`, report Markdown | runs 中允许；不要 commit private artifacts |
| External publish | 已实现（implemented） | Feishu docx/import/Drive upload | requires explicit trigger，并且 no-publish controls 必须生效 |
| External notification | 已实现（implemented） | Feishu bot card | requires send flag/webhook and publish gate |
| External workflow | 运行时外已实现（implemented outside runtime） | GitHub `workflow_dispatch` | human-triggered only |
| External delete/cleanup | 部分实现（partial） | Feishu temporary source delete | no new cleanup automation without explicit approval |
| Eval/static check | 计划中（planned） | JSONL and schema checks | 必须没有外部副作用（external_side_effects） |

## 所需密钥

状态： implemented as environment/GitHub-secret configuration。只记录变量名：

- `DEEPSEEK_API_KEY`
- `BOCHA_API_KEY`
- `TAVILY_API_KEY`
- `FEISHU_APP_ID`
- `FEISHU_APP_SECRET`
- `FEISHU_FOLDER_TOKEN`
- `FEISHU_TEMP_FOLDER_TOKEN`
- `FEISHU_BOT_WEBHOOK_URL`
- `FEISHU_BOT_SECRET`

不得打印、引用、提交或总结真实值。

## 当前缺口

- 无 formal `ToolCall` trace artifact。
- 无 machine-readable tool permission manifest。
- 无 formal run-level cost ledger。
- 外部发布 前无 formal approval artifact。
- Eval/静态检查器 在 Phase A task 中是 计划中（planned）；Phase C 已交付本地 静态检查器。
