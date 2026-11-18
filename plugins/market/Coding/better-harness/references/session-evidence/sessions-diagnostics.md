# Sessions Diagnostics

Analyze session evidence as a local engineering workflow. Keep claims tied to
files, logs, transcripts, metrics, or observed behavior.

## Bundled Tools

Use `<cli> session-analysis` for structured session inventory before manual
JSONL inspection. Resolve `<cli>` through
[Harness Execution Routing](../../skills/better-harness/SKILL.md#step-1-resolve-scope-and-collect-the-evidence-bundle)
and use [Node Runtime Discovery](../agent-customize/qoder.md#node-runtime-discovery)
if PATH `node` is unavailable or fails validation:

```bash
# Discover evidence roots for a workspace
<cli> session-analysis sources --workspace /path/to/repo

# Session list with event counts and time range
<cli> session-analysis facets --workspace /path/to/repo --limit 20

# Compact insight cards and action candidates
<cli> session-analysis insights --workspace /path/to/repo --limit 20

# Read single session events
<cli> session-analysis show --workspace /path/to/repo --session-id <id> --include-events

# Diagnose the facts admission funnel and resolve candidate refs to local sessions
<cli> session-analysis facts --workspace /path/to/repo --selection all-eligible --limit 5 --debug --output /tmp/session-facts-debug.json

# Expand one debug locator with normalized commands and user text
<cli> session-analysis show --workspace /path/to/repo --session-id <id> --include-events --include-command-text --include-user-text
```

`facts --debug` is an operator-only diagnostic route. It exposes raw session
ids under `debug.locators`, so never send that envelope to the Session Evidence
agent or copy it into a report. Compare `admission`, `omitted`,
`populationCoverage`, `observationCoverage`, and `diagnosticFlags` before
opening only the candidate sessions needed to explain a surprising aggregate.
Command and user text flags are also local-only and must not be used for broad
transcript dumps.

Always pass the absolute target workspace and use the Qoder source notes below
before interpreting source roots or workspace bindings.
Fall back to direct JSONL reads when the script is unavailable or you need
user-prompt text extraction beyond event structure.

Treat any heuristic match as a candidate until the
important findings are manually checked.

## Coding Agent Session Research

Use this flow when Qoder project or user assets, Session Insights,
validation habits, workflow friction, or repeated coding-agent workflows are
in scope:

1. Resolve the absolute target workspace.
2. Run `<cli> session-analysis sources` before declaring roots absent.
3. Use the Qoder source notes to confirm which discovered roots and
   records bind to the target workspace.
4. Run `facets` with the same `--workspace` when `sources`
   reports enabled roots or sessions; otherwise record the source-probe result
   as the no-session boundary.
5. Run `insights` with the same scope when a user-facing report, recommendation,
   or review action needs the most important session signals. Use `facets` as
   aggregate evidence and `insights` as the compact card/action input.
   `insights.keySignals.longSessions` separates active long sessions from
   wall-span-only idle/resume sessions.
6. Use `show --include-events` only for bounded samples that support important,
   surprising, or high-impact claims.
7. For important aggregate items, expand the counter before turning it into a
   report claim. Use `facets.topHookCommands` or `insights.keySignals.topHookCommands`
   to identify hook command/script targets such as
   `PostToolUse -> node hooks/post-tool.mjs`; if no command is present in the
   event data, compare with configured hook inventory and label those commands
   as configured candidates instead of observed script execution.
8. For Goal, Plan, and Spec workflow evidence, use `planningSignals` from
   `facets` or `insights`. `workspace` signals prove current-project observed
   behavior; `user-global` signals prove user/global capability only. Static
   specification directories or goal database files are project-binding or
   state evidence, not observed Goal/Plan use unless matching session evidence
   exists.
9. Join static assets and session behavior explicitly: configured Rules, Skills,
   MCP, hooks, agents, or plugins are presence/content evidence; observed tool
   calls, hook events, permission decisions, validation commands, and errors are
   execution evidence.
10. Treat `long-active-review` as an outcome-review lead. Classify task family,
    outcome, and friction before considering a durable owner. Do not recommend delegation from wall-span-only sessions.
11. Keep all active claims within the collected evidence boundary. Imported
    historical provider labels are provenance only, not active source routes.
12. Route a reviewed repeated or schedulable candidate to
    `../loop-engineering/loop-discovery.md`. Route an authorized Skill decision
    to `../agent-customize/skill-discovery.md`.

## Evidence Boundary

- Workspace context: guidance files, project manifests, validation commands,
  local runtime config, rules or policies, MCP config, local skills, plugins,
  agents, hooks, and automations.
- Runtime home: Qoder settings, audit logs, run manifests, session
  indexes, skills, plugin state, and caches only when the requested scope makes
  user-home evidence relevant.
- Session traces: event timestamps, tool calls, permission decisions, hook
  events, validation commands, edit events, model attribution, errors, and
  transcript coverage gaps.
- Generated reports: source evidence JSON, usage JSON, bounded analysis packets,
  review packets, final reports, and quality-check output.
- For installed or global assets, run
  `<cli> agent-customize inventory`
  or the `<cli> coding-agent-practices inventory` wrapper, and treat its
  output as configured asset inventory, not session behavior.

## Output Rules

- For session behavior, reconstruct the timeline from audit events before
  drawing conclusions about validation, tools, permissions, or outcomes.
- Manually inspect important evidence; do not rely on aggregate counters alone for claims.
- Separate confirmed problems, likely risks, healthy checks, and coverage gaps.
- Recommend the smallest useful fix first: close context and validation gaps
  before broader automation, policy, or model changes.
- Do not infer runtime behavior from static files alone.
- Do not merge tools into one story unless comparison is explicitly requested.
- Do not treat loaded skill text as proof that a skill/tool was invoked.
- Do not recommend broad automation before fixing missing context or validation
  commands.
- Do not print raw secrets, tokens, private keys, prompts, or `.env` contents.

## Qoder Source Notes

Always pass the current absolute project path as `--workspace`. The
analyzer computes the workspace slug by replacing path separators with `-`, so
`/Users/example/workspace/better-harness` maps to
`~/.qoder/projects/-Users-example-workspace-better-harness/**/*.jsonl` plus matching
Qoder audit, run, log, state, transcript, and optional cache roots. Do not treat
unscoped files under `~/.qoder/projects` as current-project evidence.

Inspect relevant Qoder sources such as `~/.qoder/settings.json`,
`~/.qoder/audit/audit.jsonl`,
`~/.qoder/logs/runs/*/manifest.json`,
`~/.qoder/plugins/installed_plugins*.json`, and
`~/.qoder/plugins/cache/**/SKILL.md` only when user-home scope is authorized.
Connect those files back to the selected workspace sessions instead of treating
global counters as workspace evidence.

Static locations such as `.qoder/specs` are project-binding or state evidence,
not observed Goal, Plan, or Spec use without matching session evidence. Route
Qoder Rule, Hook, Skill, Custom Agent, or MCP tuning through
`../agent-customize/qoder.md`.
