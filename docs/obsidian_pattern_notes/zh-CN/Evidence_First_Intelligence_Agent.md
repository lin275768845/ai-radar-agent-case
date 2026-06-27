---
type: pattern-note
project: AI Radar Agent
phase: Week 2
status: implemented
privacy: sanitized
external_side_effects: none
tags:
  - ai-radar
  - evidence-first
  - intelligence-agent
  - pattern-note
  - zh-CN
---

# 证据优先的情报代理中文镜像

英文权威笔记 见 [../Evidence_First_Intelligence_Agent.md](../Evidence_First_Intelligence_Agent.md)。

## 模式

evidence-first intelligence agent 在写 narrative 之前先把 claims 绑定到 来源记录。agent 应先 collect signals，apply Evidence Gate，record uncertainty，然后再 draft report 或 brief。

```text
Sources
  -> Evidence Collection
  -> Evidence Gate
  -> Intelligence Draft
  -> Report / Brief / Top Event Audits
  -> Publish Gate
  -> Local Artifacts / Optional Future Publishing
```

## 为什么证据门禁重要

Evidence Gate 防止 weak、stale、duplicated 或 unsupported items 变成 confident narrative。它也为 reviewer 提供 artifact trail，说明某个 item 为什么 accepted、warned、dropped 或 blocked。

已实现（implemented） examples：

- Phase A documents the Evidence Gate and source quality guardrails。
- Phase C includes eval cases for evidence risks。
- Phase D demo evidence uses deterministic mock records only。

## 不确定性与不过度宣称

source quality 混合或 item 类似历史事件时，agent 应保留 uncertainty。在 sanitized demo 中，一个 mock evidence item 被保留为 supportive context，而不是被写成 fresh top event。

No overclaiming means：

- 不 invent official sources。
- 不把 old events 写成 today events。
- 不把 mock demo records 当作 实时数据。
- Publish Gate blocked 时不 publish narrative。

## 状态说明

| 能力 | 状态 |
| --- | --- |
| Evidence Gate documentation | 已实现（implemented） |
| Evidence-first workflow docs | 已实现（implemented） |
| Static eval cases for evidence risks | 已实现（implemented） |
| 运行时评估集成 | 计划中（planned） |
| Runtime RunManifest emission | 计划中（planned） |

## 参考来源

- [Workflow 中文](../../zh-CN/03_WORKFLOW.md)
- [Gates And Guardrails 中文](../../zh-CN/09_GATES_AND_GUARDRAILS.md)
- [Eval Plan 中文](../../zh-CN/10_EVAL_PLAN.md)
- [Eval Cases](../../../evals/ai_radar_week2_eval_cases.jsonl)
- [Sanitized Demo Report](../../../demo_run/demo_output_report.md)

## 相关笔记

- [[Publishing_Gates_and_Safety_Model]]
- [[No_Side_Effect_Eval_Suite]]
- [[Sanitized_Demo_Run_Pattern]]
