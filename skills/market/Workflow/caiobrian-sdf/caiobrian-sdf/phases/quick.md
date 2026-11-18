# Phase: Quick Track

Compressed workflow for small, well-defined tasks. Runs in main context.

## When to use

- Bug fixes with clear reproduction
- Small UI adjustments
- Simple refactors (rename, extract, move)
- Config changes
- Small, isolated features

## When NOT to use → escalate to full flow

- New features affecting multiple modules
- Architectural changes
- Unclear requirements
- Public API changes

## Process

### Step 1: Scope

```markdown
**Problem:** [what's wrong or needed]
**Fix:** [proposed approach]
**Files:** [affected]
**Won't touch:** [boundaries]
```

Ask for confirmation.

### Step 2: Debug triage (bug fixes only — skip for other task types)

**Stop-the-Line Rule:** stop adding anything else, preserve evidence, diagnose before touching code.

1. **Reproduce** — make the failure happen reliably. If it can't be reproduced, gather context first (timing, environment, state, randomness).
2. **Localize** — identify the failing layer (UI, API, DB, build tooling, external service, or the test itself). Use `git bisect` for regressions.
3. **Reduce** — strip unrelated code until only the bug remains. Prevents symptom-fixing.
4. **Fix root cause** — ask "Why?" repeatedly until you reach the actual cause, not a surface symptom.
5. **Guard** — write a regression test that fails without the fix and passes with it.
6. **Verify end-to-end** — run the specific test, then the full suite.

Update the scope block with the identified root cause before implementing.

### Step 3: Implement

Follow CLAUDE.md conventions. No `any` types. No scope creep.

### Step 4: Quick verify

```markdown
## Quick Check
- [ ] Fix addresses the root cause (not just the symptom)
- [ ] Regression test exists and passes
- [ ] No regressions in affected area
- [ ] Types correct
- [ ] CLAUDE.md conventions followed
- [ ] Existing tests pass
```

### Step 5: Done

Present: what changed, quick check results, any risks.

If scope grows:
> "This is more complex than it seemed. I suggest escalating to the full flow. Want to continue with discovery?" (in the user's preferred language)

## Rules
- If scope grows, STOP and escalate
- Respect CLAUDE.md and LessonsLearned.md
- If mistake worth recording, suggest adding to LessonsLearned.md
- Code in English
- Always communicate in the user's preferred language
