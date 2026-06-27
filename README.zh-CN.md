# AI Radar Agent

这是 AI Radar Agent 的中文 README。英文主版本见 [README.md](README.md)，中文术语说明见 [docs/zh-CN/GLOSSARY.md](docs/zh-CN/GLOSSARY.md)。

AI Radar Agent 是一个证据优先的情报与发布代理案例。它展示了如何把分散的 AI 行业信号转化为带来源约束的每日雷达报告工作流，并用明确的自治边界、发布门禁、运行级契约、本地评估和脱敏演示产物来约束代理行为。

这个 Week 2 标准化分支聚焦于作品集级别的文档化、契约化、评估化和脱敏演示产物整理。它不声明已经生产部署，不声明采集了实时数据，也不把演示产物描述成外部发布结果。

## 本项目展示什么

- 展示从来源召回到门禁后输出的代理工作流设计。
- 证据优先的报告生成：先绑定来源，再写叙事。
- 明确本地工作、provider 访问、workflow dispatch 和发布动作的自治与权限边界。
- 基于门禁的发布安全模型，覆盖 Feishu、bot 卡片、workflow dispatch 和不发布模式。
- 面向未来运行级可观测性的 RunManifest 与 ToolCall schema 契约。
- 无外部副作用的评估套件与静态校验。
- 脱敏演示运行（sanitized demo run）：展示产物形态，但不进行网络调用或生产执行。

## 实现状态

| 领域 | 状态 | 说明 |
| --- | --- | --- |
| Phase A 核心文档 | 已实现（implemented） | 工作流、自治边界、工具权限、门禁、评估计划、可观测性和运行手册已文档化。 |
| Phase B schema 契约 | 已实现（implemented） | `RunManifest` 与 `ToolCall` schema 契约已存在于 `schemas/`。 |
| RunManifest / ToolCall 的运行时产出 | 计划中（planned） | 当前运行产物仍然分散；正式的 manifest 与 tool-call 产出仍是后续工作。 |
| Phase C 评估用例定义 | 已实现（implemented） | 10 个无外部副作用评估用例已用 JSONL 定义。 |
| Phase C 静态检查器 | 已实现（implemented） | 本地静态检查器校验 Week 2 评估文件与 Phase B schema JSON。 |
| 运行时评估集成 | 计划中（planned） | 静态检查器只校验定义，不校验真实运行时行为。 |
| Phase D 脱敏演示运行（sanitized demo run） | 已实现（implemented） | 演示产物使用确定性的模拟数据，并明确标记为模拟。 |
| Week 2 标准化过程中的外部发布 / Feishu / GitHub workflow dispatch | 未触发（not triggered） | Week 2 的文档、评估和演示流程没有触发任何外部发布、Feishu、webhook 或 GitHub workflow dispatch。 |
| Dashboard / 精修截图 | 计划中（planned，P2 / Week 7 Portfolio） | Week 2 Phase E 不创建 dashboard 或截图产物。 |
| Phase F Obsidian-ready 模式笔记 | 已实现（implemented） | 仓库内的导出笔记位于 `docs/obsidian_pattern_notes/`；未导入任何 vault。 |

## 架构概览

```text
公开来源
  -> 证据采集
  -> 证据门禁（Evidence Gate）
  -> 情报草稿
  -> 报告 / 简报 / 头条事件审核
  -> 发布门禁（Publish Gate）
  -> 本地产物 / 未来可选发布
```

当前 Week 2 产物聚焦代理的控制面：工作流文档、门禁、契约、静态评估和脱敏本地演示。外部发布仍然需要明确的人工确认，演示不会执行发布。

## 产物地图

| 产物 | 用途 |
| --- | --- |
| [docs/03_WORKFLOW.md](docs/03_WORKFLOW.md) | 英文权威工作流文档。 |
| [docs/zh-CN/03_WORKFLOW.md](docs/zh-CN/03_WORKFLOW.md) | 中文工作流镜像。 |
| [docs/04_AUTONOMY_MATRIX.md](docs/04_AUTONOMY_MATRIX.md) | 英文权威自治边界文档。 |
| [docs/zh-CN/04_AUTONOMY_MATRIX.md](docs/zh-CN/04_AUTONOMY_MATRIX.md) | 中文自治边界镜像。 |
| [docs/06_TOOLS_AND_PERMISSIONS.md](docs/06_TOOLS_AND_PERMISSIONS.md) | 英文权威工具权限矩阵。 |
| [docs/zh-CN/06_TOOLS_AND_PERMISSIONS.md](docs/zh-CN/06_TOOLS_AND_PERMISSIONS.md) | 中文工具权限镜像。 |
| [docs/09_GATES_AND_GUARDRAILS.md](docs/09_GATES_AND_GUARDRAILS.md) | 英文权威门禁与护栏文档。 |
| [docs/zh-CN/09_GATES_AND_GUARDRAILS.md](docs/zh-CN/09_GATES_AND_GUARDRAILS.md) | 中文门禁镜像。 |
| [docs/10_EVAL_PLAN.md](docs/10_EVAL_PLAN.md) | 英文权威评估计划。 |
| [docs/zh-CN/10_EVAL_PLAN.md](docs/zh-CN/10_EVAL_PLAN.md) | 中文评估计划镜像。 |
| [docs/11_OBSERVABILITY.md](docs/11_OBSERVABILITY.md) | 英文权威可观测性文档。 |
| [docs/zh-CN/11_OBSERVABILITY.md](docs/zh-CN/11_OBSERVABILITY.md) | 中文可观测性镜像。 |
| [docs/12_RUNBOOK.md](docs/12_RUNBOOK.md) | 英文权威运行手册。 |
| [docs/zh-CN/12_RUNBOOK.md](docs/zh-CN/12_RUNBOOK.md) | 中文运行手册镜像。 |
| [docs/13_RUNTIME_OBJECT_MAP.md](docs/13_RUNTIME_OBJECT_MAP.md) | 英文权威运行时对象地图。 |
| [docs/zh-CN/13_RUNTIME_OBJECT_MAP.md](docs/zh-CN/13_RUNTIME_OBJECT_MAP.md) | 中文运行时对象地图镜像。 |
| [schemas/run_manifest.schema.json](schemas/run_manifest.schema.json) | 运行级 schema 契约；字段名不翻译。 |
| [schemas/tool_call.schema.json](schemas/tool_call.schema.json) | 单次工具调用 schema 契约；字段名不翻译。 |
| [evals/ai_radar_week2_eval_cases.jsonl](evals/ai_radar_week2_eval_cases.jsonl) | 10 个本地无外部副作用评估用例定义。 |
| [evals/check_ai_radar_week2_eval_cases.py](evals/check_ai_radar_week2_eval_cases.py) | 本地静态检查器。 |
| [demo_run/demo_output_report.md](demo_run/demo_output_report.md) | 脱敏的模拟演示报告。 |
| [docs/case_study_ai_radar_week2.md](docs/case_study_ai_radar_week2.md) | 英文权威案例研究。 |
| [docs/zh-CN/case_study_ai_radar_week2.md](docs/zh-CN/case_study_ai_radar_week2.md) | 中文案例研究镜像。 |
| [docs/obsidian_pattern_notes/AI_Radar_Week2_MOC.md](docs/obsidian_pattern_notes/AI_Radar_Week2_MOC.md) | 英文权威 Obsidian-ready 内容地图。 |
| [docs/obsidian_pattern_notes/zh-CN/AI_Radar_Week2_MOC.md](docs/obsidian_pattern_notes/zh-CN/AI_Radar_Week2_MOC.md) | 中文 Obsidian-ready 内容地图镜像。 |

## 安全姿态

- 文档、评估、演示产物、提交和报告中都不应包含 secrets。
- Week 2 不执行外部发布。
- Week 2 不触发 Feishu、webhook、GitHub workflow dispatch 或 provider 写入。
- 演示运行是模拟运行，使用确定性的模拟数据。
- 评估检查器只做本地静态检查：不导入生产代码，不调用外部 API，不调用 LLM，也不运行生产流水线。
- 演示产物不是生产输出，也不应被描述为实时市场情报。

## 安全的本地检查

这些命令仅在本地运行，没有外部副作用（external_side_effects）：

```bash
python3 evals/check_ai_radar_week2_eval_cases.py
python3 -m json.tool demo_run/demo_manifest.json
```

可选 JSONL parse check：

```bash
python3 - <<'PY'
import json
from pathlib import Path

for path in [
    Path("demo_run/demo_tool_calls.jsonl"),
    Path("demo_run/demo_evidence_items.jsonl"),
    Path("evals/ai_radar_week2_eval_cases.jsonl"),
]:
    count = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            json.loads(line)
            count += 1
    print(f"{path}: {count} valid records")
PY
```

## 路线图

- Phase F: Obsidian-ready pattern notes 已作为 repo-local export notes 实现；不会自动安装到任何 vault。
- Future 运行时集成: 从真实 runs 中 emit RunManifest 与 ToolCall records。
- 未来评估集成：在没有外部副作用（external_side_effects）的前提下校验已产出的 manifests 和选定运行输出。
- Week 7 Portfolio: 可选 read-only dashboard 与 polished screenshots，基于 sanitized artifacts。
- 只有在明确批准后才进行可选 PR 或 review。

## 非目标

- 本分支不声明已经生产部署。
- 脱敏演示不是实时数据。
- 评估检查器不是生产流水线。
- README 不授权发布、workflow dispatch、Feishu 消息或 webhook 调用。
