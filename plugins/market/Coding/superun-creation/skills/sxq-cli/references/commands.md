# suxiaoqiang-cli (sxq)

`sxq` syncs a superun project (identified by a `sessionId`) with a local directory, drives the
preview pipeline, and opens the browser for production release confirmation. Use non-interactive flags only after the user has authorized the exact
operation. In particular, never add `-y` to `sxq push` before reviewing its add/modify/delete plan.

## Prerequisites

- If a command reports "Not logged in / 未登录" or "credential expired / 凭证无效",
  start `sxq login` and let the user complete authorization in the browser. Keep the
  login process and resume the blocked command after the CLI confirms success. If the
  environment cannot launch the login flow, explain the actual failure and ask the user
  to run it in that environment. If the user hands you a token, run
  `sxq login --token <token>` (it validates the token and keeps the previous credential on
  failure). Never ask the user to paste a token proactively.
- A project directory is bound via `.sxq/config.json` (created by `sxq link`). Check for it
  before assuming a directory is linked.

## Core workflow

```bash
sxq link <sessionId>        # bind current dir to a project (verifies ownership; needs login)
sxq pull                    # pull remote files (incremental, three-way merge)
# ... edit files locally ...
sxq push -m "<summary>"     # review add/modify/delete plan, then confirm the push
sxq preview                 # update the frontend preview; equivalent to sxq preview front
sxq preview ef              # update only the Edge Function preview
sxq deploy                   # open the linked project's release confirmation page
sxq deploy --status         # read-only: pending/published versions + live URL
```

## Command details & flags

- `sxq link <sessionId> [-y]` — validates the project before binding this directory. A fresh binding does not need `-y`; use it to replace an existing binding only when that replacement is intended and authorized.

- `sxq push [-f] [-y] [-m <message>]` — pulls first, then lists every added, modified, and deleted
  text file before pushing. Git projects default to the project-level `push-branch` (`main`);
  `-f` ignores branch restrictions, while `-y` confirms the displayed plan without an interactive
  prompt. Only use `-y` after the user has authorized the exact push. Respects `.gitignore` plus
  built-in ignores (`node_modules`, `dist`, `.git`; binaries and files over 5MB are skipped). If it
  aborts with conflict markers (`<<<<<<< local`), resolve the listed files, then push again.
- `sxq preview [front|ef] [--message-id <id>]` — updates the preview environment. `front` is
  the default and polls the preview build for up to 10 min; `ef` deploys all Edge Functions
  from the linked project's latest completed mainline version. `--message-id` only applies to
  `front`. The legacy `sxq publish` command remains available for compatibility, prints a
  deprecation warning, and then runs the same behavior as `sxq preview front`.
- `sxq deploy` — opens the linked project's release confirmation page in the user's browser.
  It never calls the release API directly. The user must review and confirm the release on the
  page; agents must not claim that a release happened just because this command exited 0.
- `sxq pull [-f]` — local-only edits are preserved via three-way merge. Git projects only operate
  on the configured `push-branch` by default and apply the shared local-file safety checks before
  writing the worktree. Conflicted files are listed and contain git-style markers; resolve before
  pushing. `-f` only ignores configured/manifest branch restrictions.
- `sxq config set|get|unset|list` — keys: `host` (API base URL), `lang` (`zh`/`en`), and the
  project-level `push-branch` (defaults to `main`).
- `--debug` on any command prints full request/response logs (tokens masked) — use it when
  diagnosing failures.

## Project plugins and private skills

The CLI exposes only the server allowlist of project plugins:

- `SUPERUN_CLOUD`
- `SUPERUN_AI`
- `SUPERUN_MANAGED_AGENT_V2`
- `SUPERUN_STORAGE`
- `TTS`
- `ASR`
- `VIDEO_GENERATE`
- `NANO_BANANA`
- `OCR`

Use `sxq plugin list` or `sxq plugin status [pluginId]` to inspect them. `sxq plugin enable <pluginId>`
waits for the remote integration lifecycle and, after success, installs its private skills.
`sxq plugin disable <pluginId>` may also disable dependent plugins and requires interactive
confirmation.

Plugin skills are private, plugin-owned resources rather than the general superun skill catalog.
When an agent needs one, it must run `sxq plugin skill <pluginId>` itself. The command force-upgrades
all files for every associated skill into `.superun/skills/<skillId>/`; a skill may include
`SKILL.md`, references, scripts, assets, and other files. Do not edit those generated files because a
later plugin operation may overwrite them with the newest server version.

`.superun/skills/` is deliberately outside project attachment sync: `sxq pull` never reads,
overwrites, or tracks it, and `sxq push` never uploads it. Plugin capability commands upgrade the
relevant private skills before use.

## Git collaboration safety

`.sxq/attachments.json` is a local synchronization baseline, not a Git index. The `.sxq/`
directory is intentionally ignored by Git, so switching branches changes the working tree without
changing that baseline. A file that is older, different, or absent on the new branch can therefore
look like an intended modification or deletion even when nobody edited or removed it manually.

- Run `sxq pull`, `sxq push`, and `sxq db push` only from the branch intended to sync with superun.
  Git projects allow all three local-file operations only from the project-level `push-branch`
  (`main` by default). Configure a different branch with `sxq config set push-branch <branch>`.
- Prefer a separate Git worktree for each concurrently used branch. Link and pull each worktree
  separately so every worktree has its own `.sxq` baseline. Never copy `.sxq` between repositories,
  worktrees, branches, or partial source directories, and never force-add it to Git.
- After switching branches in a directory that already contains `.sxq`, do not push immediately.
  Return to the configured push branch, run `sxq pull`, inspect `git status` / `git diff`, and review
  the complete push plan. Treat unexpected bulk modifications or deletions as a stale/mismatched
  working tree and stop instead of confirming.
- `-f` on `pull`, `push`, or `db push` bypasses only branch restrictions; it does not prove that the
  working tree matches the user's intent. Use it only when the user explicitly authorizes operating
  on that exact branch. Do not use it to bypass reset/rebase/history or worktree warnings.
- `sxq push -y` still prints the plan but skips the prompt. Use it only after the exact added,
  modified, and deleted paths have been reviewed and authorized. Never combine `-f -y` as a generic
  retry for a failed push.
- Non-Git directories skip Git-specific checks, but the push plan remains authoritative: stop on
  surprising changes and confirm only the intended files.

## Database migrations (`sxq db push`)

superun projects use Supabase. Schema changes MUST go through migration files executed by
`sxq db push` — never by pushing SQL files with `sxq push` (the CLI blocks any change under
`supabase/migrations/` during a normal push).

Full flow:

1. Write the DDL in a new file under `supabase/migrations/`. Its name MUST strictly match
   `<yyyyMMddHHmmss>_<identifier>.sql`: the prefix is exactly 14 digits, generated with
   `date +%Y%m%d%H%M%S` (for example,
   `20260506210939_b9c21d2a344c4871b08a744b2e724176.sql`). The timestamp prefix is the replay
   ordering key and MUST be unique across the project's migrations. Before creating a migration,
   inspect the existing filenames; if the timestamp already exists, generate a later one rather
   than reusing it. Do not use Unix timestamps, dates with separators, shortened dates, or any
   other prefix width: lexical filename order would no longer reliably match migration time.
2. Run `sxq db push`. It will:
   - apply the same Git local-file safety checks as `pull` and `push` before reading or writing
     project files (`-f` only ignores configured/manifest branch restrictions);
   - pull remote changes first (aborts if there are merge conflicts — resolve, then rerun);
   - diff local files against the remote baseline to find migrations that are new;
   - abort the entire pending batch before executing any SQL if any new `.sql` filename does not
     contain an exact 14-digit `yyyyMMddHHmmss` prefix;
   - reject the entire pending batch before executing SQL if a new migration reuses a timestamp
     from another pending migration or an existing remote migration;
   - execute the new migrations one at a time, in ascending timestamp order;
   - stop at the first failure and print the server's error message. Migrations before the
     failed one are already applied; fix the failing file and rerun — only the remaining
     (still-new) migrations execute again;
   - after success, the server stores each migration file as a project attachment
     automatically, and the CLI runs a final pull so the local manifest matches.
3. Never edit an already-executed migration file — it is part of the remote baseline; write a
   new migration instead.
4. Migration SQL should be idempotent where possible (`create table if not exists`, `drop ... if exists`).

## Database queries and logs

Every `sxq db` command requires `SUPERUN_CLOUD=ENABLED` and first force-upgrades that plugin's private
skills.

- `sxq db query [sql] [--file <path>] [--limit <n>] [--json]` runs SQL against Debug by default and
  accepts exactly one SQL argument, file, or stdin stream. Debug permits writes for development;
  durable, replayable schema changes should still use a migration plus `sxq db push`.
- `sxq db logs [--type <type>] [--since <range>] [--filter <text>] [--limit <n>] [--json]` queries
  superun Cloud logs. Use `sxq db logs --help` for the supported log types and time ranges.
- Add `--prod` to `db query` or `db logs` only when the linked project has isolated deployment
  enabled. Without `--prod`, isolated projects query Debug and may write. With `--prod`, they query
  Production and both CLI and backend enforce read-only SQL. If isolated deployment is not enabled,
  `--prod` fails instead of silently querying the current database.

## Rules of thumb

1. Run `sxq pull` before editing if the project may have changed remotely (e.g. the user also
   edits on the superun web UI).
2. After pushing code changes the user wants to see: `sxq preview` for a preview; only run
   `sxq deploy` when they ask to go live, then leave the final confirmation to the user in the browser.
3. `deploy --status` is read-only and always safe for checking state.
4. Exit code 0 means the requested CLI action succeeded. For `sxq deploy`, it only means the
   release confirmation page was opened, not that the project was released. Non-zero exit prints
   an actionable error message on stderr — read it before retrying.
5. Never commit or expose the contents of `.sxq/` (it contains the sessionId and session
   metadata; anyone with the sessionId may be able to read project files).
