# Upstream Import

- Source: https://github.com/ChromeDevTools/chrome-devtools-mcp
- Imported commit: `cdc365ca95f53e67a724ec45d4fca7e62cff0824`
- Upstream version: `1.9.0`
- Imported on: 2026-09-11

## Qoder Packaging Notes

- The upstream `.git/` directory is not included in the install package.
- Upstream content is pinned to the commit above. The Qoder package version is `1.9.0`.
- The Qoder entry point remains `.qoder-plugin/plugin.json`; actual component paths and MCP/hook registration are declared there.
- Qoder packaging provenance and the baseline production ZIP hash are recorded in `SOURCE.json`.
- The Qoder manifest uses the published npm command from the current upstream plugin manifest (`chrome-devtools-mcp@1.9.0`); no local source build is required.
