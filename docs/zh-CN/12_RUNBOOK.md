# 12 运行手册中文镜像

英文权威版本见 [../12_RUNBOOK.md](../12_RUNBOOK.md)。

- 项目： AI Radar Agent
- 代理类型： 证据优先的情报与发布代理
- 状态： active

## 运行原则

优先选择能回答问题的最安全模式：

1. Static/read-only inspection。
2. Eval-only/static check mode when implemented。
3. `--skip-llm` for recall only。
4. `--dry-run --output-mode none` for local no-publish validation。
5. `--dry-run` for report/brief artifacts without Feishu publish or bot send。
6. Production publish only after explicit 人工确认。

documentation、planning、inspection tasks 中不得触发 Feishu、GitHub workflow dispatch、provider writes、bot send 或 production publish。

## 本地设置

状态：已实现（implemented）。

```bash
pip install -e .
```

documentation tasks 中不要创建或检查真实 `.env` values。只使用 variable names。

## 本地 dry-run

状态：已实现（implemented）。

生成 local artifacts，但不 Feishu publish 或 bot send：

```bash
python -m ai_radar_agent --date 2026-06-01 --dry-run
```

更安全的 no-publish variant：

```bash
python -m ai_radar_agent --date 2026-06-01 --dry-run --output-mode none
```

## `skip_llm`

状态：已实现（implemented）。

Evidence-only recall debugging：

```bash
python -m ai_radar_agent --date 2026-06-01 --skip-llm
```

Expected behavior：

- collects and writes evidence artifacts。
- does not generate report/brief。
- does not publish to Feishu。
- does not send bot card。

## `output_mode=none` / No Publish

状态：已实现（implemented）。

GitHub 或 local run 需要避免 Feishu document creation 时使用：

```bash
python -m ai_radar_agent --date 2026-06-01 --dry-run --output-mode none
```

Expected behavior：

- Feishu docx/Drive publish is skipped。
- Bot send should be skipped or blocked by run flags/policy。
- Local artifacts may still be produced。

## 仅评估 / 静态检查模式

状态：计划中（planned）。

Future eval/static check mode should：

- validate `evals/*.jsonl` shape。
- validate Phase B schemas and future emitted manifests。
- confirm `no_external_side_effects`。
- avoid Feishu、GitHub workflow dispatch、LLM/provider calls、bot sends、production writes。

Phase C 已实现静态检查器。Phase B 只定义 schema 契约与运行时对象地图。

## 无 Feishu / 无 workflow dispatch 安全模式

状态：控制项已实现，正式模式部分实现（implemented through controls, partial as a formal mode）。

安全控制：

- `--dry-run`
- `--skip-llm`
- `--output-mode none`
- `SEND_BOT=false`
- `REPORT_LINT_POLICY=off` 或 `block_bot`，仅在理解行为后使用

除非用户在当前任务中明确要求这种外部副作用（external_side_effects），否则 Codex 不得调用 GitHub workflow dispatch、Feishu API 或 bot webhook。

## 生产运行

状态：操作层已实现（implemented operationally）。

Production 由 Feishu automation 调用 GitHub Actions `workflow_dispatch` for `.github/workflows/daily.yml` 触发。当前 recommended production ref 是 `main`；`single_card_v7.1` 与 `week2/standardization` 作为 branch rollback points 保留。

Production publish 需要通过 ref/input selection 体现 人工确认。不要把 documentation 或 local validation tasks 当作 publish approval。

## 常见失败

| 现象 | 状态 | 可能原因 | 安全检查 | 恢复方式 |
| --- | --- | --- | --- | --- |
| 缺少 provider secret | 已实现（implemented） | secret 未配置 | 只检查变量名或配置是否存在；不要读取值 | 在 Codex 输出之外配置 secret 后重跑 |
| 缺少证据 | 已实现（implemented） | provider 为空、禁用、失败，或没有匹配事件 | 查看 `evidence.md` 和 `evidence_gate.json` 中的 provider audit | 启用来源、重跑召回，或复核日期 |
| Provider fallback/degradation | 已实现（implemented） | RSS/search 超时、鉴权、限流或服务问题 | 查看 provider audit 和 Summary | 证据足够时继续；否则修复配置或 provider |
| Lint 失败 | 已实现（implemented） | 报告结构、来源或 placeholder 问题 | 查看 `report_lint.json` | 仅在已批准变更中调整 prompt/report 行为 |
| Source URL 不匹配 | 已实现（implemented） | 报告 URL 不在 evidence 中 | 查看 `report_lint.json` 的 unmatched URL 详情 | 重跑或修复来源绑定 / prompt 行为 |
| `source_id` 不匹配 | 已实现（implemented） | brief LLM 返回的 ID 不在 evidence catalog 中 | 查看 `brief.json`/Summary 中的 `brief_source_ids_unresolved_count` | 宁可保持 `sources=[]`，也不要编造 URL |
| Brief 解析/修复失败 | 已实现（implemented） | JSON 无效、截断或 normalization 问题 | 查看 `brief_generation_status`、parse stage、repair fields | 使用确定性 fallback；检查完整报告 |
| Final top 重复 | 已实现（implemented） | 与近期历史重复 | 查看 `final_top_dedupe.json` 和 `final_top_llm_audit.json` | 确认是否有新信号，或允许 dedupe |
| Feishu docx fallback | 已实现（implemented） | import 权限、超时或 API 问题 | 查看 Summary 和 `publish_result.json` | publish 被允许时，Markdown fallback 是预期行为 |
| Bot skipped | 已实现（implemented） | `dry_run`, `skip_llm`, `output_mode=none`, 缺少 webhook, send false, lint policy | 查看 Summary 的 bot 字段 | no-publish 模式中保持 skipped |
| 重复发布 | 部分实现（partial） | cross-run state 不持久 | 查看 `publish_result.json`，必要时人工检查 Feishu 文件夹 | 保持 `force_republish=false`；只做人工清理 |

## Provider 降级与 fallback

状态：已实现 / 部分实现（implemented / partial）。

- RSS provider failures 应 warn and continue where possible。
- Bocha/Tavily failures 会被 audited；auth/bad-request issues 可停止该 provider。
- 只有 required stages 无 evidence 时 overall run 才 block。
- Provider degradation 应在 evidence/provider audit artifacts 中可见。

## Lint 失败处理流程

状态：已实现（implemented）。

1. Inspect `report_lint.json`。
2. 区分 warnings、errors、critical errors。
3. Confirm current `REPORT_LINT_POLICY`。
4. prompt/report change 未经 dry-run validation 和 人工确认 不得 publish。

## 缺少证据处理流程

状态：已实现（implemented）。

1. Check `evidence.md` provider audit。
2. Check `evidence_gate.json` raw/filtered/dropped counts。
3. Check `evidence_dropped.md` reasons。
4. Rerun with `--skip-llm` for recall-only validation。
5. evidence missing 时不得 publish。

## Source ID 不匹配处理流程

状态：已实现（implemented）。

1. Check `brief.json` source ID counters and unresolved samples。
2. Confirm unresolved IDs did not become fabricated URLs。
3. Prefer empty `sources=[]` over incorrect 来源绑定。
4. changing 来源绑定 logic 前添加 future eval cases。

## 紧急停止

状态：操作层已实现（implemented operationally）。

- disable Feishu automation trigger，或改成 safe ref/input。
- use `dry_run=true`, `output_mode=none`, `skip_llm=true`, or `send_bot=false`。
- 如需停止 message sending，在 Codex output 外 disable/rotate bot webhook。
- 不自动删除 Feishu documents。
- emergency review 中不要从 Codex 触发 GitHub workflow dispatch，除非 explicit approval。

## 脱敏检查清单

分享、commit 或用于 case study 前，确认：

- 无 `.env` values、secrets、tokens、webhook URLs、cookies、private keys、credentials。
- 无 private logs 或 raw HTTP payloads。
- 无 unreviewed Feishu document URLs。
- 无 full prompts、full evidence payloads、private run outputs。
- 无 private business notes 或 raw private source dumps。

## 当前缺口

- 无 runtime-emitted `RunManifest`。
- 无 `ToolCall` trace artifact。
- Phase C 后已有本地静态检查器，但运行时评估集成仍计划中（planned）。
- 无 cross-run publish dedupe。
- production publish 前无 formal approval artifact。
