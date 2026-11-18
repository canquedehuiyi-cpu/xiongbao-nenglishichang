# References

Shared prose guidance lives here; executable behavior, fixtures, schemas, and
runtime bindings stay with their capability owners. Select one evidence domain
below, then load only the references needed for the current decision.

## Session Evidence

Use bounded, privacy-safe coding-agent sessions for collection, interpretation,
and Task Episodes. Session evidence does not judge static project quality or
configured asset quality by itself.

- Start with [Sessions Diagnostics](session-evidence/sessions-diagnostics.md)
  for source discovery, scope, selection, privacy, and Task Episode construction.
- Add [Session Insights Report](session-evidence/session-insights-report.md)
  only for a reader-facing insight projection.
- Add [Session Usage Efficiency](session-evidence/session-usage-efficiency.md)
  only for usage, cost, model attribution, or long-session questions.

## Project Harness

Use static repository, history, diff, startup, feedback, design, acceptance,
and recovery evidence. Keep static presence, configured policy, and observed
execution distinct. Choose the reference for the inspected concern:

| Concern | Owner |
| --- | --- |
| Profile, history, core paths, diff, recommended reads | [Core Change Watch](project-harness/core-change-watch.md) |
| Diagnostics and correlated runtime evidence | [Observability](project-harness/observability.md) |
| Project-type evidence additions | [Project Overlays](project-harness/project-overlays.md) |
| Design source of truth and verification | [DESIGN.md Contract](project-harness/design-md-contract.md) |
| Agent-friendly command interface | [Friendly CLI](project-harness/friendly-cli.md) |
| Git hook lifecycle placement and evidence | [Git Hooks](project-harness/git-hooks.md) |
| Rollback applicability, presence, wiring, and safe exercise | [Recovery Evidence](project-harness/change-safety.md#recovery-evidence) |
| Recommendation and change-review trigger policy | [Review Trigger](project-harness/change-safety.md#review-triggers) |
| Sensitive-code review and reporting | [Sensitive Code](project-harness/change-safety.md#sensitive-code) |

Direct initialization belongs to
[Project Foundation Bootstrap](../skills/better-harness/bootstrap/project-foundation.md).
Combined evidence mapping belongs to
[Agent Work Loop](../models/agent-work-loop.md#construct-task-episode-evidence).
Configured agent assets and session interpretation use their own domains below
and above.

## Agent Customize

Use configured asset quality, authority, routing, overlap, observed use, and
maintenance evidence. Start with [Agent Customize Routing](agent-customize/routing.md),
then choose the actual asset owner:

- Rules and agent guides: [AGENTS.md Review](agent-customize/agents-md-review.md).
- Skills: [Skill Discovery](agent-customize/skill-discovery.md) for owner-gated
  selection and [Skill Review](agent-customize/skill-review.md) for quality.
- Other assets: [MCP](agent-customize/mcp-review.md),
  [Memory](agent-customize/memory-review.md), [Hooks](agent-customize/hooks.md#configuration-and-performance-review),
  [Custom Agents](agent-customize/custom-agents-review.md), and
  [Knowledge Assets](agent-customize/knowledge-assets-review.md).
- Inventory/authority: [Global Assets](agent-customize/qoder.md#global-assets).
  Platform-specific runtime notes: [Qoder](agent-customize/qoder.md).

Session interpretation and static project evidence retain their own owners.
Repeated-work evidence goes through Loop Engineering before selecting a Skill
or another durable asset.

## Loop Engineering

Use repeated requests, workflow friction, local entropy, or scheduling demand
to decide whether work needs a durable owner. Prefer a known workflow over
autonomy when it provides sufficient control. This domain selects owners and
contracts; it does not implement schedulers, persistence, tracing, or approvals.
Before promoting an autonomous or scheduled loop, require a stable trigger,
replayable state where needed, observable traces, evaluation evidence, a human
gate for sensitive effects, and a stop condition.

| Current decision | Read |
| --- | --- |
| Raw prompt, session signal, report row, or entropy lead needs bounded evidence | [Demand Source Analysis](loop-engineering/demand-source-analysis.md) |
| Recurrence or durable owner remains unproven | [Loop Discovery](loop-engineering/loop-discovery.md) |
| Proven candidate and owner need an operating composition | [Operating Patterns](loop-engineering/operating-patterns.md) |
| Proven candidate needs a reusable spec/example | [Loop Spec Card](loop-engineering/loop-spec-card.md) |
| Supporting runtime/tool primitives are unclear | [Loop Primitives](loop-engineering/runtime-contracts.md#primitives) |
| Owner is automation, schedule-ready, or scheduled/background follow-up | [Automation Readiness](loop-engineering/runtime-contracts.md#automation-readiness) |
| Work pauses or spans runs, approvals, worktrees, agents, or external systems | [Loop State Ledger](loop-engineering/runtime-contracts.md#state-ledger) |
| Longitudinal Learning Capture needs patterns, negative controls, or no-finding coverage | [Learning Loop Detection Patterns](loop-engineering/learning-loop-patterns.md) |

Only a `Create Skill` or `Extend Skill` decision routes to Skill Discovery.
Acceptance, sensitive code, and Git safeguards stay under Project Harness;
asset taxonomy stays under Agent Customize.

## Tool Runtimes

[Node Runtime Discovery](agent-customize/qoder.md#node-runtime-discovery) owns runtime
discovery and execution boundaries; it is a support contract, not a practice
domain.

Detector and signal guidance stays with its owning model, executable
capability, or skill-local contract. Promote shared prose only when two visible
workflow consumers need the same owner; do not recreate a generic detector
bucket.

## Historical Paths

- `references/coding-agent-practices/` was split by evidence owner. Use
  `session-evidence/`, `project-harness/`, or `agent-customize/`.
- `references/reliable-delivery/`, `references/ai-friendly/`,
  `references/coding-agent-observability/`, and
  `references/ai-friendly-engineering/` were folded into `project-harness/`.
- `references/coding-agent-practises/` was the historical misspelled path. Do
  not recreate it; route the document to its current evidence owner.
- `references/harness-practises/` was the historical misspelled harness path.
  Do not recreate it; use `references/project-harness/`.
- `references/harness-engineering/` was the former broad project domain. Do
  not recreate it; use
  `references/project-harness/`.
