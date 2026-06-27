# 13 运行时对象地图中文镜像

英文权威版本见 [../13_RUNTIME_OBJECT_MAP.md](../13_RUNTIME_OBJECT_MAP.md)。

- 项目： AI Radar Agent
- 代理类型： 证据优先的情报与发布代理
- 状态： active
- 事实来源： Phase A docs, current artifacts, schema contracts in `schemas/`

## 目的

本 map 定义 AI Radar 作为 证据优先的情报与发布代理 case 时，计划使用的 runtime objects。

Phase B 已实现 `RunManifest` 和 `ToolCall` 的 schema 契约。Phase C 已实现 10 个本地评估用例定义和最小静态检查器。Phase D 已实现脱敏的模拟演示运行。Phase E 已实现作品集 README 与案例研究草稿。这些文档和检查不改变运行时行为，也不意味着当前 runtime 已产出 `run_manifest.json`、tool-call trace artifact 或 runtime `EvalResult` 产物。

## 状态词汇

- 已实现（implemented）：对象、产物或 schema 已存在于仓库或当前 runtime。
- 部分实现（partial）：object 已由 docs/artifacts/tests 描述，但 运行时集成、formal schema validation 或 durable trace support 尚不完整。
- 计划中（planned）：后续工作；不是当前本地标准化工作的已实现 runtime 行为。

## 对象关系

```text
RunbookMode / SafetyMode
-> RunManifest
   -> ToolCall[]
   -> EvidenceItem[]
   -> GateResult[]
   -> ArtifactRef[]
   -> PublishDecision / PublishAttempt
   -> EvalCase / EvalResult, when running future eval/static checks
```

manifest 应持有 redacted summaries 和 references，而不是 raw secrets、raw private logs、raw HTTP payloads、webhook URLs、cookies、credentials、localStorage dumps 或 private notes。

## 运行时对象清单

| 对象 | 用途 | 生产者 | 消费者 | 生命周期阶段 | 持久化位置 | Schema 状态 | 运行时产出状态 | 校验状态 | 敏感数据处理说明 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `RunManifest` | run-level evidence、gate、tool、artifact、safety、publish summary | planned runtime manifest writer | operators, eval checker, portfolio/case-study sanitizer | whole run | planned `outputs/<date>/run_manifest.json` or `runs/<run_id>/run_manifest.json` | implemented: `schemas/run_manifest.schema.json` | planned | planned | only redacted summaries and refs；never store secrets, raw logs, webhook URLs, private artifacts |
| `ToolCall` | sanitized per-tool invocation metadata | planned runtime manifest writer or tool wrapper | `RunManifest`, future eval/静态检查器, audit review | per tool/provider/local action | planned manifest `tool_calls[]` 或 tool-call trace artifact | implemented: `schemas/tool_call.schema.json` | planned | planned | raw tool inputs optional；应替换为 redacted `input_summary`/`output_summary` |
| `EvidenceItem` | source-bound AI signal candidate | implemented recall providers and Evidence Gate | report generator, report lint, brief, top event audit | recall and evidence gating | implemented `outputs/<date>/evidence.json`; planned manifest summary | partial: docs/current artifacts describe it, no dedicated formal schema in Phase B | implemented as current artifact | partial via tests and gates | may include source URLs/snippets；do not commit/share unsanitized artifacts |
| `GateResult` | pass/warn/fail/block decisions | implemented gates; planned manifest collector | runbook, Summary, eval checker, release review | after each gate | implemented gate artifacts; planned manifest `gates[]` | partial: embedded in RunManifest schema `$defs` | partial | partial | store counters and summaries；redact sensitive failure text |
| `ArtifactRef` | 产物的轻量引用，不复制内容 | 当前运行产物；计划中的 manifest collector | 操作者、案例研究脱敏流程、评估检查器 | 产物写入和最终摘要 | implemented `outputs/<date>/...`; planned manifest `artifacts[]` | partial: embedded in RunManifest and ToolCall schemas | partial | partial | 使用相对或逻辑路径；不包含 signed URL、token 或私有绝对路径 |
| `PublishDecision` | publish/bot side effects allowed, skipped, blocked, or attempted | implemented publish/bot logic; planned manifest collector | operators, approval review, privacy gate | pre-publish and post-publish | implemented `publish_result.json` and Summary fields; planned manifest section | partial: embedded in RunManifest schema | partial | partial | Feishu URLs may be private；record URL status or redacted summary |
| `PublishAttempt` | concrete 外部发布/send attempt and outcome | implemented Feishu docx/Drive/bot code | runbook, post-run audit | publish/bot stage | implemented `publish_result.json` plus bot metadata; planned external side-effect entries | partial | partial | partial | must mark 外部副作用（external_side_effects） explicitly；avoid webhook/credential values |
| `EvalCase` | synthetic or sanitized test case | implemented Phase C eval authoring | eval/静态检查器 | pre-change and regression validation | implemented `evals/ai_radar_week2_eval_cases.jsonl` | partial: JSONL contract implemented, standalone schema planned | implemented as static definitions | implemented for case-file shape; 运行时集成 planned | use sanitized summaries and synthetic inputs；never raw private run outputs |
| `EvalResult` | 本地无外部副作用检查器输出 | Phase C 静态检查器已用于定义校验；runtime eval result 仍计划中 | release review, case-study evidence | eval execution | checker stdout only for Phase C; planned local result artifact later | planned | planned | partial | aggregate outcomes only；no sensitive raw content |
| `DemoRun` | 脱敏的本地模拟产物集 | Phase D 演示编写已实现 | 作品集复核、案例研究、未来演示打磨 | demo review | implemented `demo_run/` | partial: conceptually aligned to RunManifest and ToolCall schemas | 已作为模拟产物实现 | partial: JSON/JSONL static checks only | 只使用确定性的模拟数据；不是生产输出或实时数据 |
| `RunbookMode` | dry-run, skip-llm, output-mode none, eval-only, emergency stop 等 operator-facing mode | implemented CLI/config/docs; planned manifest summary | operators and future checker | before run | docs/runbook; planned `safety_mode` in RunManifest | partial: represented by `safety_mode` in RunManifest schema | partial | partial | mode summaries must not include `.env` values, tokens, private config values |
| `SafetyMode` | 控制外部副作用（external_side_effects）的机器可读安全姿态 | 当前 flags/settings；计划中的 manifest writer | Publish Gate, Bot Gate, eval/静态检查器 | 外部动作之前 | planned RunManifest `safety_mode` | implemented in RunManifest schema | partial | planned | 记录 `publish_allowed` 等布尔值；不记录 secret 值 |

## 契约边界

- Phase B 已实现：`schemas/run_manifest.schema.json`、`schemas/tool_call.schema.json`、runtime object map。
- Phase B 后部分实现（partial）：docs 描述 `EvidenceItem`、`GateResult`、`ArtifactRef`、`PublishDecision`、`PublishAttempt`、`RunbookMode`、`SafetyMode`，但并非都有 standalone schema 或 manifest emission。
- Phase C 已实现：10 local eval case definitions 和 minimal 静态检查器。
- Phase D 已实现：`demo_run/` 下的 sanitized simulated demo artifacts。
- Phase E 已实现：portfolio README 和 Week 2 case study draft。
- Phase F 已实现：repo-local Obsidian-ready pattern notes。
- 计划中（planned）：runtime `RunManifest` generation、runtime `ToolCall` traces、emitted manifests 的 schema validation gates、dashboard/screenshots、外部发布 review artifacts、further portfolio polish。

## 阶段对应关系

| 阶段 | 状态 | 范围 |
| --- | --- | --- |
| Phase B: schema 契约与运行时对象地图 | 已实现（implemented） | 定义 RunManifest 与 ToolCall schema 契约，并文档化对象关系 |
| Phase C: 评估用例与静态检查器 | 已实现（implemented） | 添加 JSONL 评估用例和本地无外部副作用检查器 |
| Phase D: 脱敏演示运行（sanitized demo run） | 已实现（implemented） | 产出脱敏的模拟演示产物和输出包 |
| Phase E: README 作品集化改写与案例研究草稿 | 已实现（implemented） | 把已验证证据转成面向作品集的叙事 |
| Phase F: Obsidian 模式笔记 | 已实现（implemented） | 捕捉可复用模式，但不自动安装为全局规则 |

## 非目标

- No 运行时行为 change。
- No 生产流水线 run。
- No Feishu、webhook、GitHub workflow dispatch 或 外部发布 action。
- No prompt-source change。
- No runtime eval execution。
- No demo artifact creation in this localization patch。
- No schema/eval/demo JSON modification。
