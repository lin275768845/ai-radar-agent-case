---
type: pattern-note
project: AI Radar Agent
phase: Week 2
status: implemented
privacy: sanitized
external_side_effects: none
tags:
  - ai-radar
  - runmanifest
  - toolcall
  - schema-contract
  - pattern-note
  - zh-CN
---

# RunManifest 与 ToolCall 契约中文镜像

英文权威笔记 见 [../RunManifest_and_ToolCall_Contracts.md](../RunManifest_and_ToolCall_Contracts.md)。

## 模式

Schema contracts 可以在完整 运行时集成 之前，让 agent behavior 可 review。AI Radar 使用 RunManifest 和 ToolCall schemas 描述 sanitized run-level trace 与 per-tool-call trace 的预期形状。

## RunManifest 的用途

RunManifest 是计划中的 run-level object，用于记录：

- execution mode and safety mode
- input summary
- source and evidence summary
- ToolCall references
- gate results
- artifact references
- publish decisions
- 外部副作用（external_side_effects） records
- warnings, errors, metrics, and redaction status

## ToolCall 的用途

ToolCall 是计划中的 per-tool-call record，用于记录：

- tool name and category
- permission class
- purpose
- status
- redacted input and output summaries
- evidence, artifact, and gate references
- network access
- external_side_effects classification
- dry-run and sensitive-data policy

## 契约与运行时产出

| 项目 | 状态 | 含义 |
| --- | --- | --- |
| RunManifest schema | 已实现（implemented） | 契约已存在于仓库中。 |
| ToolCall schema | 已实现（implemented） | 契约已存在于仓库中。 |
| RunManifest 运行时产出 | 计划中（planned） | 当前运行时尚不产出正式 manifest 产物。 |
| ToolCall trace 运行时产出 | 计划中（planned） | 当前运行时尚不产出正式工具调用 trace 产物。 |
| Demo manifest 对齐 | 部分实现（partial） | Phase D 演示在概念上用模拟数据遵循该契约。 |

## 脱敏与敏感数据处理

contracts 要求 redacted summaries and references。它们不得存储 raw secrets、tokens、webhook URLs、cookies、credentials、private logs、private note contents、localStorage dumps 或 private runtime outputs。

## 参考来源

- [Runtime Object Map 中文](../../zh-CN/13_RUNTIME_OBJECT_MAP.md)
- [RunManifest Schema](../../../schemas/run_manifest.schema.json)
- [ToolCall Schema](../../../schemas/tool_call.schema.json)
- [Observability 中文](../../zh-CN/11_OBSERVABILITY.md)
- [Sanitized Demo Manifest](../../../demo_run/demo_manifest.json)

## 相关笔记

- [[Evidence_First_Intelligence_Agent]]
- [[No_Side_Effect_Eval_Suite]]
- [[Sanitized_Demo_Run_Pattern]]
