---
type: pattern-note
project: AI Radar Agent
phase: Week 2
status: implemented
privacy: sanitized
external_side_effects: none
tags:
  - ai-radar
  - autonomy
  - permissions
  - pattern-note
  - zh-CN
---

# 代理自治与权限边界中文镜像

英文权威笔记 见 [../Agent_Autonomy_and_Permission_Boundaries.md](../Agent_Autonomy_and_Permission_Boundaries.md)。

## 模式

Agent autonomy 应被描述成 permission model，而不只是 prompt instruction。AI Radar 区分 safe local actions、外部副作用（external_side_effects） 与 由人负责 commitments。

## 自治层级

| 层级 | 状态 | 示例 |
| --- | --- | --- |
| 只读或静态检查 | 已实现（implemented） | 读取文档、schemas、评估定义和脱敏演示产物 |
| 本地产物生成 | Week 2 产物已实现（implemented for Week 2 artifacts） | 创建文档、schema 契约、评估定义和脱敏演示产物 |
| Provider 或 LLM 调用 | Week 2 未使用（not used in Week 2） | 文档、评估、演示阶段不得发生 |
| 外部发布或通知 | Week 2 已阻断（blocked for Week 2） | 未触发 Feishu publish、bot send、webhook 或 workflow dispatch |
| Irreversible or production actions | 由人负责 / 人类负责 | explicit approval required outside Week 2 standardization artifacts |

## Week 2 允许的动作

- 创建 sanitized documentation。
- 定义 schema 契约。
- 定义无外部副作用评估用例。
- 运行 local static validation。
- 创建确定性的模拟演示产物。
- 在 repo 内创建 Obsidian-ready export notes。

## Week 2 禁止的动作

- No 外部发布。
- No Feishu call。
- No webhook call。
- No GitHub workflow dispatch。
- No external provider call。
- No LLM invocation。
- No 生产流水线 execution。
- No reading of secrets, private notes, private logs, or private runtime outputs。

## 边界原则

如果一个 action 会写到 local repo 外部、send message、publish document、trigger workflow、change production state 或 expose private data，它必须位于 人工确认 gate 后。

## 状态说明

| 边界 | 状态 |
| --- | --- |
| Autonomy matrix | 已实现（implemented） |
| Tool permission matrix | 已实现（implemented） |
| Week 2 无外部副作用 | 已实现（implemented） |
| Runtime approval artifact | 部分实现（partial） |
| 本案例中的自动外部发布 | 计划中/人工（planned/manual），Week 2 产物未启用 |

## 参考来源

- [Autonomy Matrix 中文](../../zh-CN/04_AUTONOMY_MATRIX.md)
- [Tools And Permissions 中文](../../zh-CN/06_TOOLS_AND_PERMISSIONS.md)
- [Runbook 中文](../../zh-CN/12_RUNBOOK.md)
- [Case Study 中文](../../zh-CN/case_study_ai_radar_week2.md)

## 相关笔记

- [[Publishing_Gates_and_Safety_Model]]
- [[No_Side_Effect_Eval_Suite]]
- [[Sanitized_Demo_Run_Pattern]]
