# AI Radar Week 2 Case Study 中文镜像

英文权威版本见 [../case_study_ai_radar_week2.md](../case_study_ai_radar_week2.md)。

## 1. Title

AI Radar Agent：证据优先的情报与发布代理 standardization。

## 2. Context

AI Radar 起点是一个每日 AI 行业雷达工作流：收集公开信号，把主张绑定到证据，生成简明报告，审计输出，并且只在已配置门禁允许时发布。Week 2 标准化把该项目整理成更清晰的代理产品案例：文档化工作流，定义运行时契约，增加无外部副作用评估用例，并生成脱敏演示运行（sanitized demo run）。

本案例研究只覆盖本地 Week 2 分支。它不声明演示产物是生产输出或实时市场情报。

## 3. Problem

AI news 与 product signals 噪声很高。一个有用的 intelligence agent 不只是 prompt；它需要能分离 evidence collection、evidence qualification、narrative drafting、quality checks、publishing decisions 与 observability 的 workflow。

主要风险是过度宣称。没有明确门禁和可追踪产物，代理可能把过期、薄弱、重复或缺少支撑的信号写成自信叙事。对发布工作流来说，第二个风险是副作用：文档创建、bot 消息、workflow dispatch、provider 调用都必须保持人工控制。

## 4. Design Goal

Week 2 目标是把 AI Radar 标准化为 evidence-first agent case：

- 让从 recall 到 Publish Gate 的 workflow 可读。
- 文档化 autonomy boundaries 与 tool permissions。
- 为未来 runtime observability 定义 RunManifest 与 ToolCall contracts。
- 添加禁止外部副作用（external_side_effects）的本地评估定义。
- 生成脱敏演示运行（sanitized demo run），展示产物形态但不执行生产。
- 让所有工作保持 local and reviewable。

## 5. Constraints

- No 生产流水线 execution。
- No RSS、Bocha、Tavily、LLM、Feishu、webhook、GitHub workflow、外部发布 calls。
- No business-code or prompt-source changes。
- No reading of secrets、`.env` values、tokens、webhooks、cookies、private logs、localStorage、private notes、private runtime outputs、private artifacts。
- 演示输出必须是确定性的模拟数据，或来自 Week 2 文档。
- External publishing intentionally disabled for Week 2。

## 6. Architecture

```text
Sources
  -> Evidence Collection
  -> Evidence Gate
  -> Intelligence Draft
  -> Report / Brief / Top Event Audits
  -> Publish Gate
  -> Local Artifacts / Optional Future Publishing
```

架构围绕 gates 组织，而不是单一 autonomous generation step。Source recall 与 local artifact writing 在安全语境下可以自动化；外部发布 与 workflow dispatch 被视为 high-risk side effects。

## 7. Evidence-First Workflow

workflow 从 Beijing natural-day window 开始，然后在真实系统中通过 configured recall sources 收集 public signals。Evidence 会经过 filtering、dedupe、history check，并通过 source-bound artifacts 进入 report 和 brief generation。

Week 2 在 [03_WORKFLOW.md](03_WORKFLOW.md) 中文档化 workflow，并在 [11_OBSERVABILITY.md](11_OBSERVABILITY.md) 中记录 evidence、report lint、brief、top event audit 和 publish result 等 artifacts。

sanitized demo 中的 evidence items 是 [demo_run/demo_evidence_items.jsonl](../../demo_run/demo_evidence_items.jsonl) 中的 mock records。它们不是 实时数据，也不是 network fetched。

## 8. Safety And Autonomy Model

自治模型区分低风险本地动作与外部副作用（external_side_effects）：

- Local/static checks are allowed。
- Demo artifacts are local and simulated。
- 评估定义禁止 Feishu、webhook、GitHub workflow dispatch、外部发布、provider 调用、LLM 调用和生产流水线执行。
- Publish 与 bot-send paths 仍然 gated，并且需要 Week 2 demo/eval context 外的 explicit 人工确认。

主要参考：[04_AUTONOMY_MATRIX.md](04_AUTONOMY_MATRIX.md)、[06_TOOLS_AND_PERMISSIONS.md](06_TOOLS_AND_PERMISSIONS.md)、[09_GATES_AND_GUARDRAILS.md](09_GATES_AND_GUARDRAILS.md)。

## 9. Schema Contracts

Phase B 添加两个 schema 契约：

- [run_manifest.schema.json](../../schemas/run_manifest.schema.json) 定义 sanitized run-level manifest shape。
- [tool_call.schema.json](../../schemas/tool_call.schema.json) 定义 sanitized per-tool-call record shape。

这些是已实现的 schema 契约，不是运行时产出的证明。RunManifest 与 ToolCall 记录的运行时生成仍计划中（planned）。

## 10. Eval Suite

Phase C 在 [evals/ai_radar_week2_eval_cases.jsonl](../../evals/ai_radar_week2_eval_cases.jsonl) 中添加 10 个本地评估用例定义。用例覆盖证据门禁、发布门禁、工具权限、安全模式、schema 契约、可观测性、脱敏、失败处理、静态评估检查和 emergency stop。

静态检查器 [evals/check_ai_radar_week2_eval_cases.py](../../evals/check_ai_radar_week2_eval_cases.py) 校验 case file 与 Phase B schema JSON。它是 仅本地：不 import production code，不 call external APIs，不 invoke LLMs，不 trigger Feishu or GitHub，不 run 生产流水线。

运行时评估集成仍计划中（planned）。

## 11. Sanitized Demo Run

Phase D 在 [demo_run/](../../demo_run/) 下添加 deterministic local demo。manifest 明确使用：

```json
{
  "execution_mode": "demo_sandbox",
  "runtime_status": "simulated"
}
```

demo 包括：

- `demo_manifest.json`: 模拟的运行级 manifest。
- `demo_tool_calls.jsonl`: simulated ToolCall records。
- `demo_evidence_items.jsonl`: simulated evidence items。
- `demo_output_report.md`: human-readable sanitized demo report。

demo 不是 生产执行、不是 live recall、不是 external model output，也没有 externally published。

## 12. Implemented Vs Partial Vs Planned

| 领域 | 状态 | 说明 |
| --- | --- | --- |
| Phase A 工作流文档 | 已实现（implemented） | 核心工作流、自治边界、工具、门禁、评估计划、可观测性和运行手册已文档化。 |
| Phase B schema 契约 | 已实现（implemented） | RunManifest and ToolCall schemas exist。 |
| RunManifest / ToolCall 运行时产出 | 计划中（planned） | 运行时集成尚未完整实现。 |
| Phase C 评估定义 | 已实现（implemented） | 10 个无外部副作用用例已存在。 |
| Phase C 静态检查器 | 已实现（implemented） | 本地检查器校验评估定义和 schema JSON。 |
| 运行时评估执行 | 计划中（planned） | checker validates definitions, not real 运行时行为。 |
| Phase D 脱敏演示运行（sanitized demo run） | 已实现（implemented） | 演示产物是确定性的模拟数据。 |
| External publishing during Week 2 | 有意禁用（intentionally disabled） | No Feishu, webhook, workflow dispatch, or 外部发布 action was triggered。 |
| Dashboard 与截图 | 计划中（planned，P2 / Week 7 Portfolio） | 不包含在这个 curated public mirror 中。 |
| Obsidian-ready 模式笔记 | 私有/省略 | Pattern-note exports 不属于 curated public showcase。 |

## 13. Lessons Learned

- Workflow design should precede agent autonomy。
- Evidence quality and 来源绑定 need explicit gates before narrative generation。
- Publishing agents need side-effect boundaries, not just output formatting。
- Schema contracts can clarify intended observability before 运行时集成 is built。
- Static eval definitions must clearly state what they do not execute。
- 脱敏演示可以让代理案例可复核，同时不暴露私有产物或触发外部系统。

## 14. Next Steps

- Pattern notes 和 private knowledge-base material 保持在 curated public showcase 之外。
- Future runtime work: emit RunManifest and ToolCall records from real runs。
- Future eval work: validate emitted manifests and selected runtime outputs locally。
- Portfolio work: create optional read-only dashboard/screenshots from sanitized artifacts。
- Optional PR/review after explicit approval。
