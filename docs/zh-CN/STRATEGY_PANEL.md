# Agent 策略面板

## 目的

这份面板总结 AI Radar Agent 脱敏公开镜像背后的高层运行原则。

它面向作品集和架构审阅者，帮助对方先理解这个 Agent 如何做判断，再进入
工程细节。它不是完整私有生产 runbook，也不表示这个 public mirror 可以直接
跑生产流水线。

## 策略总览

| 领域 | 原则 |
| --- | --- |
| 使命 | 把公开 AI 信号转成有来源约束的情报。 |
| 证据 | Evidence before narrative。 |
| 消息源质量 | 优先使用官方和权威来源；低置信信号需要降级或标记。 |
| 时效性 | 使用北京时间自然日窗口，并结合 recent-history checks。 |
| 去重 | 通过 event history 和 final-top dedupe 避免重复推高近期已覆盖事件。 |
| 排名 | 优先考虑高影响的模型、平台、Agent、采用、政策和基础设施信号。 |
| 发布 | 只有在 lint/audit 和 Publish Gate 通过后才进入发布路径。 |
| 人工控制 | 外部副作用仍然由人拥有最终控制权。 |
| 公开镜像边界 | 用于审阅 architecture 和 safety，不从这个 mirror 跑生产。 |

## 1. 使命

AI Radar Agent 的工作是：

- 收集公开 AI 行业信号
- 把 claims 绑定到 sources
- 通过 evidence 和 quality gates 过滤候选事件
- 生成带来源约束的每日情报报告
- 只通过私有、受门禁控制的生产路径发布

公开镜像展示的是系统形状，不暴露私有 source configuration、prompts、
production state 或发布历史。

## 2. 信号召回策略

RSS 是基础的公开来源召回路径。

Bocha 是显式可选的搜索扩展，由 `bocha_enabled` 控制。Tavily 也是可选
扩展，只有在相关运行配置明确启用时才进入召回。

LLM 用于综合和写作，不是事实来源。Source configuration 和 report prompts
属于私有生产资产，已经从公开镜像中排除。

## 3. 消息源质量策略

如果官方来源可用，它通常是最高置信来源。

权威媒体可以支持分析，特别是在官方来源不可用，或需要理解采用、市场和
行业背景时。低置信来源更适合作为观察信号、弱上下文或待验证候选，而不是
直接写成强结论。

仓库文档使用 source tier、`source_fit` 等 source-quality 概念。这里把它们
保守地描述为消息源质量信号，而不是公开私有生产策略的完整定义。

Source URL 和 evidence binding 很重要。证据不完整或相互冲突时，应该显式
表达不确定性，而不是写成过度确定的叙事。

## 4. 时间窗口与去重策略

报告窗口采用北京时间自然日。

时效性控制依赖 event history、recent-history checks 和 final-top dedupe。
重复事件或后续报道不应自动重新进入 Top，除非它们带来实质新增信息。

公开镜像说明了 recent-history 行为，但不暴露完整私有生产配置。因此这里使用
"recent-history window"，不声明固定天数。

## 5. 证据门禁策略

候选 evidence 需要通过 source、date-window、quality 和 relevance checks，
才可以进入报告叙事。

Evidence Gate 把 recall 和 narrative generation 分开。被丢弃或降级的条目
在有 artifact 的地方应保持可审计；通过门禁的 evidence 才进入候选表、
report synthesis、brief generation 和 final-top decisions。

Week 2 的一个具体修复教训是：final selections 应该更新 evidence-bound
candidate rows，而不是追加 synthetic `final_top` rows。这样才能保持从
source evidence 到 final selection 的审阅链路。

## 6. 排名与最终 Top 策略

最终 Top 应优先考虑：

- 影响强度
- 确定性
- 来源质量
- 时效性
- 与 AI 能力、产品、基础设施、治理、采用和 Agent/workflow 变化的相关性

最终 Top 必须保持 source-bound。证据较弱时，Agent 不应过度断言，而应降级、
标记，或保留为观察信号。

## 7. 发布策略

Publish Gate 与 Evidence Gate 是两个不同的边界。

Evidence Gate 判断一个条目是否有资格进入叙事。Publish Gate 判断一次运行
是否允许产生外部副作用。

No-publish 模式包括 `dry_run`、`output_mode=none` 和 `send_bot=false`。
Feishu 文档发布和 bot send 属于私有生产副作用，不属于 public mirror 行为。

`report_lint` 和 `top_event_audit` 应根据 policy 在发布前 warn、block 或
要求 review。`force_republish` 是显式的人类拥有动作，不应被视为默认自动化路径。

## 8. 人工控制边界

以下动作仍然需要人工批准：

- Cloudflare cutover
- workflow dispatch
- production publish
- bot send
- `force_republish`
- provider enablement
- 远端 artifacts 的删除或清理

Agent 可以准备 evidence、生成 draft、运行检查并总结状态。外部承诺由人负责。

## 9. 失败与降级策略

Provider failure 应该可见地降级，而不是静默编造。

RSS 普通缺页等失败应作为 warning，除非它们对本次运行构成 critical 风险。
Bocha、Tavily 和 LLM 的可用性应在 artifacts、logs 或 summaries 中可见。

如果 lint 或 audit 结果是 critical，publish 和 bot 路径应被阻断或进入人工
review，再发生外部副作用。

## 10. 这个 Agent 不做什么

- 不把 LLM output 当作事实来源。
- 不绕过 Publish Gate 发布。
- 不在 public mirror 暴露 secrets。
- 不把 public demo artifacts 说成 production outputs。
- 不把仍处于 planned 或 partial 的 runtime `RunManifest` / `ToolCall`
  emission 说成已完整实现。
- 不把 public mirror 描述成完整私有生产 clone。

## 11. 审阅者快速理解

这个 Agent 不只是 daily-report script，因为它把 recall、Evidence Gate、
synthesis、lint/audit、final-top reconciliation、Publish Gate 和人工拥有的
external side effects 分离成可审阅的工作流。
