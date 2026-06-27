---
type: pattern-note
project: AI Radar Agent
phase: Week 2
status: implemented
privacy: sanitized
external_side_effects: none
tags:
  - ai-radar
  - demo-run
  - sanitized-artifact
  - pattern-note
  - zh-CN
---

# 脱敏演示运行模式中文镜像

英文权威笔记 见 [../Sanitized_Demo_Run_Pattern.md](../Sanitized_Demo_Run_Pattern.md)。

## 模式

脱敏演示运行（sanitized demo run）让复核者看到具体产物集，同时不暴露私有运行输出，也不触发外部系统。它应当是确定性的、明确标记为模拟，并且与生产执行分离。

## Phase D 演示

AI Radar demo run 位于 `demo_run/`，包括：

- `demo_manifest.json`
- `demo_tool_calls.jsonl`
- `demo_evidence_items.jsonl`
- `demo_output_report.md`

manifest 包含：

```json
{
  "execution_mode": "demo_sandbox",
  "runtime_status": "simulated"
}
```

## 与生产执行的区别

| 维度 | 脱敏演示 | 生产执行 |
| --- | --- | --- |
| 数据 | 确定性的模拟数据 | 真实运行证据 |
| 网络 | 无 | 可能使用已配置的 provider |
| LLM | 跳过或模拟 | 可能调用已配置模型 |
| 发布 | 阻断 | 需要批准和已配置门禁 |
| 产物 | 作品集安全的演示文件 | 需要复核的私有运行输出 |

## 状态说明

| 能力 | 状态 |
| --- | --- |
| 脱敏演示 manifest | 已实现（implemented） |
| 模拟 ToolCall 记录 | 已实现（implemented） |
| 模拟 evidence items | 已实现（implemented） |
| 人类可读演示报告 | 已实现（implemented） |
| Dashboard/screenshots | 计划中（planned，P2 / Week 7 Portfolio） |

## 安全说明

- Demo artifacts are not 生产输出。
- Demo evidence is not 实时数据。
- No 外部发布 happened。
- No actual Obsidian vault was read or modified。

## 参考来源

- [Sanitized Demo Report](../../../demo_run/demo_output_report.md)
- [Sanitized Demo Manifest](../../../demo_run/demo_manifest.json)
- [Runtime Object Map 中文](../../zh-CN/13_RUNTIME_OBJECT_MAP.md)
- [Case Study 中文](../../zh-CN/case_study_ai_radar_week2.md)

## 相关笔记

- [[Evidence_First_Intelligence_Agent]]
- [[RunManifest_and_ToolCall_Contracts]]
- [[Publishing_Gates_and_Safety_Model]]
