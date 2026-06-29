# Agent Strategy Panel

## Purpose

This panel summarizes the high-level operating doctrine behind the sanitized
public mirror of AI Radar Agent.

It is meant for portfolio and architecture reviewers who want to understand
the agent's decision principles before reading the engineering drill-down. It
is not the full private production runbook, and it does not make this public
mirror a production-runnable clone.

## Strategy Snapshot

| Area | Principle |
| --- | --- |
| Mission | Turn public AI signals into source-bound intelligence. |
| Evidence | Evidence before narrative. |
| Source quality | Prefer official and authoritative sources; degrade or mark lower-confidence signals. |
| Recency | Use a Beijing natural-day window plus recent-history checks. |
| Deduplication | Avoid repeating recently covered events through event history and final-top dedupe. |
| Ranking | Prefer high-impact model, platform, agent, adoption, policy, and infrastructure signals. |
| Publishing | Publish only after lint/audit and publish gates pass. |
| Human control | External side effects remain human-owned. |
| Public mirror boundary | Review architecture and safety; do not run production from this mirror. |

## 1. Mission

AI Radar Agent's job is to:

- collect public AI industry signals
- bind claims to sources
- filter candidates through evidence and quality gates
- generate a source-aware daily intelligence report
- publish only through private, gated production controls

The public mirror shows the shape of this system without exposing private
source configuration, prompts, production state, or publication history.

## 2. Signal Intake Strategy

RSS provides the baseline public-source recall path.

Bocha is an explicit optional search expansion controlled through
`bocha_enabled`. Tavily is also optional and remains disabled unless explicitly
enabled through the relevant run configuration.

The LLM is used for synthesis, not as the source of truth. Source configuration
and report prompts are private production assets and are intentionally excluded
from this public mirror.

## 3. Source Quality Strategy

Official sources carry the highest confidence when they are available.

Authoritative media can support analysis, especially when official sources are
not available or when adoption and market context matter. Lower-confidence
sources should be treated as watch signals, weak context, or candidates for
further verification rather than hard claims.

The repo docs refer to source-quality concepts such as source tier and
`source_fit`; this panel treats them conservatively as source-quality signals,
not as a complete public definition of private production policy.

Source URL and evidence binding matter. When evidence is incomplete or
conflicting, uncertainty should be explicit rather than hidden inside confident
narrative.

## 4. Recency and Deduplication Strategy

The reporting window is a Beijing natural-day window.

Recency control is handled through event history, recent-history checks, and
final-top dedupe. Repeated or follow-up stories should not automatically
re-enter Top status unless they add material new information.

This public mirror documents the recent-history behavior but does not expose a
complete private production configuration. Therefore this panel uses
"recent-history window" rather than claiming a specific fixed number of days.

## 5. Evidence Gate Strategy

Evidence candidates must pass source, date-window, quality, and relevance
checks before they can become report narrative.

Evidence Gate separates recall from narrative generation. Dropped or degraded
items should remain auditable where artifacts exist, while accepted evidence
becomes the basis for candidate tables, report synthesis, brief generation,
and final-top decisions.

Week 2 also produced a concrete fix lesson: final selections should update
evidence-bound candidate rows rather than appending synthetic `final_top` rows.
This keeps the path from source evidence to final selection reviewable.

## 6. Ranking and Final Top Strategy

Final top selection should prioritize:

- impact
- certainty
- source quality
- recency
- relevance to AI capability, products, infrastructure, governance, adoption,
  and agent/workflow change

The final top list must remain source-bound. When evidence is weak, the agent
should not overclaim; it should demote, mark, or keep the item as a watch
signal.

## 7. Publish Strategy

Publish Gate is separate from Evidence Gate.

Evidence Gate decides whether an item is eligible for narrative. Publish Gate
decides whether the run is allowed to create external side effects.

No-publish modes include `dry_run`, `output_mode=none`, and `send_bot=false`.
Feishu document publish and bot send are private production side effects, not
public mirror behavior.

`report_lint` and `top_event_audit` should warn, block, or force review before
publish depending on policy. `force_republish` is an explicit human-owned
action and should not be treated as a default automation path.

## 8. Human Control Boundaries

These actions remain human-approved:

- Cloudflare cutover
- workflow dispatch
- production publish
- bot send
- `force_republish`
- provider enablement
- deletion or cleanup of remote artifacts

The agent can prepare evidence, generate drafts, run checks, and summarize
state. Humans own external commitment.

## 9. Failure and Degradation Policy

Provider failure should degrade visibly rather than silently fabricate.

RSS failures such as ordinary missing pages should be warnings unless they
become critical to the run. Bocha, Tavily, and LLM availability should be
visible in artifacts, logs, or summaries.

If lint or audit results are critical, publish and bot paths should be blocked
or reviewed before external side effects happen.

## 10. What This Agent Will Not Do

- It will not treat LLM output as source of truth.
- It will not publish without Publish Gate.
- It will not expose secrets in the public mirror.
- It will not claim public demo artifacts are production outputs.
- It will not pretend runtime `RunManifest` or `ToolCall` emission is complete
  while that work remains planned or partial.
- It will not present the public mirror as a full private production clone.

## 11. Reviewer Quick Read

This agent is not just a daily-report script because it separates recall,
evidence gating, synthesis, lint/audit, final-top reconciliation, publish
gating, and human-owned external side effects.
