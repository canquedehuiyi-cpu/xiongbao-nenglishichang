# Postman (Qoder Plugin)

Full API lifecycle management inside Qoder. Sync Postman collections, generate typed client code, discover APIs, run tests, create mocks, improve docs, audit security, and analyze API agent-readiness. Powered by the Postman MCP Server.

## Origin

Repackaged from [`Postman-Devrel/cursor-postman-plugin`](https://github.com/Postman-Devrel/cursor-postman-plugin) (official Postman DevRel community plugin). License: Apache-2.0. The Cursor plugin itself mirrors the [Postman Plugin for Claude Code](https://github.com/Postman-Devrel/postman-claude-code-plugin), which is Postman's source of truth for AI coding agent plugins.

## Components

### Skills (3, internal)

| Skill | Purpose |
|---|---|
| `postman-knowledge` | Postman concepts and MCP tool guidance. Auto-loaded when working with Postman MCP tools. |
| `postman-routing` | Auto-routes API/Postman requests to the correct command without prompting the user. |
| `agent-ready-apis` | Knowledge base on what makes an API "agent-ready" for AI consumption. |

> All three skills declare `user-invocable: false` — they are background context, not user-triggered. The user-facing entry points are the commands and the sub-agent.

### Commands (18)

| Command | Purpose |
|---|---|
| `/postman:deploy-flow` | Deploy a Postman Flow so it becomes triggerable, proposing and confirming a trigger path. |
| `/postman:docs` | Analyze, improve, and generate API documentation from Postman collections and specs. |
| `/postman:generate-client` | Generate typed client code from Postman collections. Reads your private APIs and writes production-ready code. |
| `/postman:generate-spec` | Generate or update an OpenAPI 3.0 spec by analyzing the API routes in your codebase. |
| `/postman:get-flow-run` | Inspect a Postman Flow run by its Run ID — per-block logs, the failing block, and status. |
| `/postman:learn` | Ask questions about Postman and how to accomplish workflows. Searches the official Postman documentation and learning resources. |
| `/postman:list-flows` | List Postman Flows in a workspace and resolve a flow name to its 24-character ID. |
| `/postman:mock` | Create Postman mock servers for frontend development. Generates missing examples, provides integration config. |
| `/postman:run-collection` | Run a Postman collection with the Postman CLI to verify your API endpoints, then parse and report results. |
| `/postman:search` | Discover APIs across your Postman workspaces. Ask natural language questions about available endpoints and capabilities. |
| `/postman:security` | Security audit your APIs against OWASP API Top 10. Finds vulnerabilities and provides remediation guidance. |
| `/postman:send-request` | Send a single HTTP request with the Postman CLI, then report the response. |
| `/postman:setup` | Set up Postman MCP Server. Configure API key, verify connection, select workspace. |
| `/postman:sync` | Sync Postman collections with your API code. Create collections from specs, push updates, keep everything in sync. |
| `/postman:test` | Run Postman collection tests, analyze results, diagnose failures, and suggest fixes. |
| `/postman:trigger-flow` | Trigger (run) a deployed Postman Flow with inputs, and deploy-then-trigger it if it isn't deployed yet. |
| `/postman:use-local` | Switch this plugin's Postman MCP server to LOCAL (stdio via the npx package), authenticated with your API key. |
| `/postman:use-remote` | Switch this plugin's Postman MCP server to the REMOTE hosted server, authenticated with your API key. |

### Sub-agents (1)

| Agent | Trigger | Model | Tools |
|---|---|---|---|
| `API Readiness Analyzer` | "Is my API agent-ready?", "Scan my API", "Analyze my spec" | `auto` (was `sonnet` in source — mapped to Qoder's auto tier) | Read, Glob, Grep, Bash, mcp__postman__* |

### Rules (1)

| Rule | Purpose |
|---|---|
| `postman-best-practices.md` | API design conventions for Postman-managed APIs (naming, HTTP semantics, OpenAPI). Source was `.mdc` (Cursor), renamed to `.md` for Qoder. Body unchanged. The Cursor `globs` frontmatter field is retained but has no effect under Qoder. |

### MCP Server (1)

```json
{
  "mcpServers": {
    "postman": {
      "type": "http",
      "url": "https://mcp.postman.com/mcp"
    }
  }
}
```

Authentication via `POSTMAN_API_KEY` environment variable. See [`CONNECTORS.md`](./CONNECTORS.md) for setup details.

## Setup

1. Install this packaged directory with `qodercli plugins install /path/to/postman` (CN: `qoderclicn`).
2. Set `POSTMAN_API_KEY` (see `CONNECTORS.md`).
3. Restart Qoder. Run `/postman:setup` to verify connectivity and pick a workspace.

## Adaptations from source

| Item | Original (Cursor) | Adapted (Qoder) | Reason |
|---|---|---|---|
| Sub-agent `model` | `sonnet` | `auto` | Qoder's `custom_agent_loader.go` only accepts `auto` / `ultimate` / `custom:xxx`. Mapping `sonnet → auto` preserves the original "default tier" intent. |
| Sub-agent `name` | `API Readiness Analyzer` | unchanged | Qoder accepts arbitrary name strings; preserved as-is. |
| Sub-agent `allowed-tools` | `Read, Glob, Grep, Bash, mcp__postman__*` | unchanged | All five names map cleanly via Qoder's `ClaudeToQoderToolMap`; MCP wildcard is preserved verbatim. |
| Rule file extension | `postman-best-practices.mdc` | `postman-best-practices.md` | `.mdc` is Cursor's "Markdown with Configuration" extension. Per [Cursor docs](https://cursor.com/docs/context/rules), the body is plain markdown; renaming to `.md` is safe and ensures Qoder treats it as a standard markdown rule file. |
| Manifest `variables` | declared in source | not used | Qoder has no equivalent UI prompt schema. `POSTMAN_API_KEY` documented in `CONNECTORS.md` instead. |
| Command frontmatter | `allowed-tools` (Claude format) | preserved verbatim | Qoder ignores unknown command frontmatter fields — commands work as plain markdown prompts. |
