# English structure example

This example demonstrates output structure, scope judgment, and evidence requirements. Replace it with the user's real goal and never copy the CSV scenario into an unrelated task.

# Task

- Type: Bugfix
- Goal: Fix Chinese characters appearing corrupted when a CSV export is opened in Excel on Windows, while preserving existing fields and behavior on other platforms.
- Assumption: The repository already has a CSV export path; Phase 1 must detect the real files, encoding library, and verification commands.

# Scope and Boundaries

Must complete: reproduce the corruption, isolate the encoding or file-header cause, implement the smallest fix, and add regression coverage that can be verified in Windows Excel.

Do not do: rewrite the export subsystem, add new export formats, or change unrelated UI and fields.

Constraints: preserve field names, ordering, public interfaces, and non-Windows behavior; detect configured commands before running them; justify any dependency; require separate authorization for publishing or production writes.

# Phases

1. Reproduce and baseline: inspect the export path and existing checks, then reproduce with one deterministic Chinese fixture and record original bytes and visible Excel behavior.
2. Apply the smallest fix: change only root-cause files, preserve contracts, and immediately run focused verification.
3. Regress and evidence: run the project's configured tests, build, and export smoke checks; cover Chinese, English, empty values, and existing platforms; diagnose, fix, and rerun failures.

Every phase follows: Plan -> Implement -> Verify -> Fix -> Evidence -> Decide.

# Verification and Evidence Report

- Record changed files, commands actually run, exit status, and meaningful results.
- Retain the same deterministic fixture before and after the fix with a byte-level comparison.
- Provide visible Windows Excel verification; unit tests alone are insufficient.
- Separate completed work, unfinished work, risks, and remaining human decisions.

# Acceptance

- [ ] Windows Excel displays Chinese correctly without changing fields or ordering
- [ ] English, empty values, and existing export paths do not regress
- [ ] Applicable tests and real runtime checks pass
- [ ] No unrelated changes, invented commands, or fabricated evidence
- [ ] The final report contains evidence and remaining risks
