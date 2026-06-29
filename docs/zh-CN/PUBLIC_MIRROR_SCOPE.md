# 公开镜像范围说明

本仓库是私有生产版 AI Radar Agent 的脱敏公开镜像，适合作品集展示、案例研究、
架构审阅和安全边界审阅。它不用于端到端复现私有生产环境。

相关入口：

- [可视化架构说明](ARCHITECTURE_OVERVIEW.md)
- [Agent 策略面板](STRATEGY_PANEL.md)

## 目的

这个公开镜像回答四个问题：

- AI Radar Agent 如何把公开 AI 信号转成有来源约束的情报？
- 证据门禁（Evidence Gate）和发布门禁（Publish Gate）如何降低误报、重复和外部副作用风险？
- 哪些 schema、评估用例和脱敏演示产物可以被公开审阅？
- 公开仓库和私有生产环境之间的边界在哪里？

## 包含内容

- 解释工作流、自治边界、工具权限、门禁、可观测性和运行手册的文档。
- 运行清单（RunManifest）和工具调用记录（ToolCall）的 schema 契约。
- 无外部副作用（external_side_effects）的评估用例和本地静态检查器。
- 脱敏、模拟的 demo artifacts，用于展示产物形态。
- 少量代表性 Python 代码片段，用于理解报告对齐和触发模式。
- 公开镜像安全的 Cloudflare Worker 触发模式文件。
- 用于公开镜像校验的手动 GitHub Actions 静态检查流程。

## 有意排除的内容

- `.env`、`.env.*`、`.dev.vars`、tokens、webhook 配置和 secrets。
- 生产 `state/event_history.jsonl`。
- 真实 Feishu 文档链接和发布历史。
- 生产输出、原始运行产物、私有日志、私有运行状态和内部运维笔记。
- 私有 prompts、消息源配置和 provider 配置。
- 私有 Cloudflare、GitHub、Feishu、provider 和账号级设置。
- 生产专用 Python 模块、provider 集成、Feishu 发布实现、完整回归测试、打包元数据和原始状态。

在私有生产仓库中，消息源配置和报告 prompts 会放在类似
`config/sources.yaml` 与 `prompts/radar_prompt.md` 的文件中。这些文件不属于公开镜像。

## 适合审阅的内容

- 证据门禁与发布门禁的设计。
- 自治边界与工具权限边界。
- 脱敏和不发布验证。
- 运行时 schema 的演进方向。
- 静态评估方法。
- 脱敏演示产物的结构。
- 代表性的报告对齐代码。
- Cloudflare / GitHub 触发模式，作为架构样例而不是线上配置。

## 可以本地运行的安全检查

```bash
python3 evals/check_ai_radar_week2_eval_cases.py
python3 -m json.tool demo_run/demo_manifest.json
python3 -m py_compile \
  ai_radar_agent/dates.py \
  ai_radar_agent/models.py \
  ai_radar_agent/report_reconcile.py \
  tests/test_report_reconcile.py \
  tests/test_cloudflare_trigger.py
```

这些检查不需要 secrets，不调用 provider，不触发 Feishu、webhook、Cloudflare 或 GitHub Actions 生产动作。

## 可运行性边界

本镜像主要用于架构和安全审阅。真实生产运行还需要私有 GitHub settings、
Cloudflare settings、Feishu app/bot credentials、provider keys、production
prompts/configuration 和 runtime state。这些内容均不在公开仓库中。

因此，本仓库可以帮助 reviewer 理解系统设计，但不应被当作可直接运行的生产系统。

## 公开安全姿态

- 已提交的 demo 是模拟且脱敏的。
- 已提交的 evals 是本地、不发布、无外部副作用的。
- 已提交的 Cloudflare 配置使用公开镜像安全默认值。
- 生产 secrets、原始输出、webhook 配置和生产 state 不包含在公开镜像中。
