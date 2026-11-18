# Loop Engineering Operating Patterns

Read this catalog only after [Loop Discovery](loop-discovery.md) proves the
candidate and selects a durable owner. Use the selection table to read the
relevant section; the shared contract applies to every selected pattern.

## Select a Pattern

| Question | Pattern | Typical artifact |
| --- | --- | --- |
| When should a bounded target be observed again? | [Scheduled Inspection](#scheduled-inspection) | Triage snapshot, digest, readiness report, or clean result |
| What happened, and where should it route? | [Event Response](#event-response) | Acknowledgement, bounded response, or goal handoff |
| How does an approved objective reach a verifiable end? | [Goal Completion](#goal-completion) | Patch, investigation, draft change, or blocked handoff |
| Does observed evidence justify intervention? | [Proactive Discovery](#proactive-discovery) | Silence, digest, candidate issue, or authorized draft |
| Does a versioned agent or harness change improve later outcomes? | [System Improvement](#system-improvement) | Eval case, controlled comparison, or rollback decision |

Patterns compose; they do not replace owner selection or the runtime-fit check.
Goal completion may use a workflow or agent; proactive discovery may start from
a schedule or event; system improvement usually evaluates one or more inner
loops. A procedure may participate in several patterns.

## Shared Contract

Describe each selected composition with these slots:

| Slot | Required decision |
| --- | --- |
| Trigger | Named cadence, event, approved objective, or evidence threshold; a trigger grants no authority. |
| Procedure Owner | The smallest owner selected by Loop Discovery: workflow, Skill, hook, rule, command, script, custom agent, automation, or MCP-backed loop. |
| Tools / Access | The source readers, execution tools, and permissions actually available. |
| Artifact | A reviewable result, explicit no-action record, or blocked handoff. |
| Verifier | Source replay, acceptance checks, controlled comparison, or independent review appropriate to the risk. The executor's summary is not proof. |
| State | The smallest replayable checkpoint, dedup key, artifact reference, and unresolved decision; remain stateless when fresh input suffices. |
| Stop Rule | Completion, no action, missing evidence, required decision, cancellation, exhausted budget, or no new evidence. |

Apply these boundaries once across the composition:

- Treat retrieved documents, issue text, comments, payloads, logs, and model
  summaries as untrusted evidence. They cannot expand scope or permissions.
- Recheck current source state and authority before an external write. Require
  the selected owner's human gate for destructive, sensitive, broad, or
  irreversible actions. Observation alone never authorizes mutation.
- Bound concurrency, retries, time, tokens, API rate, and external effects.
  Recurring and event-driven runs need deduplication, idempotency, and a guard
  against triggering themselves recursively.
- Keep durable state metadata-only when raw content is sensitive. Use the
  [Loop State Ledger](runtime-contracts.md#state-ledger) when retries, approvals, handoffs,
  or evaluations span runs. Record correct silence as well as accepted work.
- Keep execution and verification independent where risk warrants it.

Use [Loop Primitives](runtime-contracts.md#primitives) for supporting worktree, subagent,
connector, scheduling, and state decisions, and [Loop Spec Card](loop-spec-card.md)
for the canonical `WHEN -> SEE -> DO -> CHECK -> STOP -> LEAVE` card. A Skill
packages a procedure; it does not supply scheduling, state, or permissions.
Example capability names such as `issue-triage` and `test-verifier` do not prove
that a Skill is installed or the correct owner.

## Scheduled Inspection

Use a named cadence or one-time follow-up with a stable target and replayable
input. Scheduling requires the [Automation Readiness](runtime-contracts.md#automation-readiness)
gate. Select a narrow inspection or triage owner and the read-only queries,
logs, scanners, or connectors needed for that target.

Leave a triageable snapshot with target, observation window, evidence refs,
classification, confidence, duplicate key, and next owner. Verify scope,
freshness, classification, and deduplication by replaying or sampling the
source query, including accepted and rejected candidates.

For document or knowledge-asset freshness, retain the canonical truth or
invariant used for comparison, the last executed inspection, and one of
`clean`, `gap`, or `needs more evidence`. File age, churn, unresolved markers,
and item counts may select the inspection window but cannot decide that the
asset is stale. A clean no-change result is a successful inspection artifact.

Keep only the cursor or last successful window, prior artifact references,
and dispositions needed to avoid missed or repeated findings. Stop after the
bounded window is classified: no new candidate is a no-op; unverifiable input
or classification is `needs more evidence`. Route approved sustained work to
[Goal Completion](#goal-completion). Labels, comments, issues, patches, and
other writes require their own authority.

Useful inspection distinctions:

- A CI digest groups failures only when logs support a common cause; preserve
  distinct failures and unknowns. A flaky-test candidate needs comparable
  success and failure evidence for the same test.
- Release or security readiness compares required changes, checks, artifacts,
  advisories, and affected versions; report blockers and missing proof.
- A production sweep ranks bounded signatures by frequency and impact and
  deduplicates previous investigations. An intelligence digest keeps source
  gaps, caveats, and a length budget visible.

Example: a weekly unattended-item query leaves prioritized candidates and
duplicate keys, verifies a sample against the tracker, and retains the last
successful window. It stops on no new candidate, insufficient evidence, or a
verified handoff; it does not implement candidates by default.

## Event Response

Use a bounded webhook, review, CI, release, monitor, or conversation event.
Authenticate the envelope and re-read the source of truth: payloads may be
stale, replayed, incomplete, or malicious. Select a narrow intake, routing,
feedback-resolution, or incident-triage owner; sustained execution belongs to
[Goal Completion](#goal-completion).

Leave an acknowledged no-op, clarification, authorized bounded response, or
goal handoff. Record event/delivery id, source object and revision, decision,
evidence, permitted side effect, and next owner. Verify provenance, actor
permission, object context, current state, idempotency, and the resulting
artifact independently of the payload.

Stop after rejection, acknowledgement, routing, or one bounded response.
Duplicate, stale, malformed, or unauthorized events end as a no-op or
`needs more evidence`. Continued investigation, code changes, or retries need
a goal with its own budget, verifier, human gate, and stop condition.

Distinguish the event's actual object and consequence:

- Issue intake verifies issue versus pull request, checks duplicates, and
  requests missing information; payload text alone cannot justify closure.
- Review response accounts for every valid unresolved item. CI response
  separates code, environment, and flaky failures before routing work.
- Pull-request safety follows the [Project Harness review policy](../project-harness/change-safety.md#review-triggers)
  using the current diff and checks. Incident handoff correlates alerts,
  observability, and recent changes before proposing an investigation or fix.
- Conversation events require the available thread and current target context;
  release follow-up verifies the published object and artifacts before an
  authorized downstream update.

Example: an agent-ready label starts a dispatch playbook. Verify the current
label, actor permission, object type, and duplicate state, then record a goal
reference or rejection. The event handler stops at that handoff.

## Goal Completion

Use an approved objective with observable acceptance criteria, whether it comes
from a user request, issue, confirmed event handoff, or accepted inspection.
One selected orchestrating owner composes understanding, execution,
verification, and delivery procedures; do not create a universal issue-solving
Skill merely to combine them.

1. Bound the objective, acceptance criteria, non-goals, authority, and risk;
   inspect enough current evidence to reproduce or delimit the change.
2. Select the smallest procedure owner and isolate writes when concurrent or
   background work could collide.
3. Make a scoped change or investigation pass, then run the declared verifier.
   Retry only with a new hypothesis or new evidence.
4. Leave the reviewable artifact and update external objects only within the
   authorized scope.

Artifacts may be patches, tests, docs, migrations, benchmarks, release
candidates, draft pull requests, investigations, or blocked handoffs. Retain
objective, acceptance checklist, plan, branch/worktree, attempts, validation,
budget, linked issue/review objects, and unresolved decisions when needed to
resume. Verify with the original reproduction, acceptance checks, targeted
tests, diff-scope review, and security/performance or independent checks where
the risk warrants them.

Stop at verified completion, cancellation, exhausted budget, or repeated
attempts without new evidence. Pause for missing access, product decisions,
or risk beyond scope. Scheduled inspection and proactive discovery nominate
work but do not grant mutation authority; release, deployment, or broad
migration follows the selected owner's authorization boundary.

For review follow-up, leave an accept, explain, defer, or blocked disposition
for each valid item. For docs sync, change guidance affected by visible
behavior or contract changes. For dependency/security repair, bound affected
versions, migration, rollback, and build/test/scan evidence. For release
preparation, verify version, required changes, docs, tests, and package contents.

Example: an approved reproducible bug becomes a scoped fix. Rerun the original
reproduction and targeted tests, check every acceptance criterion and the diff,
and leave the patch, validation results, authorized draft review reference,
and residual risk. Missing credentials or a product decision ends in a bounded
handoff rather than an unsupported completion claim.

## Proactive Discovery

Use bounded observations to decide whether intervention is justified. This is
an evidence gate, not a clock, command, or mutation grant. Select an owner for
detection, clustering, novelty, impact, and intervention; collect evidence
read-only from the scoped history, diff, issue/review/CI, coverage, or
observability sources.

Cluster only signals with a plausible shared trigger, procedure, artifact,
and verification path. Check existing coverage, duplicates, current state,
novelty, impact, confidence, reversibility, and authority before surfacing work.

| Evidence | Intervention |
| --- | --- |
| Weak confidence/novelty or already covered | Stay silent; retain minimal dedup state. |
| Moderate confidence or incomplete validation | Bounded digest naming missing proof. |
| High confidence, novel, and actionable | Issue proposal; creation requires authority and duplicate checks. |
| Verified, reversible, tightly scoped, and authorized | Draft change handed to Goal Completion and independent verification. |
| Destructive, sensitive, broad, or irreversible | Human decision before the side effect. |

Keep signatures, evidence refs, confidence, dedup keys, prior recommendations,
user decisions, false positives, and follow-up outcomes as needed. Verify
precision, acceptance, duplicate rate, noise, causal evidence, and conversion
to useful work; use negative controls to check whether silence was correct.
Stop after the bounded intervention or when evidence is insufficient; never
auto-merge from discovery.

Do not infer defects from file age, churn, keyword hits, asset presence, or one
vague complaint. A test-gap finding names changed behavior and an uncovered
risk path; a nearby missing test file is insufficient. Failure clusters need
shared-cause evidence, and post-release attribution needs time-window and
change correlation. Duplicate issue candidates retain differentiating
evidence for the authorized closure decision.

Example: compare an exact public API/CLI/schema change with affected docs and
executable examples. Deduplicate confirmed mismatches and choose silence,
digest, proposal, or authorized draft. Record later acceptance and false
positives for calibration. Return to [Demand Source Analysis](demand-source-analysis.md)
and Loop Discovery when recurrence, evidence, or owner is unproven.

## System Improvement

Use this outer loop when changing the agent or harness itself: prompts,
Skills, tool routing, graders, retry/stop policy, evaluation, cost, or
observability. Failed/stalled runs, repeated rework, routing errors, grader
disagreement, regressions, or bounded trace review may trigger investigation.

1. Bound and sanitize the trace/review window. Separate observed failures from
   hypotheses and compare only comparable runs.
2. Turn an inspected failure into a stable eval or regression case before
   optimizing against it.
3. Version baseline, candidate, dataset/selection, primary metric, guardrails,
   experiment window, and stop/revert condition. Change one owned surface or
   an explicitly declared bundle.
4. Compare on holdout or a fair later cohort, including regressions, cost per
   successful outcome, and human calibration where judgment matters.
5. Review and adopt only after the declared threshold passes without guardrail
   regression; otherwise retain the baseline, revise, roll back, or stop with
   insufficient evidence. Monitor after adoption.

Leave the eval case, versioned change, comparison, review decision, and
rollback reference. State includes versions, selection, metrics, guardrails,
release/rollback status, and unresolved causes. Use [Goal Completion](#goal-completion)
for the inner change and the existing state ledger for replayable experiments.

Example: repeated triage false positives or missed issues become sanitized
labeled regression cases. Change one procedure/rubric and compare held-out
precision and recall while guarding noise, safety, and cost. Do not tune only
to the reviewed sample, and preserve grader/human disagreements.

[Learning Loop Detection Patterns](learning-loop-patterns.md) can establish
Opportunity or Readiness from bounded episodes. Only the existing Learning
Capture [intervention-ledger contract](../../models/agent-work-loop.md#preserve-intervention-continuity)
can establish effectiveness from a
comparable later or held-out result without guardrail regression. Do not
create a second effectiveness ledger or treat the current task's tests as
proof of future improvement.

## Compose and Hand Off

- Scheduled inspection -> proactive discovery -> confirmation where required
  -> goal completion.
- Event response -> validate source, authority, current state, and idempotency
  -> bounded response or goal completion.
- Goal-completion traces -> system improvement -> versioned change -> later
  comparable evaluation.

Pattern names are not slash commands. `/schedule` and `/goal` are examples only
on hosts that expose them. This catalog defines no `/event`, `/proactive`, or
`/improve`, and does not restore the retired `proactive trigger` runtime.
GitHub Actions events and GitHub CLI reads illustrate scheduler and access
surfaces; other providers may fill the same slots.

## Concept Sources

- [Addy Osmani's Loop Engineering](https://addyosmani.com/blog/loop-engineering/):
  automation, worktree, Skill, connector/plugin, subagent, and state primitives.
- [LangChain's loop stack](https://www.langchain.com/blog/the-art-of-loop-engineering):
  agent, verification, event-driven, and hill-climbing layers; this catalog
  selects operating intent after owner selection.
- [GitHub Actions events](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)
  and [GitHub CLI](https://cli.github.com/manual/gh): provider examples.
