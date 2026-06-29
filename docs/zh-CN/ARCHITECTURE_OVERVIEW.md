# 架构总览

## 目的

这是一份面向 AI Radar Agent 脱敏公开镜像的可视化说明。

这些图用于帮助 reviewer 理解可审阅的 architecture、safety gates、
observability contracts 和 public mirror boundary。它们不表示本仓库连接了
真实 Cloudflare、Feishu、provider 或 GitHub 生产运行配置。

## 1. End-to-End Agent Workflow

```mermaid
flowchart TD
  A["公开 AI sources"] --> B["RSS recall"]
  A --> C["Bocha recall"]
  A --> D["Optional Tavily recall"]
  B --> E["Evidence normalization"]
  C --> E
  D --> E
  E --> F{"Evidence Gate"}
  F -->|accepted| G["History and dedupe checks"]
  F -->|rejected| H["Dropped evidence audit"]
  G --> I["Filtered evidence artifacts"]
  I --> J["Report generation"]
  J --> K["report_lint"]
  K --> L["Brief and final top reconciliation"]
  L --> M{"Publish Gate"}
  M -->|dry_run or output_mode none| N["Local artifacts only"]
  M -->|private production approval| O["Private Feishu doc or bot path"]
  N --> P["Public mirror review artifacts"]
  O --> Q["Private production environment"]

  classDef mirror fill:#eef7ff,stroke:#4b87c5,color:#0b335c;
  classDef private fill:#fff4e6,stroke:#c77700,color:#4a2d00;
  classDef gate fill:#f2fff0,stroke:#4b9a4b,color:#153d15;
  class F,M gate;
  class P mirror;
  class O,Q private;
```

公开镜像只用于 review。Feishu 发布、bot notification、provider keys 和
production state 都属于私有生产环境边界。

## 2. Trigger and Control Plane

```mermaid
sequenceDiagram
  participant CF as Cloudflare cron or manual trigger
  participant GH as GitHub workflow_dispatch
  participant WF as AI Radar workflow
  participant ART as Local artifacts
  participant PUB as Private production publish path

  CF->>GH: dispatch main workflow
  Note over CF,GH: Public mirror only shows the pattern; no live secrets included
  GH->>WF: inputs dry_run, skip_llm, send_bot
  GH->>WF: inputs output_mode, bocha_enabled, tavily_enabled
  WF->>WF: recall, Evidence Gate, report lint, final top reconciliation
  WF->>ART: write review artifacts
  alt Publish Gate blocks
    WF-->>ART: publish skipped or dry-run result
  else Private production allows publish
    WF-->>PUB: Feishu doc or bot path outside public mirror
  end
```

公开镜像包含 trigger pattern，是为了让 reviewer 检查控制面设计。它不是
live deployment，也不包含 bearer secrets、GitHub secrets、provider keys、
Feishu credentials 或 Cloudflare account settings。

## 3. Evidence Gate and Publish Gate

```mermaid
flowchart TD
  A["Evidence candidates"] --> B["Source quality checks"]
  B --> C["Date window checks"]
  C --> D["Dedupe and history checks"]
  D --> E{"Evidence Gate"}
  E -->|pass| F["Accepted evidence"]
  E -->|drop or warn| G["Rejected or dropped evidence"]
  F --> H["Report candidate table"]
  H --> I["Final top events"]
  I --> J{"Publish Gate"}
  J -->|blocked| K["Publish skipped"]
  J -->|dry-run| L["Local artifacts only"]
  J -->|private production approval| M["Private production publish"]
  G --> N["Dropped evidence audit"]

  classDef gate fill:#f2fff0,stroke:#4b9a4b,color:#153d15;
  classDef private fill:#fff4e6,stroke:#c77700,color:#4a2d00;
  class E,J gate;
  class M private;
```

核心设计目标是：缺少支撑、过期或重复的 evidence 不应该被写成确定性叙事；
外部发布副作用必须被 Publish Gate 挡住，除非生产环境配置和人工意图都允许。

## 4. Observability Object Map

```mermaid
graph LR
  RM["RunManifest<br/>schema contract implemented<br/>runtime emission planned"] --> TC["ToolCall[]<br/>schema contract implemented<br/>runtime trace planned"]
  RM --> EI["EvidenceItem<br/>runtime artifact partial<br/>formal schema planned"]
  RM --> GR["GateResult<br/>current gate artifacts partial<br/>manifest summary planned"]
  RM --> AR["ArtifactRef<br/>current outputs exist privately<br/>manifest refs planned"]
  RM --> PD["PublishDecision<br/>runtime publish logic partial<br/>manifest summary planned"]
  PD --> PA["PublishAttempt<br/>private production path<br/>redacted summary only"]
  EC["EvalCase<br/>10 static cases implemented"] --> ER["EvalResult<br/>checker stdout implemented<br/>runtime eval result planned"]
  EC --> RM

  classDef implemented fill:#edf8ed,stroke:#3e8f3e,color:#143914;
  classDef planned fill:#eef2ff,stroke:#5969b3,color:#18224d;
  classDef private fill:#fff4e6,stroke:#c77700,color:#4a2d00;
  class EC,ER implemented;
  class RM,TC,EI,GR,AR,PD planned;
  class PA private;
```

公开镜像中的 schemas 可以被审阅。`RunManifest`、`ToolCall` 和更完整的
`EvalResult` runtime emission 仍是 planned 或 partial，这一点在 observability
和 runtime object map 文档中也有说明。

## 5. Public Mirror Boundary

```mermaid
graph LR
  subgraph Include["Public mirror includes"]
    A["docs"]
    B["schemas"]
    C["evals"]
    D["demo_run"]
    E["selected code"]
    F["representative tests"]
    G["workflow pattern"]
    H["Cloudflare pattern"]
  end

  subgraph Exclude["Public mirror excludes"]
    I[".env and .dev.vars"]
    J["production event_history"]
    K["production outputs"]
    L["real Feishu URLs"]
    M["secrets and tokens"]
    N["private prompts and config"]
    O["private runtime state"]
  end

  Include --> Review["Architecture and safety review"]
  Exclude --> Boundary["Production boundary"]

  classDef include fill:#eef7ff,stroke:#4b87c5,color:#0b335c;
  classDef exclude fill:#fff4e6,stroke:#c77700,color:#4a2d00;
  class A,B,C,D,E,F,G,H,Review include;
  class I,J,K,L,M,N,O,Boundary exclude;
```

Reviewer note：这个 mirror 面向 architecture、workflow、safety、eval、
schema 和 demo review，不是 turnkey production deployment repo。
