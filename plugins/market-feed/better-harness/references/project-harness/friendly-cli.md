# Friendly CLI Protocol for Agents

## Purpose

Review agent-facing CLIs as versioned protocols: command selection, scoped
invocation, observable results, and safe recovery. Use this reference when
JSON output still leaves prompts, ambiguous targets, unbounded output, opaque
failures, or unsafe retries; apply mutation and long-operation sections only
when the command has those effects.

Keep executable behavior with its capability owner and use portable argv
arrays, paths, and stream handling across Windows, macOS, and Linux. The `--agent` mode and envelopes below
are design recommendations, not claims about the current Better Harness CLI.

## Load When

Use for CLI design/review or when CLI, Skill, MCP, documentation, and tests
have conflicting capability semantics.

## Protocol Layers

| Layer | Contract to inspect |
| --- | --- |
| Selection | Purpose, use/avoid conditions, limits, effects, progressive discovery |
| Invocation | Typed inputs, resolved context, permissions, timeout |
| Observation | Versioned results/events, actual effects, warnings, artifacts, verification |
| Recovery | Stable errors, retry safety, remediation, operation identity, compensation |

## Nine Design Patterns

The sections below cover task-oriented commands, progressive discovery,
explicit agent mode, typed input, explicit context, bounded output, structured
results, recoverable errors, and safe mutation. Use the
[contract test matrix](#contract-test-matrix) to assess them without a second
checklist. This is a synthesized design; external sources support individual
parts rather than one combined protocol.

## Task-Oriented Commands and Progressive Discovery

Model the smallest stable task, not the transport topology. A command should
return a useful task result rather than force an agent to discover and compose a
long sequence of endpoint-shaped commands. Keep low-level API access as an
advanced escape hatch when it remains necessary.

Offer discovery in layers:

```text
tool capabilities --agent
tool command describe logs.search --agent
tool schema logs.search --agent
tool examples logs.search --agent
```

The initial capability and command descriptions should be short enough for
selection. Put the complete argument contract in the schema and load examples
only after selection. A compact descriptor can use this shape:

```yaml
name: logs.search
purpose: Search bounded logs that match known criteria.
use_when: A keyword, time range, trace ID, or request ID is known.
do_not_use_when: The task needs an unbounded live subscription.
returns: Matching rows, small surrounding context, result count, and next cursor.
limitations: Scans at most 24 hours and returns 50 rows by default.
effects:
  read_only: true
  destructive: false
  idempotent: true
  open_world: false
```

Keep selection descriptions compact; load schemas, policy, and examples after
selection. Evaluate task success alongside calls, steps, and context cost;
more description is not automatically better. See the description-quality
study in [External Anchors](#external-anchors) for supporting research.

## Explicit Agent Mode

`--agent` should be a documented compound mode, not a hidden collection of
terminal heuristics:

| Concern | Recommended `--agent` behavior |
| --- | --- |
| Interaction | Never prompt; either use documented defaults or return `INPUT_REQUIRED` with all missing arguments |
| Output | Emit one JSON result or a documented JSONL event stream |
| Presentation | Disable ANSI, tables, spinner frames, progress animation, and decorative status output |
| Bounds | Apply documented default fields, result limit, timeout, and maximum inline bytes |
| Context | Resolve and echo the actual account, project, region, cwd, target, and revision when relevant |
| Failure | Emit a structured error result and a non-zero coarse exit code |
| Diagnostics | Keep parser output on stdout and operational logs on stderr; provide an opt-in debug artifact for deeper diagnostics |

Keep granular flags such as `--non-interactive`, `--output json`, `--no-color`,
`--quiet`, `--limit`, and `--timeout` for humans and existing automation.
`--agent` can normalize them into one supported contract. Explicit conflicting
flags should fail fast instead of silently degrading machine output.

Agent-environment detection may choose presentation defaults, but it must not
infer an account, target, permission, confirmation, or mutation scope. An
explicit `--agent` flag remains the auditable source of protocol selection.

## Typed Input and Resolved Context

Publish JSON Schema or an equivalent type contract for every command input:

- Mark required fields and distinguish omitted, empty, and null values.
- Use enums for closed choices and formats for timestamps, durations, IDs,
  paths, URIs, revisions, and hashes.
- Document defaults in the schema and return the resolved values in context.
- Accept simple scalar values as flags; accept complex objects through
  `--input <file>` and `--input -` for stdin.
- Validate the complete input before starting side effects and return every
  correctable validation error in one response when practical.
- Never return secrets, raw credentials, environment values, authorization
  headers, or sensitive input fields in context, logs, artifacts, or errors.

Define one context precedence rule, for example:

```text
explicit flag > input document > environment/config > cwd-derived default
```

Return the resolved source and value for operational context. If two sources
conflict, or a high-risk target was inferred rather than supplied, return a
structured ambiguity or confirmation error before any effect.

## Token-Bounded Results

Every list, search, log, diff, scan, or artifact-producing command needs an
output budget:

- `--fields` selects stable fields before serialization.
- `--limit` has a safe default and a documented maximum.
- `--filter` or task-specific predicates reduce the source set before output.
- `--cursor` consumes an opaque cursor; clients must not parse or synthesize it.
- `--detail concise|standard|detailed` chooses a documented projection, not an
  arbitrary verbosity level.
- Large content returns a summary, bounded preview, and artifact reference with
  media type, size, digest, and retention information when known.

When output is truncated, say so explicitly and return `next_cursor`. Never
silently omit rows. An empty query result is a successful empty collection, not
an exception:

```json
{
  "status": "success",
  "data": { "items": [] },
  "page": {
    "returned": 0,
    "truncated": false,
    "next_cursor": null
  }
}
```

Stable ordering is part of pagination correctness. Define the sort key and
tiebreaker so retries and page transitions do not duplicate or skip entries.

## Success Result Envelope

Return schema-governed facts and a short summary. A compact illustrative
result (not the current Better Harness schema):

```json
{"schema_version":"1.0","status":"success","summary":"Closed issue BUG-142","context":{"project":"payments"},"data":{"id":"BUG-142","state":"closed"},"effects":[{"resource":"issue/BUG-142","action":"update","changed_fields":["state"]}],"verification":{"passed":true,"checks":[{"name":"issue.state","expected":"closed","actual":"closed","passed":true}]},"warnings":[],"artifacts":[],"request_id":"req_123"}
```

| Field | Meaning |
| --- | --- |
| `summary` | Orientation; never the fact source |
| `data` | Stable result facts |
| `context` | Resolved target/environment with sensitive values removed |
| `effects` | Observed mutations, not planned effects |
| `verification` | Checked postconditions; use `passed: null` with `not_run`/`unavailable` when unchecked |
| `warnings` | Nonfatal limits that affect interpretation |
| `artifacts` | Typed references for large or sensitive content |
| `request_id` | Correlation and operation lookup |

Success means the declared postconditions are met. Partial or unknown effects,
failed verification, or mere remote acceptance need an error preserving known
effects or a documented `partial`/`accepted` state. Use additive minor changes,
ignore unknown optional fields, reject unsupported major versions, and never
reuse field names with different semantics.

## Recoverable Error Envelope

Return a stable code/category, safe message, retry semantics, and constrained
remediation, for example:

```json
{"schema_version":"1.0","status":"error","error":{"code":"AUTH_EXPIRED","category":"authentication","message":"Authentication expired.","retryable":false,"safe_to_retry":false,"remediation":[{"action":"auth.login","args":{"account":"acme"},"requires_user":true}]},"request_id":"req_123"}
```

Distinguish validation, authentication/authorization, not-found, conflict,
precondition, rate-limit, timeout, partial-failure, and internal errors as
needed. `retryable` means a stated remediation may make the condition succeed;
`safe_to_retry` means repeating this invocation cannot add or duplicate effects
under its operation/idempotency contract. A remote-write timeout may satisfy
only the first: inspect the operation before replay.

Preserve observed and unknown partial effects, verification state, and a
compensation/support path. Keep redacted stack traces and raw transport details
in opt-in diagnostics; agents should not parse prose to recover.

## stdout, stderr, Exit Codes, and Time

In agent mode:

- stdout contains exactly one JSON object, or a documented JSONL stream with
  one object per line.
- stderr contains operational logs and debug diagnostics, never the only copy
  of a machine-actionable error.
- exit code represents coarse success or failure; `error.code` provides the
  stable fine-grained reason.
- exit code, terminal JSON status, and terminal event must agree.
- timestamps use RFC 3339 / ISO 8601 UTC with a `Z` suffix; durations use a
  named unit such as `duration_ms`.
- no-result queries exit successfully with an empty collection.
- ANSI escapes, table borders, spinner frames, and animated or decorative
  status output never enter the machine stream.

Document a small stable exit-code table for the product. At minimum, keep `0`
for protocol success, a separate invocation/validation bucket, and one or more
runtime failure buckets. Do not assign every `error.code` its own process code;
many shells and hosts reduce or reinterpret large exit-code ranges.

## Long-Running Operations and JSONL

For builds, scans, deployments, or imports, use a versioned JSONL stream or a
durable operation handle with status, wait, cancel, and result retrieval.
Each event needs schema version, type, operation ID, monotonic sequence, and
timestamp; include resource/phase identity when concurrent events interleave.

```jsonl
{"schema_version":"1.0","type":"operation_started","operation_id":"op_123","sequence":1,"timestamp":"2026-07-17T08:00:00Z"}
{"schema_version":"1.0","type":"operation_completed","operation_id":"op_123","sequence":2,"timestamp":"2026-07-17T08:00:30Z","status":"success"}
```

The first event identifies protocol/operation versions. Completed streams need
a terminal event; an interrupted stream is not success. Progress may have an
unknown total but must not go backward within a phase. Support reconnect using
operation identity or a sequence cursor without restarting effects. Cancellation
reports what stopped and which effects remain; it is not rollback. Ignore
compatible unknown events/fields and reject unsupported major versions.

Terraform's machine-readable UI is a JSONL precedent; these example events are
not its schema. Negotiate version/capability support for MCP task-augmented
execution rather than assuming it exists in every client.

## Mutation Protocol: Plan, Apply, Verify, Recover

State-changing commands need a stricter contract than queries:

```text
tool deploy plan --input request.json --agent
tool deploy apply --plan-id plan_123 --expect-hash abc123 --idempotency-key task_456 --agent
tool operation wait op_789 --timeout 60s --agent
```

The plan should return:

- resolved target and context;
- proposed effects and unchanged resources;
- risk, permission, approval, and irreversibility markers;
- source and target revision or state hash;
- a stable `plan_id`, digest, expiry, and schema version;
- preconditions, verification checks, and recovery options.

Apply consumes the exact plan rather than reinterpreting natural language. It
must reject expired plans, target mismatches, digest changes, failed
preconditions, or insufficient approval before starting an effect.
`--expect-hash` or an expected version prevents a lost update when state has
drifted since planning.

Bind an idempotency key to the authenticated principal, command, target, and
canonical input digest. Reusing the key with different inputs returns an
idempotency conflict. Document the retention window and whether a repeated call
returns the original result or an operation lookup. An idempotency key enables
safe replay only for the effects covered by that implementation; it does not
make every failure safe to retry.

Verification returns the actual postcondition and observed effects. When the
command cannot verify, it should return `verification: unavailable` and a
bounded next command rather than report success from process completion alone.

Rollback is only one recovery shape. Also model retry, resume, cancellation,
compensation, restore, and safe abort. Use
[Rollback and Recovery Evidence](change-safety.md#recovery-evidence)
when evaluating a concrete project's recovery mechanism.

Delete, publish, payment, production deployment, permission changes, and other
high-impact operations need command-specific approval and policy. A generic
`--yes` may acknowledge an already bounded plan; it must not bypass
authorization, target checks, drift checks, irreversible-operation policy, or
required human approval.

## One Command Contract, Multiple Surfaces

Give command identity/purpose, use/avoid conditions, input/context, result/event
schemas, effects, errors, permissions, recovery, examples, and contract tests
one semantic owner. Generate or validate CLI help, discovery/schema, Skill
instructions, MCP definitions, docs, and fixtures against it. Generation is
optional; drift checks are not. A Skill may add sequencing and judgment but
must not redefine command inputs, effects, or error meaning.

## MCP Projection

Map the Command Contract to MCP vocabulary when an MCP surface is appropriate:

| Command Contract | MCP tool surface |
| --- | --- |
| Purpose and short selection text | Tool `name`, `title`, and `description` |
| Typed input | `inputSchema` |
| Structured result | `outputSchema` and `structuredContent` |
| Effect classification | `readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint` |
| Long-running policy | `execution.taskSupport` plus negotiated Tasks capability |

MCP annotations are hints, not a trusted enforcement boundary. Validate
permissions, target context, preconditions, approvals, and effects in the
runtime. The current MCP Tasks facility is experimental, so retain version and
capability negotiation rather than assuming universal client support.

## Contract Test Matrix

Test the protocol, not only the happy-path business behavior:

| Area | Minimum evidence |
| --- | --- |
| Selection | A task can choose the intended command from compact descriptions and reject a nearby wrong command |
| Discovery | Capability, description, schema, and example surfaces work without source reading or mutation |
| Non-interaction | Agent mode never prompts, opens a browser, or waits indefinitely for stdin |
| Parser safety | Success and failure stdout parse as one JSON value or valid JSONL; no ANSI or progress text leaks |
| Validation | Missing and invalid arguments return all safe-to-disclose corrections with no effects |
| Context | The resolved account, project, region, cwd, target, and revision match the invocation |
| Bounds | Empty results succeed; limits, fields, stable ordering, truncation, and opaque cursors behave deterministically |
| Errors | Stable codes map to actionable remediation and correct retry/safe-retry semantics |
| Long operations | Started, progress, warning, terminal, resume, wait, timeout, and cancel paths remain correlated |
| Mutation | Plan digest, expiry, expected state, approval, idempotent replay, actual effects, and verification are exercised |
| Recovery | Partial or uncertain effects return lookup, retry, resume, compensation, or rollback guidance |
| Compatibility | Unknown minor fields are tolerated, unsupported major versions fail, and human help remains usable |
| Portability | argv arrays, paths, stdin, stdout/stderr, signals, and exit codes work on Windows, macOS, and Linux |

Add agent evals for four outcomes: correct tool selection, correct argument
construction, recovery from a structured failure, and refusal to perform an
unsafe mutation. Measure calls, execution steps, output bytes or tokens,
wall-clock time, and target-state success; a richer description that increases
steps without improving the outcome is not automatically better.

## First-Version Priorities

If only one incremental release is available, implement these five pieces in
order:

1. Explicit `--agent` mode with no prompts and parser-safe output.
2. One versioned success envelope with context, effects, and verification.
3. Structured errors with stable codes and retry/remediation semantics.
4. Pagination, field selection, result limits, and artifact references.
5. Plan/apply/verify plus drift checks and idempotency for mutations.

Start with high-value read commands and one carefully bounded mutation. Capture
real agent failures and turn only repeated, stable lessons into new contract
fields or focused Skill guidance.

## Review Checklist

Use the [Contract Test Matrix](#contract-test-matrix), selecting rows relevant
to the command. Preserve human usability while testing the agent protocol;
do not impose mutation or streaming machinery on a bounded read-only query.

## External Anchors

These sources support parts of the design. Local architecture and capability
contracts remain authoritative for Better Harness.

- [Speakeasy, Making your CLI agent-friendly (2026)](https://www.speakeasy.com/blog/engineering-agent-friendly-cli): real-world prompt, spinner, non-interactive, structured-output, and focused-Skill lessons. Speakeasy uses several flags; the compound `--agent` mode here is this reference's recommendation.
- [Command Line Interface Guidelines](https://clig.dev/): stdout/stderr, exit status, non-interactive, color, animation, stdin, and machine-readable output conventions.
- [GitHub CLI formatting](https://cli.github.com/manual/gh_help_formatting): selectable JSON fields and pre-context `--jq` filtering.
- [Terraform machine-readable UI](https://developer.hashicorp.com/terraform/internals/machine-readable-ui): versioned, typed, one-object-per-line event output for long-running commands.
- [Terraform plan](https://developer.hashicorp.com/terraform/cli/commands/plan) and [apply](https://developer.hashicorp.com/terraform/cli/commands/apply): saved-plan automation and final-plan review patterns.
- [Stripe idempotent requests](https://docs.stripe.com/api/idempotent_requests): replay protection for uncertain create/update results under a documented idempotency contract.
- [MCP 2025-11-25 Tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools), [Schema](https://modelcontextprotocol.io/specification/2025-11-25/schema), and [Tasks](https://modelcontextprotocol.io/specification/2025-11-25/basic/utilities/tasks): input/output schemas, structured content, effect hints, and experimental task-augmented execution.
- [Hasan et al., “MCP Tool Descriptions Are Smelly!” (2026 preprint)](https://arxiv.org/abs/2602.14878): empirical description-quality and cost trade-offs across the authors' sampled tools.
- [RFC 9457, Problem Details](https://www.rfc-editor.org/rfc/rfc9457.html), [RFC 9110 conditional requests](https://www.rfc-editor.org/rfc/rfc9110.html), and [Google AIP-151](https://google.aip.dev/151): adjacent patterns for structured errors, state preconditions, and long-running operation handles. They are design analogies, not required wire compatibility.
