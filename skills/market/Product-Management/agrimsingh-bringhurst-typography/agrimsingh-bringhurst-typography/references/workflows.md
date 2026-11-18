# Workflows

## Contents
1. Typography Audit Workflow
2. New Typographic System Workflow
3. Existing Layout Refactor Workflow
4. Web and App Typography Workflow
5. Print and PDF Workflow
6. Multilingual and Mixed-Script Workflow

## 1) Typography Audit Workflow
1. Capture context.
- Document type, audience, reading duration, and medium.
- Production constraints: viewport, paper, printer, rendering engine.
2. Run macro checks first.
- Page geometry and text block shape.
- Hierarchy clarity and heading system.
- Typeface count and role clarity.
3. Run rhythm checks.
- Measure, leading, paragraph signaling, list/table spacing.
- Hyphenation and line-break hygiene.
4. Run micro checks.
- Numeral style, ligatures, punctuation, dash and quote conventions.
- Diacritics, symbols, non-Latin script handling.
5. Return prioritized fixes.
- Start with highest-leverage structural changes.
- Delay fine polish until structure stabilizes.

## 2) New Typographic System Workflow
1. Define content architecture.
- Reading text, navigation text, metadata, display text, captions, UI controls.
2. Choose base family strategy.
- Start from one family where possible.
- Add complementary families only for explicit structural need.
3. Set core text parameters.
- Body size, line length, leading, paragraph logic.
- Defaults for lists, notes, tables, quotations.
4. Build hierarchy scale.
- Define heading levels and transitions.
- Use consistent relationship between size, weight, and spacing.
5. Specify symbol and punctuation conventions.
- Dashes, quotes, ellipses, ranges, fractions, dimensions.
6. Define production variants.
- Print profile, screen profile, and narrow/mobile profile.

## 3) Existing Layout Refactor Workflow
1. Freeze visual baseline.
- Document current type tokens and spacing rules.
- Capture screenshots or page samples for comparison.
2. Make one-axis changes.
- First: measure and leading.
- Second: hierarchy and spacing cadence.
- Third: punctuation and symbol normalization.
3. Re-check side effects after each axis.
- Overflow, awkward wraps, orphan/widow behavior.
- Table/list alignment regressions.
4. Final pass for consistency.
- Ensure style logic is coherent across all templates/components.

## 4) Web and App Typography Workflow
1. Establish robust defaults.
- Prefer readable body text with stable rhythm at common breakpoints.
- Tune line length by viewport size.
2. Define responsive hierarchy behavior.
- Heading scales that compress predictably on small screens.
- Preserve contrast without collapsing into same-size blocks.
3. Test rendering quality.
- Check real browsers and OS rendering differences.
- Verify punctuation, quotes, and special symbols in production fonts.
4. Protect interaction contexts.
- Forms, tables, and dense UI surfaces need tighter but still readable settings.
5. Validate accessibility and reading comfort.
- Contrast, zoom behavior, and sustained reading legibility.

## 5) Print and PDF Workflow
1. Bind decisions to final stock/output.
- Paper, print method, and target viewing distance affect type choice.
2. Validate physical rhythm.
- Leading cadence, margin proportions, folios, running heads.
3. Treat front/back matter as design components.
- Title page, prelims, notes, appendices, index.
4. Proof through final stage.
- Re-check after imposition/export and before final sign-off.

## 6) Multilingual and Mixed-Script Workflow
1. Choose script-compatible families intentionally.
- Avoid accidental script pairing.
2. Balance scripts optically.
- Tune x-height analogs, color, and baseline behavior by eye.
3. Normalize punctuation and spacing conventions per language.
- Hyphenation, quote marks, range notation, abbreviations.
4. Test representative language samples.
- Include difficult glyph clusters and diacritics early.

## Output Template
Return typography proposals in this order:
1. Context and goal.
2. Findings (severity ordered).
3. Recommended sequence of changes.
4. Rule references (IDs from `rules-index.md`).
5. Validation plan.
