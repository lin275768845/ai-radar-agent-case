# Architecture Overview

## Purpose

This is a visual guide for the sanitized public mirror of AI Radar Agent.

The diagrams show the reviewable architecture, safety gates, observability
contracts, and public mirror boundary. They do not imply that this repository
is connected to live Cloudflare, Feishu, provider, or production GitHub
deployment settings.

For operating principles and decision strategy, see
[docs/STRATEGY_PANEL.md](STRATEGY_PANEL.md).

## 1. End-to-End Agent Workflow

```mermaid
flowchart TD
  A["Public AI sources"] --> B["RSS recall"]
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

The public mirror is review-only. Feishu publishing, bot notification, provider
keys, and production state remain private production concerns.

## 2. Trigger and Control Plane

```mermaid
sequenceDiagram
  participant CF as CloudflareTrigger
  participant GH as GitHubActions
  participant WF as AIRadarWorkflow
  participant ART as LocalArtifacts
  participant PUB as PrivatePublishPath

  CF->>GH: workflow_dispatch on main
  CF-->>GH: review pattern only, no live secrets
  GH->>WF: dry_run, skip_llm, send_bot
  GH->>WF: output_mode, bocha_enabled, tavily_enabled
  WF->>WF: recall and Evidence Gate
  WF->>WF: report lint and final top reconciliation
  WF->>ART: write review artifacts
  alt Publish Gate blocks
    WF-->>ART: publish skipped or dry run result
  else Private production allows publish
    WF-->>PUB: Feishu doc or bot path outside public mirror
  end
```

The public mirror includes the trigger pattern so reviewers can inspect the
control surface. It is not a live deployment and does not include bearer
secrets, GitHub secrets, provider keys, Feishu credentials, or Cloudflare
account settings.

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

The design goal is simple: unsupported or stale evidence should not become
confident report narrative, and publish side effects should be blocked unless
the production environment and operator intent allow them.

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

The schemas are reviewable in this mirror. First-class runtime emission of
`RunManifest`, `ToolCall`, and richer `EvalResult` artifacts remains planned
or partial, as documented in the observability and runtime object map docs.

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

Reviewer note: this mirror is optimized for architecture, workflow, safety,
eval, schema, and demo review. It is not a turnkey production deployment repo.
