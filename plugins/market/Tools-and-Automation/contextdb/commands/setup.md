---
description: Connect Qoder to ContextDB — check the ctxdb CLI, sign in, bind the Qoder profile, and verify connectivity.
argument-hint: "[cn|intl] (optional site for first sign-in)"
allowed-tools: Bash, Read
---

# /contextdb:setup — connect Qoder to ContextDB

Goal: the `ctxdb` CLI is installed (Node.js >= 20), the `qoder` profile in `~/.ctxdb/ctxdb.json`
is authenticated, and `ctxdb ping --agent=qoder` succeeds. Fix only what is broken, report each
step to the user in one short line, and reply in the user's language.

Plugin helper (invoke with `bash`; it needs no execute bit):
`${QODER_PLUGIN_ROOT}/scripts/ctxdb-hook.sh doctor` — reports the CLI, Node.js, hook owner and
duplicate Skills, and caches the runtime paths that the plugin hooks use.

Never print or read API keys, tokens or `~/.ctxdb/credentials.json`. Never pass `--yes` or
`--login=default` unless the user explicitly agrees after you show them what it affects.

## Step 1 — Diagnose

```bash
bash "${QODER_PLUGIN_ROOT}/scripts/ctxdb-hook.sh" doctor
```

## Step 2 — Install the CLI (only if doctor reports `runtime: unavailable`)

- `Node.js >=20 is required`: tell the user to switch Node (for example `nvm install 20 && nvm use 20`),
  then rerun doctor. Do not change the user's Node installation yourself.
- `ctxdb CLI was not found`: ask the user before installing, then run
  `npm install -g @aliyunrds/ctxdb`. If npm reports a permission error, stop and show the error;
  do not retry with `sudo`.
- Rerun doctor until it reports a `ctxdb:` path.

## Step 3 — Check authentication

```bash
ctxdb status --agent=qoder --json
```

If the profile is authenticated, ping-able, and reports `integration: "plugin"`, skip to Step 5.
If it is authenticated but reports `integration: "cli"`, skip login and continue with the setup command in Step 4.

## Step 4 — Sign in and bind the Qoder profile

1. Make sure `CTXDB_API_KEY` and `CTXDB_ACCESS_TOKEN` are not set in the environment; login
   refuses to run while they are.
2. If no usable login exists, sign in once for this machine (add `--site=<cn|intl>` only if the user passed one):

   ```bash
   ctxdb login --json
   ```

   Login waits until the user approves in the browser. Run it in the background or with the longest
   timeout. As soon as stderr shows the `device_authorization` event, give the user the
   `authorization_url` and `user_code` (both are safe to show) and wait for the command to finish.
   If it says the login is shared by other Agents and needs `--yes`, show the listed Agents and
   rerun with `--yes` only after the user agrees.
3. Bind the Qoder profile and make the plugin the owner of Hooks and Skills:

   ```bash
   ctxdb setup --agent=qoder --integration=plugin --json
   ```

   This persists plugin ownership and removes only ContextDB Hooks and user-level Skills previously
   installed by the CLI. It preserves authentication, other Qoder Hooks, and unrelated Skills.
   If setup reports that the Qoder profile is explicitly unbound or uses a different login, explain
   that to the user and only rerun with `--login=default --integration=plugin` if they agree.
   If `--integration` is unknown, the CLI is too old; ask before upgrading `@aliyunrds/ctxdb`, then retry.

## Step 5 — Verify

```bash
ctxdb ping --agent=qoder --json
bash "${QODER_PLUGIN_ROOT}/scripts/ctxdb-hook.sh" doctor
```

Then tell the user:

- `ctxdb status` must report `integration: "plugin"`, doctor must report `hook_owner: plugin`, and
  `user_level_skills` should be `none`.
- Capture can begin later in the current session; SessionStart recall is fully active in the **next** Qoder session.
- The CLI keeps authentication and data access; the plugin is the only owner of Qoder Hooks and Skills.
