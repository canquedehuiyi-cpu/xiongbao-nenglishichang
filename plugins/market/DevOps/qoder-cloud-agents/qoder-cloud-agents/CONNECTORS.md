# QCA connection

The `qca` entry in `mcp.json` connects this CN plugin to `https://mcp.qoder.cn/api/v1/mcp/servers/qca` using remote HTTP MCP.

Qoder supplies authentication through its shared login state with QCA. Users sign in to Qoder and enable the plugin; no separate PAT configuration or additional OAuth setup is required by this package.

Requirements:

- A Qoder account with Cloud Agents access.
- Network access to the configured MCP endpoint.

If tools are unavailable, check Qoder login, plugin status and connectivity. Available operations and arguments come from the current tool schemas; no fixed internal provider version or tool count is assumed.
