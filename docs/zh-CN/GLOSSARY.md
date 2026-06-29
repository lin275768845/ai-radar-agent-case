# zh-CN 术语表

本术语表服务于 AI Radar Agent 的中文公开文档。英文文档仍是事实来源；中文文档采用中文优先表达，
只在代码标识符、schema 对象、flag、文件路径、provider/product 名称或 workflow event 名称上保留英文。

## 状态词

| 中文写法 | 英文标识 | 含义 |
| --- | --- | --- |
| 已实现 | implemented | 当前 repo、文档、测试或运行路径中已经存在。 |
| 部分实现 | partial | 已有文档、产物或部分运行路径，但缺少完整运行时集成、正式校验或持久追踪。 |
| 计划中 | planned | 已明确为后续工作；不得写成已经实现。 |
| 未启用 | not enabled | 能力可能存在于系统中，但当前公开镜像、eval 或 demo 不启用它。 |
| 私有生产环境控制 | private production controlled | 能力存在于私有生产环境，不属于公开镜像可运行范围。 |

## 核心概念

| 中文术语 | 保留英文 | 说明 |
| --- | --- | --- |
| 证据优先的情报与发布代理 | evidence-first intelligence and publishing agent | 先收集和约束证据，再生成报告和发布决策的 Agent 形态。 |
| 证据门禁 | Evidence Gate | 在写叙事前过滤、标记或阻断低质量、过期、重复或缺少证据的信号。 |
| 发布门禁 | Publish Gate | 在 Feishu、bot、`workflow_dispatch` 或其他外部副作用之前执行的发布控制。 |
| 运行清单 | RunManifest | 计划中的运行级追踪对象，记录输入摘要、证据、门禁、工具调用、产物、发布决策和脱敏状态。 |
| 工具调用记录 | ToolCall | 计划中的单次工具调用记录，保存工具类别、权限级别、状态、脱敏输入输出摘要和副作用分类。 |
| 证据项 | EvidenceItem | 可进入报告、brief 或 audit 的来源绑定信号。 |
| 门禁结果 | GateResult | 某个 gate 的 pass、warn、fail 或 block 结果。 |
| 产物引用 | ArtifactRef | 指向运行产物的轻量引用，不复制私有内容。 |
| 发布决策 | PublishDecision | 记录 publish/bot 是否允许、跳过、阻断或尝试。 |
| 评估用例 | EvalCase | 使用 synthetic 或 sanitized 输入定义的测试/评估用例。 |
| 评估结果 | EvalResult | 未来本地评估执行后的结果摘要。 |
| 外部副作用 | external_side_effects | 会写外部系统、发消息、触发 workflow、发布文档或改变生产状态的动作。 |
| 脱敏公开镜像 | sanitized public mirror | 从私有生产项目中抽取、删去敏感内容后公开展示的作品集仓库。 |
| 脱敏演示运行 | sanitized demo run | 使用确定性模拟数据、本地生成、无外部副作用的演示产物集。 |
| 模拟运行 | simulated run | 不调用真实 provider、不运行生产流水线、不代表实时数据的本地演示运行。 |
| 不发布验证 | no-publish validation | 只做本地检查或产物生成，不触发 Feishu、webhook、bot、workflow 或其他外部发布动作。 |
| 生产试运行 | production pilot | 在私有生产环境中受控验证真实运行路径，通常仍保留人工门禁。 |

## 保持英文的技术标识符

以下名称在中文文档中保持英文：

- `RunManifest`, `ToolCall`, `EvidenceItem`, `GateResult`, `ArtifactRef`, `PublishDecision`, `EvalCase`, `EvalResult`
- `Evidence Gate`, `Publish Gate`
- `dry_run`, `skip_llm`, `output_mode=none`, `send_bot=false`, `bocha_enabled`, `demo_sandbox`, `emergency_stop`
- `workflow_dispatch`, `CLI`, `GitHub Actions`, `Cloudflare`, `Feishu`, `RSS`, `Bocha`, `Tavily`
- 文件路径、命令、artifact 文件名、JSON schema 字段名

## 中文写作约定

- 优先写“公开镜像”或“脱敏公开镜像”，少写 public mirror。
- 优先写“完整生产仓库”或“可直接部署的生产仓库副本”，少写 production clone。
- 优先写“架构审阅”“工作流审阅”“案例研究”，少写英文 review 名词串。
- 第一次出现核心门禁和 schema 对象时，可使用“中文（English）”形式；后文优先使用中文术语。
- 不翻译 JSON schema 字段名、命令、flag 和文件路径。
- 不把计划中的运行时产出写成已实现。
- 不把脱敏演示写成生产输出或实时情报。
- 不声明 Week 2 触发过 Feishu、GitHub workflow、webhook、LLM、provider 或外部发布。
- 不写入绝对本地路径、私有 vault 路径、私有笔记名、token、webhook URL 或 secret-like string。
