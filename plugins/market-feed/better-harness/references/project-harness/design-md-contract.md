# DESIGN.md Contract

Use this when coding-agent practice evidence includes `DESIGN.md`, design
tokens, visual/UI generation, design-review skills, or repeated UI style drift.
This is a readiness reference, not a full authoring guide. For creation or
detailed review, hand off to `design-md-review` when available.

## Meaning

`DESIGN.md` is a plain-text visual design-system contract for humans and coding
agents: YAML frontmatter carries machine-readable tokens, and Markdown carries
design rationale and guardrails.

When authoring support is needed, load the
[complete packaged example](design-md-contract.md#complete-example) after this
contract. It is a generic structural fallback, not product evidence: replace
its illustrative values only with inspected project sources.

Do not route lowercase `design.md` architecture specs, `requirements.md`, or
`tasks.md` here. This reference is only about uppercase `DESIGN.md` visual
identity and design-token guidance.

## Applicability

Apply only when the target owns user-facing UI, visual reports, generated UI,
brand surfaces, component libraries, themes, or design systems. For backend,
CLI, SDK, data, or infra projects, mark `not applicable`.

Outside a confirmed frontend or visual project, absence is a recommendation,
not a risk, unless repeated visual drift, inconsistent generated UI, or invented
local style rules are observed. In the default Agent Work Loop repository scan,
a confirmed frontend or visual project
without an exact uppercase root `DESIGN.md` is one ordinary `Low` finding mapped
to Task Understanding / Relevant Context. Projects without confirmed frontend
or visual implementation evidence remain not applicable.

## Inspect

Look for `DESIGN.md`, Tailwind config, CSS variables, theme files, token
JSON/YAML, Storybook, component docs, design-review skills, lint commands, CI
checks, hooks, or reports. Classify evidence separately:

- **Present**: `DESIGN.md` exists.
- **Structured**: it has frontmatter plus readable sections.
- **Token-ready**: frontmatter uses top-level `colors`, `typography`,
  `rounded`, `spacing`, and `components` groups.
- **Agent-ready**: prose explains product feel, component use, states, and
  do/don't rules.
- **Aligned**: tokens map to implementation theme, CSS variables, Tailwind,
  component props, or Storybook.
- **Backstopped**: lint, diff, export, CI, hook, or review gate checks drift.

File presence is not enforcement.

Classify an exact root `DESIGN.md` as a project **Rules** asset beside
`AGENTS.md`. Keep provider-native Rules first, then `AGENTS.md`, then the visual
contract. Lowercase architecture `design.md` and nested design notes do not
become this Rules asset.

## Quality Signals

Strong evidence:

- Semantic color roles, foreground/background pairs, and state colors.
- Structured typography, spacing, and radius scales.
- Component token maps for real UI surfaces and states such as
  `button-primary-hover` or `text-input-focused`.
- Markdown sections for Overview, Colors, Typography, Layout,
  Elevation & Depth, Shapes, Components, and Do's and Don'ts.
- Rationale that says when to use a token, when not to use it, and what agent
  mistake it prevents.
- Accessibility guidance for contrast, focus-visible, color-not-alone, reduced
  motion, forms, and error states.

Weak evidence:

- Prose-only brand description with no token frontmatter.
- Nested `tokens:` instead of top-level token groups.
- Raw names such as `blue500` without semantic roles.
- Component names without variants, states, or token mappings.
- Vague guidance such as "make it clean".
- Tokens that drift from implementation theme or current product.

## Validation

Prefer cross-platform commands:

```bash
npx -p @google/design.md designmd lint DESIGN.md
npx -p @google/design.md designmd diff DESIGN.md DESIGN-next.md
npx -p @google/design.md designmd export --format css-tailwind DESIGN.md
```

Use the `designmd` alias in package scripts because the `design.md` binary name
can collide with Markdown file associations on Windows.

Lint proves structure and token checks. Export proves tokens can feed
Tailwind/CSS/DTCG workflows. Diff is drift evidence, not visual QA by itself.

## Recommendation Rules

Recommend `DESIGN.md` when agents generate UI and invent colors, spacing,
typography, radii, or component variants; when a visual system has no
agent-readable source of truth; or when tokens exist without usage rationale.

When the file is missing, inspect existing UI evidence before authoring. Use
`design-system-capture` when the contract must be inferred from code,
screenshots, Figma, themes, or components, then use `design-md-review` to author
or review the root file when those Skills are available. Preserve inferred
rules as inference and mark unresolved policy `needs-design-decision` instead
of inventing brand decisions.

When those optional Skills are unavailable, use the
[complete packaged example](design-md-contract.md#complete-example) as the
structural fallback while keeping every project value evidence-bound.

Recommend lint, CI, or hooks only after the team has a stable `DESIGN.md`
shape. Route screenshot/CSS/Figma/live-UI extraction to `design-system-capture`
first when available.

## Projection

Use `DESIGN.md` as positive `AI Agent Practices` evidence:

- **Context Map**: agents can understand the visual language quickly.
- **Quality Gates**: token contracts and lint/export checks reduce style drift.
- **AI Readiness**: UI generation has a reusable visual source of truth.
- **Rules inventory**: the root file appears beside `AGENTS.md`; in the
  standalone per-asset Rules evaluator it can raise the bounded surface mean
  without removing another Rule's warning or worst risk.
- **Agent Work Loop**: static presence supports `relevant-context`; routed and
  task-applied use can support stronger Task Understanding evidence and score
  only within the model's existing evidence ceilings.

Do not add a new scorecard row. Do not let visual design docs replace executed
build, lint, typecheck, preview, accessibility, or visual-regression evidence.

## Output Shape

```markdown
### DESIGN.md contract
- **Scope**: in scope | not applicable | needs evidence
- **Evidence level**: Present | Structured | Token-ready | Agent-ready | Aligned | Backstopped
- **Strongest evidence**: <file, command, report, or implementation mapping>
- **Main gap**: <missing token/rationale/alignment/backstop>
- **Recommendation**: <smallest next action>
```

## Complete Example

Copy the fenced document as a starting structure; replace illustrative values
with inspected project evidence before using it.

````markdown
---
version: alpha
name: Example Product
description: Complete generic DESIGN.md structure; replace illustrative values with inspected project evidence.
colors:
  primary: "#0F766E"
  primary-hover: "#115E59"
  on-primary: "#FFFFFF"
  text: "#111827"
  text-muted: "#4B5563"
  surface: "#FFFFFF"
  surface-subtle: "#F3F4F6"
  border: "#D1D5DB"
  focus: "#2563EB"
  danger: "#991B1B"
  danger-surface: "#FEF2F2"

typography:
  heading:
    fontFamily: "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: 24px
    fontWeight: 600
    lineHeight: 32px
    letterSpacing: 0px
  body:
    fontFamily: "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: 16px
    fontWeight: 400
    lineHeight: 24px
    letterSpacing: 0px
  label:
    fontFamily: "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: 14px
    fontWeight: 600
    lineHeight: 20px
    letterSpacing: 0px
  caption:
    fontFamily: "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: 12px
    fontWeight: 400
    lineHeight: 16px
    letterSpacing: 0px

rounded:
  sm: 4px
  md: 8px
  lg: 12px
  full: 9999px

spacing:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px

components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.label}"
    rounded: "{rounded.md}"
    padding: "{spacing.sm} {spacing.md}"
    height: 40px
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
    textColor: "{colors.on-primary}"
  text-input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    typography: "{typography.body}"
    rounded: "{rounded.sm}"
    padding: "{spacing.sm} {spacing.md}"
    height: 40px
  card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    typography: "{typography.body}"
    rounded: "{rounded.lg}"
    padding: "{spacing.lg}"
  helper-text:
    backgroundColor: "{colors.surface-subtle}"
    textColor: "{colors.text-muted}"
    typography: "{typography.caption}"
    rounded: "{rounded.sm}"
    padding: "{spacing.xs} {spacing.sm}"
  alert-error:
    backgroundColor: "{colors.danger-surface}"
    textColor: "{colors.danger}"
    typography: "{typography.body}"
    rounded: "{rounded.md}"
    padding: "{spacing.md}"
  avatar:
    backgroundColor: "{colors.surface-subtle}"
    textColor: "{colors.text}"
    typography: "{typography.label}"
    rounded: "{rounded.full}"
    size: "{spacing.xl}"
  section-heading:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    typography: "{typography.heading}"
    rounded: "{rounded.sm}"
  focus-indicator:
    backgroundColor: "{colors.focus}"
    textColor: "{colors.on-primary}"
    rounded: "{rounded.sm}"
    width: 2px
  divider:
    backgroundColor: "{colors.border}"
    textColor: "{colors.text}"
    rounded: "{rounded.sm}"
    height: 1px
---

# Example Product

## Overview

Use this file as a structural example only. Derive the real product character,
tokens, component states, and accessibility rules from inspected source files,
rendered UI, and approved design evidence. Record an inference as an inference;
mark unresolved policy `needs-design-decision`.

## Colors

- Use semantic roles such as `primary`, `surface`, and `danger`; do not introduce
  palette names such as `teal-500` into component guidance.
- Maintain at least WCAG AA contrast for normal text and visible focus states.
- Do not use color as the only carrier of error, success, or selection state.

## Typography

- Use `heading` for page or major section titles, `body` for primary reading,
  `label` for controls, and `caption` for secondary metadata.
- Preserve the documented line height and weight instead of selecting nearby
  values ad hoc.

## Layout

- Build spacing from the documented scale. Use `md` for ordinary component
  padding, `lg` between related sections, and `xl` for major page separation.
- Confirm narrow, regular, and wide viewport behavior from the real product.
- Responsive breakpoint policy: `needs-design-decision` until project evidence
  identifies the approved breakpoints.

## Elevation & Depth

- Use borders for ordinary grouping and add a project shadow token only when
  inspected evidence shows content elevated above another surface.
- Do not add shadows to compensate for unclear spacing or hierarchy.

## Shapes

- Use `sm` for compact fields and helpers, `md` for controls, `lg` for cards,
  and `full` only for circular or pill-shaped elements.
- Do not introduce one-off radii outside the documented scale.

## Components

- Primary buttons use the documented hover state and retain a visible keyboard
  focus indicator.
- Inputs pair labels, help text, and errors programmatically; placeholder text
  is not a label.
- Cards use border-first separation. Alerts pair semantic color with an icon,
  heading, or explicit text.
- Document loading, empty, error, disabled, selected, and focus-visible states
  whenever the corresponding component exists in the product.

## Do's and Don'ts

### Do

- Reuse semantic tokens and documented component variants.
- Verify representative rendered states, keyboard flow, contrast, and reduced
  motion behavior after changing the contract.
- Cite source files, screenshots, or approved design artifacts for inferred
  project-specific rules.

### Don't

- Do not invent brand colors, typefaces, breakpoints, or interaction policy.
- Do not copy the illustrative values in this example without project evidence.
- Do not treat a passing structural lint as visual or accessibility acceptance.
````
