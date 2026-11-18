# 连接器配置技能（tm-cad）

启用后每个 CAD 命令变成可直接调用的工具 `mcp__tm-cad__<command>`。
前置：对应平台的 DLL 已 NETLOAD（脚本按 CAD 自动选 TmAgent-ZCAD.dll / TmAgent-ACAD.dll），
否则 `/api/mcp` 不存在。两个 DLL 不随包分发（平台剥离二进制），由 `setup_tagent.py` 自动下载（见 `dll-download.md`）。

## 自动配置（推荐，分发场景）
```
python "scripts/setup_tagent.py"
```
脚本最开始（与 TmAgent 是否运行无关）自动维护本产品的 `~/.qwenworkcn/mcp.json`：
不存在→新建；`disabled:true`→改 `false`；已启用→不动。
输出 `connector.action`：`created`(需信任) / `enabled`(已启需信任) / `already_ok` / `skipped`(--no-connector) / `error`。

## 手动配置（脚本失败时的备选）
编辑本产品的 `~/.qwenworkcn/mcp.json`：
```json
{"mcpServers":{"tm-cad":{"type":"streamableHttp","url":"http://localhost:9876/api/mcp","disabled":false}}}
```
注意端点是 `/api/mcp` 不是 `/mcp`。写配置 ≠ 生效，仍需下方信任。

## 信任（安全闸门，用户手动一次）
连接器管理页（右上角）→ 找到 `tm-cad` → 点 **[信任]**。之后即启用。

## 验证
- MCP：`mcp__tm-cad__get_drawing_summary` 能返回即通。
- 等价握手：
```bash
curl -s -X POST http://localhost:9876/api/mcp -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"t","version":"1"}}}'
```
应返回 `serverInfo.name:"TmAgent-ZWCAD"`（中望）或 `serverInfo.name:"TmAgent-AutoCAD"`（AutoCAD）且 `capabilities.tools` 非空。

## 常见故障
集中收口在 **`faq.md`** §2 连接器类（信任后无工具 / 连不上 / 改 mcp.json 不生效），此处不重复。
