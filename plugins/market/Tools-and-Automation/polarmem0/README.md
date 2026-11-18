# PolarDB-PG 记忆管理

为 Qoder / QoderWork 接入 PolarDB-PG 记忆管理，让助手具备长时记忆：自动记录并召回项目上下文、技术决策与个人偏好。

## 前置要求

- 一套已部署的 PolarDB-PG 记忆管理服务，并已获取**服务端点**（`http://<host>:<port>`）与 **API Key**
- Node.js 20 及以上版本
- 当前已验证平台：Linux / macOS / WSL

## 安装与接入

装好本插件后，在会话中执行斜杠命令：

```
/polarmem0-setup
```

助手会引导你完成：检查 Node.js 版本 → 索取 API Key 与服务端点 → 安装 `polarmem0` CLI → 完成接入配置 → 验证连通性。也可以直接用自然语言触发，例如"帮我接入 PolarDB 记忆管理"。

接入过程实际执行的命令（也可手动执行）：

```bash
npm install -g @aliyunpolar/polarmem0
polarmem0 setup --agent qoder --api-key <API_KEY> --base-url http://<host>:<port>
```

QoderWork 用户将 `--agent` 改为 `qoderwork`。完成后**需新开一个会话**使配置生效。

## 接入后获得的能力

| 能力 | 说明 |
| --- | --- |
| 自动召回 | 每次提问前自动检索相关记忆并注入上下文 |
| 自动沉淀 | 每轮对话结束后自动将本轮内容提炼为长时记忆 |
| 手动管理 | `polarmem0 memory add\|search\|list\|update\|delete` 命令，也可直接用自然语言让助手代为操作 |

接入时会额外安装一份 `polarmem0-memory` skill，供助手在日常记忆操作时使用。

## 接入后落地的文件

| 路径 | 内容 |
| --- | --- |
| `~/.polarmem0/config.json` | 连接配置（含 API Key，请勿提交到代码库） |
| `~/.qoder/settings.json`（或 `~/.qoderwork/settings.json`） | 生命周期 Hooks 注册项，修改前自动备份，不影响已有配置 |
| `~/.qoder/skills/polarmem0-memory/`（或 `~/.qoderwork/skills/...`） | 日常记忆操作 skill |

## 验证与排查

```bash
polarmem0 status --agent qoder --json
```

`connected`、`hooks_installed`、`skill_installed` 三项均为 `true` 即接入成功。若记忆未自动召回或沉淀，请先确认已新开会话；配置不完整时重新执行一次 `polarmem0 setup --agent qoder` 即可修复，无需重新传入 API Key 与端点。

## 卸载

顺序不能颠倒，否则会残留失效的 Hooks 配置。

```bash
polarmem0 uninstall --agent qoder
npm uninstall -g @aliyunpolar/polarmem0
```

## 说明

- 本插件本身不包含任何服务端点或凭证，接入时由用户自行提供，存放于本机 `~/.polarmem0/config.json`。
- 端点使用 HTTP 时，凭证与记忆内容在网络上未加密传输，适用于 VPC / 内网环境；公网环境建议使用 HTTPS。
- 多人共用同一服务实例时，可在 `setup` 时追加 `--user-id <id>` 隔离各自的记忆。

## 许可

Apache-2.0
