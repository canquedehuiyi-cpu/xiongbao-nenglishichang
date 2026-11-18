---
name: contextdb-memory
description: contextdb 长期记忆高频操作（主动记忆 / 搜索过往 / 列出审计 / 改删某条）和命令速查。当用户提到"记住 / 记一下 / 记一笔 / 写进记忆 / 查记忆 / 找记忆 / 列记忆 / 删记忆 / 改记忆 / 之前说过 / 上次提到"等场景时使用。配套 contextdb-knowledge 处理知识库。
---

# contextdb Memory 操作

## 1. 什么时候用这个 skill

用户在做"写/找/改/删长期记忆"的任何动作时进这个 skill。触发关键词：**记住 / 记一下 / 记一笔 / 写进记忆 / 查记忆 / 找记忆 / 列记忆 / 删记忆 / 改记忆 / 之前说过 / 上次提到**。

- 用户说"记住 X"、"帮我记一下" → §2 recipe 1
- 用户问"之前我们聊过 Y 吗"、"上次怎么说的" → §2 recipe 2
- 用户想**审计/排查**记忆是否写进去 → §2 recipe 3
- 用户要**改某条 / 删某条** → §2 recipe 4

配套 skill：**contextdb-knowledge**（知识库操作）。两者用同一份 `~/.ctxdb/ctxdb.json` 配置和同一个 `--agent` 路由。

## 2. 高频 recipes

> 命令里的 `--agent=qoder` 是当前 skill 安装目标。不要把示例改成 `qoder`；如果读到未替换的双花括号 agent 模板，先按 §6 判定真实 agent，再替换成 `qoder` / `qoderwork` / `qwenwork` / `codex` / `claude` / `opencode` / `hermes` / `workbuddy` / `default`。

### Recipe 1：主动记忆（"记住 X"）

**场景**：用户明确说"记住"、"帮我记一下"、"把这条写进记忆"。

```sh
ctxdb memory add "<text>" --agent=qoder

# 图文记忆；--image 可重复
ctxdb memory add "<text>" --image=<local-path> --agent=qoder

# 纯图片记忆
ctxdb memory add --image=<local-path> --agent=qoder
```

纯文本默认走 LLM fact-extraction；想原文存（项目代号 / 精确数值）加 `--no-infer`（见 §6）。图片会先转成文字事实，必须启用推理；服务端接收后返回 `PENDING` 和 `event_id`，命令不等待处理完成。图文记忆只收**静态 PNG / JPEG / WebP**；这与知识库文件上传（`ctxdb kb upload-file`，格式与大小由服务端判定，另支持文档 / 更多图片格式 / 音频 / 视频）是两条链路，两套口径不得互相套用（见 contextdb-knowledge skill）。

**何时不适用**：用户没明示要记 → 不要主动调；autoCapture 已在每轮结束 hook/plugin 自动跑（见 §4）。

**`event: NONE` 情况**：返回 `results: []` 时表示 LLM 觉得没新事实可提，是**正常返回不是错误**（见 §5 注意事项 1）。

### Recipe 2：找过去说过的（搜记忆）

**场景**：用户问"之前我们讨论过 X 吗"、"上次怎么说的"、"我之前提过 Y 没"。

```sh
ctxdb memory search "<query>" --agent=qoder
```

返回 `results` 数组，每项含 `id` / `memory` / `score`，按 score 倒序。top-5 默认。想同时搜知识库 chunks 加 `--knowledge`（见 §6）。

**何时不适用**：用户想看的是当前会话的原对话（不是提炼后的事实） → 走 transcript / 聊天记录而非这个命令；记忆桶里只有提炼版（见 §5 注意事项 2）。

### Recipe 3：浏览/审计记忆

**场景**：排查"刚才那条记进去没"、用户想看"系统记了我什么"。

```sh
ctxdb memory list --page-size=20 --agent=qoder
```

返回 `results` 数组（含 `total` 计数）。按 category 过滤加 `--category=<cat>`（见 §6）。

**何时不适用**：明确知道要找某关键词 → 用 recipe 2 更精准。

### Recipe 4：改/删某条记忆

**场景**：用户说"把那条改成 X"、"删掉之前关于 Y 的记忆"。

```sh
# 改
ctxdb memory update <memory-id> --text="<new-text>" --agent=qoder

# 删单条
ctxdb memory delete <memory-id> --agent=qoder
```

`<memory-id>` 必须先用 recipe 2 或 recipe 3 拿到。

**何时不适用**：用户说"清空所有记忆" → 走 `ctxdb memory delete --all`，**必须先跟用户二次确认**（见 §5 注意事项 3，不可逆操作）。

## 3. 命令速查

`--agent=<name>` 必填；详细解析链见 §6。其他 advanced flag 见 §6。

| 子命令 | minimal signature |
|---|---|
| `memory add` | `ctxdb memory add ["<text>"] [--image=<local-path> ...] --agent=<name>` |
| `memory search` | `ctxdb memory search "<query>" --agent=<name>` |
| `memory list` | `ctxdb memory list --agent=<name>` |
| `memory get` | `ctxdb memory get <memory-id> --agent=<name>` |
| `memory update` | `ctxdb memory update <memory-id> --text="<new-text>" --agent=<name>` |
| `memory delete` | `ctxdb memory delete <memory-id> --agent=<name>` <br> `ctxdb memory delete --all --agent=<name>` |

所有命令 JSON 写 stdout、错误写 stderr 非零退出码。

## 4. Hooks 感知

**`<recalled-memories>` 块**：UserPromptSubmit hook 在每个 user prompt 提交时自动用 prompt 作 query 跑 `memory search`，把命中的 top-K 记忆塞进 system context。存在 → 当前在 hook 环境（recall 自动）。

**autoCapture（Stop / post_llm_call / plugin）**：每轮对话结束后服务端异步提炼事实写记忆，**不用 agent 主动调** `memory add`。`memory add` 用于用户**明确强调**的内容（强加重要性）。

**B-3c 守卫**：含 `kb upload-text` / `kb upload-file` / `kb update-text` / `kb update-file` 的轮次，**autoCapture 跳过**这一轮（防新建或更新的文档原文进记忆桶）。

**纯 CLI 模式**：对话里没 `<recalled-memories>` 块 → 不在 hook 环境（裸 CLI），所有 recall / capture 只能主动 `ctxdb memory search` / `ctxdb memory add`。

## 5. 注意事项

### 注意事项 1：`memory add` 返回 `event: NONE` 是正常的

- **现象**：调 `memory add "<text>"` 后 `results` 为空数组、`event: NONE`
- **根因**：服务端默认走 LLM fact-extraction，LLM 判断这段话**没新事实可提**（已存在 / 太啰嗦 / 不构成事实）
- **正确做法**：想强制原文存加 `--no-infer`；如果用户输入的就是"已知事实重复"，告诉用户"系统认为这条不构成新事实"而不是判定写失败

### 注意事项 2：`memory search` 拿到的是**提炼后事实**，不是原对话

- **现象**：用户问"上次我说过 X 吗"，`memory search "X"` 返回的是 LLM 提炼出的事实，跟用户原话措辞不同；用户会觉得"这不是我说的"
- **根因**：autoCapture / `memory add` 默认走 fact-extraction，存的是提炼版
- **正确做法**：要拿用户原话 → 看 transcript / 聊天记录文件；记忆桶只能告诉你"用户曾说过类似 X 这个事实"

### 注意事项 3：`memory delete --all` 不可逆，**必须二次确认**

- **现象**：用户说"清空记忆"，agent 直接跑 `memory delete --all`
- **根因**：这条命令清掉四项有效业务 ID 交集范围内的**所有**记忆；`--agent` 只选择配置与凭据；服务端不存软删，事后无法恢复
- **显式范围**：使用 `--no-default-scope` 且未传 `--user-id` 时，不按业务用户限定删除范围，可能删除当前授权范围内多个业务用户的匹配记忆；仍受服务端权限约束。只删除某个业务用户时，显式传入 `--user-id=<id>`。
- **参数检查**：`memory delete` 在请求前拒绝未知参数；应用范围必须写为 `--app-id`，不能写成 `--app_id` 或 `--appId`。
- **正确做法**：跑之前必须跟用户确认"将清空这些有效 user_id / agent_id / app_id / run_id 交集范围内的记忆，不可恢复，确认吗？"；用户回 yes 才执行

### 注意事项 4：`--user-id` 覆盖配置桶，**别随手传**

- **现象**：调 `memory add "..." --user-id=foo` 后 `memory search` 找不到（搜默认桶）；或反过来 search 用了 `--user-id` add 没用 → 写一个桶搜另一个桶
- **根因**：`--user-id` 直接覆盖配置文件里 `agents.<name>.user_id`，桶就切了
- **正确做法**：除非你明确知道"现在要操作另一个 user 的记忆"，**否则不要传 `--user-id`**。让默认配置 user_id 兜底，写读自动一致

## 6. 高级参数

### 四项业务 ID（add / search / list / delete --all 通用）

| 参数 | 环境变量 | 配置项 | 未配置时 |
| --- | --- | --- | --- |
| `--user-id=<id>` | `CTXDB_USER_ID` | `user_id` | `default` |
| `--agent-id=<id>` | `CTXDB_AGENT_ID` | `agent_id` | 写入回退宿主 Agent 名；查询不回退 |
| `--app-id=<id>` | `CTXDB_APP_ID` | `app_id` | 省略 |
| `--run-id=<id>` | `CTXDB_RUN_ID` | 无，运行时值不落盘 | 手动省略；自动采集回退宿主会话 ID |

逐字段按参数 > 环境变量 > 配置 > 默认值解析；多个 ID 取交集，只覆盖一项时其余项仍继承。`--agent` 只选择本地配置与凭据，与业务 `--agent-id` 独立。查询和范围删除现在也继承配置中的 agent_id/app_id 及环境 run_id；写读应使用相同的预期范围。

环境 ID 为空或仅含空白时按未设置处理，继续使用配置/默认值；空白 `CTXDB_RUN_ID` 在自动采集时回退宿主会话 ID。非空 ID 原样保留；显式命令行 ID 的空值或仅空白仍会报错。

`search/list/delete --all` 还支持无值开关 `--no-default-scope`：四项业务 ID 仅使用本次显式参数，忽略所有继承值及 user 的内置 default。必须显式提供至少一个非空 ID，不改变认证、工作空间或成员身份。ID 缺值、空值、仅空白或重复参数都会在请求前报错。

```bash
# 仅覆盖 app，其他范围继续继承
ctxdb memory add "发布检查清单" --app-id=release-tools --agent=qoder
ctxdb memory search "发布检查清单" --app-id=release-tools --agent=qoder
# 只按 app 查，不继承任何其他 ID
ctxdb memory list --no-default-scope --app-id=release-tools --agent=qoder
# 已确认删除范围后，按显式 app/run 交集删除
ctxdb memory delete --all --no-default-scope --app-id=release-tools --run-id=trial-1 --agent=qoder
```

`ctxdb status --agent=qoder --json` 展示四项有效配置值及 `scope_sources`。宿主 agent/session 的兜底仅在写入/采集路径产生。`CTXDB_RUN_ID` 覆盖不改变会话去重、轮次完成判断或技能关联；自动召回及 warmup 不增加 run_id 过滤。

以下命令表中的高级参数均包含本节适用的通用范围参数。

### `memory add` 全部 flag

| 参数 | 说明 |
|------|------|
| `--image=<local-path>` | 添加本地静态 PNG / JPEG / WebP 图片；可重复，至少提供文字或一张图片；图片记忆不能与 `--no-infer` 同用；图片入知识库文件走 `ctxdb kb upload-file`，不适用本参数口径 |
| `--no-infer` | 跳过 LLM fact-extraction，原文直存（项目代号 / 精确数值用）|
| `--metadata=K1=V1,K2=V2` | 附加键值对元数据，逗号分隔 |
| `--user-id=<id>` | 覆盖配置 user_id（**慎用**，见 §5 注意事项 4）|

纯文本请求保持同步模式（`async_mode: false`），`event` 字段可能是 `ADD` / `UPDATE` / `NONE`。图片请求异步处理，返回 `status: PENDING` 和 `event_id`；这只表示服务端已经接收，后续仍用 `memory search` / `memory list` 查看生成的文字事实。

### `memory search` 全部 flag

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--top-k=N` | 正整数；只控制 memory 条数，不控制知识 chunks | 配置 top_k（初始 5） |
| `--threshold=F` | `[0, 1]` 内的有限数值；0 关闭过滤 | 配置 threshold（初始 0.4） |
| `--knowledge` | 同时搜知识库 chunks | false |
| `--verbose` | knowledge 模式下加 `doc_name` / `kb_id` / `doc_id` / `tags` | false |
| `--raw` | 服务端原始响应 | false |
| `--user-id=<id>` | 覆盖配置 user_id（**慎用**）| |

带 `--knowledge` 时返回 `knowledge.chunks`，条数由独立的配置 `knowledge_top_k` 控制。CLI search 会继承显式配置的 agent_id/app_id 和运行时 run_id；不会单独由 `--agent` 推导 agent_id。

### `memory list` 全部 flag

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--page=N` | 从 1 开始的整数页码 | 1 |
| `--page-size=N` | 整数，每页 1..200 条 | 100 |
| `--category=<cat>` | 按分类过滤 | |

### `memory get` / `memory update` / `memory delete`

`delete <memory-id>` 与 `delete --all` 必须二选一，不能混用或增加多余位置参数。
`delete --all` 继承四项有效业务 ID，或用 `--no-default-scope` 仅选择显式 ID。单条删除不能混用任何范围参数。`get --verbose` 保留旧版完整 Fact 详情查询；`update` 使用 `--text=<new-text>`。

无值开关（`--all`、`--knowledge` 等）不接受 `=true` / `=false`；省略表示使用默认行为，正反开关不能并用。`--auto-ingest-enabled=true|false` 是显式值参数，继续支持。
数值、user-id 等值参数显式缺值／空值时不能回退默认；页码和条数使用十进制整数，不接受 `0x10`、`1e2`、`1.0`。threshold 必须在 `[0, 1]` 内，可用十进制科学计数法，例如 `4e-1`；继承配置越界也会在请求前退出 2，可用合法 flag／运行时环境覆盖或修改 profile 配置纠正。带空格的 query、rule 用引号包住。
基础 memory 命令及 entity/rule 拒绝未知参数、重复单值和多余位置参数，输入错误退出 2；已声明的多值参数（例如 add 的 image）仍可重复。promotion 保持原有准入规则。
`memory rule set <rule>` 与 `--content=<rule>` 保留各自入口，但不能同时提供。
`--agent` 选本地凭据／配置；实体命令的 `--agent-id` 是独立业务字段。entity list/relations 未提供 user-id 时不注入配置桶。
entity list 的 `--app-id` / `--run-id` 仅在带 keyword 时由服务端应用；keyword 模式固定按 entity_name 升序，sort-by/order 不生效。
entity relations 的 max-nodes/max-edges 必须为 32 位十进制整数；省略使用服务端默认，已提供值保留 Core 的上下限钳制行为。显式 user-id/agent-id 缺值时报错，不自动扩大查询范围。

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

知识晋升的目标库使用 `--kb-id=<ID>` 或 `--kb-name=<精确名字>`，单库且互斥。`settings update --default-kb-id` 修改持久默认目标，不能用本次操作的 `--kb-id` 代替。
