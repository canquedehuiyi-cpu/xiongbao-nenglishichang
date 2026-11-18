---
description: Show ContextDB health for Qoder — CLI, sign-in, connectivity, hook owner and duplicate Skills.
allowed-tools: Bash
---

# /contextdb:status — ContextDB health for Qoder

Run these read-only checks and summarize them for the user in one short block, in the user's
language. Do not change any configuration.

```bash
bash "${QODER_PLUGIN_ROOT}/scripts/ctxdb-hook.sh" doctor
ctxdb status --agent=qoder --json
ctxdb ping --agent=qoder --json
```

Report:

- CLI path and version, Node.js version.
- Whether the Qoder profile is authenticated, whether ping succeeds, and its `integration` mode.
- Healthy plugin-managed setup means `integration: "plugin"` and hook owner `plugin`.
  Hook owner `global` means legacy CLI Hooks are active and the plugin Hooks are idle.
- Duplicate user-level `contextdb-*` Skills, if any.

If the CLI is missing, sign-in is not ready, or ping fails, suggest `/contextdb:setup`.
Never print API keys or tokens.
