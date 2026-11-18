# Report Routing

This file owns report selection and the Markdown body skeleton. Output-mode
owners retain their runtime and validation rules.

## Core Contract

- Markdown structure -> [Markdown Report Structure](#markdown-report-structure).
- Model judgement -> `../../models/routing.md` and the selected model.
- Project trait -> `project-traits.md`.
- Runtime, data, and validation -> selected output-mode owner.

## Reference Route

Read in this order: base report template, model routing, project traits, then
the selected output-mode owner when the route has one.

## Output Route

Choose exactly one output route. Generate only the named artifacts unless the
user asks for an explicit companion; omit metadata lines, companion sections, and
files from other routes.

| Route | Use when | Artifacts | Runtime owner |
| --- | --- | --- | --- |
| Qoder Canvas report | Active host is Qoder | renderer-owned `findings.json`, `canvas.json`, `report.canvas.tsx` | `qoder-canvas.md` |
| Portable HTML report | A self-contained visual is explicitly requested | renderer-owned `findings.json`, `report.md`, `report.html` | `html-visual.md` |
| Markdown only | No visual companion is requested or feasible | `report.md`, `findings.json` | none |

## Markdown Report Structure

Use this template for every `harness` Markdown report. It owns the Markdown
skeleton, parser anchors, headings, and section semantics. Selection rules live above;
metadata, scoring, and parity rules live in
`skills/better-harness/SKILL.md#report-output` and
`references/project-harness/core-change-watch.md`.

Before drafting Markdown, use the selected maturity model, primary project
trait, and primary style from the routing references. Read the selected maturity
model. Style selection is internal; do not expose style ids or display labels in
visible artifact text.

### Markdown Body Skeleton

When Markdown is generated, use these `##` headings in order:

1. `## Project Overview`
2. `## Harness Dimensions`
3. `## Issue Findings`
4. `## Next Recommendations`
5. `## Notes And Method`

`Project Overview` gives the target identity. `Harness Dimensions` is the
style-selected dimension, fluency, matrix, or scorecard assessment.
`Issue Findings` contains shared risk/action rows.
`Next Recommendations` contains follow-up actions, validation steps, schedule
handoffs, broader AI-readiness follow-ups, and concise reasons for why the
important recommendations were selected. For architecture, generated-artifact,
API/schema, or design-contract drift, explain the observed contract, drift risk,
recommended check or small repair, and pass condition inline; when this lens is
central to the report, add a short method note that combines deterministic
structural signals, LLM semantic evaluation, triage, focused fixes, and
post-fix verification. For Loop Engineering follow-ups, show the selected
pattern or composition, owner, why the loop matters, expected artifact,
validation path, and stop condition or missing proof without rendering the full
discovery decision tree. New reports do not author `summary.suggestions`.
Promote an evidence-eligible follow-up to an ordinary `Low` finding; defer a
pure opportunity. Renderers may keep historical v24/v25 suggestions readable
for compatibility, separate from shared finding/action rows.
`Notes And Method`
contains calibration caveats, generated artifacts, and compact current-model
dimension notes when methodology is requested or all five dimension labels are
displayed.
