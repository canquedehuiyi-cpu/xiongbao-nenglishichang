# dify-canvas

Qoder 插件：在对话里直接读写、发布、试运行 Dify 工作流画布。

## 构成

| 组件 | 内容 |
| --- | --- |
| Skill | `skills/dify-canvas/SKILL.md` —— 操作流程、安全闸门、验收口径 |
| MCP | `.mcp.json` 声明 `dify-canvas` server（`npx -y dify-canvas-mcp`） |
| 其他 | 无 commands / agents / hooks / output-styles / bin，刻意不做 |

一个插件、一个 Skill：所有请求都收敛到同一条「读→dry-run→确认→写回」的工作流，没有第二个触发场景需要拆目录。

## 能力来源与出处

实际能力全部来自 npm 包 [`dify-canvas-mcp`](https://github.com/elegant01/dify-canvas-mcp)（发布版本 0.1.3），由其底层模块在实践中验证过：浏览器通道解析、草稿补丁 + 备份 + 自检、发布 hash 核对、草稿两阶段试跑。

本插件没有新写业务逻辑，只补齐了 Skill 层的操作规范（默认 dry-run、`expectedHash` 乐观锁、发布需单独授权、草稿试跑不进日志页）。未包含任何上游未实现的能力。

## 前置条件

- 本机 `node`/`npx` 在 PATH 上（首次运行会拉取 `dify-canvas-mcp`，不锁版本，跟随 npm latest）。
- 日常 Chrome 已登录目标 Dify 站点。凭据即浏览器登录态，插件不落盘任何 cookie 或 token。

## 首次使用

```
dify_instances                                  # 看已配置实例
dify_setup { alias: "prod", baseUrl: "https://<你的 dify 站点>" }
```

之后按应用名称操作即可，不需要 UUID。连接通道按 chrome-pool → 调试端口 Chrome → autoConnect → 专用 Chrome 顺序自动解析，正常情况零配置、零重启。

## 数据安全

- `dify_canvas_patch` 默认 dry-run，只返回 diff；`apply: true` 才写回。
- 写回前自动备份到 `~/.dify-canvas/backups/`，并自检悬空边、自环、`default_value` 类型、Code 节点参数一致性；不通过则拒写。
- 写后刷新页面核对渲染节点数；`dify_canvas_publish` 核对发布态 hash。
- 发布立即上线，需要单独授权。

## 已知边界

- 草稿试跑记录只写 workflow-runs，Dify 日志页看不到；需要对外留痕要发布后走 `/v1`。
- 只能改草稿已存在的节点内容，画布级的新增/删除节点与连线不在这个 MCP 的写入范围内。
- 需要 Chrome 允许远程调试；首次 autoConnect 会在浏览器里问一次授权，之后复用。

MIT.
