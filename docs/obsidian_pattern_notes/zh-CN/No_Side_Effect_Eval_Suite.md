---
type: pattern-note
project: AI Radar Agent
phase: Week 2
status: implemented
privacy: sanitized
external_side_effects: none
tags:
  - ai-radar
  - evals
  - no-side-effect
  - pattern-note
  - zh-CN
---

# 无外部副作用评估套件中文镜像

英文权威笔记 见 [../No_Side_Effect_Eval_Suite.md](../No_Side_Effect_Eval_Suite.md)。

## 模式

无外部副作用评估套件在不调用生产系统的情况下校验定义和安全预期。它应先证明评估输入形态正确，再考虑运行时集成。

## Week 2 评估套件

Phase C 已实现 10 个本地评估用例定义，覆盖：

- evidence_gate
- publish_gate
- tool_permission
- safety_mode
- schema_contract
- observability
- redaction
- failure_handling
- eval_static_check
- emergency_stop

每个用例都把 `no_external_side_effects` 设为 true，并禁止外部发布、workflow dispatch、webhook 调用、provider 调用、LLM 调用和生产流水线执行。

## 静态检查器

checker 校验：

- exactly 10 JSONL records
- required fields
- expected case ids
- unique case ids
- category coverage
- forbidden external-risk actions
- related docs and schemas
- Phase B schema JSON validity

checker 是 local/static。它不 import production code，不 call external APIs，不 invoke LLMs，不 trigger Feishu 或 GitHub，不 run 生产流水线。

## 仍处于计划中的内容

| 项目 | 状态 |
| --- | --- |
| 评估用例定义 | 已实现（implemented） |
| 静态检查器 | 已实现（implemented） |
| 运行时评估执行 | 计划中（planned） |
| 校验已产出的 RunManifest 产物 | 计划中（planned） |
| stale rate 或 source validity 的指标报告 | 计划中（planned） |

## 参考来源

- [Eval Plan 中文](../../zh-CN/10_EVAL_PLAN.md)
- [Eval Cases](../../../evals/ai_radar_week2_eval_cases.jsonl)
- [Eval Checker](../../../evals/check_ai_radar_week2_eval_cases.py)
- [Runtime Object Map 中文](../../zh-CN/13_RUNTIME_OBJECT_MAP.md)

## 相关笔记

- [[Evidence_First_Intelligence_Agent]]
- [[RunManifest_and_ToolCall_Contracts]]
- [[Publishing_Gates_and_Safety_Model]]
