# AI Radar Agent

英文主版本见 [README.md](README.md)。中文术语说明见
[docs/zh-CN/GLOSSARY.md](docs/zh-CN/GLOSSARY.md)。

## 一眼看懂

AI Radar Agent 是一个面向 AI 行业信息的证据优先情报 Agent。它每天从公开信息源中收集
AI 行业信号，例如模型发布、Agent 产品、企业采用、基础设施变化、政策动态和投融资事件；
再通过消息源质量、时间窗口、历史去重和证据门禁筛选出真正值得关注的事件，最终生成带来源约束的
AI 雷达报告。

它的核心亮点不是“自动写日报”，而是把日报生产过程拆成一个可审计的 Agent 工作流：
先召回和过滤证据，再让 LLM 在受约束的环节参与综合与表达。

LLM 参与的环节主要有三类：

- 报告生成：基于通过门禁的、带来源约束的证据生成每日雷达报告。
- brief / card 生成与修复：生成结构化摘要内容，并尽量把其中的来源引用对齐回 evidence catalog。
- 可选的最终 Top 审计：在确定性去重之后，通过 `final_top_llm_audit` 辅助识别高置信重复事件。

LLM 不被当作事实来源，不负责搜源，不拥有主去重逻辑，也不能决定是否发布。
系统还通过 Evidence Gate、report_lint、top_event_audit、发布门禁（Publish Gate）
和人工控制边界，尽量避免低质量消息、重复事件、幻觉内容和误发布。

简单说，它展示的是：如何把一个真实运行的 AI 信息流工具，升级成一个能解释判断依据、
能审计运行过程、能评估输出质量、并能安全发布的情报 Agent。

## 公开镜像定位

本仓库是生产版 AI Radar Agent 的脱敏公开镜像，面向作品集展示、架构审阅、
工作流审阅、安全边界审阅和案例研究。

它展示的是一个证据优先的情报 Agent 如何组织信号召回、证据门禁
（Evidence Gate）、发布门禁（Publish Gate）、评估用例、schema 契约、
脱敏演示产物和人工控制边界。

它不是可直接部署的生产仓库副本，也不连接真实的 Cloudflare、Feishu 或
GitHub Actions 生产运行配置。私有生产仓库仍然独立保留。

生产 secrets、私有配置、真实生产输出、真实 Feishu 发布历史、私有运行状态，
以及生产 `state/event_history.jsonl` 都已从公开镜像中排除。

推荐先阅读：

- [公开镜像范围说明](docs/zh-CN/PUBLIC_MIRROR_SCOPE.md)
- [Agent 策略面板](docs/zh-CN/STRATEGY_PANEL.md)
- [可视化架构说明](docs/zh-CN/ARCHITECTURE_OVERVIEW.md)

## 这个公开镜像是什么

- 基于真实生产 Agent 整理出的脱敏作品集镜像。
- 用来展示证据优先的情报工作流、门禁设计和安全边界。
- 适合审阅工作流、自治边界、schema 契约、评估用例、脱敏演示产物和公开安全姿态。
- 保留少量有代表性的代码片段，帮助理解关键运行逻辑。

## 这个公开镜像不是什么

- 不是完整的生产代码库导出。
- 不是 clone 后即可端到端运行的生产系统。
- 不包含生产 secrets、webhook 配置、私有运行状态、真实发布历史或原始生产输出。
- 不连接真实 Cloudflare、Feishu、provider 或 GitHub Actions 生产配置。
- 不承诺复现私有生产流水线。
- 不包含大部分生产专用模块、provider 集成、Feishu 发布实现和完整回归测试。

## 适合审阅的内容

- 从公开信号召回到证据门禁、报告生成、报告审计、发布门禁和审阅产物的完整思路。
- 本地执行、provider 调用、GitHub Actions、Feishu 发布和外部通知之间的权限边界。
- 运行清单（RunManifest）和工具调用记录（ToolCall）的 schema 契约。
- `evals/` 下无外部副作用（external_side_effects）的评估定义和本地静态检查器。
- `demo_run/` 下脱敏、模拟的演示产物。
- Cloudflare 与 GitHub Actions 的触发模式。这里展示的是可审阅的架构模式，不是线上部署。
- 有代表性的运行时代码片段，尤其是报告/brief 对齐与 Cloudflare 触发模式。

## 可以本地运行的安全检查

这些检查只读本地文件，不需要 secrets 或 provider keys，也不会产生外部副作用：

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

完整私有生产流水线不属于本公开镜像的可运行范围。

## 有意排除的内容

- `.env`、`.env.*`、`.dev.vars`、token 文件、webhook 配置和 secrets。
- 生产 `state/event_history.jsonl`。
- 真实 Feishu 文档链接与生产发布历史。
- 生产输出、原始运行产物、私有日志、私有运行状态和内部运维笔记。
- Cloudflare、GitHub、Feishu、search provider 和 LLM secrets。
- 私有生产消息源配置。
- 私有生产 prompts。
- 私有部署配置和账号级设置。
- 生产专用 Python 模块、provider 集成、Feishu 发布实现、完整回归测试、打包元数据和原始状态。

在私有生产仓库中，消息源配置和报告 prompts 会放在类似
`config/sources.yaml` 与 `prompts/radar_prompt.md` 的文件中。这些文件不属于公开镜像。

## 可运行性边界

本镜像服务于架构审阅和安全审阅，不是可直接部署的生产仓库。

真实生产运行还需要私有 GitHub repository settings、Cloudflare Worker
settings、Feishu app/bot credentials、provider keys、production
prompts/configuration、production state 和 deployment controls。以上内容都不在公开仓库中。

## 项目概览

AI Radar Agent 是一个证据优先的情报与发布代理。它收集公开 AI 行业信号，
先把主张绑定到来源，再通过证据质量、时间窗口和去重检查筛选候选事件，
最后生成每日雷达报告。只有在人工控制的发布门禁允许时，生产环境才会进入发布路径。

这个公开镜像重点展示以下工作原则：

- 先召回，再生成。
- 先证据，后叙事。
- 先定义 schema 契约，再扩展运行时可观测性。
- 先过门禁，再发布。
- 先做本地评估，再扩大自动化范围。
- 先脱敏，再公开展示。

## 当前实现状态

| 领域 | 公开镜像状态 | 说明 |
| --- | --- | --- |
| 核心工作流文档 | 已实现 | 工作流、自治边界、工具权限、门禁、评估计划、可观测性和运行手册已文档化。 |
| `RunManifest` / `ToolCall` schemas | 已实现 | 契约位于 `schemas/`；运行时完整产出仍计划中。 |
| 静态评估定义 | 已实现 | 10 个无外部副作用评估用例使用 JSONL 定义。 |
| 静态评估检查器 | 已实现 | 本地检查器校验评估定义和 schema JSON。 |
| 运行时评估集成 | 计划中 | 当前检查器校验定义，不校验真实运行行为。 |
| 脱敏演示运行 | 已实现 | 演示产物使用确定性 mock data，并明确标记为模拟运行。 |
| 中文文档 | 已实现 | 中文文档位于 `README.zh-CN.md` 和 `docs/zh-CN/`。 |
| 代表性代码片段 | 已实现 | 镜像保留报告对齐和触发模式代码，不保留完整生产代码库。 |
| 外部发布 | 私有生产环境控制 | 真实发布能力不属于公开镜像的可运行范围。 |
| Dashboard / screenshots | 计划中 | 不包含在当前作品集镜像中。 |

## 工作流概览

```text
触发模式或本地操作者
  -> 北京时间自然日窗口
  -> 公开来源召回
  -> 证据门禁与历史去重检查
  -> 过滤后的证据产物
  -> 报告生成路径
  -> 报告审计与 brief 校验
  -> 最终 Top 事件对齐
  -> 发布门禁
  -> 本地产物或私有生产发布路径
```

公开镜像保留了让这条工作流可审阅的文档、schema、评估用例、脱敏演示产物和少量代码片段。
它不包含端到端运行生产路径所需的私有配置或完整生产实现。

## 产物地图

| 产物 | 用途 |
| --- | --- |
| [docs/zh-CN/PUBLIC_MIRROR_SCOPE.md](docs/zh-CN/PUBLIC_MIRROR_SCOPE.md) | 说明公开镜像包含什么、不包含什么，以及可运行性边界。 |
| [docs/zh-CN/STRATEGY_PANEL.md](docs/zh-CN/STRATEGY_PANEL.md) | 说明信号筛选、证据门禁、发布门禁和人工控制边界。 |
| [docs/zh-CN/ARCHITECTURE_OVERVIEW.md](docs/zh-CN/ARCHITECTURE_OVERVIEW.md) | 用图示说明工作流、触发控制面、可观测对象和公开/私有边界。 |
| [docs/03_WORKFLOW.md](docs/03_WORKFLOW.md) | 从召回到产物和发布门禁的工作流说明。 |
| [docs/04_AUTONOMY_MATRIX.md](docs/04_AUTONOMY_MATRIX.md) | 自治边界和人工批准点。 |
| [docs/06_TOOLS_AND_PERMISSIONS.md](docs/06_TOOLS_AND_PERMISSIONS.md) | 工具权限矩阵和外部副作用分类。 |
| [docs/09_GATES_AND_GUARDRAILS.md](docs/09_GATES_AND_GUARDRAILS.md) | 证据、报告、brief、发布、隐私和 manifest 门禁。 |
| [docs/10_EVAL_PLAN.md](docs/10_EVAL_PLAN.md) | 评估策略和静态检查器状态。 |
| [docs/11_OBSERVABILITY.md](docs/11_OBSERVABILITY.md) | 当前产物、可观测性缺口和 manifest 方向。 |
| [docs/12_RUNBOOK.md](docs/12_RUNBOOK.md) | 安全本地模式、常见失败和紧急停止说明。 |
| [docs/13_RUNTIME_OBJECT_MAP.md](docs/13_RUNTIME_OBJECT_MAP.md) | manifests、tool calls、gates、evals 和 demos 的关系。 |
| [schemas/run_manifest.schema.json](schemas/run_manifest.schema.json) | 运行级 schema 契约。 |
| [schemas/tool_call.schema.json](schemas/tool_call.schema.json) | 单次工具调用 schema 契约。 |
| [evals/ai_radar_week2_eval_cases.jsonl](evals/ai_radar_week2_eval_cases.jsonl) | 无外部副作用的评估用例定义。 |
| [evals/check_ai_radar_week2_eval_cases.py](evals/check_ai_radar_week2_eval_cases.py) | 本地静态检查器。 |
| [demo_run/demo_output_report.md](demo_run/demo_output_report.md) | 脱敏模拟演示报告。 |
| [docs/case_study_ai_radar_week2.md](docs/case_study_ai_radar_week2.md) | 英文案例研究草稿。 |
| [ai_radar_agent/report_reconcile.py](ai_radar_agent/report_reconcile.py) | 代表性的报告/brief 对齐逻辑。 |
| [cloudflare/ai-radar-trigger/src/index.js](cloudflare/ai-radar-trigger/src/index.js) | 公开镜像安全的 Worker 触发模式代码。 |

## 公开仓库结构

```text
.
├── ai_radar_agent/          # 供审阅的代表性 Python 代码片段
├── cloudflare/              # 公开镜像安全的 Worker 触发模式
├── demo_run/                # 脱敏模拟演示产物
├── docs/                    # 架构、工作流和安全文档
├── evals/                   # 无外部副作用的静态评估用例与检查器
├── schemas/                 # RunManifest / ToolCall schema 契约
├── tests/                   # 代表性代码片段的测试
├── .github/workflows/       # 手动工作流模式
└── README.md
```

## 脱敏演示产物

`demo_run/` 目录中的产物是确定性、脱敏、模拟生成的样例。它们用于展示产物形态和安全姿态，
不使用生产数据。

包含的演示产物：

- `demo_manifest.json`
- `demo_tool_calls.jsonl`
- `demo_evidence_items.jsonl`
- `demo_output_report.md`

这些文件不是实时市场情报，也不应被描述为生产输出。

## Cloudflare 与 GitHub Actions 触发模式

镜像包含 `cloudflare/ai-radar-trigger/` 下的 Cloudflare Worker 触发模式，
以及 `.github/workflows/` 下的手动 GitHub Actions 静态检查流程。

这些文件用于架构和安全审阅。它们不表示公开仓库已经部署到 Cloudflare，
也不表示它连接了真实 Feishu 或 provider credentials。

公开镜像中的默认值保持安全：

- `GITHUB_REPO = "ai-radar-agent-case"`
- `GITHUB_REF = "main"`
- `BOCHA_ENABLED = "false"`

私有生产部署必须在公开仓库之外覆盖部署设置和 secrets。

## 安全姿态

- 不提交 `.env`、secrets、tokens、cookies、webhooks、私有日志或真实凭据。
- 不把真实 Feishu、GitHub、DeepSeek、Bocha、Tavily、Cloudflare 或 provider secrets 写入 issues、docs、prompts、logs 或 chat。
- 生产 `outputs/` 和生产 `state/event_history.jsonl` 应视为私有运维产物。
- 日志和摘要应保持脱敏，不输出完整 prompts、完整 evidence payloads、LLM payloads、HTTP headers、secrets 或 webhook URLs。
- 外部发布、`workflow_dispatch`、Feishu bot 发送和部署变更仍然是人工拥有的生产动作。

## 维护原则

- 公开 README 聚焦架构、工作流、安全边界、评估、schema 和脱敏演示。
- 私有生产 runbook、prompts、消息源配置和 state 应留在公开镜像之外。
- 生产专用实现文件只有在明显有助于架构审阅时才应进入公开镜像。
- 更新文档时，必须区分已实现、部分实现、计划中、模拟产物和私有生产环境能力。
- 更新 Cloudflare 示例时，必须保持公开镜像安全默认值，不加入真实 account IDs、tokens、worker URLs、webhook URLs 或 secrets。

## License / 使用限制

License not yet specified。本仓库用于作品集审阅；除非后续添加 license，否则不授予复用权利。
