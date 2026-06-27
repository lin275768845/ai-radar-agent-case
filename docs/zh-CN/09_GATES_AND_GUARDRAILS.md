# 09 门禁与护栏中文镜像

英文权威版本见 [../09_GATES_AND_GUARDRAILS.md](../09_GATES_AND_GUARDRAILS.md)。

- 项目： AI Radar Agent
- 代理类型： 证据优先的情报与发布代理
- 状态： active
- 事实来源： repository code, `prompts/radar_prompt.md`, tests, current artifacts

## 护栏理念

AI Radar 依赖分层门禁：召回前检查日期和输入；报告生成前执行 Evidence Gate 和来源质量检查；LLM 输出后执行 report lint 与 brief normalization；card/history 前执行 final top dedupe/audits；外部副作用（external_side_effects）前执行 publish 和 privacy gates。

## 门禁清单

| 门禁 | 状态 | 触发时机 | 通过条件 | 失败处理 | 是否阻断 | 证据 / 代码 |
| --- | --- | --- | --- | --- | ---:| --- |
| Input/date gate | 已实现（implemented） | CLI/settings 加载 | 参数可解析；日期有效或为空 | raise 或停止 | Yes | `__main__.py`, `dates.py`, tests |
| Time window gate | 已实现（implemented） | 创建日期窗口并过滤 provider | 精确的北京时间自然日窗口 | 无效日期会 raise；provider 日期缺口尽力审计 | 日期阻断，provider metadata 部分阻断 | `dates.py`, fetchers |
| Evidence Gate | 已实现（implemented） | 召回之后 | evidence 存在，且低质量/过期/重复项被过滤或标记 | 无 evidence 时阻断；被丢弃证据会记录 | 无 evidence 时阻断 | `evidence_gate.py`, `evidence_gate.json`, `evidence_dropped.md` |
| Source quality gate | 已实现（implemented） | Evidence Gate 和 top event audit | 应用 source tier/fit；低质量来源被过滤或警告 | drop、demote 或 warn | 部分阻断 | `source_quality.py`, `evidence_gate.py`, `top_event_audit.py` |
| Provider degradation / fallback gate | 已实现（implemented） | 召回期间 | provider 成功，或失败被记录且不隐藏 outage | warn/continue，除非没有证据剩余 | 除非所有证据失败，否则不阻断 | `collector.py`, `fetchers/*`, provider audit |
| Source URL guardrail | 已实现（implemented） | report 和 brief 生成期间 | URL 必须来自 evidence 或允许的 report/Feishu URL | `report_lint` 报错；brief 丢弃不安全来源 | 取决于 policy | `report.py`, `report_lint.py`, `brief.py` |
| History / dedupe gate | 已实现（implemented） | Evidence Gate and final top processing | recent repeated events marked/dropped unless strong new signal exists | drop, mark, or allow with audit | Partial | `event_history.py`, `event_history_matches.json`, `final_top_dedupe.json` |
| report_lint gate | 已实现（implemented） | after report generation | required sections, source URLs, no placeholders, size/shape checks | warn, block bot, or strict raise based on policy | policy-dependent | `report_lint.py`, `report_lint.json` |
| Brief source_ids normalization gate | 已实现（implemented） | brief generation/repair | LLM source IDs resolve to evidence records；unsafe/unresolved sources 不变成 fabricated URLs | repair, salvage, fallback, warn | Partial | `brief.py`, `brief.json`, tests |
| final_top_dedupe gate | 已实现（implemented） | after brief | repeated final top events removed unless strong new signal exists | drop repeated top and related bullets | Partial | `event_history.py`, `final_top_dedupe.json` |
| final_top_llm_audit gate | 已实现（implemented） | deterministic final top dedupe 后且 enabled 时 | high-confidence duplicate decisions only | audit failure does not block publish by default | Non-blocking | `final_top_auditor.py`, `final_top_llm_audit.json` |
| top_event_audit gate | 已实现（implemented） | after final brief top events | top events have acceptable source/date quality or warnings | warn and record counts | Non-blocking | `top_event_audit.py`, `top_event_audit.json` |
| Publish Gate | 已实现（implemented） | before Feishu docx/Drive publish | not `dry_run`, not `output_mode=none`, publish config available, policy permits | skip, fallback, or record failure | Yes/partial depending mode | `__main__.py`, `feishu_docx.py`, `publish_result.json` |
| Bot Gate | 已实现（implemented） | before Feishu bot webhook | send flag, webhook, lint policy, doc link/card payload acceptable | skip or record bot failure | usually non-blocking | `feishu_bot.py`, Summary fields |
| Privacy / redaction gate | 部分实现（partial） | logs, Summary, artifacts, completion reports | no secrets, webhook values, full payloads, private logs, raw private artifacts exposed | redact/truncate/stop manually | Partial | `test_logging.py`, `feishu_result.py`, `feishu_bot.py` |
| Approval gate | 部分实现（partial） | production trigger/ref/publish decision | human selected ref/inputs externally | no formal approval artifact | Partial | GitHub/Feishu ops, runbook |
| Future RunManifest gate | 计划中（planned） | run 结束 / release acceptance 前 | 脱敏 run manifest 记录步骤、门禁、ToolCall 记录、产物和批准状态 | 缺失时阻断标准化验收 | 计划中 | Phase B schema 契约；runtime gate 计划中 |
| Future eval gate | 计划中（planned） | prompt/schema/gate 变更前 | JSONL eval/static check 在无外部副作用（external_side_effects）下通过 | 保持为草稿 | 计划中 | future eval checker |

## 阻断规则

- Date/input failures block。
- No evidence blocks。
- Strict `report_lint` can block when configured。
- Publish 被 `dry_run`、`skip_llm`、`output_mode=none`、missing required config 或 publish policy block。
- Bot send 被 `dry_run`、`skip_llm`、missing webhook、send flag、output mode 或 lint policy block。

## 不阻断但会记录

- 单个 provider degradation，但其他 evidence 仍可用。
- Feishu docx import fallback to Drive Markdown。
- report publish 之后的 bot webhook failure。
- final_top_llm_audit failure，除非未来 policy 变更。
- top_event_audit warnings。

## 当前缺口

- 无 runtime `RunManifest` gate。
- 无 `ToolCall` trace artifact。
- publish 前无 formal approval record。
- 对 stale rate、duplicate rate、hallucinated citation rate、source validity 尚无 formal eval thresholds。
- Privacy gate 仍部分依赖 convention/tests，而不是单一 blocking runtime policy。

## 计划工作

- `RunManifest` 与 `ToolCall` schema 契约已在 Phase B 定义；运行时产出和 gate integration 仍计划中（planned）。
- Phase C 已添加 10 个评估用例与无外部副作用静态检查器。
- Publish、workflow dispatch、Feishu、bot actions 保持在 documentation/eval/demo work 之外。
