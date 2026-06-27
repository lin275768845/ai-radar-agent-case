# 03 工作流中文镜像

英文权威版本见 [../03_WORKFLOW.md](../03_WORKFLOW.md)。

- 项目： AI Radar Agent
- 代理类型： 证据优先的情报与发布代理
- 状态： active
- 最后更新： 2026-06-19
- 事实来源： README、workflow docs、schemas、evals、demo artifacts，以及私有生产 runtime files
- 公开镜像说明：完整生产 runtime files 不包含在 curated public mirror 中。

## 工作流概览

AI Radar 是证据优先的情报与发布代理。它将公开 AI signals 转成 带来源约束的每日雷达报告，并且只在 explicit trigger 与 publish controls 允许时发布。

当前接近生产环境的执行流：

```text
workflow_dispatch / CLI
-> Beijing day window
-> RSS / Bocha / Tavily recall
-> Evidence Gate + history
-> report
-> report_lint
-> brief
-> final top dedupe / LLM audit / top event audit
-> Feishu publish or dry-run
-> bot card
-> artifacts / Summary
```

## 阶段地图

| 阶段 | 状态 | 输入 | 输出 | 产物 | 门禁 |
| --- | --- | --- | --- | --- | --- |
| Trigger: `workflow_dispatch` / CLI | 已实现（implemented） | GitHub workflow inputs 或 CLI args | parsed settings 和 requested date | GitHub run metadata when available | Input/date gate |
| Beijing day window | 已实现（implemented） | target date 或 blank date | Asia/Shanghai natural day 的 `TimeWindow` | Summary fields；date-specific output path | Time window gate |
| RSS recall | 私有 runtime 已实现（implemented） | private source configuration，target window | RSS evidence items 和 RSS audit | `evidence.json`, `evidence.md` | Provider degradation gate；Evidence Gate |
| Bocha recall | 已实现（implemented） | query baskets，target window，configured key | search evidence items 和 provider audit | `evidence.json`, `evidence.md` | Tool permission gate；provider degradation gate |
| Tavily recall | 已实现（implemented） | query baskets，target window，enabled flag，configured key | optional search evidence items 和 provider audit | `evidence.json`, `evidence.md` | Cost gate；provider degradation gate |
| Evidence dedupe and cap | 已实现（implemented） | raw evidence list | unique capped evidence list | `evidence.json` | Dedupe gate |
| Evidence Gate + history | 已实现（implemented） | raw evidence，source quality config，event history | filtered/marked evidence 和 dropped evidence audit | `evidence_gate.json`, `evidence_dropped.md`, `event_history_matches.json`, `event_history_context.md` | Evidence Gate；history gate；privacy gate |
| Report generation | 私有 runtime 已实现（implemented） | private prompt，target window，filtered evidence context | Markdown radar report | `AI_radar_<date>.md` | Prompt source gate；source URL guardrail |
| Report source appendix | 已实现（implemented） | Report Markdown 和 evidence | 必要时带 fallback source appendix 的 report | `AI_radar_<date>.md` | Source URL guardrail |
| `report_lint` | 已实现（implemented） | Report Markdown 和 evidence | lint warnings/errors/critical errors | `report_lint.json` | report_lint gate |
| Brief generation and repair | 已实现（implemented） | report，audit，evidence catalog | normalized brief data 和 brief Markdown | `brief.json`, `brief.md` | Brief schema/source_ids normalization gate |
| Final top dedupe | 已实现（implemented） | `brief.json`，recent history，evidence | 移除或标记 repeated events 的 final top list | `final_top_dedupe.json` | history / dedupe gate |
| Final top LLM audit | 已实现（implemented） | final top candidates 和 history context | enabled 时的 LLM duplicate-review decisions | `final_top_llm_audit.json` | final_top_llm_audit gate |
| Top event audit | 已实现（implemented） | final `brief.json`，evidence，history | top events 的 source/date/quality audit | `top_event_audit.json` | top_event_audit gate |
| Feishu publish or dry-run | 已实现（implemented） | report file，settings，publish flags | Feishu docx/MD result 或 skipped dry-run result | `publish_result.json` | Publish Gate；privacy/redaction gate |
| Bot card send | 已实现（implemented） | `brief.json`，doc URL，bot settings | Feishu bot result 或 skipped result | Summary fields；bot result metadata | Bot Gate；Publish Gate |
| Artifacts / GitHub Summary | 已实现（implemented） | all run outputs and audit results | local artifacts 和 GitHub Step Summary | `outputs/<date>/...`, GitHub artifact bundle | Observability gate；privacy/redaction gate |
| Formal RunManifest | 计划中（planned） | sanitized run steps，gates，tool calls，artifact refs | `RunManifest` object | planned `run_manifest.json` | Future run manifest gate |
| ToolCall trace artifact | 计划中（planned） | sanitized tool-call metadata | `ToolCall` records | planned tool-call trace 或 manifest section | Future ToolCall trace gate |

## 状态流转

当前运行状态隐含在产物中，还不是正式状态机。

```text
triggered
-> settings_loaded
-> window_ready
-> evidence_recalled
-> evidence_gated
-> report_generated
-> report_linted
-> brief_ready
-> final_top_audited
-> publish_skipped_or_completed
-> summary_written
```

状态： 部分实现（partial）。状态流转可以从代码路径和产物中看到，但尚无正式 `RunManifest` 记录每一步流转。

## 当前产物

已实现（implemented）的 artifacts 包括：

- `outputs/<date>/evidence.json`
- `outputs/<date>/evidence.md`
- `outputs/<date>/evidence_gate.json`
- `outputs/<date>/evidence_dropped.md`
- `outputs/<date>/AI_radar_<date>.md`
- `outputs/<date>/report_lint.json`
- `outputs/<date>/brief.json`
- `outputs/<date>/brief.md`
- `outputs/<date>/final_top_dedupe.json`
- `outputs/<date>/final_top_llm_audit.json`
- `outputs/<date>/top_event_audit.json`
- `outputs/<date>/publish_result.json`
- GitHub Actions 中运行时的 GitHub Summary / artifact bundle

## 安全运行模式

| 模式 | 状态 | 是否有外部副作用 | 用途 |
| --- | --- | ---:| --- |
| `--skip-llm` | 已实现（implemented） | No | evidence-only recall debugging |
| `--dry-run` | 已实现（implemented） | No Feishu publish or bot send | local artifact generation without publishing |
| `output_mode=none` | 已实现（implemented） | No Feishu publish | GitHub/local validation that should not publish |
| Static eval/check mode | 计划中（planned） | No | future JSONL/static eval validation without Feishu or workflow dispatch |

## 人工复核点

状态： 部分实现（partial）。

Human approval 当前是 operational 的，而不是 formal artifact：

- 选择生产 GitHub ref。
- 触发生产 workflow。
- 启用 Feishu publish 或 bot send。
- 修改 prompts、schemas、workflow behavior、provider configuration 或 publish behavior。
- 清理或删除任何 remote artifact。

## 当前缺口

- 无 formal `RunManifest`。
- 无 `ToolCall` trace artifact。
- approval 隐含在 trigger/ref choice 中，而不是记录到 run artifact。
- cross-run publish idempotency 是 部分实现（partial）。
- 正式的评估/静态检查模式已经计划中（planned），但不是 Phase A task 的已实现内容。

## P2 未来工作：只读产物工作台

状态：计划中（planned）。

未来只读 Artifact Workbench 可以查看脱敏产物和摘要。它不得触发 Feishu、GitHub workflow dispatch、provider 调用或生产写入。
