# Phase: Document

Close the SDF cycle. Runs in main context (interactive).

**This phase only runs when explicitly invoked by the user.**

## Process

### Step 1: Technical record

```markdown
# Record: [feature/fix name]

## What changed
[summary with RF-xx references]

## Technical decisions
- [decision + justification + related RF/RNF]

## Trade-offs accepted
- [what was sacrificed + why acceptable]

## Spec deviations
- [changes during implementation + justification]
- If none: "No deviations"

## Technical debt created
- [if any + when to resolve]

## Post-deploy monitoring
- [what to monitor + alert thresholds]
```

### Step 2: Architectural Decision Records (ADRs)

Check if any decision made during this cycle qualifies as an ADR — something that:
- Introduced or removed a library/framework
- Changed an API contract or data model
- Adopted a new pattern or rejected an existing one
- Made a trade-off with long-term consequences

If yes, create one file per decision at `.claude/decisions/YYYYMMDD-<slug>.md`:

```markdown
# ADR: [title]

## Status
Accepted

## Context
[what situation or constraint led to this decision]

## Decision
[what was decided, in one clear sentence]

## Consequences
- **Easier:** [what becomes simpler]
- **Harder:** [what becomes more complex or costly]

## Alternatives considered
- [alternative] — rejected because [reason]
```

If no architectural decisions were made, skip this step and state "No ADRs — no architectural decisions this cycle."

Reference any generated ADRs in the PR description (Step 3) and in the Technical Record (Step 1).

### Step 3: Update artifacts

- [ ] `specs/<feature>/plan.md` — reflects what was ACTUALLY implemented
- [ ] `specs/<feature>/tasks.md` — all checkboxes marked [x]
- [ ] `LessonsLearned.md` — session errors documented
- [ ] `.claude/decisions/` — ADR files created (if applicable)

### Step 4: PR Description

```markdown
## What
[2-3 sentences]

## Why
[problem + impacted metric]

## How
[technical approach]

## Tests
[coverage + what was validated]

## Risks
[attention points for reviewer]

## Rollback
[how to revert]
```

### Step 5: Confirm

State cycle is complete (e.g., "SDF cycle complete. Artifacts updated. Anything else before closing?") in the user's preferred language.

## Rules
- Only document decisions that actually happened
- If no deviations, state "No deviations" (in the user's preferred language)
- Always suggest additions to LessonsLearned.md if errors occurred
- **LessonsLearned.md size cap**: max 50 entries. If adding a new entry would exceed 50, remove the oldest entry first. This keeps the file's token cost constant across the project's lifetime.
- Always communicate in the user's preferred language
