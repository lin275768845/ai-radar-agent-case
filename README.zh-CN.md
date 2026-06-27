# AI Radar Agent

英文主版本见 [README.md](README.md)。

中文术语说明见 [docs/zh-CN/GLOSSARY.md](docs/zh-CN/GLOSSARY.md)。

## 公开案例镜像

本仓库是生产版 AI Radar Agent 的脱敏公开作品集镜像。

它主要用于：

- 架构审阅。
- 工作流审阅。
- 证据优先的情报 Agent 设计审阅。
- 安全与自治边界审阅。
- 评估用例、schema 契约和 demo artifacts 审阅。
- 案例研究和作品集展示。

它不是完整生产 clone，也不连接真实 Cloudflare、Feishu 或 GitHub
Actions 生产运行配置。私有生产仓库仍然独立保留。

生产 secrets、私有配置、真实生产 outputs、真实 Feishu 发布历史、
私有 runtime state，以及生产 `state/event_history.jsonl` 都被有意排除。

更多范围说明见
[docs/zh-CN/PUBLIC_MIRROR_SCOPE.md](docs/zh-CN/PUBLIC_MIRROR_SCOPE.md)。

## 这个镜像是什么

- 基于真实生产 agent 的脱敏作品集镜像。
- 用于展示证据优先的情报 Agent 架构与方法论。
- 用于审阅 workflow、gates、autonomy boundaries、schema contracts、
  evals、demo artifacts 和 public safety posture。
- 展示系统结构，但不暴露 credentials、private runtime state 或生产发布历史。

## 这个镜像不是什么

- 不是 turnkey deployment repo。
- 不是私有生产仓库的完整 clone。
- 不连接真实 Cloudflare、Feishu、provider 或 GitHub 生产配置。
- 不承诺 clone 后即可端到端复现私有生产流水线。
- 不存放生产 secrets、raw outputs、webhook configs 或 private
  operational notes。

## 你可以审阅什么

- 从 public-source recall 到 Evidence Gate、report generation、
  report linting、Publish Gate 和 review artifacts 的 evidence-first
  workflow。
- 本地工作、provider calls、GitHub Actions、Feishu publishing 和
  external notifications 的安全与自治边界。
- 面向未来运行时可观测性的 `RunManifest` 与 `ToolCall` schema contracts。
- `evals/` 下无外部副作用的 eval definitions 和本地静态 checker。
- `demo_run/` 下脱敏、模拟的 demo artifacts。
- Cloudflare + GitHub Actions trigger pattern。它是可审阅的部署模式，
  不是 live deployment。
- 关键 runtime reconciliation 与 safety logic，特别是 report
  reconciliation、lint、evidence gates 和 publish/bot guardrails。

## 你可以在本地运行什么

这些检查只在本地运行，不需要 secrets、provider keys，也没有外部副作用：

```bash
python3 evals/check_ai_radar_week2_eval_cases.py
python3 -m json.tool demo_run/demo_manifest.json
python3 -m py_compile ai_radar_agent/report_reconcile.py tests/test_report_reconcile.py
```

完整私有生产流水线不属于这个 public mirror 的可运行范围。

## 哪些内容被有意排除

- `.env`、`.env.*`、`.dev.vars`、token files、webhook configs 和 secrets。
- 生产 `state/event_history.jsonl`。
- 真实 Feishu 文档 URL 与生产发布历史。
- 生产 outputs、raw run artifacts、private logs、private runtime state 和
  private operational notes。
- Cloudflare、GitHub、Feishu、search provider 和 LLM secrets。
- 私有生产 source configuration。
- 私有生产 prompts。
- 私有部署配置和账号级设置。

在私有生产仓库中，source configuration 和 report prompts 会放在类似
`config/sources.yaml` 与 `prompts/radar_prompt.md` 的文件中。
这些文件被有意排除在公开镜像之外。

## 可运行性边界

这个 mirror 面向可审阅的架构与安全模式，不是 clone-and-run 的生产部署仓库。

真实生产执行需要私有 GitHub repository settings、Cloudflare Worker
settings、Feishu app/bot credentials、provider keys、production
prompts/configuration、production state 和 deployment controls。
这些内容都不包含在公开仓库中。

## 项目概览

AI Radar Agent 是一个证据优先的情报与发布代理。它收集公开 AI 行业信号，
通过 evidence 和 quality gates 过滤，再生成带来源约束的每日雷达报告。
只有在人工控制的发布门禁允许时，生产环境才会进入发布路径。

这个公开镜像重点展示 agent design：

- Recall before generation。
- Evidence before narrative。
- Schema contracts before runtime observability。
- Gates before publish。
- Local evals before broader automation。
- Redacted artifacts before public storytelling。

## 当前状态

| 领域 | 公开镜像状态 | 说明 |
| --- | --- | --- |
| 核心工作流文档 | 已实现 | Workflow、autonomy、tools、gates、eval plan、observability 和 runbook 已文档化。 |
| `RunManifest` / `ToolCall` schemas | 已实现 | Contracts 位于 `schemas/`；runtime emission 仍是 planned。 |
| 静态 eval definitions | 已实现 | 10 个 no-side-effect eval cases 用 JSONL 定义。 |
| 静态 eval checker | 已实现 | 本地 checker 校验 eval definitions 和 schema JSON。 |
| Runtime eval integration | 计划中 | Checker 校验定义，不校验真实 runtime behavior。 |
| Sanitized demo run | 已实现 | Demo artifacts 使用确定性 mock data，并明确标记为 simulated。 |
| 中文文档 | 已实现 | 中文镜像文档位于 `README.zh-CN.md` 和 `docs/zh-CN/`。 |
| External publish | 私有生产环境控制（human-gated） | 真实发布能力不属于公开镜像的可运行范围。 |
| Dashboard/screenshots | 计划中 | 不属于本次 mirror polish。 |

## 工作流草图

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

公开镜像包含让这个 workflow 可审阅的代码、文档、schemas、evals 和脱敏
demo artifacts。它不包含端到端运行生产路径所需的私有配置。

## 产物地图

| 产物 | 用途 |
| --- | --- |
| [docs/zh-CN/PUBLIC_MIRROR_SCOPE.md](docs/zh-CN/PUBLIC_MIRROR_SCOPE.md) | 公开镜像范围与可运行性边界。 |
| [docs/03_WORKFLOW.md](docs/03_WORKFLOW.md) | 从 recall 到 artifacts 和 publish gate 的工作流。 |
| [docs/04_AUTONOMY_MATRIX.md](docs/04_AUTONOMY_MATRIX.md) | 自治边界和人工批准点。 |
| [docs/06_TOOLS_AND_PERMISSIONS.md](docs/06_TOOLS_AND_PERMISSIONS.md) | 工具权限矩阵和 side-effect classes。 |
| [docs/09_GATES_AND_GUARDRAILS.md](docs/09_GATES_AND_GUARDRAILS.md) | Evidence、report、brief、publish、privacy 和 manifest gates。 |
| [docs/10_EVAL_PLAN.md](docs/10_EVAL_PLAN.md) | Eval strategy 和 static checker status。 |
| [docs/11_OBSERVABILITY.md](docs/11_OBSERVABILITY.md) | 当前 artifacts、observability gaps 和 manifest direction。 |
| [docs/12_RUNBOOK.md](docs/12_RUNBOOK.md) | Safe local modes、common failures 和 emergency stop guidance。 |
| [docs/13_RUNTIME_OBJECT_MAP.md](docs/13_RUNTIME_OBJECT_MAP.md) | Manifests、tool calls、gates、evals 和 demos 的关系。 |
| [schemas/run_manifest.schema.json](schemas/run_manifest.schema.json) | Run-level schema contract。 |
| [schemas/tool_call.schema.json](schemas/tool_call.schema.json) | Per-tool-call schema contract。 |
| [evals/ai_radar_week2_eval_cases.jsonl](evals/ai_radar_week2_eval_cases.jsonl) | No-side-effect eval case definitions。 |
| [evals/check_ai_radar_week2_eval_cases.py](evals/check_ai_radar_week2_eval_cases.py) | 本地静态 checker。 |
| [demo_run/demo_output_report.md](demo_run/demo_output_report.md) | 脱敏模拟 demo report。 |
| [docs/case_study_ai_radar_week2.md](docs/case_study_ai_radar_week2.md) | Public case-study draft。 |

## 公开仓库结构

```text
.
├── ai_radar_agent/          # 供审阅的 Python package 和 runtime logic
├── ai_radar_agent/fetchers/ # RSS、Bocha、Tavily fetcher modules
├── cloudflare/              # Mirror-safe Worker trigger pattern
├── demo_run/                # 脱敏模拟 demo artifacts
├── docs/                    # Architecture、workflow、operations docs
├── evals/                   # Static no-side-effect eval cases and checker
├── schemas/                 # RunManifest / ToolCall schema contracts
├── state/                   # 仅 sample event-history shape
├── tests/                   # Regression tests
├── .github/workflows/       # Manual workflow pattern
├── pyproject.toml
└── README.md
```

## Demo Artifacts

`demo_run/` 目录包含 deterministic、sanitized、simulated artifacts。
它们用于展示 artifact shape 和 safety posture，不使用生产数据。

包含的 demo artifacts：

- `demo_manifest.json`
- `demo_tool_calls.jsonl`
- `demo_evidence_items.jsonl`
- `demo_output_report.md`

这些不是实时市场情报，也不应被描述为 production outputs。

## Cloudflare 与 GitHub Actions Pattern

镜像包含 `cloudflare/ai-radar-trigger/` 下的 Cloudflare Worker trigger
pattern，以及 `.github/workflows/` 下的 manual GitHub Actions workflow
pattern。

这些文件用于 architecture 和 safety review。它们不表示这个公开仓库已经部署
到 Cloudflare，也不表示它连接了真实 Feishu/provider credentials。

提交到公开镜像里的默认值是安全的：

- `GITHUB_REPO = "ai-radar-agent-case"`
- `GITHUB_REF = "main"`
- `BOCHA_ENABLED = "false"`

私有生产部署必须在公开仓库之外覆盖 deployment settings 和 secrets。

## 安全姿态

- 不提交 `.env`、secrets、tokens、cookies、webhooks、private logs 或
  real credentials。
- 不把真实 Feishu、GitHub、DeepSeek、Bocha、Tavily、Cloudflare 或
  provider secrets 粘贴进 issues、docs、prompts、logs 或 chat。
- 生产 `outputs/` 和生产 `state/event_history.jsonl` 应视为 private
  operational artifacts。
- Logs 和 summaries 应保持 redacted，不输出 full prompts、full evidence
  payloads、LLM payloads、HTTP headers、secrets 或 webhook URLs。
- External publishing、workflow dispatch、Feishu bot sends 和 deployment
  changes 仍然是 human-owned production actions。

## 维护说明

- 公开 README 应聚焦 architecture、workflow、safety、evals、schemas 和
  sanitized demos。
- 私有 production runbooks、prompts、source configs 和 state 应留在公开
  mirror 之外。
- 更新文档时，应保持 implemented、partial、planned、simulated 和
  private-production-only 的区别。
- 更新 Cloudflare 示例时，应保持 mirror-safe defaults，不加入真实 account
  IDs、tokens、worker URLs、webhook URLs 或 secrets。

## License / 使用限制

License not yet specified。本仓库用于作品集审阅；除非后续添加 license，
否则不授予复用权利。
