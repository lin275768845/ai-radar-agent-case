---
type: pattern-note
project: AI Radar Agent
phase: Week 2
status: implemented
privacy: sanitized
external_side_effects: none
tags:
  - ai-radar
  - gates
  - publish-safety
  - pattern-note
  - zh-CN
---

# 发布门禁与安全模型中文镜像

英文权威笔记 见 [../Publishing_Gates_and_Safety_Model.md](../Publishing_Gates_and_Safety_Model.md)。

## 模式

发布型代理需要分别为证据质量和外部副作用（external_side_effects）设置门禁。Evidence Gate 保护叙事质量；Publish Gate 保护外部系统和由人负责的承诺。

## 证据门禁（Evidence Gate）

Evidence Gate 检查 recalled items 是否可用于 narrative。它应发现 missing evidence、weak source fit、repeated history、stale events 和 unsupported source references。

状态：文档和当前运行时行为已实现（implemented）；运行时 manifest 集成仍计划中（planned）。

## 发布门禁（Publish Gate）

Publish Gate 决定文档发布、bot 卡片、workflow dispatch 或其他外部副作用（external_side_effects）是否可以继续。

For Week 2 standardization：

- Feishu publish is blocked。
- GitHub workflow dispatch is blocked。
- Webhook calls are blocked。
- External publish is blocked。
- Demo artifacts are local and simulated。

## 安全模式

| 模式 | 用途 | Week 2 状态 |
| --- | --- | --- |
| dry_run | 不发布的本地验证 | 已实现（implemented） |
| skip_llm | 只调试证据召回 | 已实现（implemented） |
| output_mode=none | 不发布的本地或 workflow 验证 | 已实现（implemented） |
| eval/static check | 本地定义校验 | Phase C checker 已实现；运行时集成计划中（planned） |
| emergency stop | 复核期间阻断外部动作 | 已文档化；更强的 runtime artifacting 仍计划中（planned） |

## 无外部边界

Week 2 案例有意保持无外部动作。它不触发 Feishu、GitHub workflow dispatch、webhook、外部发布、provider 调用或 LLM 调用。

## 状态说明

| 领域 | 状态 |
| --- | --- |
| Evidence Gate docs | 已实现（implemented） |
| Publish Gate docs | 已实现（implemented） |
| 评估/演示阶段无外部副作用（external_side_effects） | 已实现（implemented） |
| Formal runtime approval artifact | 部分实现（partial） |
| Runtime RunManifest gate | 计划中（planned） |
| Dashboard/screenshots | 计划中（planned，P2 / Week 7 Portfolio） |

## 参考来源

- [Gates And Guardrails 中文](../../zh-CN/09_GATES_AND_GUARDRAILS.md)
- [Runbook 中文](../../zh-CN/12_RUNBOOK.md)
- [Autonomy Matrix 中文](../../zh-CN/04_AUTONOMY_MATRIX.md)
- [Sanitized Demo Report](../../../demo_run/demo_output_report.md)

## 相关笔记

- [[Agent_Autonomy_and_Permission_Boundaries]]
- [[Evidence_First_Intelligence_Agent]]
- [[Sanitized_Demo_Run_Pattern]]
