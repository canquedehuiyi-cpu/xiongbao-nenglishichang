# Skill Discovery Reference

Use this reference after `../loop-engineering/loop-discovery.md` decides `Create Skill` or
`Extend Skill`, when the user explicitly asks to evaluate known repeated work as a
Skill, or when the user asks for a session-informed profile of their
software-lifecycle Skill coverage. This reference does not choose among
automation, hooks, commands, custom agents, MCP, scripts, rules, or project
policy. Return new durable-owner questions to
`../loop-engineering/loop-discovery.md`. Use [Skill Quality Review](skill-review.md)
when the Skill already exists and the question is whether it is well written,
safe, efficient, or demonstrably effective.

## Contents

- [Core Idea](#core-idea)
- [Executable Onboarding Documentation](#executable-onboarding-documentation)
- [Inputs](#inputs)
- [Skill Coverage Check](#skill-coverage-check)
- [Session-Informed Lifecycle Coverage](#session-informed-lifecycle-coverage)
- [Bug-Diagnosis Skill Examples](#bug-diagnosis-skill-examples)
- [Analysis Loop](#analysis-loop)
- [Candidate Score](#candidate-score)
- [Skill Package Shape](#skill-package-shape)
- [Output Template](#output-template)
- [Quality Bar](#quality-bar)
- [Qoder Notes](#qoder-notes)

## Core Idea

A good Skill candidate has a stable reusable procedure with a trigger, input
context, repeatable steps, clear output, failure modes, and a validation path.
For a session-derived durable recommendation, require the same procedure across
at least two independent comparable Episodes. A single current handoff remains
a routing lead even when it is costly or well bounded. Do not create broad
Skills from noisy clusters or from a loop that is already covered by an
existing Skill.

Treat a Skill as packaged procedural knowledge for an agent to load at the
right time. A Skill can describe how to run a loop, collect evidence, validate
output, and hand off to automation, but it is not by itself runtime
persistence, tracing, approval handling, background scheduling, or external
system access.

Default to read-only analysis. Do not modify Qoder user-home state,
project settings, auth files, model catalogs, plugin caches, transcripts, or
repository files unless the user explicitly asks for implementation.

## Executable Onboarding Documentation

Onboarding is Skill-shaped when repository or environment inspection and
agent judgment connect setup, validation, and repair. This applies to local
project setup, maintainer-shipped library/API adoption, and internal platform
or design-system conventions. Keep deterministic setup in scripts and static
explanation in README/docs; a single install command does not need a Skill.

## Inputs

Start from the Loop Discovery evidence pack:

- target workspace, platform, and time window
- candidate loop name and repeated intent
- evidence refs such as session ids, reports, artifacts, prompts, commands, or
  changed files
- proposed decision: `Create Skill` or `Extend Skill`
- existing coverage and the missing Skill-owned behavior
- trigger, input context, output, verification, stop condition, and failure
  modes

For Agent Work Loop review, generated
`repositoryEvidence.workflowDemandDiagnostics` may supply a normalized current
handoff or repeated-work lead. Its fixed intent, family, coverage, and owner
fields come from deterministic aliases and patterns; treat them as recall and
routing metadata, never as the semantic workflow, capability relationship, or
recommended action. Reconstruct the procedure from bounded Episode evidence,
freeze it, and then compare actual capability content. A token, command name,
Skill name, catalog label, or machine action cannot enter the coverage ladder
without that Prompt review. A repeated candidate still returns to Loop
Discovery for owner selection before `Create Skill` or `Extend Skill`.
`owner-review` means unresolved only; it is not creation approval. Never bypass
a matching built-in, configured, observed, or extendable capability.

A single current handoff plus an empty or unresolved inventory is not an
uncovered workflow. In particular, `scanned-empty` records only the bounded
roots that were scanned, while a Qoder catalog label is routing metadata only.
Together they still require `Needs more evidence`; they cannot select a durable
Skill owner or support `Create Skill` or `Extend Skill`.

Keep an explicit user request to create or extend a concrete Skill as a separate
authorized implementation entry. Check existing coverage and scope, but do not
present that direct request as a session-derived recommendation or use it to
upgrade a single handoff, empty inventory, or catalog row into recurrence.

If no evidence pack exists, run `../loop-engineering/loop-discovery.md` first unless the user
explicitly asked for the session-informed lifecycle profile below. That profile
may return `Try Qoder built-in`, `Try configured Skill`, or
`Needs more evidence` without proving a new loop. Send uncertain owner or new
durable-workflow questions back to Loop Discovery before creating or extending
a Skill.

## Skill Coverage Check

Inspect only enough existing assets to avoid duplicate recommendations:

- repository-local shared and Qoder Skill stores
- user or plugin Skill packages when the task is about installed/global assets
- command or prompt aliases that invoke an existing Skill
- Skill references, scripts, assets, templates, and validation notes
- mirror metadata such as `.agents/skills/*/mirror.json` when present

Treat observed Skill use as coverage. Recommend `Extend Skill` only when the
evidence shows repeated manual setup, repair, validation, context collection,
or schedule handoff around that Skill.

## Session-Informed Lifecycle Coverage

Use this path only when the user asks to inspect their Skill use across
projects, find software-lifecycle coverage gaps, or recommend Skills from
global session history. It may recommend trying or creating a Skill, but it
does not turn every unobserved lifecycle stage into a new durable loop.

### Freeze the evidence boundary

Resolve `<cli>` through
[Harness Execution Routing](../../skills/better-harness/SKILL.md#step-1-resolve-scope-and-collect-the-evidence-bundle).

1. Run `<cli> session-analysis sources` with the target workspace first. Add
   `--include-global-capabilities` only because this workflow explicitly asks
   for a user-global profile.
2. Run bounded `facets` or `insights` with an explicit `--since`/`--until`
   window when available, `--selection stratified`, and a stated `--limit`.
   Record the eligible/analyzed counts and source gaps; do not silently present
   a latest-N sample as a complete history.
3. Load the Qoder Notes before classifying analyzer Skill signals,
   inferred reads, built-ins, or configured stores. Keep all of them separate
   from prose mentions. Machine lifecycle labels and aliases are recall leads;
   cluster the bounded requests and Episodes semantically before using them.
4. Run `<cli> agent-customize inventory` or
   `<cli> coding-agent-practices inventory --workspace
   <absolute-target-path> --format markdown` to collect
   configured personal, project, plugin, and built-in coverage.
5. Label each claim `workspace`, `user-global`, or `configured`. A capability
   absent from the bounded sample is `not observed`, not `missing`.

Do not expose raw prompts, commands, absolute home paths, or stable session ids
in the reader-facing profile. Cite bounded evidence refs in internal or review
artifacts only.

### Use two coverage axes

Do not rebuild a flat SDLC stage list. Map normalized capability aliases onto
two orthogonal axes:

| Axis | Coverage families | Common comparison vocabulary |
|---|---|---|
| Lifecycle artifacts | brainstorm/research, specify/clarify, plan/tasks, architecture/UX, release/incident, retrospective/standards | Spec Kit, OpenSpec, BMAD, and Agent OS workflows |
| Engineering disciplines | isolate/worktree, execute/delegate, TDD, systematic debugging, review, verification, branch completion | Superpowers and equivalent discipline Skills |

Treat those ecosystems as comparison vocabularies. A session using
`test-driven-development`, `/opsx:propose`, `speckit-plan`, or an equivalent
team Skill can cover a family without requiring a same-named platform Skill.
Look for observable workflow behavior and artifacts, not exact brand strings
alone.

### Project lifecycle coverage into Agent Work Loop

For the default Agent Work Loop combined review, inspect the practical handoffs
from goal/clarification through specification/planning, setup/isolation,
debugging/testing/verification, and review/acceptance/branch completion. Do not
require a generic coding or implementation Skill: the base agent already owns
ordinary code generation, and a Skill is useful only for non-obvious reusable
procedure.

Apply the observed -> platform built-in -> configured -> extend -> create ->
needs evidence ladder below. A session-derived `Create Skill` or `Extend Skill`
recommendation enters it only after semantic review establishes the same
procedure across at least two independent comparable Episodes.
Keep confirmed project activation, unscoped observed activation, apparent
reads, and configured presence as separate evidence classes; none substitutes
for another. Likewise, count built-in coverage only from an inspected,
host-scoped built-in catalog entry that matches the normalized workflow; the
presence of a slash-command token does not establish coverage.
One current-task handoff may route a bounded coverage review, but it cannot by
itself select a durable Skill owner. When at least two comparable Episodes
support the same repeated opportunity and inspected session plus inventory
evidence leaves such a family uncovered, project a supported, deduplicated
Learning Capture finding under `loop-engineering`. Without recurrence, keep the
observation as an unresolved current-task lead and do not emit a durable Skill
recommendation or finding. Group lifecycle gaps by causal chain rather than
emitting one finding per stage.
`Not observed`, an unavailable source, or a merely configured asset does not by
itself prove a gap. Covered or weak-evidence profiles create no finding.

Treat these as positive review leads, not automatic findings:

- observed planning or a non-trivial change with no canonical Spec workflow,
  when opened Skill coverage has no specification and acceptance-traceability
  procedure;
- observed branch/worktree setup, rebase or conflict recovery, review handoff,
  or branch completion with no matching Skill or built-in procedure.

The missing Spec document alone is not a Skill, and a lone `git status`, commit,
or other ordinary Git command is not a Git workflow. Recommend a new Skill only
for the smallest reusable procedure behind the evidenced handoff; never
recommend a generic `git`, `coding`, or whole-SDLC Skill.

### Select coverage before creation

Use this priority order for every coverage family:

1. **Covered — observed**: keep the observed Skill or equivalent Qoder
   capability and cite its evidence.
2. **Try Qoder built-in**: when a matching built-in is available but no similar
   workflow was observed, recommend one concrete trial and its success check.
3. **Try configured Skill**: when no Qoder built-in matches but an installed
   personal/project/plugin Skill already covers the family, recommend a bounded
   trial before declaring a gap.
4. **Extend existing Skill**: when personal/project/plugin coverage is partial,
   name the exact Skill and missing trigger, step, output, or validation.
5. **Create Skill**: when no built-in or installed Skill covers a stable
   Skill-shaped playbook, use Qoder's supported creation path
   instead of inventing a broad lifecycle package.
6. **Needs more evidence**: use this when the sample, demand, workflow shape,
   or validation path is too weak.

Customization Checkup may supply machine-selected routing candidates with
missing proof. They are not a coverage decision, trial, handoff, or finding.
Repeated friction still routes through Repeated Friction Triage and a semantic
Prompt or optional Skill Recommendation. A
current-task lifecycle review may describe the possible procedure, but a single
handoff cannot select `Create Skill` or `Extend Skill`. Re-run the ladder against
current observed, built-in, and configured content only after the independent
recurrence gate is satisfied.

### Create the Skill when authorized

Keep the default profile read-only. If the user only asks for analysis, return
a ready-to-use creation handoff containing the trigger, target workflow,
required context, output, validation, and one failure boundary.

If the user explicitly asks to create or extend a concrete Skill, treat that as
a separately authorized implementation request rather than a session-derived
recommendation. Use Qoder's supported creation workflow and
proceed without asking for another generic approval. Use personal scope for a
cross-project user workflow and project scope for repository-specific
conventions; ask once only when that boundary is genuinely ambiguous. Use the
host-native personal/project store reported by inventory.

Create the smallest useful package. Give the Skill a narrow verb-led name and
a description that states the triggering condition or state transition. Keep
`SKILL.md` navigation-sized, add scripts only for repeated deterministic work,
then validate discovery and run one representative dry-run or task check.
Never overwrite an existing or built-in Skill silently.

## Bug-Diagnosis Skill Examples

Use bug-topic session evidence only as a lead. For a session-derived repeated
opportunity, require at least two distinct comparable Task Episodes with the
same reusable reproduction or diagnosis need. Bug/error keywords, issue counts,
or repeated attempts inside one Episode do not establish recurrence.

Do not select a frontend or backend example from Session Evidence alone. Join
its Task Episodes or Insight Ledger with inspected Project Evidence using the
matching [project overlay](../project-harness/project-overlays.md), then use Agent Customize
evidence to check existing coverage. Only the lead may route the supported
candidate through Loop Discovery and the coverage ladder above.

| Supported procedure shape | Joined evidence | Smallest procedure |
|---|---|---|
| Browser or UI reproduction | GitHub Issue, Jira, Aone, or exported screenshots/video/comments plus a project-owned browser, component, E2E, WebView, IDE, or desktop route | Reproduce the observed UI failure through the project-owned route and record a verifiable result |
| Backend correlated diagnosis | Issue evidence plus a project-owned service/test/job route, readable logs or traces, and a stable request/trace/job/run id | Correlate a bounded failure with its request/trace/job/run and verify the diagnosis |

These procedure shapes are calibration examples, not built-ins, configured or
observed coverage, creation authorization, or a universal issue-solving Skill.
Compose any later authorized repair, validation, PR/MR, and review through the
[Goal Completion pattern](../loop-engineering/operating-patterns.md#goal-completion).

## Analysis Loop

Apply the entry conditions in [Inputs](#inputs) and the
[coverage ladder](#select-coverage-before-creation), then record the smallest
Skill boundary: trigger, user intent, required context, procedure, output,
validation, failure/handoff points, and external runtime dependencies.

Return **Covered by Skill**, **Extend Skill**, **Create Skill**, **Not a Skill**,
or **Needs more evidence**, naming the supporting owner or missing proof.
Non-Skill owners return to Loop Discovery. For an authorized implementation,
use [Create the Skill when authorized](#create-the-skill-when-authorized).

## Candidate Score

Use this compact scoring table before recommending Skill work:

| Field | Good signal | Weak signal |
|---|---|---|
| Demand | The same procedure is supported by independent comparable Episodes, or the user directly requests implementation of a concrete Skill | One isolated session-derived request, current handoff, or tool invocation |
| Skill fit | Reusable how-to workflow with judgment | Deterministic transform or policy check |
| Onboarding fit | README plus setup script plus environment-aware agent judgment | Single command or static setup notes |
| Stability | Same trigger, inputs, steps, and output shape | Different goal each time |
| Validation | Clear test, command, review, or artifact check | Success depends only on taste |
| Coverage | Missing or incomplete existing Skill coverage | Existing Skill already handles it |
| Scope | Narrow workflow a first `SKILL.md` can own | Whole product area or vague theme |
| Evidence | Session/report/repo facts align | Only cache names, counts, or guesses |

For medium-confidence items, output `needs more evidence` with the exact
missing proof.

## Skill Package Shape

Keep `SKILL.md` limited to trigger, workflow, output, validation, and routing.
Add references for conditional detail, scripts for repeated deterministic work,
and assets for reusable output resources only when needed. For an extension,
name the existing file and missing trigger, step, reference, validation, or
handoff; do not scaffold a duplicate package.

Resumable state, scheduling, approvals, tracing, external access, and multi-run
storage remain runtime responsibilities. After Loop Discovery selects an owner,
use [Loop Primitives](../loop-engineering/runtime-contracts.md#primitives),
[Automation Readiness](../loop-engineering/runtime-contracts.md#automation-readiness), or
[Loop State Ledger](../loop-engineering/runtime-contracts.md#state-ledger) for its contract.

## Output Template

Report the target, bounded evidence, candidate procedure, mode (read-only or
creation authorized), inspected coverage, chosen action, and missing proof.
For a lifecycle profile, compare only relevant families:

| Axis / capability | Observed use and scope | Inspected built-in or configured owner | Decision and evidence | Next validation |
| --- | --- | --- | --- | --- |
| … | workspace / user-global / not observed | … | Keep / Try / Extend / Create / Needs evidence | … |

Include implementation handoffs only for supported Create/Extend decisions;
omit empty action sections. Describe the smallest next validation in prose.
Keep private evidence identifiers out of reader-facing output as required by
[the evidence boundary](#freeze-the-evidence-boundary).

## Quality Bar

Use [Candidate Score](#candidate-score) to check demand, fit, stability,
validation, coverage, scope, and evidence. Apply the coverage ladder before
creation; keep activation, inferred reads, configured presence, and built-in
availability distinct. For onboarding, cite the README/scripts/platform owner
that the agent's judgment complements. A missing Spec document or ordinary Git
command does not establish a reusable Skill workflow.

## Qoder Notes

Read Qoder `topSkills` as observed Skill activation. Prove the current product
surface from host inventory. In a Qoder source checkout, the embedded built-in
owner is `chat/agents/tool/skill/builtin_skills/` plus its loader, not repository-local
`.qoder/skills` or `.agents/skills`.

- `~/.qoder/skills` and `~/.agents/skills` are personal stores;
  `<repo>/.qoder/skills` and `<repo>/.agents/skills` are project stores. They
  can supplement the product surface, but they are not Qoder built-ins. The
  current loader gives an embedded built-in precedence over a same-named
  personal or project Skill; do not promise a same-name override.
- Separate globally visible, mode-restricted, feature-gated, command,
  agent-private, and subagent-private surfaces. Load the current catalog row,
  runtime discovery, and actual bounded instructions for plausible candidates;
  never infer invocability from a remembered product name or example.
- A built-in command can be observed workflow coverage without being a
  `SKILL.md`. An agent-private Skill routes to its owning Agent rather than the
  main session. Neither relationship may be inferred from a lexical match.

For **Try Qoder built-in**, apply the shared
[coverage ladder](#select-coverage-before-creation) using host-scoped discovery.
For an authorized Create decision, use Qoder's built-in `create-skill` and the
personal/project store reported by inventory. A catalog row alone does not
establish availability or authorize creation.

Do not keep a Prompt-level list of preferred Qoder capabilities. After the
semantic pattern is frozen, route only plausible rows from the current catalog
and compare their bounded instructions and current runtime context. A catalog
label may increase recall; it never supplies the recommendation.

Use current host-provided capability metadata for mode, provenance, and
lifecycle mappings. A Qoder Platform SDLC Capability Catalog, if supplied by
the user or host, is optional reference material; no bundled catalog is required. Treat the
product runtime repository as partial Qoder provenance, not as a separate
platform. The catalog is routing and provenance metadata, not proof of current
availability. Current runtime discovery may establish availability; explicit
task-linked activation proves use, and outcome evidence is still required
before calling it effective.
Project the catalog by current surface. IDE, CLI, SDK, main-agent, and subagent
discovery are not interchangeable; current runtime discovery wins, including
an explicitly disabled or unavailable row. If discovery was not collected,
declare that omission instead of treating catalog presence as availability.
Catalog metadata cannot substitute for the bounded capability instructions
needed by Skill Recommendation.
For retained-session evidence, use the bounded `session-analysis` facts and
usage-summary routes. Treat catalog rows as maintained product metadata; do not
infer use merely because a prompt or tool result advertised or mentioned a
Skill.

For every stable repeated-workflow candidate, compare meaning against the
actual content of plausible relevant Skills, built-ins, and project owners in
the bounded authorized scope. Suggest Qoder-native `/create-skill <workflow
description>` only when that content-backed comparison supports no complete or
extendable owner. Uninspected or unavailable content is unknown, and inventory
count never changes the decision. Keep the description concrete: trigger,
target workflow, required context, output, validation, and one failure boundary.

For a single current Qoder handoff, an empty or unresolved scan and a matching
catalog row still yield `Needs more evidence`; the row may route later semantic
comparison but cannot recommend a durable Skill. If the user instead explicitly
asks to create a concrete Skill, handle that independent authorization through
Qoder's built-in `create-skill`. Use the host-native personal/project store
reported by inventory and never overwrite an existing or built-in Skill
silently.
