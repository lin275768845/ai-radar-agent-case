---
type: pattern-note
project: AI Radar Agent
phase: Week 2
status: implemented
privacy: sanitized
external_side_effects: none
tags:
  - ai-radar
  - agent-engineering
  - moc
  - pattern-note
  - zh-CN
---

# AI Radar Week 2 内容地图中文镜像

英文权威笔记 见 [../AI_Radar_Week2_MOC.md](../AI_Radar_Week2_MOC.md)。

## 摘要

AI Radar Week 2 将证据优先的情报与发布代理案例标准化。该工作把代理整理成可复核的作品集产物：文档化工作流、自治边界、门禁、schema 契约、评估定义，并生成脱敏的模拟演示运行。

这个文件夹只包含 Obsidian-ready export notes。notes 创建在 repo 内，没有导入任何 vault。

## 模式笔记

- [[Evidence_First_Intelligence_Agent]]
- [[Agent_Autonomy_and_Permission_Boundaries]]
- [[RunManifest_and_ToolCall_Contracts]]
- [[No_Side_Effect_Eval_Suite]]
- [[Sanitized_Demo_Run_Pattern]]
- [[Publishing_Gates_and_Safety_Model]]

## 状态快照

| 领域 | 状态 | 说明 |
| --- | --- | --- |
| Phase A 文档 | 已实现（implemented） | 工作流、自治边界、工具、门禁、评估计划、可观测性和运行手册已文档化。 |
| Phase B schema 契约 | 已实现（implemented） | RunManifest 与 ToolCall 契约已存在。 |
| Phase C 评估用例与静态检查器 | 已实现（implemented） | 10 个本地无外部副作用评估用例和检查器已存在。 |
| Phase D 脱敏演示运行（sanitized demo run） | 已实现（implemented） | 演示产物是确定性的模拟数据。 |
| Phase E README 与案例研究 | 已实现（implemented） | 面向作品集的 README 和案例研究草稿已存在。 |
| Phase F Obsidian-ready 笔记 | 已实现（implemented） | 仓库内脱敏笔记已可导出。 |
| RunManifest 与 ToolCall 的运行时产出 | 计划中（planned） | schema 契约已存在，但运行时产出仍是后续工作。 |
| 运行时评估集成 | 计划中（planned） | 静态检查器只校验定义，不校验真实运行时行为。 |
| 外部发布集成 | 部分实现（partial） | 运行时存在发布路径，但 Week 2 笔记和演示不启用外部发布。 |
| Feishu publish 与 GitHub workflow dispatch | 计划中/人工（planned/manual） | Week 2 标准化产物没有触发或启用它们。 |
| Dashboard 与截图 | 计划中（planned） | P2 / Week 7 Portfolio。 |

## 仓库产物地图

- [README 中文](../../../README.zh-CN.md)
- [Case Study 中文](../../zh-CN/case_study_ai_radar_week2.md)
- [Workflow 中文](../../zh-CN/03_WORKFLOW.md)
- [Autonomy Matrix 中文](../../zh-CN/04_AUTONOMY_MATRIX.md)
- [Tools And Permissions 中文](../../zh-CN/06_TOOLS_AND_PERMISSIONS.md)
- [Gates And Guardrails 中文](../../zh-CN/09_GATES_AND_GUARDRAILS.md)
- [Eval Plan 中文](../../zh-CN/10_EVAL_PLAN.md)
- [Observability 中文](../../zh-CN/11_OBSERVABILITY.md)
- [Runbook 中文](../../zh-CN/12_RUNBOOK.md)
- [Runtime Object Map 中文](../../zh-CN/13_RUNTIME_OBJECT_MAP.md)
- [RunManifest Schema](../../../schemas/run_manifest.schema.json)
- [ToolCall Schema](../../../schemas/tool_call.schema.json)
- [Eval Cases](../../../evals/ai_radar_week2_eval_cases.jsonl)
- [Eval Checker](../../../evals/check_ai_radar_week2_eval_cases.py)
- [Sanitized Demo Report](../../../demo_run/demo_output_report.md)
- [Sanitized Demo Manifest](../../../demo_run/demo_manifest.json)

## 导出边界

这些 notes 是 sanitized and portfolio-safe。它们不包含 secrets、private note contents、private paths、private runtime outputs 或 raw production artifacts。
