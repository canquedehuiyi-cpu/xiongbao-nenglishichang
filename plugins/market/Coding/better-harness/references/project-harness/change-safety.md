# Change Safety

Select only the section relevant to the current task; shared storage does not
combine authority or require every procedure.

- [Review Triggers](#review-triggers)
- [Sensitive Code](#sensitive-code)
- [Recovery Evidence](#recovery-evidence)

## Review Triggers

### Review Triggers: Purpose

Review Trigger defines when an AI-assisted change needs extra review and which
next action is required.

It is a routing reference, not a full code-review checklist:

```text
local signals -> review trigger -> self-check / fresh Agent review / human review / split change / more evidence
```

Keep thresholds, path lists, and ownership rules in analyzer config or project
policy. This document should explain how to interpret signals and turn them into
recommendations.

### Review Triggers: Trigger Signals

| Signal | Why It Matters | Recommendation |
| --- | --- | --- |
| large diff | reviewer context may be too broad | split the change or request fresh Agent review |
| high blast radius | callers may regress | inspect callers and add regression tests |
| shared symbol changed | compatibility risk | review edge cases and public behavior |
| core path hit | ownership or architecture risk | request domain or human review |
| new dependency growth | supply-chain and maintenance scope may expand | verify necessity, pre-existing coverage, and lockfile or policy evidence |
| new file sprawl | one change may hide mixed responsibilities | split by owner or justify the cohesive boundary |
| non-trivial untested logic | behavior is not proven at the changed boundary | add a focused test or record why execution is unavailable |
| explicit deferral comment | known work may escape the acceptance path | link the deferral to an owner, follow-up, or deliberate non-goal |
| missing test evidence | behavior is not proven | add targeted tests or justify the gap |
| security-like removal | a safety boundary may be weaker | block for security or domain review |
| generated or binary output | hard to review directly | verify source generator and output parity |
| truncated analysis | confidence is limited | require another review pass |

Do not route only on a numeric score. Use the score to decide whether to
interrupt, then use the reasons to choose the next action.

These are qualitative review cues unless an owning analyzer, project policy,
configuration, and behavior test define a threshold. This reference does not
provide a standalone complexity score.

### Review Triggers: Example Signal Owner: Diff Impact

A project-owned diff-impact or call-graph analyzer can turn a diff into
structural signals such as changed symbols, affected callers, core hits, test
gaps, security-like removals, severity, and reasons. Do not claim this owner
exists until its entrypoint, configuration, and tests are present.

Example commands:

```bash
better-harness core-change-watch diff-impact --json
```

Recommended hook pattern:

- On write/edit events, show advisory feedback without blocking immediately.
- On task stop/completion, block only when a recent write occurred and review is
  recommended.
- In pre-push or CI, read JSON output and translate `shouldReview`, `severity`,
  and `reasons` into review requirements.

### Review Triggers: Recommendation Format

```text
Review recommended: <severity>

Signals:
- <specific reason>

Next action:
- <split change / inspect callers / add tests / run fresh Agent review / request owner review>

Evidence required:
- <test command, log, screenshot, owner approval, or rationale>
```

Good recommendations name the concrete action. Avoid vague wording such as
`review carefully`, `add more tests`, or `this looks risky`.

## Sensitive Code

### Sensitive Code: Purpose

Sensitive Code defines code and diff patterns that require elevated review. It is not a secret scanner and must not contain real secrets.

Use this rule when a change may affect confidentiality, integrity, availability, identity boundaries, execution boundaries, production safety, or security evidence.

Sensitive code changes must trigger stricter AI review or human review.

### Sensitive Code: Trigger Categories

#### Sensitive Code: 1. Plaintext Sensitive Information

Trigger when a diff adds, modifies, moves, logs, or exposes:

- API keys, tokens, private keys, passwords, certificates
- `.env`, config secrets, credentials, connection strings
- real accounts, internal URLs, production endpoints
- service credentials or cloud/provider credentials

Escalate to: `secrets-and-credentials-review`

#### Sensitive Code: 2. Credential Handling Code

Trigger when code reads, caches, refreshes, forwards, serializes, prints, stores, rotates, or deletes secrets.

Examples:

- `process.env`
- secret manager clients
- token refresh logic
- credential cache
- secret masking / redaction
- logs containing auth headers or tokens

Required evidence:

- file and line
- secret source
- secret sink
- masking/rotation behavior
- command or test used to verify no leakage

#### Sensitive Code: 3. Identity and Permission Boundaries

Trigger when code changes:

- authentication
- authorization
- role / permission checks
- owner/admin checks
- session, cookie, JWT, OAuth, OIDC
- middleware enforcing access control

Escalate to: `auth-boundary-review`

Required evidence:

- protected resource
- actor/user role
- permission check location
- bypass path considered
- negative test or proof

#### Sensitive Code: 4. Sensitive Data Surface

Trigger when code handles:

- PII
- user-generated content
- logs containing user/session data
- export/delete/retention flows
- backup/restore
- analytics or telemetry
- data masking or redaction

Escalate to: `privacy-data-review`

Required evidence:

- data class
- storage location
- retention/delete behavior
- redaction behavior
- affected users or scope

#### Sensitive Code: 5. Execution Boundaries

Trigger when code invokes or modifies:

- shell/process execution
- dynamic code execution
- plugin execution
- agent/tool calls
- filesystem read/write/delete
- network requests
- sandbox permissions or bypass paths
- webhook/callback URLs

Escalate to: `execution-boundary-review`

Required evidence:

- source of input
- execution sink
- allowlist/denylist behavior
- sandbox boundary
- failure mode
- test command

#### Sensitive Code: 6. Cryptography and Signatures

Trigger when code changes:

- encryption/decryption
- signing/verification
- JWT handling
- webhook signature verification
- hashing
- nonce/random generation
- key rotation or key storage

Escalate to: `crypto-signature-review`

Required evidence:

- algorithm/library
- key source
- verification path
- replay/expiry behavior
- backward compatibility impact

#### Sensitive Code: 7. Release and Supply Chain

Trigger when code changes:

- CI/CD workflows
- release scripts
- install scripts
- dependency update paths
- package manager scripts
- Docker/build files
- generated artifacts
- provenance/signing/attestation
- GitHub Actions permissions or secrets

Escalate to: `supply-chain-release-review`

Required evidence:

- workflow entrypoint
- token permissions
- secret access
- third-party actions/dependencies
- artifact produced
- release path affected

#### Sensitive Code: 8. Destructive or Production-Affecting Operations

Trigger when code can:

- delete data
- run migrations
- perform bulk updates
- change production flags
- elevate privileges
- disable safety checks
- modify backups or restore paths
- change admin-only operations

Escalate to: `destructive-change-review`

Required evidence:

- affected data/resource
- blast radius
- rollback plan
- dry-run/staging result
- approval requirement
- monitoring or alerting evidence

### Sensitive Code: Review Escalation Rules

A change is sensitive if any of the following is true:

1. It touches a known sensitive path.
2. It introduces a sensitive keyword or sink.
3. It changes a trust boundary.
4. It changes credential, auth, data, execution, crypto, CI/CD, or destructive behavior.
5. It weakens validation, authorization, logging redaction, sandboxing, or review requirements.
6. It adds generated, obfuscated, minified, vendored, or binary content to a release path.
7. It changes code that controls production behavior.

### Sensitive Code: Required Output

For every sensitive-code finding, the reviewer must output:

- category
- severity
- trigger reason
- file and line
- diff evidence
- affected boundary or asset
- required follow-up skill/reviewer
- command/test/evidence required before merge
- whether human review is mandatory

### Sensitive Code: Non-Goals

This file does not:

- store actual secrets
- replace gitleaks, trufflehog, GitHub secret scanning, or SAST
- prove exploitability by itself
- automatically approve security-sensitive changes

It classifies sensitive changes and routes them to stricter review.

## Recovery Evidence

Use this reference to inspect the operating evidence for Agent Work Loop
`rollback-recovery`. The model owns the judgment; this file owns the bounded
inspection procedure. Do not perform a destructive rollback merely to improve
the evidence state.

### Recovery Evidence: Start from the actual effect

Name the affected resource, data, revision, environment, or external action and
its blast radius. Then inspect the project's owned recovery shape: rollback,
restore, retry, compensation, idempotent replay, safe abort, prior revision,
backup, dry-run, or a proven no-persistent-effect boundary. A recovery-looking
filename or prose promise is only a discovery lead.

### Recovery Evidence: Evidence progression

| Level | Required evidence |
| --- | --- |
| Present | Owned mechanism, responsible owner, and intended effect class. |
| Wired | Affected resource or revision, supported entrypoint, required permission or credential scope, postcondition, and validation route are connected. |
| Exercised | Safe simulation, rehearsal, comparable retained task, or actual recovery ran and recorded the before state, decision, result, and postcondition. |
| Not applicable | Inspection proves the task has no persistent or externally visible effect that needs recovery. |
| Unobserved | Recovery depends on external state, credentials, environment, or history that the review cannot safely inspect. |

An exercised recovery can fail; evidence strength does not replace the model's
pass/fail judgment. Prefer a project-owned dry-run or isolated rehearsal. For a
real recovery, require explicit authority, least privilege, and risk-appropriate
approval before the effect.

### Recovery Evidence: Validation by recovery shape

- **Revision rollback:** bind the previous and current revision, target
  environment, rollout owner, health or acceptance check, and final active
  revision.
- **Backup and restore:** bind the backup to the affected data and time, verify
  readability or restore in a safe target, and check integrity after restore.
- **Retry or idempotent replay:** preserve operation identity, attempt history,
  duplicate protection, terminal result, and residual partial effects.
- **Compensation:** name the original effect, compensating action, ordering,
  unrecoverable residue, and business or state invariant after compensation.
- **Safe abort or no persistent effect:** show the transaction, sandbox,
  temporary workspace, preview, or cleanup boundary that prevents lasting
  effects.

### Recovery Evidence: Return

Return the actual effect, mechanism owner, entrypoint, permission boundary,
before/after identity, exercise type, validation result, and precise blocker.
Keep external or unsafe evidence `Unobserved`; do not downgrade it to `Missing`
or substitute a matching filename.
