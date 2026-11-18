# Loop Runtime Contracts

Read only the section selected by the calling workflow; co-location does not
combine their entry conditions or authorize another mode.

- [Primitives](#primitives)
- [Automation Readiness](#automation-readiness)
- [State Ledger](#state-ledger)

## Primitives

Use this after `loop-discovery.md` proves a loop candidate but the durable
building blocks are still unclear. Keep the decision owner-focused: primitives
are ingredients, not answers by themselves.

### Primitives: Primitive Map

| Primitive | Use when | Better Harness owner |
|---|---|---|
| Automation | The trigger is scheduled or event-like and each run can start from stable input | `runtime-contracts.md#automation-readiness`, then host automation |
| Worktree | More than one agent or run may write files, or background work must not touch active local edits | Git/worktree policy plus selected loop owner |
| Skill | The durable asset is procedural knowledge, examples, references, scripts, or validation steps | `../agent-customize/skill-discovery.md` |
| Plugin / Connector | The loop must be installed across repos or access external systems | Plugin packaging or MCP-backed access after an owner exists |
| Subagent | Independent exploration, maker/checker review, or parallel evidence collection is valuable | Custom Agent/Subagent route |
| State | The loop spans turns, days, runs, worktrees, or external systems | `runtime-contracts.md#state-ledger` |

### Primitives: Selection Rules

- Prefer one primary owner and only the primitives needed to make it reliable.
- Use automation for the heartbeat, not for broad judgment.
- Use worktrees when file isolation is the main risk; do not use them as a
  substitute for review.
- Use Skills for reusable procedure; do not use them as runtime memory,
  scheduling, approval, or tracing infrastructure.
- Use plugins only after the canonical Skill, hook, script, agent, or reference
  is stable enough to distribute.
- Use MCP/connectors as access layers. The workflow owner still needs trigger,
  input, validation, stop, and safety contracts.
- Use subagents when the split improves evidence quality, not merely to make a
  task sound more autonomous.
- Use state ledgers when the next run must know what already happened.

### Primitives: Output Addendum

When Loop Discovery needs primitive detail, add this compact line to the result:

```text
Primitives: primary=<owner>; support=<automation|worktree|skill|plugin|connector|subagent|state>; why=<one sentence>
```

If no primitive is needed beyond the selected owner, say so explicitly.

## Automation Readiness

Use this after `loop-discovery.md` selects automation, `schedule-ready`, or a
scheduled/background loop. This file does not create automations; it defines the
minimum contract before a report or skill recommends one.

### Automation Readiness: Readiness Gate

Recommend automation only when all fields are concrete:

1. **Target**: repository, path, issue, PR, report artifact, or external object.
2. **Trigger**: cadence, cron-like schedule, event, or one-time follow-up.
3. **Run scope**: standalone fresh run or thread-attached continuation.
4. **Execution location**: local checkout, background worktree, CI, or external
   host; name why this location is safe enough.
5. **Input pack**: exact command, prompt, report row, finding id, artifact,
   query, or MCP resource the run starts from.
6. **Sandbox**: read-only, restricted write, full access, or explicit human
   approval for side effects.
7. **Validation**: command, report quality check, CI result, review result,
   trace/eval comparison, or `needs more evidence` outcome.
8. **Triage path**: where findings land and who reviews them.
9. **Risk boundary**: files, systems, credentials, external writes, and
   destructive actions the automation must not touch without approval.
10. **Stop condition**: state, count, date, score, passing validation, repeated
    covered result, or human decision that ends the loop.

If any field is missing, return `needs more evidence` or recommend a one-time
manual follow-up instead of recurring automation.

### Automation Readiness: Automation Shapes

- **Standalone automation**: use when each run should start fresh from stable
  inputs and report findings into triage.
- **Thread automation**: use when the scheduled work must preserve the current
  conversation or approval context.
- **Background worktree**: use when the run may write files and must avoid
  unfinished local edits.
- **Local checkout**: use only when direct access to the current workspace is
  required and the write risk is acceptable.
- **CI/GitHub Action**: use when the loop is tied to repository events,
  protected checks, or branch policy.

### Automation Readiness: Output Addendum

For schedule-ready outcomes, fill these slots:

```text
Automation readiness: target=...; trigger=...; run scope=...; location=...;
input=...; sandbox=...; validation=...; triage=...; risk=...; stop=...
```

Do not call generic improvement advice automation-ready.

## State Ledger

Use this when a loop may pause, resume, recur, run in the background, span
worktrees, or hand off between agents. The state ledger is the durable memory of
the loop; it is not raw transcript storage.

### State Ledger: When State Is Required

Require a ledger when any condition is true:

- The next run must know what was already tried.
- A schedule or background worker may run without the original conversation.
- Multiple agents, worktrees, or external systems share one loop.
- A human can approve, reject, edit, or defer a side effect.
- The loop compares results across runs, scores, findings, traces, or evals.
- The stop condition depends on previous outcomes.

If the loop is purely stateless, say what fresh input fully determines each run.

### State Ledger: Ledger Locations

Choose the smallest durable location:

| Location | Use when | Avoid when |
|---|---|---|
| Markdown note | Human-readable triage, plans, or next steps are enough | Machine replay or concurrent writes are required |
| Run directory | Reports, validation output, screenshots, or generated artifacts need evidence | The loop only needs one current status |
| JSON sidecar | A script or validator must consume the state | Humans must edit it frequently |
| Issue / PR / tracker | The loop is tied to external review, ownership, or status | External access is unavailable or unverified |
| Memory | A reusable lesson or preference is explicit and safe to persist | It contains raw transcripts, secrets, or one-off state |

### State Ledger: Ledger Fields

Use only fields the next run needs:

- loop id or finding id
- target path, repo, issue, PR, or artifact
- owner and supporting primitives
- trigger and cadence
- current status: open, paused, covered, blocked, skipped, or done
- last run time and evidence refs
- actions attempted and validation result
- risk boundary and approval status
- next input or next command
- stop condition and stop evidence

### State Ledger: Privacy And Safety

- Store references to evidence instead of raw private transcripts.
- Redact secrets, tokens, credentials, customer data, and private tool output.
- Keep approvals as decisions and reason codes, not long copied discussions.
- Treat external tracker state as unverified unless opened or provided.
- Keep generated state out of source control unless the repo intentionally
  tracks that artifact.

### State Ledger: Output Addendum

When state is required, add:

```text
State ledger: location=...; fields=...; update rule=...; privacy boundary=...;
resume input=...; stop evidence=...
```
