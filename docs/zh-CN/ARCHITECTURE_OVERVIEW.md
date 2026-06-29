# 架构总览

## 目的

这份文档用图示说明 AI Radar Agent 脱敏公开镜像中的关键设计：证据优先工作流、
触发控制面、证据门禁（Evidence Gate）、发布门禁（Publish Gate）、
可观测对象，以及公开仓库与私有生产环境之间的边界。

这些图用于帮助审阅者快速理解系统形状。它们不表示本仓库连接了真实
Cloudflare、Feishu、provider 或 GitHub Actions 生产运行配置。

运行原则和决策策略见 [Agent 策略面板](STRATEGY_PANEL.md)。

## 1. 端到端工作流

```mermaid
flowchart TD
  A["公开 AI 消息源"] --> B["RSS 召回"]
  A --> C["Bocha 召回"]
  A --> D["可选 Tavily 召回"]
  B --> E["证据标准化"]
  C --> E
  D --> E
  E --> F{"证据门禁"}
  F -->|通过| G["历史记录与去重检查"]
  F -->|拒绝| H["被丢弃证据的审计记录"]
  G --> I["过滤后的证据产物"]
  I --> J["报告生成"]
  J --> K["report_lint"]
  K --> L["brief 与最终 Top 对齐"]
  L --> M{"发布门禁"}
  M -->|dry_run 或 output_mode none| N["只写本地产物"]
  M -->|私有生产环境允许| O["私有 Feishu 文档或 bot 路径"]
  N --> P["公开镜像审阅产物"]
  O --> Q["私有生产环境"]

  classDef mirror fill:#eef7ff,stroke:#4b87c5,color:#0b335c;
  classDef private fill:#fff4e6,stroke:#c77700,color:#4a2d00;
  classDef gate fill:#f2fff0,stroke:#4b9a4b,color:#153d15;
  class F,M gate;
  class P mirror;
  class O,Q private;
```

公开镜像只展示可审阅的工作流和脱敏产物。Feishu 发布、bot 通知、provider keys
和生产状态都属于私有生产环境。

## 2. 触发与控制面

```mermaid
sequenceDiagram
  participant CF as CloudflareTrigger
  participant GH as GitHubActions
  participant WF as AIRadarWorkflow
  participant ART as LocalArtifacts
  participant PUB as PrivatePublishPath

  CF->>GH: workflow_dispatch on main
  CF-->>GH: 公开镜像仅展示模式，不包含线上 secrets
  GH->>WF: dry_run, skip_llm, send_bot
  GH->>WF: output_mode, bocha_enabled, tavily_enabled
  WF->>WF: 召回与证据门禁
  WF->>WF: 报告审计与最终 Top 对齐
  WF->>ART: 写入审阅产物
  alt 发布门禁阻断
    WF-->>ART: 记录跳过发布或 dry run 结果
  else 私有生产环境允许发布
    WF-->>PUB: Feishu 文档或 bot 路径在公开镜像之外
  end
```

公开镜像保留触发模式，是为了让审阅者检查控制面设计。它不包含 bearer secrets、
GitHub secrets、provider keys、Feishu credentials 或 Cloudflare account settings。

## 3. 证据门禁与发布门禁

```mermaid
flowchart TD
  A["候选证据"] --> B["消息源质量检查"]
  B --> C["时间窗口检查"]
  C --> D["去重与历史记录检查"]
  D --> E{"证据门禁"}
  E -->|通过| F["可用证据"]
  E -->|丢弃或警告| G["被拒绝或降级的证据"]
  F --> H["报告候选表"]
  H --> I["最终 Top 事件"]
  I --> J{"发布门禁"}
  J -->|阻断| K["跳过发布"]
  J -->|不发布验证| L["只写本地产物"]
  J -->|私有生产环境允许| M["私有生产发布路径"]
  G --> N["证据丢弃审计"]

  classDef gate fill:#f2fff0,stroke:#4b9a4b,color:#153d15;
  classDef private fill:#fff4e6,stroke:#c77700,color:#4a2d00;
  class E,J gate;
  class M private;
```

核心目标是：缺少来源支撑、过期或重复的证据不应被写成确定性结论；
任何外部发布动作都必须先通过发布门禁。

## 4. 可观测对象关系

```mermaid
graph LR
  RM["RunManifest<br/>schema 契约已实现<br/>完整运行时产出计划中"] --> TC["ToolCall[]<br/>schema 契约已实现<br/>运行时 trace 计划中"]
  RM --> EI["EvidenceItem<br/>运行产物部分存在<br/>正式 schema 计划中"]
  RM --> GR["GateResult<br/>当前已有部分门禁产物<br/>manifest 摘要计划中"]
  RM --> AR["ArtifactRef<br/>私有环境已有运行产物<br/>manifest 引用计划中"]
  RM --> PD["PublishDecision<br/>发布逻辑部分存在<br/>manifest 摘要计划中"]
  PD --> PA["PublishAttempt<br/>私有生产路径<br/>只保留脱敏摘要"]
  EC["EvalCase<br/>10 个静态用例已实现"] --> ER["EvalResult<br/>检查器 stdout 已实现<br/>运行时评估结果计划中"]
  EC --> RM

  classDef implemented fill:#edf8ed,stroke:#3e8f3e,color:#143914;
  classDef planned fill:#eef2ff,stroke:#5969b3,color:#18224d;
  classDef private fill:#fff4e6,stroke:#c77700,color:#4a2d00;
  class EC,ER implemented;
  class RM,TC,EI,GR,AR,PD planned;
  class PA private;
```

公开镜像中的 schemas 可供审阅。`RunManifest`、`ToolCall` 和更完整的
`EvalResult` 运行时产出仍处于计划中或部分实现状态，这一点也在可观测性和运行时对象图文档中说明。

## 5. 公开镜像边界

```mermaid
graph LR
  subgraph Include["公开镜像包含"]
    A["docs"]
    B["schemas"]
    C["evals"]
    D["demo_run"]
    E["代表性代码片段"]
    F["代表性测试"]
    G["workflow pattern"]
    H["Cloudflare pattern"]
  end

  subgraph Exclude["公开镜像排除"]
    I[".env 与 .dev.vars"]
    J["生产 event_history"]
    K["生产输出"]
    L["真实 Feishu 链接"]
    M["secrets 与 tokens"]
    N["私有 prompts 与配置"]
    O["私有运行状态"]
  end

  Include --> Review["架构与安全审阅"]
  Exclude --> Boundary["生产环境边界"]

  classDef include fill:#eef7ff,stroke:#4b87c5,color:#0b335c;
  classDef exclude fill:#fff4e6,stroke:#c77700,color:#4a2d00;
  class A,B,C,D,E,F,G,H,Review include;
  class I,J,K,L,M,N,O,Boundary exclude;
```

审阅提示：本镜像用于理解架构、工作流、安全边界、评估、schema 和脱敏演示产物，
不是可直接部署的生产仓库。
