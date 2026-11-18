# Postman Connector Setup

This plugin connects to the Postman MCP Server (`https://mcp.postman.com/mcp`). Authentication is via the `POSTMAN_API_KEY` environment variable.

## Required Environment Variable

| Variable | Required | Description |
|---|---|---|
| `POSTMAN_API_KEY` | Yes | Your personal Postman API key. Format: `PMAK-xxxxxxxx`. |

## How to Set

### 1. Generate an API key

1. Go to <https://postman.postman.co/settings/me/api-keys>
2. Click **Generate API Key**
3. Name it (e.g., "Qoder Plugin") and copy the value (starts with `PMAK-`)

### 2. Export the variable

```bash
# zsh
echo 'export POSTMAN_API_KEY="PMAK-your-key-here"' >> ~/.zshrc
source ~/.zshrc

# bash
echo 'export POSTMAN_API_KEY="PMAK-your-key-here"' >> ~/.bashrc
source ~/.bashrc
```

Persist it in your shell profile so Qoder picks it up at startup.

## Verify Connectivity

After setting the key and restarting Qoder, run the `/postman:setup` command. It will call `getAuthenticatedUser` via the Postman MCP server and greet you by name if auth succeeds.

If the call fails:

1. Check `test -n "$POSTMAN_API_KEY"` succeeds in the shell that launched Qoder; do not print the key.
2. Confirm the key has not been rotated/revoked at <https://postman.postman.co/settings/me/api-keys>.
3. Try regenerating a fresh key.

## Permissions / Scope

The API key inherits **all permissions of your Postman account** — workspaces, collections, mocks, monitors, environments. There is no scope-restricted token. Treat the key like a password and avoid committing it.

## Notes

- The hosted URL is `https://mcp.postman.com/mcp`. `mcp.json` forwards `Authorization: Bearer ${POSTMAN_API_KEY}` using the environment variable; a remote HTTP server cannot read your local shell environment directly.
- The original Cursor plugin manifest had no `variables` schema for this — Postman documents the env-var approach in their setup flow instead.
