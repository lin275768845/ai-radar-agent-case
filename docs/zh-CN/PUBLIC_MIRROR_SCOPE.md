# 公开镜像范围说明

本仓库是私有生产版 AI Radar Agent 的脱敏公开镜像。它用于作品集展示和案例研究审阅，不用于端到端复现私有生产部署。

## 目的

- 审阅 evidence-first intelligence agent 的架构。
- 审阅工作流设计、自治边界、门禁、schema、eval 和脱敏 demo artifacts。
- 展示 Cloudflare + GitHub Actions 的触发模式，同时不暴露真实部署状态。

## 包含内容

- 用于理解运行时设计的核心 Python package 模块。
- 架构、工作流、门禁、runbook、observability 和 case study 文档。
- `RunManifest` 与 `ToolCall` schema 契约。
- 无外部副作用的 eval definitions 和静态 checker。
- 脱敏的模拟 demo artifacts。
- mirror-safe 的 Cloudflare Worker pattern 文件。

## 有意排除

- `.env`, `.env.*`, `.dev.vars`, tokens, webhook configs 和 secrets。
- 生产 `state/event_history.jsonl`。
- 真实 Feishu 文档 URL 与发布历史。
- 生产 outputs、raw run artifacts、private logs、private runtime state 和 private operational notes。
- 端到端生产执行所需的私有 prompts/configuration。

## 本地可运行检查

```bash
python3 evals/check_ai_radar_week2_eval_cases.py
python3 -m json.tool demo_run/demo_manifest.json
python3 -m py_compile ai_radar_agent/report_reconcile.py tests/test_report_reconcile.py
```

## 可运行性边界

这个镜像主要用于架构与安全审阅。真实生产部署需要私有 GitHub settings、Cloudflare settings、Feishu app/bot credentials、provider keys、production prompts/configuration 和 runtime state，这些内容都不在公开仓库中。
