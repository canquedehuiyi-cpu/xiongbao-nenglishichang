# qoder-usage · Qoder 使用统计

Qoder / Qoder CN 本地用量面板：统计条、一年活动热力图、近 7 / 近 30 日模型趋势与用量占比，可一键切换 **Token / 积分（Credits）** 模式。

## 口径

| 项 | 定义 |
|---|---|
| Token | `输入 + 输出`，不含 cacheRead/cacheWrite |
| 积分 | SQLite 每轮 `turn_credits` + 旧版会话日志的每请求 credits |
| 近 N 日 | 今天 + 前 N-1 个自然日（与热力图、X 轴对齐） |
| 最长聊天时长 | 单个会话内相邻消息间隔 ≤30 分钟的最长连续段 |
| 模型名 | 去掉 `byok:<uuid>/`、`magpie/...` 路径前缀与 `网关·` 前缀，同名（含大小写差异）合并 |

## 数据来源（全部本地，只读）

| 来源 | 内容 |
|---|---|
| `main.sqlite`（Qoder / Qoder CN） | 会话元数据、每轮 `turn_credits`、消息时间戳 |
| `~/.qoder(-cn)/projects/**/*.jsonl` | BYOK 模型的每请求 token、旧版内置模型 credits |
| `~/.config/magpie/usage.jsonl`（可选） | 经 magpie 网关的请求 token |

已知限制：桌面端直连的内置模型只有 Credits、没有 token 明细；网关只覆盖走网关的请求；BYOK 与网关同名模型会合并展示（`token.byModel` 仍保留 `网关·` 前缀字段供核对）。

## 开发

界面源码在 `ui/`（React 19 + TypeScript + Vite），构建为单文件 HTML 输出到 `app/main.html`：

```
cd ui
npm install
npm run dev     # 打开 http://localhost:5173/main.html，直接读本机真实数据
npm run build   # 产出内联 JS/CSS 的 app/main.html
```

`vite.config.ts` 里的 dev 中间件把 `buildStats` 结果喂给面板，支持 `?theme=light`、`?empty=1`、`?error=1`、`?client=qoder-cn`。

## 打包 / 安装

```
node pack.mjs ../qoder-usage-0.2.0.zip .qoder-plugin .mcp.json server app README.md
```

在 Qoder 设置中导入 zip，Qoder 与 Qoder CN 各装一份。安装后落盘 `~/.qoder(-cn)/plugins/cache/local/qoder-usage/<version>/`。

注意：
- 同版本不会覆盖旧目录，改版必须升版本号。
- server 启动时会缓存 `app/main.html`，重新导入后需重启 Qoder（或重载 MCP server）才会看到新界面。
