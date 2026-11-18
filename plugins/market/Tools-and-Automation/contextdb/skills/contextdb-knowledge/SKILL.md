---
name: contextdb-knowledge
description: contextdb 知识库高频操作（查询 / 浏览 KB / 上传或更新文档）和命令速查。当用户提到"查知识库 / 查 KB / 搜知识库 / 查 KB chunks / 上传到 KB / 灌进知识库 / 更新 KB 文档 / 列出知识库 / 列出 KB / 看文档 / 建知识库 / 建 KB"等场景时使用。配套 contextdb-memory 处理长期记忆。
---

# contextdb Knowledge Base 操作

## 1. 什么时候用这个 skill

用户在做"查/灌/列/更新知识库"的任何动作时进这个 skill。触发关键词：**查知识库 / 查 KB / 搜知识库 / 查 KB chunks / 上传到 KB / 灌进知识库 / 更新 KB 文档 / 列出知识库 / 列出 KB / 看文档 / 建知识库**。

- 用户想**找已有 KB 里的内容** → §2 recipe 1
- 用户**不知道有哪些 KB** → §2 recipe 2
- 用户想**了解某个 KB 收了哪些文档** → §2 recipe 3
- 用户要**新建/上传内容** → §2 recipe 4/5
- 用户要**更新已有文档** → §2 recipe 6/7

配套 skill：**contextdb-memory**（长期记忆操作）。两者用同一份 `~/.ctxdb/ctxdb.json` 配置和同一个 `--agent` 路由。

## 知识库定位参数

- `--kb-name=<名字>` 按精确名字定位，`--kb-id=<ID>` 按 ID 定位；二者互斥，不猜类型，不在失败后改用另一种解释。
- 搜索多个 KB 的主要用法：`ctxdb kb search "<query>" --kb-name=库1,库2 --agent=qoder`；已知 ID 时用 `--kb-id=id1,id2`。重复参数只作兜底，按出现顺序合并去重。
- 除搜索外，本 Skill 中的 KB 操作只接收一个库。显式空值、名字与 ID 混用会报错；不要删掉筛选条件重试。
- 名字含逗号时用 KB ID。ID 来自 `kb list` 或当前响应；自动化与修改操作优先保存并使用 ID。需要转成 ID 时由 CLI 精确解析，解析不代表绕过最终接口鉴权。
- 创建的名字与 `kb update --name=<new-name>` 是业务字段；document-ID 更新不需要再传 KB，也不能与 KB/文档名/路径逻辑键混用。

## 2. 高频 recipes

> 命令里的 `--agent=qoder` 是当前 skill 安装目标。不要把示例改成 `qoder`；如果读到未替换的双花括号 agent 模板，先按 §6 判定真实 agent，再替换成 `qoder` / `qoderwork` / `qwenwork` / `codex` / `claude` / `opencode` / `hermes` / `workbuddy` / `default`。

### Recipe 1：在已知 KB 中查内容（最常见）

**场景**：用户问"X KB 里关于 Y 的内容"、"在知识库 Z 查一下 W"。

```sh
ctxdb kb search "<query>" --kb-name=<kb-name> --top-k=6 --agent=qoder
```

返回两类信息：

- `chunks`：可用于回答和引用的文档证据；默认项为 `{content, score}`，保持服务端顺序。`score` 只在文档 chunk 之间比较。
- `graph_context`（可选）：图谱合成的关系上下文，固定含 `type: "graph_context"`、`knowledge_base_ids`、`citation_eligible: false`。它用于理解实体关系和生成追检词，**不是可直接引用的文档证据**，也没有可与 chunk 比较的 score。

需要引用来源时，初查或追检加 `--verbose`；空结果时见 §5 注意事项 4。

#### 图增强的一层追检

初查已返回足够文档证据时直接回答，不额外检索。证据不足但 `graph_context` 暴露了具体实体、指标、配置项或关系时：

1. 从 `graph_context` 选最多 3 个与问题直接相关的实体/关系组合，分别改写为精确 query；不要把整段图内容原样当 query。
2. 对这些 query 最多执行**一层** `ctxdb kb search`，沿用原 KB 范围；需要引用时加 `--verbose`。
3. 合并初查与追检的 `chunks`，按 `doc_id` 优先、其次 `doc_name + content` 去重。最终结论和引用只来自这些文档 chunks。
4. 追检结果里的 `graph_context` 只作辅助理解，**不再据此递归发起下一层检索**。
5. 找到直接证据，或追检没有带来新文档时立即停止。一次追检最多 3 个 query。

**何时不适用**：用户没指定 KB → 先走 recipe 2 列出来确认。

### Recipe 2：列出所有 KB（不知道有哪些）

**场景**：用户问"有哪些知识库"、"列一下 KB"，或本身在写 recipe 1 之前需要确认 KB 名。

```sh
ctxdb kb list --agent=qoder
```

返回 `knowledge_bases` 数组，每项含 `name` / `id` / `document_count`。跨多 KB 查 chunk 时把 `name` 拼起来：`--kb-name=a,b,c`。

**何时不适用**：hook 已注入 `<available-knowledge-bases>` 块时，直接读那个块更省一次调用（见 §4）。

### Recipe 3：列出某 KB 的文档清单

**场景**：用户问"X KB 收了哪些文档"、"X KB 里有几篇"。

```sh
ctxdb kb documents-list --kb-name=<kb-name> [--sort-by=created_at] [--sort-order=asc|desc] [--fields=name,created_at,ingest_status,size_bytes,updated_at] --agent=qoder
```

返回 `documents` 数组，每项含 `name` / `id` / `size`。

**何时不适用**：用户要的是文档**正文**而不是清单 → 走 recipe 1 用 `kb search`（见 §5 注意事项 1）。

### Recipe 4：灌一段文字进 KB

**场景**：用户说"把这段记进 X KB"、"上传这段文字到知识库 Y"。

```sh
ctxdb kb upload-text --kb-name=<kb-name> <doc-name> --text="<body>" --agent=qoder
```

副作用操作。命令默认在服务端接受文档后立即返回；此时
`ingest_status=processing` 只表示已受理，不表示入库成功。调用方必须等到文本可检索时加
`--wait`。**用户没明示 KB 名前先 recipe 2 列出来确认**（见 §5 注意事项 3）。KB 不存在会直接报错，不自动创建。

**何时不适用**：内容是本地文件 → recipe 5。

### Recipe 5：上传本地文件到 KB

**场景**：用户说"把 X.pdf 上传到 Y KB"、"灌这个文件进知识库 Z"。

```sh
ctxdb kb upload-file --kb-name=<kb-name> <local-path> --agent=qoder
```

文件格式和大小限制由服务端决定，CLI 不维护本地允许列表；未知扩展名也会提交给服务端
判断。图片（png / jpg / jpeg / gif / bmp / webp / tiff / tif / svg）、音频、视频和
复杂文档（pdf / doc / docx / ppt / pptx / xls / xlsx / epub）都是知识库文件上传的
支持对象；格式准入没有封闭白名单，一律以服务端判定为准。服务端现行单文件大小分四档：
复杂文档与图片 500 MB、文本与代码 20 MB、音频 10 MB（约 5 分钟）、视频 2 GB；
超过 500 MB 自动走分片上传。控制台上传入口另有更严限制（单文件 1 B～2 MB），
与 API/CLI 口径不通用。CLI 先尝试普通流式上传，服务端明确要求时会自动切换为分片上传。默认在服务端接受
文档后立即返回；调用方必须等到 chunking 结束时加 `--wait`。`--no-wait` 仍可使用，
行为与默认值相同（见 §6）。分片 init、part、complete 当前均为单次请求，超时或断网后
不会自动重试，以免服务端已成功但响应丢失时产生重复副作用。

把图片写入知识库走本命令；`ctxdb memory add --image` 是图文记忆链路，只收静态
PNG / JPEG / WebP，两条链路的格式与大小口径不得互相套用（图文记忆见
contextdb-memory skill）。

**何时不适用**：要上传的内容是字符串而非本地文件 → recipe 4。

### Recipe 6：更新已有文本文档

**场景**：用户明确要替换某个已存在 KB 文本文档的内容。

```sh
ctxdb kb update-text <document-id> --text="<new-body>" --agent=qoder

# 只有拿不到精确 document ID、但已知完整逻辑键时才用：
ctxdb kb update-text --kb-name=<kb-name> --doc-name=<logical-name> --text="<new-body>" [--file-path=<logical-parent-path>] --agent=qoder
```

已有精确 `document-id` 时优先用第一种，不需要再向用户索取 KB，也不要同时传
`--kb-name` / `--doc-name` / `--file-path`。服务端会从文档 ID 校验权限并解析所属 KB。
命令返回的 `document.id` 是后续更新的新权威 ID：内容变化时通常会换 ID，相同内容也可能
复用原 ID，Agent 都必须以本次返回值为准。只有拿不到 ID、但已确认完整 **KB + 文档名 +
`file_path`** 逻辑键时才用第二种；目标信息不完整时先核对或向用户确认，不能模糊猜测。
重复调用 `upload-text` 是创建冲突，不会自动转成更新。

### Recipe 7：更新已有文件文档

**场景**：用户用新的本地文件内容替换某个已存在 KB 文件文档。

```sh
ctxdb kb update-file <document-id> <local-path> --agent=qoder

# 只有拿不到精确 document ID、但已知完整逻辑键时才用：
ctxdb kb update-file <local-path> --kb-name=<kb-name> [--doc-name=<existing-logical-name>] [--file-path=<logical-parent-path>] --agent=qoder
```

ID 模式只用 `document-id` 定位远端文档，本地文件名只是上传的物理文件名；替换文件改了
文件名也不需要补远端名称或 KB。逻辑键模式下，远端逻辑文档名默认取本地文件名；若替换
文件名不同，必须用 `--doc-name` 继续传已有逻辑名。两种定位方式不能混用。分片更新只在
init 使用 PUT，part/complete 保持原协议；网络结果不明确时不自动重试或删除旧文档。
成功后同样必须保存返回的 `document.id`，不要继续沿用输入 ID。

`--file-path` 始终使用连字符，映射服务端 `file_path`：创建时保存逻辑父目录，逻辑键更新时匹配已有路径，不是新路径或本地路径。省略表示空父目录；ID 更新不能同时提供它。例如：

```sh
ctxdb kb upload-file ./draft.md --kb-name=Team --doc-name=guide.md --file-path=guides --agent=qoder
ctxdb kb update-file ./revised.md --kb-name=Team --doc-name=guide.md --file-path=guides --agent=qoder
```

`./revised.md` 是本地读取路径，`guides` 是远端已有逻辑父目录。无值开关如 `--wait` / `--review-enabled` 不接受 `=true` / `=false`；正反开关不能并用。关闭评审用 `--no-review-enabled`。
评审记录和模板分别使用对应的位置 ID；不要把 KB ID 当作评审记录或模板 ID。


## 3. 命令速查

`--agent=<name>` 必填；详细解析链见 §6。其他 advanced flag 见 §6。

| 子命令 | minimal signature |
|---|---|
| `kb entity-create / entity-update` | `ctxdb kb entity-create --help` / `ctxdb kb entity-update --help` |
| `kb relation-create / relation-update` | `ctxdb kb relation-create --help` / `ctxdb kb relation-update --help` |
| `kb entity-delete` | `ctxdb kb entity-delete --kb-id=<kb-id> --entity-id=<id> --yes --agent=<name>` |
| `kb relation-delete` | `ctxdb kb relation-delete --kb-id=<kb-id> --relation-id=<id> --yes --agent=<name>` |
| `kb search` | `ctxdb kb search "<query>" --agent=<name>` |
| `kb list` | `ctxdb kb list --agent=<name>` |
| `kb documents-list` | `ctxdb kb documents-list --kb-name=<kb-name> [--sort-by=created_at] [--sort-order=asc|desc] [--fields=field1,field2] --agent=<name>` |
| `kb document-get` | `ctxdb kb document-get --kb-name=<kb-name> <doc-id> --agent=<name>` |
| `kb create` | `ctxdb kb create <kb-name> --agent=<name>` |
| `kb get` | `ctxdb kb get (--kb-id=<kb-id> \| --kb-name=<kb-name>) --agent=<name>` |
| `kb update` | `ctxdb kb update --kb-id=<kb-id> [--name=<new-name>] --agent=<name>` |
| `kb delete` | `ctxdb kb delete (--kb-id=<kb-id> \| --kb-name=<kb-name>) --agent=<name>` |
| `kb upload-text` | `ctxdb kb upload-text --kb-name=<kb-name> <doc-name> --text="<body>" --agent=<name>` |
| `kb upload-file` | `ctxdb kb upload-file --kb-name=<kb-name> <local-path> --agent=<name>` |
| `kb update-text` | `ctxdb kb update-text <document-id> --text="<body>" --agent=<name>` |
| `kb update-file` | `ctxdb kb update-file <document-id> <local-path> --agent=<name>` |

图谱写命令的 `--kb-id` 必须是 KB ID；用 `entities` 和 `relations --verbose` 获取实体/关系 ID。
create/update 需要完整可编辑字段，update 是全量替换，先回读再修改；空描述和空列表必须显式传入。
删除不可恢复，实体删除会级联清除全部入边和出边，关系删除保留两端实体。确认用户授权及精确 ID 后
才使用 `--yes`；省略确认时不会发送删除请求。命令结果不明确时先回读，不要直接重试。

所有命令 JSON 写 stdout、错误写 stderr 非零退出码。

## 4. Hooks 感知

**`<available-knowledge-bases>` 块**：UPS / SessionStart hook 注入到 system context；存在时直接列出 workspace 内所有 KB 名（省一次 `kb list` 调用）。可直接喂给 `--kb-name=<name>`。

**`<recalled-memories>` 块**：是 contextdb-memory 的产物，但 `memory search --knowledge` 会复用同样的 retrieval 路径。两块独立。

**`<external-knowledge>` 块**：开启 KB 自动召回时，内部按 `## 图谱合成上下文` / `## 文档证据` 分区。图谱区只用于关系理解和检索导航，文档区才是回答与引用证据；图谱区被独立限制长度，不会挤掉已选中的文档证据。

**B-3c 守卫**：含 `kb upload-text` / `kb upload-file` / `kb update-text` / `kb update-file` 的对话轮次，其内容**不会**被 autoCapture 写入记忆（防文档原文混进记忆桶）。

**纯 CLI 模式**：对话里没有上面任何块 → 说明当前不在 hook 环境（agent 是裸 CLI 调用），所有信息只能主动调命令拿。

## 5. 注意事项

### 注意事项 1：`kb document-get` 只返 metadata，**不返正文**

- **现象**：想读文档内容，调 `kb document-get` 拿到的只有 `{id, name, size, upload_time, tags}`，没 `content` 字段
- **根因**：服务端当前只暴露元信息端点；获取正文需走 chunk 检索
- **正确做法**：用 `kb search "<关键词>" --kb-name=<name>` 拿 chunks，或 `kb documents-list --kb-name=<name>` 后浏览返回的内嵌 chunk（如有）

### 注意事项 2：解析 JSON 用 `jq`，**不要 inline `python3 -c`**

- **现象**：在 shell 里写 `ctxdb kb list | python3 -c "import json,sys; ..."` 经常因为单/双引号嵌套 escape 失败
- **根因**：shell + python -c 的引号是两层独立 escape，组合时极容易漏
- **正确做法**：`ctxdb kb list --agent=qoder | jq '.knowledge_bases[].name'`；jq 表达式在单引号里不需要 escape

### 注意事项 3：创建和逻辑键更新没明示 KB 名前必须先确认

- **现象**：用户只说"把这段记进知识库"没指定 KB，agent 直接用了某个猜的 KB 名 → 写到错的桶
- **根因**：写命令不会跟 agent 二次确认；KB 不存在时报错，但**KB 名拼错却恰好命中另一个真实 KB**时会静默写错
- **正确做法**：`upload-*` / `create` / 逻辑键 `update-*` 在用户没明示 KB 时，必须先
  `kb list` 拿候选清单并确认；精确 document-ID 更新已经绑定目标，不再额外要求 KB

### 注意事项 4：`kb search` 空结果时降阈值再试一次

- **现象**：query 明明跟内容相关，但 `chunks: []`
- **根因**：默认 `--threshold=0.4`，短 query / 关键词偏冷时打不到
- **正确做法**：降到 `--threshold=0.2` 或 `--threshold=0.3` 重试一次再判定真的没命中；仍空才放弃

### 注意事项 5：`upload-*` 不会自动建 KB

- **现象**：`kb upload-text foo bar --text=...` 报错 "kb 'foo' not found"
- **根因**：上传命令只写已有 KB，**不会**为了你 implicit 建一个
- **正确做法**：先 `ctxdb kb create foo --agent=qoder`，再 upload

## 6. 高级参数

### `kb search` 全部 flag

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--kb-name=<name1,name2>` | 按名字限定搜索的 KB，逗号分隔；与 ID 参数互斥 | 搜所有 |
| `--kb-id=<id1,id2>` | 按 ID 限定搜索的 KB，逗号分隔 | 搜所有 |
| `--top-k=N` | chunk 数上限 | 6 |
| `--threshold=F` | 相关度阈值 | 0.4 |
| `--verbose` | 每个 chunk 加 `doc_name` / `kb_id` / `doc_id` / `tags` | false |
| `--raw` | 服务端原始响应（13+ 字段，图结果仍混在 `chunks`，含 tokenizer 细节） | false |

### `kb upload-*` / `kb update-*` 全部 flag

| 参数 | 说明 |
|------|------|
| `--kb-name` / `--kb-id` | 按精确名字或 ID 定位单个 KB；逻辑键更新时不能与 document ID 混用 |
| `--doc-name` | `upload-file` 的逻辑文档名，或逻辑键更新的精确文档名；ID 更新不使用 |
| `--file-path` | 创建/逻辑键更新时 KB 内的逻辑父目录；ID 更新不使用 |
| `--wait` | 等到 ingest 成功、失败或达到原有超时；需要等待处理完成时使用 |

`--wait` 与 `--no-wait` 互斥。无等待模式返回的
`ingest_status=processing` 不能当作终态成功。

### `kb create` 全部 flag

| 参数 | 说明 |
|------|------|
| `--description` | 知识库描述 |
| `--graph-enabled` / `--no-graph-enabled` | 创建时显式开启或关闭知识图谱 |
| `--review-enabled` / `--no-review-enabled` | 创建时显式开启或关闭知识评审 |

### `kb get` / `kb update` / `kb delete`

- `get`、`update` 和 `delete` 必须且只能传 `--kb-id` 或 `--kb-name` 之一。
- `update` 还至少传 `--name`、`--description`、图谱开关或评审开关之一。
- 删除后用 `kb list` 回读，确认目标不存在。

### `kb list` / `kb documents-list` / `kb document-get`

`kb documents-list` 可用 `--sort-by`、`--sort-order` 对常用文档字段排序，并用逗号分隔的 `--fields` 缩减大列表输出；其他两个命令无额外 flag（除通用参数）。

### 通用参数

| 参数 | 说明 |
|------|------|
| `--agent=<name>` | **必填**。指定操作哪个 agent 的配置桶（`qoder` / `qoderwork` / `qwenwork` / `codex` / `claude` / `opencode` / `hermes` / `workbuddy` / `default`） |

`--agent` 解析顺序：
1. 命令行显式 `--agent=<name>` → 用它
2. 缺省 → 读 `CTXDB_AGENT` 环境变量
3. env 也没有 → 落到 `"default"` 桶
4. 新版本 `/contextdb:setup` 会在 `agents.default` 缺失时复制当前 agent 配置作为兜底
5. 若 `"default"` 桶仍不存在或未配置完整 → exit 2 "config incomplete for agent default"

## 7. 配置

- 配置文件：`~/.ctxdb/ctxdb.json`，分 `agents.<name>` 段（`qoder` / `qoderwork` / `qwenwork` / `codex` / `claude` / `opencode` / `hermes` / `workbuddy` / `default`），互不复用
- 配置命令：`/contextdb:setup`
  - 带 `--agent` 时还会装 hooks + skill；若 `agents.default` 缺失，会复制当前 agent 配置作为 CLI 兜底
  - `--agent default` 只写 `agents.default` 段（仅 CLI 用，不装 hooks / skill）
- 连接检查：`ctxdb ping --agent=<name>`
- 状态查看：`ctxdb status --agent=<name>`
