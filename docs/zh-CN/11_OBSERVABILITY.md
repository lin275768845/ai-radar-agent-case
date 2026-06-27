# 11 可观测性中文镜像

英文权威版本见 [../11_OBSERVABILITY.md](../11_OBSERVABILITY.md)。

- 项目： AI Radar Agent
- 代理类型： 证据优先的情报与发布代理
- 状态： active

## 可观测性目标

每次 run 都应足够可解释，能够调试 source recall、Evidence Gate decisions、LLM/report behavior、report lint、brief generation、final-top dedupe、Feishu publishing、bot sending 和 safety gates，同时不暴露 secrets 或 private artifacts。

## 当前产物

状态：已实现（implemented）。

runtime 当前会或可能会产生这些 local/GitHub artifacts：

- `evidence.json`
- `evidence.md`
- `evidence_gate.json`
- `evidence_dropped.md`
- `AI_radar_<date>.md`
- `report_lint.json`
- `brief.json`
- `brief.md`
- `final_top_dedupe.json`
- `final_top_llm_audit.json`
- `top_event_audit.json`
- `publish_result.json`
- GitHub Summary / artifact bundle

## 产物用途地图

| 产物 | 状态 | 用途 | 隐私说明 |
| --- | --- | --- | --- |
| `evidence.json` | 已实现（implemented） | 结构化召回证据 | 可能包含 source URLs 和 full evidence snippets；视作 private run artifact |
| `evidence.md` | 已实现（implemented） | 人类可读的召回/provider 审计 | 可能包含 URLs 和 source summaries |
| `evidence_gate.json` | 已实现（implemented） | Evidence Gate 计数和决策 | review/redaction 后才适合公开 |
| `evidence_dropped.md` | 已实现（implemented） | 被丢弃证据的原因 | 可能包含 URLs；分享前 review |
| `AI_radar_<date>.md` | 已实现（implemented） | 完整生成的雷达报告 | review 前不要 publish/share |
| `report_lint.json` | 已实现（implemented） | 报告质量警告/错误 | 通常更安全，但仍需检查 embedded text |
| `brief.json` | 已实现（implemented） | 结构化卡片/报告 brief | 可能包含 doc URL/source URLs |
| `brief.md` | 已实现（implemented） | 人类可读 brief | sharing 前 review |
| `final_top_dedupe.json` | 已实现（implemented） | final top 去重决策 | 可能包含 titles/source refs |
| `final_top_llm_audit.json` | 已实现（implemented） | LLM 重复审计决策 | 可能包含 event titles/history context |
| `top_event_audit.json` | 已实现（implemented） | top event 来源/日期质量审计 | sanitized 后可作为 case-study candidate |
| `publish_result.json` | 已实现（implemented） | Feishu 发布/canonical URL 结果 | 私有；可能包含 Feishu URL |
| GitHub Summary / artifact bundle | 已实现（implemented） | 运行摘要和可下载产物 | 必须保持脱敏 |
| `RunManifest` | schema 已实现；runtime 计划中（schema implemented; runtime planned） | 统一运行追踪，包含步骤、门禁、工具调用和产物 | Phase B 后 schema exists；runtime artifact not generated yet |
| `ToolCall` trace | schema 已实现；runtime 计划中（schema implemented; runtime planned） | 脱敏的单工具调用 metadata | Phase B 后 schema exists；runtime trace not generated yet |

## 当前日志能力

状态：已实现 / 部分实现（implemented / partial）。

- Python logging 记录 runtime progress。
- verbose mode enabled 时，third-party HTTP libraries 仍保持 WARNING。
- 存在 `GITHUB_STEP_SUMMARY` 时，GitHub Step Summary 记录多个 run fields。
- 部分 result summary 和 bot error summary 已实现脱敏/截断。
- 尚无 single privacy gate 可以 block 所有 artifact sharing；人工复核 仍然 required。

## 当前缺口

- Current gap: no runtime-emitted `RunManifest`。
- Current gap: no `ToolCall` trace artifact。
- Current gap: no durable observability store outside GitHub artifacts/local outputs。
- Current gap: no formal cost/token ledger。
- Current gap: runtime generation of `RunManifest` is not implemented by Phase B。

## Week 2 P0 计划工作

状态：`RunManifest` 与 `ToolCall` 的 schema 已实现；运行时集成仍计划中（planned）。

Phase B 定义 schema 契约与运行时对象地图，覆盖：

- `RunManifest`
- `ToolCall`
- `EvidenceItem`
- `RecallAudit`
- `EvidenceGateAudit`
- `ReportLintResult`
- `Brief`
- `FeishuResult`
- `BotResult`
- `FinalTopDedupe`
- `FinalTopLLMAudit`
- `TopEventAudit`

Runtime generation 不在 Phase B task 中实现。

## RunManifest 建议结构

状态：schema 已实现；runtime 生成计划中（schema implemented; runtime generation planned）。

不要记录 real secrets、webhooks、tokens、private logs、full prompts、full evidence payloads 或 private artifact contents。

```json
{
  "run_id": "github-run-id-or-local-uuid",
  "agent": "ai-radar-agent",
  "status": "completed",
  "trigger": "workflow_dispatch",
  "input_summary": {
    "date": "YYYY-MM-DD",
    "dry_run": true,
    "skip_llm": false,
    "output_mode": "none",
    "production_ref": "main"
  },
  "steps": [
    {"name": "recall", "status": "implemented", "result": "ok"}
  ],
  "tool_calls": [
    {"tool": "rss", "status": "ok", "side_effect": false}
  ],
  "gates": [
    {"gate": "Evidence Gate", "status": "passed"}
  ],
  "artifacts": [
    {"type": "report_lint", "path": "outputs/YYYY-MM-DD/report_lint.json"}
  ],
  "human_approval": {
    "required_for_publish": true,
    "status": "external_trigger"
  }
}
```

## 故障排查阅读顺序

状态：作为文档/运行手册指引已实现；工具层部分实现（partial）。

1. GitHub Summary, if available。
2. `evidence.md` and provider audit。
3. `evidence_gate.json` and `evidence_dropped.md`。
4. `report_lint.json`。
5. `brief.json` and `brief.md`。
6. `final_top_dedupe.json`, `final_top_llm_audit.json`, `top_event_audit.json`。
7. `publish_result.json`, only if publish was allowed。
8. Bot result/Summary fields, only if bot send was allowed。

## 脱敏检查清单

分享或 commit 任何 artifact 前，确认不暴露：

- Secrets、`.env` values、tokens、cookies、webhook URLs、private keys、credentials。
- Private logs 或 full HTTP payloads。
- Feishu document URLs，除非 intentionally public-safe。
- Full prompts、full evidence payloads 或 private source dumps。
- Private business notes 或 unreviewed generated claims。
