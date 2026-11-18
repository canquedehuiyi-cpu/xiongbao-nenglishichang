# Upstream Import

- Source: https://gitcode.com/Cangjie-SIG/CangjieSkills
- Imported commit: `6dba62a8fada30663535d31f16183b29547147ff`
- Imported on: 2026-06-16

## Qoder Packaging Notes

- The upstream `.git/` directory is intentionally not vendored.
- The upstream repository has no `.claude-plugin/`, `.cursor-plugin/`, or
  `.github/` metadata directories — its native distribution format is the
  `.agents/skills/` layout used by the `npx skills` tool. There is therefore
  no upstream platform metadata to preserve.
- The upstream `.agents/skills/` directory was relocated to top-level `skills/`
  to match the Qoder plugin convention. Skill content (SKILL.md frontmatter and
  bodies, references, etc.) is preserved as-is from upstream.
- Frontmatter additions per Qoder requirements: `version: 1.0.0`, English
  `description`, Chinese `description_zh`, and `user-invocable: false` on the
  `cangjie-original-docs` fallback skill. All other fields are upstream values.
- `assets/logo.png` is a 512×512 RGBA PNG rendered from the upstream Cangjie
  SVG logo via `rsvg-convert`. Source SVG was supplied by the user.
- The upstream `tests/` directory (6 sample Cangjie projects used to demonstrate
  skill effectiveness) and `verification/` directory (skill usage screenshots)
  are not vendored — they are upstream maintainers' working artifacts, not
  required for runtime use of the skills.
