# 公开镜像范围说明

本仓库是私有生产版 AI Radar Agent 的脱敏公开镜像。

它用于作品集展示和案例研究审阅，不用于端到端复现私有生产部署。

可视化 workflow 与 boundary diagrams 见
[docs/zh-CN/ARCHITECTURE_OVERVIEW.md](ARCHITECTURE_OVERVIEW.md)。

高层运行原则见
[docs/zh-CN/STRATEGY_PANEL.md](STRATEGY_PANEL.md)。

## 目的

- 审阅 evidence-first intelligence agent 的架构。
- 审阅 workflow design、autonomy boundaries、gates、schemas、evals、
  selected code slices 和 sanitized demo artifacts。
- 展示 Cloudflare + GitHub Actions 的触发模式，同时不暴露真实部署状态。
- 让 public safety posture 可审阅，同时不发布 private runtime data。

## 包含内容

- 用于理解代表性 runtime design choices 的 selected Python code slices。
- Architecture、workflow、gate、runbook、observability 和 case-study
  documentation。
- `RunManifest` 与 `ToolCall` schema contracts。
- No-side-effect eval definitions 和 static checker。
- Sanitized simulated demo artifacts。
- Mirror-safe Cloudflare Worker pattern files。
- 用于 public mirror validation 的 manual static-check workflow。

## 有意排除

- `.env`、`.env.*`、`.dev.vars`、tokens、webhook configs 和 secrets。
- 生产 `state/event_history.jsonl`。
- 真实 Feishu 文档 URL 与发布历史。
- 生产 outputs、raw run artifacts、private logs、private runtime state 和
  private operational notes。
- 私有 production prompts 和 source configuration。
- 私有 Cloudflare、GitHub、Feishu、provider 和 account settings。
- Production-only Python modules、provider integrations、Feishu publishing
  implementation、完整 regression tests、packaging metadata 和 raw state。

在私有生产仓库中，source configuration 和 report prompts 会放在类似
`config/sources.yaml` 与 `prompts/radar_prompt.md` 的文件中。
这些文件被有意排除在公开镜像之外。

## 可以审阅什么

- Evidence Gate 与 Publish Gate 设计。
- Autonomy 和 tool-permission boundaries。
- Redaction 与 no-side-effect posture。
- Runtime schema direction。
- Static eval methodology。
- Sanitized demo artifact shape。
- 代表性的 report reconciliation code。
- Cloudflare/GitHub trigger pattern 作为架构模式，而不是 live deployment。

## 本地可运行检查

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

## 可运行性边界

这个镜像主要用于 architecture 和 safety review。

真实生产部署需要私有 GitHub settings、Cloudflare settings、Feishu app/bot
credentials、provider keys、production prompts/configuration 和 runtime state。
这些内容都不在公开仓库中。

## 公开安全姿态

- Checked-in demo 是 simulated 和 sanitized。
- Checked-in evals 是 local 和 no-side-effect。
- Checked-in Cloudflare config 默认 mirror-safe。
- Production secrets、raw outputs、webhook configs 和 state 不包含在公开镜像中。
