# zh-CN 术语表

本术语表服务于 AI Radar Week 2 中文文档。英文 权威文档仍是事实来源；中文镜像采用中文优先表达，只在代码标识符、schema 对象、flag、文件路径、provider/product 名称或 workflow/event 名称上保留英文。

## 状态词

| 中文优先写法 | 英文标识 | 含义 |
| --- | --- | --- |
| 已实现（implemented） | implemented | 当前 repo、文档、测试或 runtime 中已经存在。 |
| 部分实现（partial） | partial | 已有文档、产物或部分运行路径，但缺少完整 runtime 集成、正式校验或持久追踪。 |
| 计划中（planned） | planned | 已明确为后续工作；不得写成已经实现。 |
| 未启用（not enabled） | not enabled | 能力可能存在于系统中，但 Week 2 文档、eval、demo 不启用它。 |

## 核心概念

| 中文术语 | 保留英文 | 说明 |
| --- | --- | --- |
| 证据优先的情报与发布代理 | evidence-first intelligence and publishing agent | 先收集和约束证据，再生成报告和发布决策的代理形态。 |
| 证据门禁 | Evidence Gate | 在写叙事前过滤、标记或阻断低质量、过期、重复或缺证据的信号。 |
| 发布门禁 | Publish Gate | 在 Feishu、bot、workflow dispatch 或其他外部副作用之前执行的发布控制。 |
| 运行清单 | RunManifest | 计划中的运行级追踪对象，记录输入摘要、证据、门禁、工具调用、产物、发布决策和脱敏状态。 |
| 工具调用记录 | ToolCall | 计划中的单次工具调用记录，保存工具类别、权限级别、状态、脱敏输入输出摘要和副作用分类。 |
| 证据项 | EvidenceItem | 可进入报告、brief 或 audit 的来源绑定信号。 |
| 门禁结果 | GateResult | 某个 gate 的 pass、warn、fail 或 block 结果。 |
| 产物引用 | ArtifactRef | 指向运行产物的轻量引用，不复制私有内容。 |
| 发布决策 | PublishDecision | 记录 publish/bot 是否允许、跳过、阻断或尝试。 |
| 评估用例 | EvalCase | synthetic 或 sanitized 的测试/评估输入定义。 |
| 评估结果 | EvalResult | 未来本地评估执行后的结果摘要。 |
| 外部副作用 | external_side_effects | 会写外部系统、发消息、触发 workflow、发布文档或改变生产状态的动作。 |
| 脱敏演示运行 | sanitized demo run | 使用确定性模拟数据、本地生成、无外部副作用的演示产物集。 |
| 模拟运行 | simulated run | 不调用真实 provider、不运行生产流水线、不代表实时数据的本地演示运行。 |

## 保持英文的技术标识符

以下名称在中文文档中保持英文：

- `RunManifest`, `ToolCall`, `EvidenceItem`, `GateResult`, `ArtifactRef`, `PublishDecision`, `EvalCase`, `EvalResult`
- `Evidence Gate`, `Publish Gate`
- `dry_run`, `skip_llm`, `output_mode=none`, `demo_sandbox`, `emergency_stop`
- `workflow_dispatch`, `CLI`, `GitHub Actions`, `Feishu`, `RSS`, `Bocha`, `Tavily`
- 文件路径、命令、artifact 文件名、JSON schema 字段名

## 翻译边界

- 不翻译 JSON schema 字段名。
- 不把计划中的 runtime emission 写成已实现。
- 不把脱敏演示写成生产输出或实时情报。
- 不声明 Week 2 触发过 Feishu、GitHub workflow、webhook、LLM、provider 或外部发布。
- 不写入绝对本地路径、私有 vault 路径、私有笔记名、token、webhook URL 或 secret-like string。
