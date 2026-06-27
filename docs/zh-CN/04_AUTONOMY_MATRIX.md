# 04 自治矩阵中文镜像

英文权威版本见 [../04_AUTONOMY_MATRIX.md](../04_AUTONOMY_MATRIX.md)。

- 项目： AI Radar Agent
- 代理类型： 证据优先的情报与发布代理
- 状态： active
- 事实来源： repository code, `README.md`, `AGENTS.md`, `.github/workflows/daily.yml`

## 自治原则

AI Radar 可以在明确触发后自动执行公开信号召回、证据过滤、草稿生成、lint、本地产物写入，以及配置允许的发布。它不得自主改变 production configuration、secrets、code、prompts、schemas、GitHub refs 或 user-confirmed operational state。

Publish、bot send、workflow dispatch、Feishu 文档创建和远端清理都属于外部副作用（external_side_effects）。它们需要 人工确认，或显式 no-publish controls，例如 `dry_run`、`skip_llm`、`output_mode=none`、`send_bot=false`。

## 动作矩阵

| 动作 | 状态 | 是否自动执行 | 是否只生成草稿 | 是否需要人工确认 | 禁止自动化 | 是否有外部副作用 | 风险 | 门禁 |
| --- | --- | ---:| ---:| ---:| ---:| ---:| --- | --- |
| Read public RSS/search sources | 已实现（implemented） | Yes | No | No | No | No | stale 或 low-quality public evidence | Time window gate；Evidence Gate |
| Recall via RSS / Bocha / Tavily | 已实现（implemented） | configured 时 yes | No | provider key/config 属于 由人负责 | No | provider API read only | quota、outage、bad source mix | Tool permission gate；provider degradation gate |
| Draft report generation | 已实现（implemented） | not `skip_llm` 时 yes | Yes | prompt/provider changes need approval | No | No external write | hallucination、stale event framing | Evidence Gate；source URL guardrail |
| Local artifact write | 已实现（implemented） | Yes | No | normal run artifacts 不需要 | No | local filesystem only | private artifact leakage if committed/shared | Privacy gate |
| Lint and audit | 已实现（implemented） | Yes | No | No | No | No | false pass 或 overly broad warnings | report_lint gate；top_event_audit gate |
| Dry-run | 已实现（implemented） | requested 时 yes | No | No | No | No | 被误当 production 时会造成 false confidence | Publish Gate should stay blocked |
| `skip_llm` evidence-only run | 已实现（implemented） | requested 时 yes | No | No | No | No | 只验证 evidence quality，不验证 report | Evidence Gate |
| Feishu docx/Drive publish | 已实现（implemented） | explicit trigger 且未禁用后 yes | No | Yes | No autonomous publish | Yes | wrong ref/date/folder, duplicate publish | Publish Gate；approval gate |
| Feishu bot card send | 已实现（implemented） | configured 且未 blocked 时 yes | No | Yes | No autonomous new channel | Yes | wrong audience/noisy card | Bot Gate；Publish Gate |
| GitHub workflow dispatch | 运行时外已实现（implemented outside runtime） | external caller triggers | No | Yes | No autonomous dispatch from docs/Codex tasks | Yes | wrong ref, production side effect | Approval Gate |
| Config / secret handling | 部分实现（partial） | runtime reads configured env names | No | humans own secret creation/rotation | Codex must not read/output values | Potentially | secret exposure | Privacy gate |
| Delete / cleanup | 部分实现（partial） | temp Feishu source cleanup only | No | required for any new cleanup | No user-data cleanup automation | Yes | deleting wrong remote file | Rollback/destructive-action gate |
| Production ref change | 计划中/人工（planned/manual） | No | No | Yes | 未经明确任务不得自动化 | Yes | 生产分支漂移 | Approval Gate |
| Static eval checker | 计划中（planned） | implemented 后 yes | No | No | No | No | incomplete coverage | Eval gate |
| Read-only Artifact Workbench | 计划中（planned，P2） | 只读 | No | 脱敏演示产物不需要 | 不写入、不发布 | No | 意外暴露私有产物 | Privacy gate |

## 必要控制

- Secrets、`.env` values、webhooks、tokens、cookies、private logs、private run outputs 不得被读取、打印、总结、提交或导出。
- `outputs/` 可能包含 private run artifacts 和 Feishu URLs；除非 artifacts 已 explicitly sanitized，否则视为 private local storage。
- documentation、eval、inspection tasks 中 Feishu publish 和 bot send 必须保持 disabled。
- 新 publish/delete behavior 需要先 dry-run validation，并获得 explicit 人工确认。

## 状态说明

- 已实现（implemented）：当前 运行时行为 已存在于 code/tests/docs。
- 部分实现（partial）：behavior 存在，但缺少 formal approval artifact、manifest 或 durable trace。
- 计划中（planned）：仅为 documented target；不是 Phase A docs task 已实现内容。

## 当前缺口

- normal Feishu publish 前无 formal approval artifact。
- 无 formal `RunManifest` 展示 approval/ref/date/publish decisions。
- 无 `ToolCall` trace artifact 记录 external/local tool usage。
- Cross-run idempotency 仍是 部分实现（partial）。

## P2 未来工作：只读产物工作台

状态：计划中（planned）。

如果后续构建，它只能查看脱敏产物，绝不能触发 provider 调用、Feishu publish、bot send、GitHub workflow dispatch、删除或清理动作。
