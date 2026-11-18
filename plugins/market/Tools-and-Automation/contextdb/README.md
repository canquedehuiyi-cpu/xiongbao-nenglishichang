# ContextDB for Qoder

为 Qoder 接入阿里云 ContextDB 的云端上下文，让企业级知识库与长期记忆参与每一次对话。

## 主要能力

- **企业级知识库**：查询、浏览和管理知识库文档，让回答参考团队已有的知识与经验；云端支持知识库知识图谱。
- **自动上下文接入**：通过 Qoder 原生 Hooks，在每轮对话前自动召回知识库内容与相关记忆，对话结束后自动沉淀可复用的信息。
- **知识与记忆整理**：ContextDB 云端支持多级记忆整理，以及将记忆提炼成文、沉淀至知识库，让零散经验成为可复用的知识。
- **私有 Skills**：发现、加载和管理私有 ContextDB Skills，复用团队的工作方法。

## 使用示例

完成接入后，可以直接对 Qoder 说：

- “从知识库里查一下项目的部署流程。”
- “根据最近记忆帮我整理一份工作报告。”
- “把这次排查的结论整理成文档，保存到知识库。”

## 开始使用

1. 安装插件后，在任意会话里运行 `/contextdb:setup`。
2. 按提示在浏览器里完成授权。
3. 新开一个会话，知识库与记忆的自动召回、对话信息的自动沉淀即可生效。

依赖：Node.js 20 及以上，以及 `ctxdb` CLI（`npm install -g @aliyunrds/ctxdb`）。`/contextdb:setup` 会先征求你的同意再安装 CLI。

## 技能与命令

| 技能 | 用途 |
| --- | --- |
| `contextdb-knowledge` | 查询、浏览知识库，上传或更新文档。 |
| `contextdb-memory` | 主动记录、搜索、列出、修改和删除记忆。 |
| `contextdb-skills` | 发现并加载私有 ContextDB Skills，维护草稿和上传。 |

- `/contextdb:setup`：检查 CLI、登录、连接 Qoder，并验证连通性。
- `/contextdb:status`：只读健康检查。

## 工作方式

插件负责 Qoder 原生 Hooks、Skills 和命令，认证与数据读写由本机的 `ctxdb` CLI 完成。凭据保存在 `~/.ctxdb/` 下，插件不读取凭据。

`/contextdb:setup` 会让插件统一管理 Qoder 的 ContextDB Hooks 和 Skills，避免重复安装；CLI 继续负责认证与数据访问。

## 关闭与移除

| 你想要 | 操作 |
| --- | --- |
| 停止自动召回和沉淀，并移除技能和命令 | 在 Qoder 里禁用或删除本插件；新会话不再加载插件能力。CLI 和登录配置会保留。 |
| 清除 Qoder 的 ContextDB 绑定 | 运行 `ctxdb uninstall --agent=qoder`。它会删除 Qoder 配置段和可能残留的 CLI Hook、用户级 Skills，但不会删除本插件。 |
| 让服务端会话失效 | 运行 `ctxdb logout`。禁用或删除插件不会撤销服务端会话。 |
| 删除 CLI | 运行 `npm uninstall -g @aliyunrds/ctxdb`。 |

云端已有的知识库和记忆不会因为以上操作被删除。
