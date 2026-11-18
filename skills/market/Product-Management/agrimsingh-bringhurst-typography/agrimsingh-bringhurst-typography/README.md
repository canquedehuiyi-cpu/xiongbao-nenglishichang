# Bringhurst Typography Skill

Human-facing overview for the `bringhurst-typography` agent skill.

## What This Skill Does

Applies principles from _The Elements of Typographic Style_ to:

- UI and web typography
- Editorial and long-form layouts
- PDF/print typography review
- Typeface selection, pairing, spacing, and punctuation quality

## Skill Files

- `SKILL.md`: agent instructions and workflow.
- `agents/openai.yaml`: UI metadata and default prompt.
- `references/book-map.md`: chapter and appendix map.
- `references/rules-index.md`: condensed rule index by chapter.
- `references/workflows.md`: practical execution workflows.
- `references/checklists.md`: audit and sign-off checklists.

## How to Invoke

Use:

`/bringhurst-typography`

Example prompt:

`Use /bringhurst-typography to audit this landing page typography and suggest fixes in priority order.`

## Notes

- Keep agent-operational guidance in `SKILL.md` and `references/`.
- Keep this README for quick human orientation.
