# 10 评估计划中文镜像

英文权威版本见 [../10_EVAL_PLAN.md](../10_EVAL_PLAN.md)。

- 项目： AI Radar Agent
- 代理类型： 证据优先的情报与发布代理
- 状态： active
- 事实来源： tests, `evals/`, runtime artifacts, report lint, brief normalization, Evidence Gate

## 评估理念

AI Radar 应基于 source fidelity、time-window correctness、duplicate suppression、stale-rate control、report structure、brief/card reliability、publish safety 和 observability 进行评估。

当前状态：部分实现（partial）。pytest suite 已经较完善；Phase C 增加了 Week 2 JSONL 评估定义文件和最小本地静态检查器。这些评估的运行时集成仍计划中（planned）。

## 当前覆盖范围

已实现（implemented）的测试覆盖：

- Beijing date windows。
- RSS / Bocha / Tavily provider behavior。
- Provider degradation and query budgets。
- Evidence Gate、source quality、event history、final-top dedupe、top-event audit behavior。
- Report source appendix and `report_lint`。
- Brief JSON parsing、repair、来源绑定、count matching、card field quality。
- Feishu docx fallback and bot card behavior。
- Log redaction and GitHub workflow configuration。

Phase C 已实现：

- `evals/ai_radar_week2_eval_cases.jsonl`，包含 10 个无外部副作用评估用例定义。
- `evals/check_ai_radar_week2_eval_cases.py`，使用 standard library 的 静态检查器，校验 Week 2 case file 与 Phase B schemas。

计划中（planned）：

- stale rate、duplicate rate、hallucinated citation rate、source validity 的 metric report。

## 评估用例目录

| ID | 类型 | 状态 | 用例 | 预期行为 | 检查项 | no_external_side_effects |
| --- | --- | --- | --- | --- | --- | ---:|
| `regression_old_news_repeat` | regression | 计划中（planned） | 旧新闻重复：same event appears in recent history and today's recall without strong new signal | evidence 或 final top 被 marked/dropped as old repeated；report/card 不应把它提升为今日 core event | `evidence_gate.json`, `event_history_matches.json`, `final_top_dedupe.json`, no repeated top title | Yes |
| `failure_out_of_window_news` | failure | 计划中（planned） | 窗口外新闻：evidence date is outside Beijing natural-day window | item 被 dropped 或 marked out-of-window；不进入 core top event | Evidence Gate drop reason；top_event_audit out-of-window count | Yes |
| `failure_low_quality_aggregator` | failure | 计划中（planned） | 低质量聚合源：aggregator/reprint source with weak fit | source 被 dropped、demoted 或 not core-eligible | `source_tier`, `source_fit`, `dropped_low_source_fit_count` | Yes |
| `edge_missing_official_source` | edge | 计划中（planned） | 官方来源缺失：only second/third-party source exists | event 可保留但带 warning/uncertainty；不得 fake official source | top_event_audit warnings；no invented URL | Yes |
| `failure_llm_old_event_today` | failure | 计划中（planned） | LLM 把旧事件写成今日事件 | report_lint/top_event_audit/history flags 捕捉 stale framing；final top dedupe 适用时移除 | stale warning, old_repeated count, no publish in eval | Yes |
| `failure_report_url_not_in_evidence` | failure | 计划中（planned） | report 正文 URL 不在 evidence | `report_lint` 根据 policy 报 unmatched URL 或 critical error | `report_lint.json` unmatched URL fields | Yes |
| `failure_brief_source_ids_unresolved` | failure | 计划中（planned） | brief `source_ids` 无法解析 | brief 可保留 item，但 unresolved IDs 不得变成 fabricated source URLs | `brief_source_ids_unresolved_count`, `sources=[]` where needed | Yes |
| `regression_final_top_duplicate` | regression | 计划中（planned） | final top 重复 | duplicate top event 被 dropped unless strong new signal exists | `final_top_dedupe_dropped_count`, final list uniqueness | Yes |
| `edge_feishu_card_too_long` | edge | 计划中（planned） | 飞书卡片过长 | card safe truncate/split，保留 meaning，避免 bad fragments | bot render metadata, card text quality counters | Yes |
| `golden_provider_fallback_dry_run_no_publish` | golden | 计划中（planned） | provider 失败 fallback / dry-run no publish | provider failure 被 audited；remaining evidence 可继续；`dry_run` 或 `output_mode=none` 阻止 Feishu 与 bot side effects | provider audit, publish skipped reason, bot skipped reason | Yes |

## 评估记录格式要求

状态：`evals/ai_radar_week2_eval_cases.jsonl` 已实现（implemented）；更广泛的 eval record migration 仍计划中（planned）。

future JSONL case 应包括：

- `id`
- `type`: `golden`, `failure`, `edge`, or `regression`
- `status`: `planned`, `implemented`, or `disabled`
- `input_ref` or synthetic inline input
- `expected_behavior`
- `checks`
- `no_external_side_effects: true`
- `privacy_notes`

## 验收阈值

状态：计划中（planned）。

初始 non-publishing eval/static check thresholds：

- sampled eval outputs 中 0 fabricated source URLs。
- target window 外 core events 为 0，除非明确标记并说明。
- repeated final top events 为 0，除非 strong new signal。
- 外部发布、bot send、workflow dispatch、provider write side effects 为 0。
- eval fixtures 不包含 secrets、webhooks、tokens、private logs 或 raw private artifacts。

## 评估执行策略

- Eval/static check mode 不得 call Feishu。
- Eval/static check mode 不得 trigger GitHub workflow dispatch。
- Eval/static check mode 不得 call production providers，除非 explicit approval。
- 优先使用 synthetic 或 sanitized fixtures。
- 不要读取 private `outputs/` artifacts，除非用户 explicitly approves a redaction task。

## 当前缺口

- 现有 scaffold 文件留作后续扩展；`evals/ai_radar_week2_eval_cases.jsonl` 在 Week 2 已实现（implemented）。
- Week 2 eval case file 和 Phase B schema JSON 已有 minimal 静态检查器。
- `RunManifest` 与 `ToolCall` schema contracts 在 Phase B 后存在，但尚未验证 runtime-emitted manifest。
- top-event quality 的人工标注 rubric 仍计划中（planned）。

## Phase C 已交付内容

- 添加 10 个 Week 2 JSONL cases，覆盖 evidence gate、publish gate、tool permission、safety mode、schema contract、observability、redaction、failure handling、eval static check、emergency stop。
- 添加 minimal local checker，校验 JSONL shape、required fields、case ids、category coverage、forbidden external actions、`no_external_side_effects`、related docs/schemas 和 Phase B schema JSON。
- checker 是 仅本地 和 no-publish；它不 import production code，不 call external APIs，不 invoke LLMs，不 trigger Feishu/GitHub/webhooks，不 run 生产流水线。
