# Connector Dependencies

This plugin depends on **no QoderWork Connector**, so no `.mcp.json` is provided.

Reason: every capability is delivered through the locally installed `workbench` CLI (invoked via Bash). Credentials are read from the local `~/.workbench/config.json`, and all traffic to Alibaba Cloud OpenAPI and the Workbench backend is initiated by the CLI itself — no MCP Server relay is involved.

## If a Connector is added later

Create a `.mcp.json` in the plugin root, for example:

```json
{
  "mcpServers": {
    "example-service": {
      "type": "streamable-http",
      "url": "{{USER_CONFIG}}",
      "_setup": {
        "configUrl": "https://example.com/mcp/get-url",
        "guide": "Open the link above, sign in, and copy your personal MCP Server URL.",
        "required": true
      }
    }
  }
}
```

Requirements: the referenced Connector must already be published in the QoderWork marketplace; `url` must use the `{{USER_CONFIG}}` placeholder so the user supplies the real endpoint during installation. Also declare the file in `.qoder-plugin/plugin.json` with `"mcpServers": "./.mcp.json"`, matching how the published GitLab and Postman plugins wire theirs up.
