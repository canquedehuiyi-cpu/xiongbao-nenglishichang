# Better Harness

> Better Harness = Engineering Best Practices × Coding Agent Governance × Self-improving AI Delivery.

Better Harness is the package, plugin, CLI, and report-artifact layer for the
Better Harness methodology. It helps teams build a system where AI can safely
understand, change, review, report, and improve software over time.

- Project Harness. Prepares the repository as an AI-ready engineering environment by wiring together project context,
  structure, commands, history, sessions, and executable signals.
- Engineering Fluency. Translates complex engineering signals into a shared language for developers, architects,
  leaders, and agents, making health, readiness, risk, and delivery quality easier to understand.
- Change Confidence. Evaluates each AI-generated change through blast radius, sensitive paths, change size, commit
  patterns, and validation signals to decide whether it is safe to land.
- Agent Guardrails. Defines the behavioral boundaries for coding agents, keeping their actions safe, scoped,
  permission-aware, and aligned with team engineering standards.
- Action Pathways. Turns engineering insights into clear, sequenced, and reviewable paths for improvement, helping teams
  decide what to automate, test, split, govern, or review next.
- Adaptive Engineering Loop. Closes the loop across sessions, hooks, reviews, reports, memory, and outcomes,
  continuously tuning recommendations, rules, and agent behavior.

## Quickstart

Get a first readiness report from the Qoder Skill:

```bash
/better-harness
```

The Skill routes the project, session, and customization evidence lanes and
writes findings-backed Qoder Canvas artifacts to
`.qoder/better-harness/<date>/<time>-<target>/`:

- `findings.json`
- `report.canvas.tsx`

The legacy `qoder-harness` bin remains a compatibility entrypoint while the
visible product surface moves to Better Harness.

New to the workflow? Start with the [Better Harness Skill](skills/better-harness/SKILL.md).
Its routing keeps the project, session, and customization evidence lanes
progressively discoverable.

## Packaging

`@ali/better-harness` is the lightweight build-time package for IDE hosts.
The npm tarball contains the source CLI and runtime builder plus the skills,
models, references, templates, examples, datasets, and architecture contract.
It excludes tests, dev preview tools, retired hooks, repository-only package
verification tools, and `node_modules`.

Use `npm run bundle:zip -- --out <path>` from an installed package to create the self-contained runtime bundle for an IDE
installer. The zip compiles public Node entrypoints into minified ESM and shared
chunks while preserving their public paths. It also vendors `esbuild-wasm` for
Canvas transforms, so the installed runtime does not need `node_modules`.
