# Qoder Feature Overview and Official Examples

This document summarizes Qoder's main extension capabilities based on the
official Qoder documentation. Each feature keeps only a brief introduction and
copyable official examples. Replace placeholders in the examples with values
from your actual environment.

Use this file as the Qoder-specific feature taxonomy for Rules, Hooks, Skills,
Custom Agents, MCP, and Plugins. For shared owner selection, start from
`routing.md`. Keep claims bounded to observed Qoder surfaces.

## Rules

> Official documentation: https://docs.qoder.com/user-guide/rules

**Feature Summary**

Rules configure project-level context so Qoder can follow the project's
frameworks, code style, and team preferences in Chat, Inline Chat, and Agent
Mode. Rules are stored in `.qoder/rules` and can be shared with the repository
or kept local-only.

**Official Examples**

Manually reference a rule in Chat or Inline Chat:

```text
@rule
```

Example applicability description for the `Model Decision` type:

```text
Generate a unit test.
```

Example file pattern for the `Specific Files` type:

```text
*.md, src/*.java
```

Official rule types:

| Type | Purpose |
|---|---|
| `Apply Manually` | The user applies the rule manually with `@rule` |
| `Model Decision` | Agent Mode decides whether to apply the rule based on its description |
| `Always Apply` | Applies to all Chat and Inline Chat requests |
| `Specific Files` | Applies only to matching files |

## Hooks

> Official documentation: https://docs.qoder.com/extensions/hooks

**Feature Summary**

Hooks are automation scripts in the Qoder Agent lifecycle. A script receives a
JSON event context from `stdin` and controls whether execution should continue
through its exit code or standard output.

**Official Examples**

Safety note for Better Harness reports: the official snippets below demonstrate
Qoder hook mechanics, not final security posture. Do not echo full shell
commands, raw prompts, environment values, or suspected secrets in denial
messages. For copyable guardrails, prefer Node.js or Python entrypoints over
Bash plus `jq` so Windows, macOS, and Linux projects can use the same script.

Copy this as a Hook script, for example `check-command.sh`:

```bash
#!/bin/bash

input=$(cat)
tool_name=$(echo "$input" | jq -r '.tool_name')
tool_input=$(echo "$input" | jq -r '.tool_input')

if [ "$tool_name" = "Bash" ]; then
  command=$(echo "$input" | jq -r '.tool_input.command')

  if echo "$command" | grep -qE 'rm\s+-rf|DROP\s+TABLE'; then
    echo "Operation denied: $command" >&2
    exit 2
  fi
fi

exit 0
```

Register the script in the settings file:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "./check-command.sh"
          }
        ]
      }
    ]
  }
}
```

When finer control is needed, output JSON to `stdout` while exiting with
`exit 0`:

```bash
#!/bin/bash
input=$(cat)

echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"This operation is not allowed"}}'
exit 0
```

Common events and matchers:

| Event | Example Matcher | Purpose |
|---|---|---|
| `PreToolUse` | `Bash` | Check before tool execution |
| `PostToolUse` | `Write \| Edit` | Process after file writes or edits |
| `PostToolUseFailure` | `Bash` | Process after tool failure |
| `UserPromptSubmit` | No matcher required | Process when the user submits a prompt |
| `Stop` | No matcher required | Process after the Agent stops |
| `PreToolUse` | `mcp__.*` | Intercept MCP tool calls |

Exit code meanings:

| Exit code | Meaning |
|---:|---|
| `0` | Allow execution to continue |
| `2` | Block the current action |
| Other non-zero values | Report an error but continue execution |

## Skills

> Official documentation: https://docs.qoder.com/extensions/skills

**Feature Summary**

Skills are reusable Agent capabilities, usually described by a `SKILL.md` file.
Qoder can trigger a Skill automatically based on the user's request, or the user
can trigger one manually with `/skill-name`.

**Official Examples**

Automatic trigger example:

```text
Analyze the errors in this log file
```

Manual trigger example:

```text
/log-analyzer
```

Create a Skill with the built-in assistant:

```text
/create-skill <Skill description, e.g., convert Word documents to PDF>
```

When Qoder is in scope, compare an evidence-bound repeated workflow with the
actual content of plausible relevant built-ins, configured Skills, and project
owners. Suggest `/create-skill <workflow description>` only when the bounded
content-backed comparison supports no complete or extendable owner. Unknown or
uninspected content defers the suggestion; Skill count never changes it.

Keep IDE, CLI, SDK, and subagent surfaces separate. Current runtime discovery
and scope win over the maintained SDLC catalog: the SDK can suppress CLI
factory built-ins, and an Agent-preloaded Skill is not main-session coverage.
An uncollected runtime inventory is an omission; an observed disabled or
not-discovered capability is an explicit unavailable state. Catalog metadata
routes the conditional Skill Recommendation pass only and never establishes instructions
or a trial.
See the official SDK boundary at
https://docs.qoder.com/en/cli/sdk/python/skills.

Install a Skill from the skills.sh marketplace:

```bash
npx skills add vercel-labs/agent-browser -a qoder
```

Install a specific Skill from GitHub:

```bash
npx skills add https://github.com/anthropics/skills --skill skill-creator -a qoder
```

Skill file locations:

```text
~/.qoder/skills/{skill-name}/SKILL.md
.qoder/skills/{skill-name}/SKILL.md
```

Official scenario examples:

| Skill | Scenario |
|---|---|
| `log-analyzer` | Analyze log errors |
| `api-doc-generator` | Generate API documentation |
| `code-reviewer` | Perform code review |

## Custom Agents

> Official documentation: https://docs.qoder.com/extensions/subagent

Use [Custom Agent Review](custom-agents-review.md) for content
quality, tool-boundary, count, and report-summary checks. This section owns the
Qoder file format and invocation examples only.

**Feature Summary**

A Custom Agent is a Qoder Agent specialized for a specific task. Each Agent can
define its own name, description, tool permissions, model, Skills, MCP servers,
and system prompt.

**Official Examples**

Create an Agent with the built-in assistant:

```text
/create-agent <Your requirement, e.g., code review expert>
```

Agent file locations:

```text
~/.qoder/agents/<agentName>.md
${project}/.qoder/agents/<agentName>.md
```

Copy this as `code-review.md`:

```markdown
---
name: code-review
description: Code review expert, checks code quality and security
tools: Read, Grep, Glob, Bash
model: "[ModelName](modelId)"
skills:
  - {skillName1}
  - {skillName2}
mcpServers:
  - {mcpServerName1}
  - {mcpServerName2}
---

You are a senior code reviewer responsible for ensuring code quality.

Review checklist:
1. Code readability
2. Naming conventions
3. Error handling
4. Security checks
5. Test coverage
```

Natural-language trigger:

```text
Help me review the implementation of this interface
```

Manual trigger:

```text
/code-review
```

## MCP

> Official documentation: https://docs.qoder.com/user-guide/chat/model-context-protocol

**Feature Summary**

MCP connects external systems and data sources to Qoder. Qoder selects a
suitable MCP tool based on the user's input, the tool name, and the tool
description, then asks for confirmation before calling it.

**Official Examples**

Configure a remote SSE `fetch` server:

```json
{
  "mcpServers": {
    "fetch": {
      "type": "sse",
      "url": "https://mcp.api-inference.modelscope.net/******/sse"
    }
  }
}
```

Use the `fetch` server:

```text
Summarize this document: https://docs.qoder.com/user-guide/chat/overview
```

Configure a local STDIO `weather` server:

```json
{
  "mcpServers": {
    "weather": {
      "command": "npx",
      "args": [
        "-y",
        "@h1deya/mcp-server-weather"
      ]
    }
  }
}
```

Use the `weather` server:

```text
Check the weather in San Francisco, United States
```

Follow-up question:

```text
Are there any weather alerts in the United States tomorrow?
```

## Plugins

> Official documentation: https://docs.qoder.com/extensions/plugins

**Feature Summary**

Plugins package Skills, Commands, and MCP capabilities into installable units
that extend Qoder's domain knowledge or external tool integrations. The
official documentation states that Plugins are currently available only in
Quest.

For inventory-backed review, count a Plugin only when the installed index
supports it and `settings.json.enabledPlugins` does not disable it. A
settings-only entry is diagnostic, not installation evidence.

**Official Examples**

Capabilities a plugin can include:

| Component | Purpose |
|---|---|
| `Skills` | Provide specialized Agent capabilities for complex tasks |
| `Commands` | Provide commands or shortcut actions executable by the Agent |
| `MCP Servers` | Provide external tool or data source integrations |

Marketplace usage flow:

1. Open Marketplace in the IDE.
2. Select a plugin and open its detail page.
3. Review the Skills, Commands, or MCP Servers included in the plugin.
4. Click install.
5. Manage versions and enabled status in the Installed list.
6. Click `Try now` to start an Agent session and try the plugin capabilities.

View plugin capabilities after installation:

| Page | Visible Content |
|---|---|
| Qoder Settings / Skills | Skills introduced by the plugin |
| Qoder Settings / Commands | Commands introduced by the plugin |
| Qoder Settings / MCP | MCP servers introduced by the plugin |

## Documentation Links

- Rules: https://docs.qoder.com/user-guide/rules
- Hooks: https://docs.qoder.com/extensions/hooks
- Skills: https://docs.qoder.com/extensions/skills
- Custom Agents: https://docs.qoder.com/extensions/subagent
- MCP: https://docs.qoder.com/user-guide/chat/model-context-protocol
- Plugins: https://docs.qoder.com/extensions/plugins

## Global Assets

Use this reference when a readiness run, screenshot, or user request points to
Qoder settings, installed assets, global skills, user hooks,
commands, agents, plugins, MCPs, or memories. Treat this as a configured asset
inventory, not a session behavior report.

### Global Assets: Scope

- Project assets: `.qoder`, `.agents`, project rules,
  skills, agents, commands, hooks, workflows, settings, and MCP config.
- User/global assets: `~/.qoder` skills, hooks, commands, agents, rules,
  settings, and MCP config. Qoder also recognizes the
  compatible `~/.agents/{skills,agents,commands}` surfaces.
- Plugin/marketplace assets: Qoder plugin caches and install evidence under
  `~/.qoder`, including plugin-declared Skills,
  MCPs, Commands, Hooks, Rules, and Subagents.
- Memories: `~/.qoder/memories/**` plus Qoder `SharedClientCache`
  `app-config.json` memory keys and `cache/db/*.db*` file presence.
- Session observed behavior: cite `<cli> session-analysis sources/facets`
  separately; configured assets do not prove runtime use.

### Global Assets: Inventory Command

Resolve `<cli>` through
[Harness Execution Routing](../../skills/better-harness/SKILL.md#step-1-resolve-scope-and-collect-the-evidence-bundle).

Run the read-only inventory for the default project plus user/global metadata
scope:

```bash
<cli> agent-customize inventory --workspace <absolute-target-path>
<cli> coding-agent-practices inventory --workspace <absolute-target-path> --include-memories --format markdown
<cli> coding-agent-practices asset-integrity --workspace <absolute-target-path> --language <en|zh-CN> --json [--include-memories]
```

Use `--qoder-home <path>` or `--shared-cache <path>` for fixtures, alternate
installs, or non-standard homes. Use the `agent-customize` command as the
Qoder configured asset source of truth; use the
`coding-agent-practices` wrapper when the report also needs the matrix shape or
Qoder memory metadata summary. For reports, project
`summary.practiceCoverageRows`; it resolves `~/.qoder` assets separately from
the active `SharedClientCache` MCP home, excludes runtime-only project MCP
metadata, and omits zero-count rows.

User/global asset metadata is included by default. Use
`--include-user-home=false` only for an explicitly project-only scan. This does
not authorize raw Memory bodies, credentials, or private transcripts. Qoder
does not treat `~/.agents/plugins/marketplace.json` as installed or executable
Plugin evidence.

Treat `.agents/agents` entries as configured compatibility evidence. Their
presence does not by itself prove full Task-Agent registration or runtime use.

The provider-labelled asset-integrity command reuses that inventory for a lightweight
second pass. It checks Memory filename-title collisions/similarity, enabled
Plugin canonical/display-name and non-empty capability-fingerprint overlap,
and Hook count/exact-duplicate/fan-out pressure when those surfaces are available. Treat exact name and fingerprint
matches as owner-review candidates and similar E2E/P7/P8-style Plugin names as
advisory families. Never edit a Plugin cache or disable a variant from naming
similarity alone.

### Global Assets: Evidence Levels

- **Configured**: path or settings entry exists.
- **Inspected**: metadata, frontmatter, settings sections, or plugin index was
  opened.
- **Observed**: session, audit, hook, permission, or tool event shows runtime
  use.
- **Backstopped**: CI, host policy, sandbox, or hook tests enforce the practice.

Report configured and inspected global assets as evidence, but do not claim a
Skill, Hook, Command, MCP, Plugin, Agent, Workflow, or Memory was used unless
session or audit evidence shows it. For the cross-asset Exists -> Routed ->
Applied -> Effective check, continue with
[Knowledge-Asset Review](knowledge-assets-review.md).

### Global Assets: Presence, Use, And Cleanup Eligibility

Customization Checkup projects the evidence ladder into these reader states:

- `observed`: mapped runtime use exists in the bounded scope;
- `configured-only`: configuration was inspected but runtime use was not in
  scope;
- `unobserved`: a bounded window did not contain mapped use;
- `candidate`: sufficiently covered, outside a new-install grace period,
  unshadowed, owner-mapped, and safe for a disable-first plan;
- `healthy`: configured/effective state and observation are consistent;
- `unavailable`: active source, identity, or coverage cannot be established.

No observed use in one workspace cannot make a user/global asset a cleanup
candidate. User/global cleanup needs an explicitly enabled user-global session
pass and a declared time/session window. Plugin use can be demonstrated by an
observed plugin-owned Skill, MCP tool, Command, Hook, or Agent only when stable
metadata maps the child to the plugin. Ambiguous ownership stays `unobserved`.

Keep generated runtime state, caches, merged MCP snapshots, logs, and encrypted
diagnostics read-only. Plan changes against author-owned files or supported host
CLI operations.

### Global Assets: Memory Boundary

Do not read raw memory text, private transcripts, auth files, token stores,
model catalogs, or database rows by default. For memories, summarize only:

- memory root existence and category/path counts
- memory-related config keys such as Qoder `memory.fetch.enable`,
  `memory.retrieve.enable`, `memory.file_memory.prompt.enabled`, and
  `memory.topictree.enable`
- database file presence such as `local.db`, `memory.db`, WAL, and SHM files
- drift or risk notes such as stale, duplicated, or sensitive-looking category
  names without printing content

If raw memory content is explicitly requested, treat it as sensitive user data
and ask for a bounded scope before opening files. For recall, stale-memory,
adoption, or learning-loop claims, continue with
[Memory Review And Learning-Loop Evidence](memory-review.md); metadata and
configuration never prove that a task retrieved or applied a memory.

### Global Assets: Report Projection

In `AI Agent Practices`, surface a compact matrix with these rows when the
inventory is in scope: Project assets, User/global assets,
Plugin/marketplace assets, Session observed behavior, and Memories. Each row
should show configured/inspected/observed status, strongest evidence, main gap,
and `Low`, `Medium`, or `High` confidence.

Current Harness coverage rows remain inventory-only. Project material
asset-integrity observations as ordinary grouped `findings[]` for `Memories`,
`Plugins`, and `Hooks`; do not add health status or evaluation fields to the
coverage rows.

## Node Runtime Discovery

Use this reference before running Better Harness Node-backed tools when `node` is
not available on `PATH` or `node --version` fails. Treat the resolved executable
as `<node>` in command examples.

Do not install Node, mutate PATH, or create symlinks as part of discovery.

### Node Runtime Discovery: Discovery Order

1. Use `NODE_REPL_NODE_PATH` or a user-provided Node path when present.
2. Use `node` from `PATH` only if `node --version` succeeds.
3. Prefer standalone Codex and Cursor helpers:
   - macOS Codex:
     `/Applications/Codex.app/Contents/Resources/cua_node/bin/node`
   - macOS Cursor:
     `/Applications/Cursor.app/Contents/Resources/app/resources/helpers/node`
4. Only use Electron-as-Node as a final fallback after validating that it runs
   as Node and exits quickly. For example:
   - macOS current app name:
     `ELECTRON_RUN_AS_NODE=1 "/Applications/Qoder.app/Contents/MacOS/Qoder" -e 'console.log(process.version)'`
   - macOS legacy app name:
     `ELECTRON_RUN_AS_NODE=1 "/Applications/Qoder IDE.app/Contents/MacOS/Qoder" -e 'console.log(process.version)'`
   - Windows PowerShell:
     `$env:ELECTRON_RUN_AS_NODE="1"; & "$env:LOCALAPPDATA\Programs\Qoder\Qoder.exe" -e "console.log(process.version)"`
   - Windows CMD:
     `set "ELECTRON_RUN_AS_NODE=1" && "%LOCALAPPDATA%\Programs\Qoder\Qoder.exe" -e "console.log(process.version)"`

Qoder app binaries are Electron launchers, not standalone Node helpers. Use them
only in Electron-as-Node mode, and skip them unless validation proves they
behave as Node.

### Node Runtime Discovery: Candidate Validation

Validate every candidate before using it:

```sh
"$NODE" -p 'JSON.stringify({node:process.versions.node,electron:process.versions.electron||null})'
```

Accept the candidate only when the command exits quickly, returns valid JSON,
and reports `node >= 22.22.0`.

For Electron-as-Node, set the host's Node mode if needed, run the same
validation with a short timeout, and require quick exit. If it launches the app,
hangs, or reports an older Node version, reject it.

### Node Runtime Discovery: Command Usage

After resolving `<node>` and the installed `<better-harness-root>`, use
`<cli>` as `<node> <better-harness-root>/scripts/better-harness.mjs`:

```sh
<cli> session-analysis sources --workspace <absolute-target-path> --format markdown
<cli> core-change-watch evidence-pack --cwd <repo> --json
<cli> harness report-quality --report <report.md>
```

When command execution becomes report evidence, cite the resolved runtime source
and version, for example `Node runtime: Qoder.app Electron-as-Node v24.x` or
`Node runtime: PATH node v22.22.0`.

If no candidate validates, ask the user to install Node.js `>=22.22.0` or
provide `NODE_REPL_NODE_PATH`.
