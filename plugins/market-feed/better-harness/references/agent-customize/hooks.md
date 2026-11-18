# Agent Hooks

Select only the section relevant to the current task; shared storage does not
combine authority or require every procedure.

- [Design and Installation](#design-and-installation)
- [Configuration and Performance Review](#configuration-and-performance-review)

## Design and Installation

Use this reference when Qoder runtime hooks are in scope. For Git commit and
push hooks, use
`../project-harness/git-hooks.md`.

For an explicit customization cleanup, duplicate-registration review, failure
diagnosis, or latency budget, first use
[Hook Configuration And Performance Review](hooks.md#configuration-and-performance-review); return here only
after the remediation form and lifecycle owner are clear.

### Design and Installation: Core Idea

Treat agent hooks as the deterministic constraint layer around an agent loop,
not as another prompt. Prompts, Rules, `AGENTS.md`, Skills, and references guide
the model. Hooks run at lifecycle points to block, approve, log, validate, or
inject bounded context.

The durable ownership split is:

- **Rules / AGENTS.md**: explain stable project facts and soft constraints.
- **Permissions / Sandbox**: set hard access boundaries.
- **Hooks**: inspect lifecycle events and enforce deterministic decisions.
- **Skills**: describe the safe workflow, remediation, or exception process.
- **Scripts**: own parsing, policy checks, formatting, and validation logic.
- **CI / policy services**: rerun critical checks and provide final backstop.

Do not put broad workflow prose inside hook wrappers. A hook should call a
stable script or policy service and return a narrow allow, deny, ask, feedback,
or context result.

### Design and Installation: Lifecycle Strategy

| Lifecycle point | Typical names | Good use | Avoid |
|---|---|---|---|
| Prompt submit | `UserPromptSubmit`, `beforeSubmitPrompt` | secret, customer-data, environment, and prompt-shape screening | rewriting the whole user request |
| Before tool use | `PreToolUse`, `beforeShellExecution`, `beforeMCPExecution`, permission events | block destructive commands, protected paths, risky MCP calls, external-state writes, unknown package installs | broad auto-allow matchers |
| After tool use or file edit | `PostToolUse`, `afterFileEdit`, failure events | formatting, linting, dependency scans, advisory feedback, structured logging | relying on post hooks to undo side effects |
| Stop or handoff | `Stop`, `SubagentStop`, handoff gates | verify tests, required evidence, protected-file review, generated-artifact checks | blocking without a clear next command or fix path |
| Session start or resume | `SessionStart`, compact/resume hooks | inject current branch, workspace, issue, test command, and policy context | loading long static docs on every session |

Use the earliest lifecycle point that can make the decision safely. Pre hooks
are for blocking or approval. Post hooks are for observation, repair feedback,
and validation after a change. Stop hooks are for final readiness gates.

### Design and Installation: Session-To-Hook Promotion

Do not add broad hooks from theory alone. Promote repeated session evidence into
hooks through this loop:

```text
session log -> normalized events -> recurring risk pattern -> earliest safe
lifecycle point -> fixture replay -> log-only/warn/ask/block
```

Use `log-only` or advisory output for noisy quality signals. Use `ask` or
`block` only when the signal is deterministic, the false-positive cost is
acceptable, and the message gives the next safe action.

### Design and Installation: Secret Guard Pattern

Secrets need layered hooks because leakage can happen before the model, during a
tool call, or in a written diff:

- `UserPromptSubmit`: block likely keys, tokens, passwords, private keys, and
  credential dumps before the model sees them.
- `PreToolUse`: block credential-file reads, environment dumps, raw kubeconfig
  output, and commands containing literal secrets.
- `PostToolUse` or `Stop`: scan changed files or diffs before continuation,
  commit, handoff, or final response.
- Session/audit output: store redacted metadata only; never store raw prompt,
  command, transcript, secret value, or unredacted tool output.

Never send a suspected secret to another LLM for classification. Use a
deterministic scanner and print only a rule id, severity, hash/fingerprint, or
redacted preview.

Resolve `<cli>` through
[Harness Execution Routing](../../skills/better-harness/SKILL.md#step-1-resolve-scope-and-collect-the-evidence-bundle).

Better Harness provides a copyable starting point:

```bash
<cli> guardrails install-secret-guard --target <project>
```

This installer copies the standalone `scripts/agent-guardrails/secret-scan.mjs`
and `scripts/agent-guardrails/qoder-hook.mjs` into the target project and merges
`UserPromptSubmit` plus `PreToolUse` Qoder hook
configuration. The direct Qoder hook owner defines config paths, event
contracts, generated commands, and runtime block payloads.
Use `--check --json` to detect copied-runtime or hook-config drift without writing
files. Use it as an AI Fix when session analysis finds user-pasted credentials,
agent-initiated credential reads, or absent secret hook coverage.

### Design and Installation: Implementation Contract

- Prefer deterministic command hooks or local scripts for stable policies.
  Use LLM/prompt hooks only for judgment-heavy advisory work.
- Keep matchers narrow by tool, command family, path, event type, or host.
- Normalize host event payloads into an internal schema before applying policy:
  `event`, `tool`, `cwd`, `path`, `commandHash`, `decision`, `reasonCode`,
  `durationMs`, `exitCode`, and `sessionId`.
- Render Qoder hook output at the runtime edge without duplicating policy.
- Log structured metadata by default, not raw prompts, secrets, environment
  variables, command output, file contents, or private transcripts.
- Make denial messages short and actionable: name the policy, blocked target,
  and smallest safe next step.
- Validate hooks with fixture JSON, unit tests for the policy module, and at
  least one real host event sample before claiming runtime enforcement.

For cross-platform repositories, prefer Node.js or Python entrypoints over
shell-only scripts. Resolve paths from the repository root, handle Windows path
separators, quote shell arguments when a shell is unavoidable, and avoid host
commands that only exist on one operating system.

### Design and Installation: Security And Trust Rules

Treat hook input as untrusted external data. Validate event shape, clean command
strings before display, reject path traversal, resolve symlinks when path policy
matters, and skip sensitive files such as `.env`, credentials, tokens, private
keys, and VCS internals.

A pre-tool hook is not a complete security boundary by itself. Pair it with
host permissions, sandbox policy, CI, branch protection, or central policy
services when the risk involves credentials, production systems, destructive
commands, external writes, or release actions.

Review hook configuration like executable code. Any project-level hook config,
managed hook, central policy wrapper, or host trust file should have a clear
owner, review path, and drift check. If a host requires hook trust review, treat
that review as part of the release process.

### Design and Installation: Evidence Rules

Separate these evidence levels in reports and readiness reviews:

- **Configured**: hook settings or wrapper files exist.
- **Policy content**: the script or policy logic was inspected.
- **Tested**: fixture tests or unit tests exercise the policy.
- **Observed**: a real host event sample shows the hook ran.
- **Backstopped**: CI, branch protection, sandbox, or policy service also
  enforces the same critical rule.

Do not claim enforcement from static configuration alone. Static config plus
no event sample is a presence/content signal, not runtime proof.

### Design and Installation: Host Notes

Use `qoder.md` for Qoder event names, matchers, stdin JSON shape,
exit-code behavior, and official examples.

### Design and Installation: Review Checklist

- The policy is deterministic, narrow, and tied to a lifecycle point.
- The hook calls a stable script or central policy service.
- The same critical rule has a CI, sandbox, permission, or policy backstop when
  the risk is high.
- The implementation is cross-platform or explicitly host-scoped.
- The failure message tells an agent what to run, inspect, or ask next.
- Tests cover allow, deny, malformed input, protected paths, and sensitive-file
  cases.
- Reports separate configured hooks, inspected content, tests, observed runtime,
  and backstop evidence.

### Design and Installation: External Anchors

These sources are background. Local Better Harness routing and repository tests win
when they disagree.

- Qoder hooks documentation: https://docs.qoder.com/extensions/hooks

## Configuration and Performance Review

Use this reference for an explicit Customization Checkup or hook-performance
request. Use [Agent Lifecycle Hooks](hooks.md#design-and-installation) for hook design and
implementation practice.

### Configuration and Performance Review: Inspection Contract

Inventory project, user/global, enterprise-plugin, normal-plugin, and local
hook sources. Preserve, when visible:

- lifecycle event;
- matcher;
- handler type and sanitized command identity;
- timeout;
- `if` condition;
- `async` state;
- source scope and plugin owner.

Configuration proves only that a hook is wired. Runtime claims require session
or host-log evidence.

Ordinary Better Harness source generation runs the read-only asset-integrity
pass. It can report more than 10 enabled Hooks, exact full-configuration digest
duplicates, and event-plus-matcher fan-out that reaches the existing static
review threshold. These are configuration observations, not proof of latency,
failure, or one command's runtime cost. Use explicit Customization Checkup for
runtime attribution, p95, failure evidence, and cleanup eligibility.

### Configuration and Performance Review: Runtime Attribution

For session evidence:

- `hook.started` may carry event, source, index, and command identity;
- `hook.finished` carries completion, success/failure, and `duration_ms` when
  the runtime emits them;
- one finished event counts as one execution; do not double-count its start;
- join start/finish only through stable source/index/invocation evidence;
- when parallel hooks finish without identity, attribute latency to the hook
  event group, not to one command.

Plaintext Qoder hook logs may add per-command duration when available. Missing
logs lower attribution confidence; they do not fail the scan. Never replay a
hook merely to benchmark it because hooks can write files, call networks, or
block lifecycle actions.

### Configuration and Performance Review: Initial Diagnostic Budgets

Use configurable budgets as review triggers, not universal performance scores:

- high-frequency Pre/Post tool hooks: p95 at or below 500 ms;
- prompt, session, and Stop hooks: p95 at or below 2 s;
- command-specific slow findings: at least five attributable finished samples.

Timeouts, repeated failures, duplicate registrations, and unnecessarily broad
high-frequency matchers are independent findings even when latency samples are
insufficient.

### Configuration and Performance Review: Finding States

- `configured-only`: static hook exists; no runtime window was requested.
- `observed`: at least one execution is attributable.
- `healthy`: observed results remain inside configured budgets without repeated
  failures or duplicates.
- `candidate`: evidence supports a specific narrow remediation.
- `unavailable`: completion identity or duration cannot be safely attributed.

Do not name one command as slow when only group-level timing exists.

### Configuration and Performance Review: Remediation Order

Prefer the smallest safe move:

1. narrow a matcher or lifecycle event;
2. remove a duplicate registration;
3. eliminate redundant repeated work;
4. make a purely observational non-blocking hook async when the host contract
   supports it;
5. increase or split timeouts only after inspecting the work;
6. disable only through a confirmed owner plan.

Never convert security, permission, approval, or blocking hooks to async only
to improve latency. Never patch plugin caches. Plugin-owned hooks are repaired
through the plugin owner unless a supported per-hook override exists.

### Configuration and Performance Review: Verification

After an approved change, reparse the owning source, run the smallest safe
fixture/parser check, and distinguish disk/config success from runtime reload.
A new session or host refresh may still be required before the new behaviour is
`Observed`.
