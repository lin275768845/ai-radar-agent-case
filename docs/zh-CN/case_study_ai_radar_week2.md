# AI Radar Week 2 案例研究中文镜像

英文权威版本见 [../case_study_ai_radar_week2.md](../case_study_ai_radar_week2.md)。

## 1. 标题

AI Radar Agent：证据优先的情报与发布代理标准化。

## 2. 背景

AI Radar 最初是一个每日 AI 行业雷达工作流：收集公开信号，把关键主张绑定到证据，
生成简明报告，审计输出，并且只在门禁允许时进入发布路径。

Week 2 的目标，是把这个工作流整理成更清晰的 Agent 产品案例：文档化工作流，
定义运行时契约，增加无外部副作用的评估用例，并生成一组脱敏演示产物。

本案例只描述 Week 2 标准化成果。脱敏演示产物不是生产输出，也不是实时市场情报。

## 3. 问题

AI 新闻和产品信号噪声很高。一个有用的情报 Agent 不能只依赖 prompt，
还需要清楚地区分信号收集、证据筛选、叙事生成、质量审计、发布决策和可观测性。

主要风险是过度断言。没有明确门禁和可追踪产物时，Agent 可能把过期、薄弱、
重复或缺少来源支撑的信号写成自信结论。

对发布工作流来说，另一个风险是外部副作用（external_side_effects）：
创建文档、发送 bot 消息、触发 `workflow_dispatch`、调用 provider 等动作都必须保持人工控制。

## 4. 设计目标

Week 2 将 AI Radar 标准化为一个证据优先的 Agent 案例：

- 让从召回到发布门禁（Publish Gate）的工作流可读。
- 文档化自治边界和工具权限。
- 为未来运行时可观测性定义运行清单（RunManifest）和工具调用记录（ToolCall）契约。
- 添加禁止外部副作用的本地评估定义。
- 生成脱敏演示运行，展示产物形态但不执行生产。
- 让所有 Week 2 验收保持本地、可复核、不发布。

## 5. 约束

- 不运行生产流水线。
- 不调用 RSS、Bocha、Tavily、LLM、Feishu、webhook、GitHub workflow 或其他外部发布路径。
- 不修改业务代码或 prompt 源。
- 不读取 secrets、`.env` values、tokens、webhooks、cookies、私有日志、localStorage、私有笔记、私有运行输出或私有 artifacts。
- 演示输出必须使用确定性模拟数据，或来自 Week 2 文档。
- Week 2 期间外部发布保持禁用。

## 6. 架构

```text
公开来源
  -> 证据收集
  -> 证据门禁
  -> 情报草稿
  -> 报告 / brief / Top 事件审计
  -> 发布门禁
  -> 本地产物 / 可选的私有生产发布路径
```

架构围绕门禁组织，而不是围绕单次自动生成组织。来源召回和本地产物写入可以在安全语境下自动化；
外部发布和 `workflow_dispatch` 被视为高风险副作用，需要人工控制。

## 7. 证据优先工作流

工作流从北京时间自然日窗口开始。真实系统会通过配置好的召回来源收集公开信号，
随后进行过滤、去重、历史记录检查，并通过来源绑定的产物进入报告和 brief 生成。

Week 2 在 [03_WORKFLOW.md](03_WORKFLOW.md) 中说明工作流，并在
[11_OBSERVABILITY.md](11_OBSERVABILITY.md) 中记录 evidence、report lint、brief、
top event audit 和 publish result 等产物方向。

脱敏演示中的 evidence items 位于
[demo_run/demo_evidence_items.jsonl](../../demo_run/demo_evidence_items.jsonl)，
是 mock records。它们不是实时数据，也不是网络抓取结果。

## 8. 安全与自治模型

自治模型区分低风险本地动作和外部副作用：

- 允许本地静态检查。
- 演示产物必须本地生成且保持模拟。
- 评估定义禁止 Feishu、webhook、GitHub workflow dispatch、外部发布、provider 调用、LLM 调用和生产流水线执行。
- 发布和 bot 发送路径仍受门禁控制，并且需要 Week 2 demo/eval 语境之外的明确人工确认。

主要参考：
[04_AUTONOMY_MATRIX.md](04_AUTONOMY_MATRIX.md)、
[06_TOOLS_AND_PERMISSIONS.md](06_TOOLS_AND_PERMISSIONS.md)、
[09_GATES_AND_GUARDRAILS.md](09_GATES_AND_GUARDRAILS.md)。

## 9. Schema 契约

Phase B 添加了两个 schema 契约：

- [run_manifest.schema.json](../../schemas/run_manifest.schema.json)：定义脱敏运行级 manifest 的形状。
- [tool_call.schema.json](../../schemas/tool_call.schema.json)：定义脱敏单次工具调用记录的形状。

这些是已实现的 schema 契约，不等于运行时已经完整产出对应对象。
`RunManifest` 与 `ToolCall` 的完整运行时生成仍计划中。

## 10. 评估用例

Phase C 在 [evals/ai_radar_week2_eval_cases.jsonl](../../evals/ai_radar_week2_eval_cases.jsonl)
中添加 10 个本地评估用例定义，覆盖证据门禁、发布门禁、工具权限、安全模式、schema 契约、
可观测性、脱敏、失败处理、静态检查和 emergency stop。

静态检查器 [evals/check_ai_radar_week2_eval_cases.py](../../evals/check_ai_radar_week2_eval_cases.py)
校验 case file 与 Phase B schema JSON。它只在本地运行：不 import production code，
不调用外部 API，不 invoke LLMs，不触发 Feishu 或 GitHub，不运行生产流水线。

运行时评估集成仍计划中。

## 11. 脱敏演示运行

Phase D 在 [demo_run/](../../demo_run/) 下添加确定性的本地演示。manifest 明确标记：

```json
{
  "execution_mode": "demo_sandbox",
  "runtime_status": "simulated"
}
```

演示包含：

- `demo_manifest.json`：模拟的运行级 manifest。
- `demo_tool_calls.jsonl`：模拟的 ToolCall records。
- `demo_evidence_items.jsonl`：模拟的 evidence items。
- `demo_output_report.md`：面向人阅读的脱敏演示报告。

这些 demo 不是生产执行，不是 live recall，不是外部模型输出，也没有被外部发布。

## 12. 已实现、部分实现与计划中

| 领域 | 状态 | 说明 |
| --- | --- | --- |
| Phase A 工作流文档 | 已实现 | 核心工作流、自治边界、工具、门禁、评估计划、可观测性和运行手册已文档化。 |
| Phase B schema 契约 | 已实现 | `RunManifest` 和 `ToolCall` schemas 已存在。 |
| `RunManifest` / `ToolCall` 运行时产出 | 计划中 | 完整运行时集成尚未实现。 |
| Phase C 评估定义 | 已实现 | 10 个无外部副作用用例已存在。 |
| Phase C 静态检查器 | 已实现 | 本地检查器校验评估定义和 schema JSON。 |
| 运行时评估执行 | 计划中 | 检查器校验定义，不校验真实运行行为。 |
| Phase D 脱敏演示运行 | 已实现 | 演示产物使用确定性模拟数据。 |
| Week 2 外部发布 | 有意禁用 | 未触发 Feishu、webhook、workflow dispatch 或外部发布动作。 |
| Dashboard 与截图 | 计划中 | 不包含在当前精选公开镜像中。 |
| Obsidian-ready 模式笔记 | 私有 / 省略 | Pattern-note exports 不属于当前公开作品集范围。 |

## 13. 经验总结

- 先定义工作流，再讨论 Agent 自治。
- 叙事生成前必须有证据质量和来源绑定门禁。
- 发布型 Agent 需要外部副作用边界，而不只是输出格式。
- Schema 契约可以在运行时集成完成前，先澄清可观测性方向。
- 静态评估定义必须明确说明自己不会执行什么。
- 脱敏演示可以让 Agent 案例可复核，同时避免暴露私有产物或触发外部系统。

## 14. 下一步

- Pattern notes 和私有知识库材料继续留在精选公开镜像之外。
- 未来运行时工作：从真实运行中产出 `RunManifest` 和 `ToolCall` records。
- 未来评估工作：在本地校验已产出的 manifests 和选定运行产物。
- 作品集工作：基于脱敏 artifacts 制作可选的只读 dashboard 或 screenshots。
- 任何 PR / review 流程都需要明确批准后再进行。
