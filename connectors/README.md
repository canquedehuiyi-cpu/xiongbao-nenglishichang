# connectors

- `local-configured/`：本机 `~/.qoder-cn/mcp.json` 的**脱敏**条目（凭据值一律 <REDACTED>，需使用者自行填入；本机绝对路径已匿名为 `<HOME>/`，原值只存在于本机配置中）。
- `market-metadata/`：市场连接器元数据 127 条（来源 catalog/mcp.json，Phase1 实测并集）。
  连接器本体是远程 MCP 端点配置，无内容包可下载，故移植=配置模板+元数据。
- 移植后需在 Qoder/Claude/Codex 等客户端里按各自格式引用，端点与鉴权由使用者提供。
