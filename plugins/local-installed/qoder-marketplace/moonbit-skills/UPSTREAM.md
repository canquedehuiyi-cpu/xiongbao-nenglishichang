# Upstream Import

- Source: https://github.com/moonbitlang/skills
- Imported commit: `c3f061da2abf7c6914e06df93572858dd21ef6bc`
- Imported on: 2026-06-15

## Qoder Packaging Notes

- The upstream `.git/` directory is intentionally not vendored.
- Upstream platform and repository metadata directories (`.claude-plugin/` and
  `.github/`) are preserved.
- Upstream implementation files are preserved as-is. This package exposes the
  upstream `skills/` directory directly through `.qoder-plugin/plugin.json`.
- `assets/logo.png` is a 200x200 square version of the official MoonBit logo
  from `https://docs.moonbitlang.com/en/latest/_static/logo.png`.
