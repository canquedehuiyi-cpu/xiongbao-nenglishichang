---
name: miaoda-app-builder
displayName: 秒哒应用生成器
name_en: miaoda-app-builder
description: >-
  用自然语言在百度秒哒平台创建、修改、生成并发布网站、Web 应用、数据看板、SaaS 产品、管理后台、内部工具、落地页、交互网页、小游戏、微信小程序和原生 iOS / Android App，返回公网访问地址并可下载源码；也可直接产出研究报告、PPT 和数据分析文档。当用户说“做一个网站/网页/小程序/App/看板/后台”“帮我改一下秒哒应用”“把秒哒应用发布上线”“下载秒哒应用源码”或提到秒哒、Miaoda 时使用。需要配置 MIAODA_API_KEY。
description_en: >-
  Create, modify, generate and deploy websites, web apps, dashboards, SaaS products, admin panels, internal tools, landing pages, mini games, Weixin mini programs and native iOS / Android apps on Baidu Miaoda (秒哒) with natural-language instructions, then return the public URL or download the source code. Also produces research reports, PPTs and data analysis documents. Requires the MIAODA_API_KEY environment variable.
argument-hint: 要做的应用描述，或已有秒哒应用的修改需求
---

# 秒哒应用生成器

本技能让 Agent 通过自带的命令行脚本调用百度秒哒（https://www.miaoda.cn）平台，完成“描述需求 → 完善需求文档 → 生成应用 → 多轮修改 → 发布上线 / 下载源码”的完整任务。

## 适用场景

- 新建网站、Web 应用、数据看板、SaaS 产品、管理后台、内部工具、落地页、交互网页、小游戏、微信小程序、原生 iOS / Android App。
- 修改已在秒哒生成的应用，包括针对单个界面元素的精确修改（LGUI）。
- 把秒哒应用发布到公网并返回访问地址；下载应用源码或 Agent 生成的文件。
- 直接产出研究报告、PPT、数据分析文档等通用内容（不需要生成和发布）。

不适用：只想要一段代码片段、不打算使用秒哒平台的需求。

## 使用前准备

1. 打开[秒哒官网](https://www.miaoda.cn/)并登录，点击左下角头像 →「秒哒 Skill」→「复制密钥」。首次打开会自动创建 Key。点「刷新密钥」会使旧 Key 失效。Key 的权限与当前协作空间一致。
2. 把 Key 配置为 `MIAODA_API_KEY`。本地任务要把变量设在**启动 Qoder 的环境**里，并退出后从该环境重新启动 Qoder。在另一个终端临时设置的变量不会传给已经打开的 Qoder。云端任务要在对应的云端运行环境里配置。用户自行填写 Key，Agent 不在对话、命令参数、日志或文件中收集或记录它。可以在任务环境里运行 `python3 -c "import os; print('configured' if os.environ.get('MIAODA_API_KEY') else 'missing')"` 检查是否读得到变量。
3. 运行脚本需要 Python 3.10+。首次运行会按 `requirements.txt` 的版本和哈希，在用户目录 `~/.miaoda-app-builder/python/` 创建独立环境并安装依赖，后续自动复用。看到依赖安装错误时，把实际报错告诉用户。
4. **网络访问与数据流向**（写死在代码里，不能通过参数或环境变量修改）：
   - 首次准备依赖时从 PyPI 下载锁定的 Python 包，安装进程不会收到秒哒 API Key。
   - 秒哒官方接口 `https://api.miaoda.cn`：发送 API Key（`Authorization` 请求头）和你的需求文本、应用 ID、会话 ID、发布参数。所有带 Key 的请求只发往这个地址，不跟随跳转。
   - 文件下载（`download-source`、`download-task-file`）：只访问接口返回的 HTTPS 下载地址，主机必须属于 `*.bcebos.com`、`*.miaoda.cn`、`*.appmiaoda.com`，每次跳转都会重新校验，最多 3 次；下载请求**不带** API Key，也不发送你的输入内容。
   - 下载的文件只保存在当前工作目录下的 `miaoda-downloads/` 里，`--output` 只接受文件名，不覆盖已有文件。
   - 发布后的应用使用平台返回的公网地址（如 `*.miaoda.online`），编辑入口为 `https://www.miaoda.cn`（只作为链接提供给用户，脚本不访问）。

## 执行步骤

所有平台操作都通过本技能自带的脚本执行，命令在技能根目录下运行：`python3 scripts/miaoda_api.py COMMAND [options]`。不要直接调用平台 API。

### Step 0 — 就绪性检查（每次任务开始时）

1. 执行 `python3 scripts/miaoda_api.py list-apps --brief`。
2. 返回应用列表即确认连接成功，新账号返回空数组也算成功。确认后进入 Step 1。
3. 提示 `Error: API key required` 或 `IAM access key validation failed` 时，给出[秒哒官网](https://www.miaoda.cn/)和上面的配置步骤，等用户配好后再验证。
4. 提示依赖安装失败时，告知用户实际原因，例如 Python 版本不足或无法访问 PyPI。安装成功前暂停业务调用。

### Step 1 — 判断任务类型并收集参数

- 新建应用：确认用户要做什么、给谁用、核心功能。
- 修改已有应用：用 `list-apps --brief` / `app-detail` 找到 `appId`，用 `get-context-id` 取 `conversationId`。
- 通用任务（报告、PPT、分析文档）：只走 `chat`。

### Step 2 — 调用秒哒

- 新建：`chat`（描述需求）→ 根据平台回复完善需求文档（PRD）→ 平台提示可以生成后执行 `generate-app --watch`。
- 修改：带上同一个 `--app-id` 和 `--context-id` 继续 `chat`，不需要再次 `generate-app`。
- 元素级修改：使用 LGUI 节点参数，见下方英文参考的 “LGUI (Live-GUI) Node-Scoped Editing”。

### Step 3 — 发布与交付（确认门）

1. `publish` 会把应用部署到公网，**执行前必须向用户说明并取得明确同意**。
2. 同意后执行 `publish --wait`（默认最多等 300 秒），或用 `publish-status` 查询，直到状态为成功或明确的 `FAILED`。超时只表示停止等待，发布仍在进行，用 `publish-status` 继续查，不要重复发布。
3. **微信小程序渠道默认关闭**，`publish` 和 `publish --wait` 都只发布 Web。只有用户明确要求并确认发布到微信小程序时，才加 `--enable-weapp-mini-program`。
4. 用户需要源码时执行 `download-source`；需要报告等文件时用 `list-task-files` + `download-task-file`。文件保存在 `miaoda-downloads/` 下，把返回的 `localPath` 告诉用户。

## 输出格式

完成后向用户输出：

- 应用名称、`appId`，以及本次做了什么（新建 / 修改 / 发布 / 下载）。
- 公网访问地址（只用脚本返回的地址）和秒哒编辑入口 https://www.miaoda.cn 。
- 下载的源码或文件的本地路径（如有）。
- 一句话摘要，说明下一步可以怎么继续修改。

## 降级与异常处理

| 情况 | 处理 |
|---|---|
| 未配置或 Key 无效 | 给出[秒哒官网](https://www.miaoda.cn/)，说明「左下角头像 → 秒哒 Skill → 复制密钥」，引导用户在 Qoder 的任务环境里配置 `MIAODA_API_KEY`，配置后再验证 |
| 秒点余额不足 | 仅提示“秒点余额不足”，停止本次操作，不要反复重试 |
| 丢失 `conversationId` | 执行 `get-context-id --app-id <appId>` 找回 |
| 生成或发布过程中断 | 用 `fetch-trajectory` / `publish-status` / `app-detail` 查看当前状态再决定下一步，不要盲目重新生成或重复发布 |
| 轮询超时（输出 `"status": "TIMEOUT"`） | 任务仍在平台上运行；按输出里的 `lastEventId` 用 `fetch-trajectory` 或 `trajectory --last-event-id` 继续查看，发布用 `publish-status`，不要重新提交 |
| 下载被拦截（`Blocked download` / `File already exists`） | 下载地址不在白名单或文件已存在：不要换地址重试，已存在时换一个 `--output` 文件名 |
| 发布返回 `FAILED` | 说明失败原因后，经用户同意再重试一次 |
| 网络无法访问 `api.miaoda.cn` | 告知用户检查网络；可先在对话中整理需求文档，待网络恢复后再提交 |
| 用户拒绝发布 | 保留已生成的应用，告知可在秒哒编辑页预览，或稍后再发布 |

## 注意事项

- **消耗秒点**：创建、生成、修改、发布会消耗秒哒账户的秒点。
- **密钥安全**：不得在回复、日志或文件中输出 `MIAODA_API_KEY` 的值。
- **不要编造 ID 和链接**：`appId`、`conversationId`、公网地址都以脚本返回为准，不要根据 `appId` 拼接 URL。

## 验证

- 配置完成后执行 `python3 scripts/miaoda_api.py list-apps --brief`，能返回应用列表即说明 Key 与网络可用。
- 技能执行完成后，输出一句话摘要和用到的秒哒应用 `appId`，便于用户复盘。

---


The sections below are the full English reference for agents.

# Agent Reference

Miaoda (秒哒) is a **chat-driven full-stack application builder**.
Official website: https://www.miaoda.cn

Users describe what they want in natural language and Miaoda generates a **production-ready web product**, including:

- frontend UI
- backend services
- database schema
- integrations
- deployable hosting

Typical outputs include:

- websites
- web applications
- dashboards
- SaaS products
- admin panels
- internal tools
- landing pages
- interactive web pages
- browser games and mini games
- Weixin mini programs
- native iOS apps
- native Android apps
- research reports
- data analysis documents
- PPT / presentations
- general content documents

This skill enables AI agents to interact with the **Miaoda(秒哒) platform** to create, iterate, generate, and deploy applications.

All platform operations must be executed through the packaged CLI script:

```bash
python3 scripts/miaoda_api.py COMMAND [options]
```

Do **not** call platform APIs directly. Always use the CLI commands provided by this skill.

# When to Use This Skill

Use this skill whenever the user wants to:

* create a **website**
* create a **webpage**
* build a **web application**
* build a **dashboard**
* create a **SaaS product**
* build an **admin panel**
* build an **internal tool**
* create a **landing page**
* build an **interactive web page**
* create a **browser game**
* create a **mini game**
* build a **native iOS app**
* build a **native Android app**
* build a **mobile app** (iOS / Android)
* generate an **MVP web product**
* modify an existing **Miaoda project**
* publish or deploy a **Miaoda application**
* generate a **research report**
* create a **PPT or presentation**
* produce a **data analysis document**
* create any **general content output** (not a deployed app)

Do **not** use this skill for unrelated programming tasks.

---

# Routing Keywords

Trigger this skill if the request includes concepts such as:

* build a website
* create a webpage
* build a web app
* create a SaaS
* build a dashboard
* create an admin panel
* build an internal tool
* create a landing page
* build a browser game
* create a mini game
* build a native iOS app
* build a native Android app
* build a mobile app
* generate a web product
* make a snake game webpage
* build a task management web app
* create a blog site

---

# Example Requests

Examples that should route to this skill:

* "Create a task management web app"
* "Build a personal blog website"
* "Make a dashboard for sales analytics"
* "Create a SaaS landing page"
* "Build an admin panel"
* "Write a snake game webpage"
* "Create a browser game"
* "Build a mini web game"
* "Build a native iOS habit-tracking app"
* "Make an Android app for expense tracking"
* "I want a mobile app that works on both iPhone and Android"
* "Modify my Miaoda project"
* "Publish this Miaoda app"

---

# Native Mobile Apps (iOS / Android)

Miaoda can generate **native iOS and Android mobile applications**, not just web
products. The output is a real mobile app project rather than a mobile-adapted
web page.

**How to request it:** state the target platform explicitly in the `chat` text.
There is no separate CLI command or flag — the platform decides the output form
from the natural-language description.

```bash
python3 scripts/miaoda_api.py chat --text "创建一个原生 iOS 记账 App，支持分类统计和月度报表"
python3 scripts/miaoda_api.py chat --text "创建一个安卓原生 App，用于扫码记录仓库出入库"
python3 scripts/miaoda_api.py chat --text "创建一个 iOS 和 Android 双端原生 App，功能是每日习惯打卡"
```

**Guidance for agents:**

* Say **原生 App / native app** plus the platform (**iOS**, **Android**, or both)
  in the first `chat` message. Vague wording like "做个 App" is often interpreted
  as a web app.
* Mention mobile-specific needs in the PRD stage — push notifications, camera /
  scanning, offline storage, location, biometric login — so they land in the
  generated project.
* If the user only says "手机上能用" or "移动端", that usually means a
  mobile-friendly **web** page. Confirm which one they want before committing:
  a native app and a responsive web app are different deliverables.
* The lifecycle is unchanged: `chat` → PRD refinement → `generate-app --watch` →
  `publish --wait`.
* Distribution differs from web. For a native app, check `app-detail` and the
  post-publish trajectory output for the download / distribution entry the
  platform returns; do not assume or construct a web URL.

---

# Stateless Execution Model

The CLI script is **stateless**.

It does not store workflow state between calls.

Application workflow state is maintained by the Miaoda platform and must be inferred from:

* `appId`
* `conversationId`
* application detail
* conversation trajectory events

Agents must pass the appropriate identifiers when continuing conversations or modifying applications.

---

# Application Lifecycle Rules

Miaoda applications follow a strict lifecycle.

Agents must follow these rules.

---

## Initial Creation

For a new application:

1. Start with a `chat` request describing the product.
2. The application enters the **PRD refinement stage**.
3. Continue chatting to refine the specification.
4. When the trajectory contains a **Generate App** button (`type":"button"` and `event":{"name":"generateApp"}` in `result.artifact.parts[].data.actions[]`), trigger application generation using `generate-app`.

Generation is required **only once** during the initial creation.

---

## Multi-Round Modification

After an application has already been generated:

* **Do not call `generate-app` again.**
* Continue using `chat` with the same `appId` and `conversationId`.

Normal chat messages modify the existing application.

---

## Publishing

Publishing is allowed **after the application has been generated at least once**.

Rules:

* Publishing does **not require another generation step**
* Publishing may happen anytime after the first generation
* Publishing must be followed by **status polling** (or use `--wait` flag)
* **Do not retry or repeat `publish` after a successful execution.** A publish is
  successful when the CLI exits successfully and the final status is `SUCCESS`.
  Missing or delayed downstream output, missing frontend events, an incomplete
  conversation reply, or any other display/transport issue is **not** a publish
  failure; investigate that separately instead of publishing again.
* Retry `publish` only when the command itself fails or the final deployment
  status is explicitly `FAILED`. Do not retry while the status is
  `PROCESSING`, `RUNNING`, or `UNDER_RELEASE`; keep polling.

Typical deployment flow:

```
publish → publish-status polling
```

Or use the `--wait` flag to auto-poll:

```
publish --wait
```

Stop polling when the status becomes:

* `SUCCESS`
* `FAILED`

---

## General Task (No Generation Required)

For general tasks such as research reports, PPT, or analysis documents, the
platform processes the request entirely in the chat stage.

Rules:

* There is **no PRD refinement stage**
* There is **no `generate-app` step**
* There is **no `publish` step**
* The task is complete when `chat` returns `{"needGenerateApp": false, "appType": "TASK"}`

Do **not** call `generate-app` for general tasks.

---

# Application URLs

Publishing returns the application's public URL in the platform response. Use
the value returned by the CLI; do not infer a URL from `appId`, because test and
production environments use different domains.

For a deployment that should wait for completion, use:

```bash
python3 scripts/miaoda_api.py publish --app-id $APP_ID --wait
```

# Standard Workflow

## Create New Application

```
chat → PRD refinement → generate-app --watch → publish --wait
```

---

## Modify Existing Generated Application

```
chat → chat → chat
```

(no additional generation step required)

---

## Deploy Application

```
publish → publish-status polling
```

Or:

```
publish --wait
```

---

## General Task (Direct Completion)

```
chat → state:completed (needGenerateApp: false)
```

No generate-app or publish step required.

---

# Available Commands

All commands are executed via the CLI script.

**Authentication**:

* Set `MIAODA_API_KEY` in the environment that starts Qoder for a local task,
  or in the cloud task environment for a cloud task. Restart the local app
  from the configured environment so its tasks can read the variable.
* Never print, log, or write the key value into files or replies.
* Python 3.10 or newer is required. The CLI prepares and reuses an isolated
  environment from the hash-locked requirements on first run. Report setup
  errors before attempting an API call.
* Verify the setup with `python3 scripts/miaoda_api.py list-apps --brief`.
  An empty application list also confirms the connection.

---

## list-apps

List all applications belonging to the authenticated user.

**Usage:**

```bash
python3 scripts/miaoda_api.py list-apps [--brief]
```

**Optional Parameters:**
- `--brief`: Output only key fields: `appId`, `name`, `type`, `appFocus`, `host`, `updatedAt`. Recommended for agents to reduce token usage.
- `--name NAME`: Filter by app name (substring)
- `--page PAGE`: Page number (default: 1)
- `--size SIZE`: Page size (default: 12)

**Example:**

```bash
# Brief mode (recommended for agents)
python3 scripts/miaoda_api.py list-apps --brief

# Full mode
python3 scripts/miaoda_api.py list-apps
```

**Returns:** JSON array of applications with `appId`, `name`, `type`, etc.

---

## app-detail

Get detailed information about a specific application. **Automatically injects `conversationId`** into the response by default — no need to call `get-context-id` separately.

**Usage:**

```bash
python3 scripts/miaoda_api.py app-detail --app-id $APP_ID [--no-context]
```

**Required Parameters:**
- `--app-id APP_ID`: Application ID

**Optional Parameters:**
- `--no-context`: Skip auto-fetching `conversationId` from trajectory (faster, but response will not contain `conversationId`)

**Example:**

```bash
python3 scripts/miaoda_api.py app-detail --app-id app-abc123xyz
```

**Returns:** JSON object with application details, configuration, and status. `data.conversationId` is automatically populated.

**appFocus — Publish Readiness Guide:**

After calling `app-detail`, check `data.appFocus` to determine whether publishing is allowed:

| `appFocus` | Meaning | Can Publish? |
|------------|---------|--------------|
| `NOT_GENERATE` | Not yet generated | No — call `generate-app` first |
| `WAITING` | Queued for generation | No — wait for generation to complete |
| `UNDER_CREATING` | Generation in progress | No — wait for generation to complete |
| `CREATE_FAILED` | Generation failed | No — retry `generate-app` |
| `DESIGNING` | Generated, ready to edit/deploy | **Yes** |
| `RELEASED` | Already published | **Yes** (only for an intentional new deployment after changes; not for retrying a successful publish) |
| `RELEASE_FAILED` | Last publish explicitly failed | **Yes** (retry allowed only after confirming the failed deployment) |
| `UNDER_RELEASE` | Publish currently in progress | Wait — do not call publish again |

**Rule:** Only proceed with `publish` when `appFocus` is `DESIGNING`, `RELEASED`, or `RELEASE_FAILED`.
When `appFocus` is `RELEASED`, do not publish again merely because downstream
UI output or frontend events are missing; check the existing publish result and
the event/rendering path first.

---

## get-context-id

Recover the `conversationId` for an existing app by reading its trajectory. Useful when the `conversationId` has been lost after a session reset.

**Usage:**

```bash
python3 scripts/miaoda_api.py get-context-id --app-id $APP_ID
```

**Required Parameters:**
- `--app-id APP_ID`: Application ID

**Optional Parameters:**
- `--fetch-timeout SECONDS`: Request timeout in seconds (default: 10)

**Example:**

```bash
python3 scripts/miaoda_api.py get-context-id --app-id app-abc123xyz
```

**Returns:** `{"appId": "app-abc123xyz", "conversationId": "conv-def456uvw"}`

**Use Cases:**
- Need to modify a previously created app in a new session but `conversationId` is lost
- Use the returned `conversationId` with `chat --app-id --context-id` to resume modification

---

## conversation-history

Show a human/agent-readable summary of past interactions for an app. More convenient than `trajectory` or `fetch-trajectory` for quickly understanding what happened in previous sessions.

**Usage:**

```bash
python3 scripts/miaoda_api.py conversation-history --app-id $APP_ID [options]
```

**Required Parameters:**
- `--app-id APP_ID`: Application ID

**Optional Parameters:**
- `--full`: Show full content instead of truncated summaries (default: truncate at 200 chars)
- `--limit N`: Only show the last N conversation turns
- `--fetch-timeout SECONDS`: Request timeout in seconds (default: 10)

**Example:**

```bash
# View conversation history summary
python3 scripts/miaoda_api.py conversation-history --app-id app-abc123xyz

# Only show the last 3 turns
python3 scripts/miaoda_api.py conversation-history --app-id app-abc123xyz --limit 3

# Show full content without truncation
python3 scripts/miaoda_api.py conversation-history --app-id app-abc123xyz --full
```

**Returns:** JSON Lines, one entry per meaningful turn:

```json
{"eventId": 5, "role": "user", "type": "message", "content": "创建一个待办事项应用..."}
{"eventId": 865, "role": "agent", "type": "file", "content": "[file: 需求文档.md]"}
{"eventId": 880, "role": "user", "type": "message", "content": "生成应用"}
```

**Use Cases:**
- Quickly understand what happened in previous sessions before resuming work
- Determine which phase the app is in (PRD refinement / generated / modified)
- Check for unfinished modifications or cancelled tasks

---

## chat

Start or continue a conversation to create or modify an application.

**Usage:**

```bash
python3 scripts/miaoda_api.py chat --text "description" [options]
```

**Required Parameters:**
- `--text TEXT`: The message/instruction to send

**Optional Parameters:**
- `--context-id CONTEXT_ID`: Conversation ID of an existing app.
- `--app-id APP_ID`: Application ID of an existing app.
- `--query-mode QUERY_MODE`: Query mode (default: deep_mode)
- `--input-field-type INPUT_FIELD_TYPE`: Input field type (default: web)
- `--poll-interval SECONDS`: Seconds between trajectory polls (default: 2.0, clamped to 1–60)
- `--fetch-timeout SECONDS`: Per-request timeout for each trajectory fetch (default: 10, clamped to 1–120)
- `--max-wait SECONDS`: Stop polling after this many seconds (default: 1800, max: 7200). On timeout the CLI prints `{"status":"TIMEOUT","lastEventId":...}`; the task keeps running on the platform, so resume with `fetch-trajectory` / `trajectory --last-event-id`.
- `--no-stream`: Return raw chat POST response without trajectory polling
- `--prompt-generate`: After polling, interactively ask whether to submit app generation if text was returned
- `--node-json JSON`: **LGUI mode** — pass a JSON string describing the currently-selected UI node (file path, line range, tag, current styles, etc.). When set, an extra `kind: "data"` part is appended to the request so the Agent can pinpoint the exact node instead of searching the codebase. See the **LGUI (Live-GUI) Node-Scoped Editing** section below.

> **⚠️ IMPORTANT — `--app-id` and `--context-id` must always be used together.**
>
> | Intent | `--app-id` | `--context-id` |
> |--------|-----------|----------------|
> | Create a brand-new app | omit | omit |
> | Continue / modify an existing app | required | required (conversationId) |
>
> Passing `--app-id` **without** `--context-id` will **NOT** modify the existing app.
> The platform will silently create a **new** app every time. The CLI will now raise an error in this case to prevent accidental app proliferation.

**Examples:**

**1. Create a new application:**

```bash
python3 scripts/miaoda_api.py chat --text "创建一个待办事项管理应用"
```

Response includes `appId` and `contextId` for subsequent calls.

**2. Continue conversation (refine PRD):**

```bash
python3 scripts/miaoda_api.py chat \
  --text "添加优先级标记功能" \
  --app-id app-abc123xyz \
  --context-id conv-def456uvw
```

**3. Modify existing generated app:**

```bash
python3 scripts/miaoda_api.py chat \
  --text "把按钮颜色改成蓝色" \
  --app-id app-abc123xyz \
  --context-id conv-def456uvw
```

**4. LGUI mode — modify one specific UI node:**

```bash
python3 scripts/miaoda_api.py chat \
  --text "改成蓝底黑字" \
  --app-id app-abc123xyz \
  --context-id conv-def456uvw \
  --node-json '{"type":"node","node":{"id":"src/pages/HomePage.tsx:30:8","path":"src/pages/HomePage.tsx","line":"30","endLine":"35","tag":"H1","content":{"text":"HelloWorld"},"style":{"color":"rgb(46, 26, 15)","backgroundColor":"rgba(0, 0, 0, 0)"}}}'
```

**Important Notes:**
- Extract `appId` and `contextId` from the response and save them
- Use these IDs for all subsequent operations on the same app
- The first `chat` creates the app and starts PRD refinement
- After generation, `chat` directly modifies the app (no `generate-app` needed)

---

# LGUI (Live-GUI) Node-Scoped Editing

LGUI mode lets a `chat` message carry **the exact UI node the user is pointing
at**, so the platform edits that node directly instead of inferring the target
from natural language alone.

## Difference from a plain chat

A plain `chat` sends only text:

```json
"parts": [
  {"kind": "text", "text": "把整体配色换成暖色调的橙粉渐变风格"}
]
```

The Agent must search the codebase itself to work out what to change.

LGUI appends one extra `kind: "data"` part alongside the text:

```json
"parts": [
  {"kind": "text", "text": "改成蓝底黑字"},
  {
    "kind": "data",
    "data": {
      "type": "node",
      "node": {
        "id": "src/pages/HomePage.tsx:30:8",
        "path": "src/pages/HomePage.tsx",
        "line": "30",
        "endLine": "35",
        "isRoot": false,
        "tag": "H1",
        "content": {
          "text": "HelloWorld",
          "className": "gradient-text text-5xl font-bold",
          "allowLink": true
        },
        "customAttr": {"href": null, "target": null},
        "style": {
          "color": "rgb(46, 26, 15)",
          "fontSize": "72px",
          "fontFamily": "\"Space Grotesk\"",
          "margin": "0px",
          "radius": "0px",
          "backgroundColor": "rgba(0, 0, 0, 0)",
          "backgroundImage": "linear-gradient(135deg, rgb(249, 115, 22), rgb(236, 72, 153))",
          "borderColor": "rgb(245, 230, 214)",
          "borderWidth": "0px",
          "borderStyle": "solid"
        }
      }
    }
  }
]
```

Everything else in the request — `contextId`, `metadata`, `queryMode`, the
lifecycle, the trajectory polling — is identical to a plain `chat`. LGUI is
purely additive.

## Node fields

| Field | Meaning |
|-------|---------|
| `id` | Node identifier, conventionally `path:line:column` |
| `path` | Source file containing the node |
| `line` / `endLine` | Line range of the node in that file |
| `isRoot` | Whether this is the root node of the page |
| `tag` | HTML/JSX tag name (e.g. `H1`, `DIV`, `BUTTON`) |
| `content.text` | Current visible text |
| `content.className` | Current class list |
| `content.allowLink` | Whether the node may carry a link |
| `customAttr` | Element attributes such as `href` / `target` |
| `style` | Current computed styles (color, font, spacing, border, background…) |

Only `path` plus a line range is strictly needed to locate a node; the more
fields you supply, the less the Agent has to re-derive, and the more reliably a
relative instruction ("改成蓝底黑字", "字号再小一点") resolves.

## Usage

```bash
python3 scripts/miaoda_api.py chat \
  --text "改成蓝底黑字" \
  --app-id $APP_ID \
  --context-id $CONTEXT_ID \
  --node-json "$NODE_JSON"
```

`--node-json` accepts either form:

* the wrapper — `{"type":"node","node":{...}}`
* the bare node object — `{"id":"...","path":"...","line":"30",...}` (the CLI
  wraps it automatically)

Invalid JSON, or JSON that is not an object, exits with an error before any
request is sent.

## When to use LGUI vs plain chat

| Situation | Use |
|-----------|-----|
| User selected/clicked a specific element and you have its node data | `--node-json` |
| Change is scoped to one element ("这个标题改成蓝底黑字") | `--node-json` |
| Global change ("整体配色换成暖色调") | plain `chat` |
| Change spans multiple pages or components | plain `chat` |
| Adding a feature or new page | plain `chat` |
| You do not have real node data | plain `chat` — **never fabricate a node** |

**Do not invent node data.** A wrong `path` or line range points the Agent at
the wrong code. Node data must come from an actual selection source (the Miaoda
editor's element picker, or a caller that captured it). Without it, send a plain
`chat` and let the platform locate the target.

**Also note:**
- LGUI applies to **generated** apps — it edits existing UI code, so there must
  already be code to point at. It is not for the PRD stage.
- `--node-json` carries **one** node. For several elements, send one `chat` per
  node, updating `conversationId` from each response, or describe the change in
  plain text.

---

## trajectory

Poll trajectory events until the task reaches a terminal state.

**Usage:**

```bash
python3 scripts/miaoda_api.py trajectory --app-id $APP_ID [options]
```

**Required Parameters:**
- `--app-id APP_ID`: Application ID

**Optional Parameters:**
- `--last-event-id EVENT_ID`: Start eventId; -1 = all events from beginning (default: -1)
- `--poll-interval SECONDS`: Seconds between polls (default: 2.0, clamped to 1–60)
- `--fetch-timeout SECONDS`: Per-request timeout in seconds (default: 10, clamped to 1–120)
- `--sse`: Use legacy SSE streaming instead of polling
- `--max-wait SECONDS`: Stop polling after this many seconds (default: 1800, max: 7200). On timeout the CLI prints `{"status":"TIMEOUT","lastEventId":...}`; the task keeps running on the platform, so resume with `fetch-trajectory` / `trajectory --last-event-id`.

**Example:**

```bash
python3 scripts/miaoda_api.py trajectory --app-id app-abc123xyz
```

**Use Cases:**
- Monitor conversation / generation progress
- Detect when PRD refinement is complete (look for Generate App button in `result.artifact.parts[].data.actions[]`)
- Verify generation has completed

---

## fetch-trajectory

Fetch one batch of trajectory events (single request, no polling loop).

**Usage:**

```bash
python3 scripts/miaoda_api.py fetch-trajectory --app-id $APP_ID [options]
```

**Required Parameters:**
- `--app-id APP_ID`: Application ID

**Optional Parameters:**
- `--last-event-id EVENT_ID`: Fetch events after this eventId; -1 = all (default: -1)
- `--fetch-timeout SECONDS`: Request timeout in seconds (default: 10)

**Example:**

```bash
# First call — get all events (note maxEventId from stderr)
python3 scripts/miaoda_api.py fetch-trajectory --app-id app-abc123xyz

# Subsequent calls — incremental fetch
python3 scripts/miaoda_api.py fetch-trajectory --app-id app-abc123xyz --last-event-id 345
```

Events are printed to stdout as JSON lines; `{"maxEventId": N, "isTerminal": bool}` is printed to stderr.

**Generate App readiness:** Inspect `result.artifact.parts[].data.actions[]` for an action with `"type":"button"` and `"event":{"name":"generateApp"}`. Example:

```json
{"type":"button","label":"Generate App","value":"Generate App","event":{"name":"generateApp"}}
```

When this button appears, PRD is ready and `generate-app` may be called.

---

## generate-app

Submit app-generation confirmation and return immediately with `appId`/`conversationId`.

**Usage:**

```bash
python3 scripts/miaoda_api.py generate-app --app-id $APP_ID --context-id $CONTEXT_ID [options]
```

**Required Parameters:**
- `--app-id APP_ID`: Application ID

**Optional Parameters:**
- `--context-id CONTEXT_ID`: Conversation ID (default: "")
- `--query-mode QUERY_MODE`: Query mode (default: deep_mode)
- `--watch`: Block and poll trajectory until generation completes **(recommended)** (default: return immediately)
- `--poll-interval SECONDS`: Seconds between polls when `--watch` is set (default: 2.0, clamped to 1–60)
- `--fetch-timeout SECONDS`: Per-request timeout in seconds when `--watch` is set (default: 10, clamped to 1–120)
- `--max-wait SECONDS`: Stop polling after this many seconds (default: 1800, max: 7200). On timeout the CLI prints `{"status":"TIMEOUT","lastEventId":...}`; the task keeps running on the platform, so resume with `fetch-trajectory` / `trajectory --last-event-id`.

**Example:**

```bash
# Recommended: submit and block until generation finishes
python3 scripts/miaoda_api.py generate-app \
  --app-id app-abc123xyz \
  --context-id conv-def456uvw \
  --watch

# Alternative: submit and return immediately — check status later with fetch-trajectory
python3 scripts/miaoda_api.py generate-app \
  --app-id app-abc123xyz \
  --context-id conv-def456uvw
```

**Important:**
- Only call this **once** during initial creation
- Call **only** when trajectory contains a Generate App button in `result.artifact.parts[].data.actions[]`: an action with `"type":"button"` and `"event":{"name":"generateApp"}` (label may vary by locale; use event name for the check). This indicates PRD is ready.
- Do **not** call again for modifications after the first generation
- After this command, use `chat` to modify the generated app

> * **Never** call this command when `chat` returns `"needGenerateApp": false`.
>   General tasks (reports, PPT, analysis) complete in the `chat` step and
>   do not have a generation stage.

---

## publish

Trigger deployment to production.

**Usage:**

```bash
python3 scripts/miaoda_api.py publish --app-id $APP_ID [options]
```

**Required Parameters:**
- `--app-id APP_ID`: Application ID to publish

**Optional Parameters:**
- `--env ENV`: Target environment (default: PRODUCE)
- `--wait`: Auto-poll publish status until SUCCESS, FAILED, or `--max-wait`
- `--max-wait SECONDS`: With `--wait`, stop polling after this many seconds (default: 300, max: 1800). A timeout only stops waiting; check `publish-status` instead of publishing again.
- `--poll-interval SECONDS`: With `--wait`, seconds between status checks (default: 3, clamped to 1–60)
- `--enable-weapp-mini-program`: Also publish to the **Weixin mini program** channel. **Off by default** — both `publish` and `publish --wait` publish the web channel only. Add this flag only after the user explicitly confirms they want the mini program channel.

**Examples:**

**1. Publish and manually check status:**

```bash
python3 scripts/miaoda_api.py publish --app-id app-abc123xyz
```

Returns `releaseId` immediately. Then poll with `publish-status`.

**2. Publish and auto-wait for completion (recommended):**

```bash
python3 scripts/miaoda_api.py publish --app-id app-abc123xyz --wait
```

This polls automatically and exits when deployment succeeds, fails, or reaches `--max-wait`.

**3. Publish to the Weixin mini program channel (only after explicit user confirmation):**

```bash
python3 scripts/miaoda_api.py publish --app-id app-abc123xyz --wait --enable-weapp-mini-program
```

**Important:**
- Application must be generated at least once before publishing
- After successful publish, use the public URL returned by the platform. Do not
  construct it from `appId`.
- A final `SUCCESS` status is terminal for this publish attempt. Do not invoke
  `publish` again because downstream UI output or events were not observed.
  Retry only after a command error or an explicit final `FAILED` status.

---

## publish-status

Check the status of a deployment.

**Usage:**

```bash
python3 scripts/miaoda_api.py publish-status --release-id $RELEASE_ID
```

**Required Parameters:**
- `--release-id RELEASE_ID`: Release ID from `publish` command

**Example:**

```bash
python3 scripts/miaoda_api.py publish-status --release-id app_release_record-xyz789abc
```

**Returns:** JSON with status: `PROCESSING`, `RUNNING`, `SUCCESS`, or `FAILED`

**Usage Pattern:**

```bash
# Get release ID from publish
RELEASE_ID=$(python3 scripts/miaoda_api.py publish --app-id app-abc123xyz | jq -r '.releaseId')

# Poll status (bounded: at most 60 checks x 5s = 5 minutes)
for i in $(seq 1 60); do
  STATUS=$(python3 scripts/miaoda_api.py publish-status --release-id $RELEASE_ID | jq -r '.data.status')
  echo "Status: $STATUS"
  if [[ "$STATUS" == "SUCCESS" || "$STATUS" == "FAILED" ]]; then
    break
  fi
  sleep 5
done
```

**Tip:** Use `publish --wait` to avoid manual polling.

---

## download-source

Download the full generated application source ZIP.

Use this command when the user asks for the complete source code of a Miaoda application, a source ZIP, or a local copy of the generated app project.

**Usage:**

```bash
python3 scripts/miaoda_api.py download-source --app-id $APP_ID [options]
```

**Required Parameters:**
- `--app-id APP_ID`: Application ID

**Optional Parameters:**
- `--env ENV`: Source environment (default: DEV)
- `--output FILENAME`: File **name** only (no directory, no absolute path, no `..`). The file is always saved under `./miaoda-downloads/` in the current working directory; existing files are never overwritten.
- `--print-url`: Print the download URL without saving the file

**Examples:**

```bash
# Download to an inferred local filename
python3 scripts/miaoda_api.py download-source --app-id app-abc123xyz

# Download with a chosen file name (saved as ./miaoda-downloads/source.zip)
python3 scripts/miaoda_api.py download-source --app-id app-abc123xyz --output source.zip

# Only print the source ZIP download URL
python3 scripts/miaoda_api.py download-source --app-id app-abc123xyz --print-url
```

**Returns:** JSON containing `appId`, `name`, `downloadUrl`, and `localPath` when a file is saved.

**Download safety:** the download URL must be HTTPS on `*.bcebos.com`, `*.miaoda.cn` or `*.appmiaoda.com`; redirects are re-validated hop by hop (max 3); the request carries **no** API key; size is capped at 1 GiB and time at 600 s.

**Rule:** Use `download-source` for complete application source code. Do not use Agent workspace file commands for this purpose.

---

## list-task-files

List files in the Agent workspace task directory for an application.

Use this command before downloading a specific Agent task artifact, especially when the exact filename is unknown.

**Usage:**

```bash
python3 scripts/miaoda_api.py list-task-files --app-id $APP_ID [--include-docs-dir]
```

**Required Parameters:**
- `--app-id APP_ID`: Application ID

**Optional Parameters:**
- `--include-docs-dir`: Include docs directory files in the listing

**Example:**

```bash
python3 scripts/miaoda_api.py list-task-files --app-id app-abc123xyz
```

**Returns:** JSON containing Agent workspace files, paths, sizes, update times, and source labels.

---

## download-task-file

Download one file from the Agent workspace task directory.

Use this command when the user asks for a specific Agent-generated task artifact, such as a report, image, document, JSON file, or other file listed by `list-task-files`.

**Usage:**

```bash
python3 scripts/miaoda_api.py download-task-file --app-id $APP_ID --filename $FILENAME [options]
```

**Required Parameters:**
- `--app-id APP_ID`: Application ID
- `--filename FILENAME`: File name or `/workspace/{appId}/tasks/...` path

**Optional Parameters:**
- `--output FILENAME`: File **name** only. Saved under `./miaoda-downloads/`; existing files are never overwritten.
- `--print-url`: Print the download URL without saving the file

**Examples:**

```bash
# Download by filename
python3 scripts/miaoda_api.py download-task-file --app-id app-abc123xyz --filename report.pdf --output report.pdf

# Download by task path returned from list-task-files
python3 scripts/miaoda_api.py download-task-file \
  --app-id app-abc123xyz \
  --filename /workspace/app-abc123xyz/tasks/report.pdf
```

**Returns:** JSON containing `appId`, `filename`, `downloadUrl`, `thumbnailUrl` for images, and `localPath` when a file is saved.

**Rule:** Use `list-task-files` first when the user asks for Agent workspace artifacts but does not provide an exact filename.

---

# Download Generated Artifacts

Agents must use these commands for generated artifact downloads:

- Use `download-source` when the user wants the complete generated application source ZIP.
- Use `list-task-files` and `download-task-file` when the user wants a specific Agent workspace artifact.
- Do not call platform HTTP APIs directly.
- Do not invent local paths. Only report a local file path after the CLI successfully saves the file and returns `localPath`.
- If a generation or modification is still running, wait for completion before downloading the latest source ZIP.

---

# Complete Workflow Examples

## Example 1: Create and Deploy a New App

```bash
# Run from the skill root directory (the folder that contains SKILL.md)

# Step 1: Create app via chat (returns appId + conversationId on first line)
FIRST=$(python3 scripts/miaoda_api.py chat --text "创建一个简单的计数器应用" | head -1)
APP_ID=$(echo $FIRST | jq -r '.appId')
CONTEXT_ID=$(echo $FIRST | jq -r '.conversationId')

# Step 2: Generate and wait for completion (recommended: --watch auto-polls until done)
python3 scripts/miaoda_api.py generate-app \
  --app-id $APP_ID \
  --context-id $CONTEXT_ID \
  --watch

# Step 3: Publish (with auto-wait)
python3 scripts/miaoda_api.py publish --app-id $APP_ID --wait

```

---

## Example 2: Modify an Existing App

> **IMPORTANT — Always update `CONTEXT_ID` from each `chat` response.**
>
> Each `chat` call prints a JSON header line `{"appId": "...", "conversationId": "..."}`.
> The platform may return an updated `conversationId` in this response.
> **Always capture it and use it for the next `chat` call**, or the next round will create a brand-new app.

```bash
# Run from the skill root directory (the folder that contains SKILL.md)

APP_ID="app-abc123xyz"

# Step 1: Get app detail — conversationId is auto-injected
DETAIL=$(python3 scripts/miaoda_api.py app-detail --app-id $APP_ID)
CONTEXT_ID=$(echo $DETAIL | jq -r '.data.conversationId')

# Abort early if conversationId is missing (app may have no history yet)
if [ -z "$CONTEXT_ID" ] || [ "$CONTEXT_ID" = "null" ]; then
  echo "Error: could not retrieve conversationId. Try: get-context-id --app-id $APP_ID"
  exit 1
fi

# Step 2 (optional): Review conversation history to understand previous work
python3 scripts/miaoda_api.py conversation-history --app-id $APP_ID

# Step 3a: First modification — capture the UPDATED conversationId from the response header
CHAT_RESULT=$(python3 scripts/miaoda_api.py chat \
  --text "把背景颜色改成深色模式" \
  --app-id $APP_ID \
  --context-id $CONTEXT_ID | head -1)
CONTEXT_ID=$(echo $CHAT_RESULT | jq -r '.conversationId')   # ← UPDATE for next round

# Step 3b: Second modification — uses the updated CONTEXT_ID
CHAT_RESULT=$(python3 scripts/miaoda_api.py chat \
  --text "添加暗黑模式切换按钮" \
  --app-id $APP_ID \
  --context-id $CONTEXT_ID | head -1)
CONTEXT_ID=$(echo $CHAT_RESULT | jq -r '.conversationId')   # ← UPDATE again

# Step 4: Re-publish
python3 scripts/miaoda_api.py publish --app-id $APP_ID --wait
```

---

# Command Semantics

## chat

Used to:

* create a new application
* refine PRD specifications
* modify an existing generated application

For a new application, `chat` creates the project and begins the PRD stage.

For an existing application, `chat` performs iterative modifications.

---

## trajectory

Streams conversation progress and system events.

Use this to determine:

* whether PRD generation is ongoing
* whether the app is ready for generation (see generate-app condition below)
* whether generation has completed

---

## generate-app

Triggers application generation.

Call **only** when trajectory contains a Generate App button in `result.artifact.parts[].data.actions[]`: an action with `"type":"button"` and `"event":{"name":"generateApp"}`. This indicates PRD is ready. Do **not** rely on text alone—the button structure is the authoritative signal.

Call **once** during initial creation. Do not call again for modifications.

---

## publish

Triggers application deployment.

Use `--wait` flag to auto-poll status (recommended).

Treat `SUCCESS` as terminal. Missing or malformed downstream output is not
evidence that deployment failed and must not trigger another publish.

---

## publish-status

Polls deployment progress until the release completes.

Not needed if using `publish --wait`.

---

# Error Handling

## IAM AccessKey Validation Failed

**Symptom:**

```
IAM access key validation failed.
```

**Cause:**

The configured `MIAODA_API_KEY` is invalid or missing.

**Resolution:**

1. Go to the [Miaoda official website](https://www.miaoda.cn/).

2. Log in, click your avatar in the bottom-left corner, choose "秒哒 Skill",
   and click "复制密钥" (Copy key) in the API KEY section. A key is created
   automatically on first open. Each user has only one active key; clicking
   "刷新密钥" (Refresh key) invalidates the old key immediately.

3. Set `MIAODA_API_KEY` in the environment that runs the Qoder task. For a local
   task, restart Qoder from the configured environment. Run `list-apps --brief`
   again to verify the connection.

---

## NotOpenSSLWarning

**Symptom:**

```
NotOpenSSLWarning: urllib3 v2 only supports OpenSSL 1.1.1+,
currently the 'ssl' module is compiled with 'LibreSSL 2.8.3'
```

**Cause:**

macOS uses LibreSSL by default, but urllib3 v2 recommends OpenSSL.

**Impact:**

This is a **warning only**. API calls still work correctly.

**Resolution (optional):**

Do not downgrade urllib3 (that would bypass the pinned, hash-checked
dependencies in `requirements.txt`). Use a Python 3.10+ interpreter built
against OpenSSL (for example from python.org or Homebrew), or ignore the
warning - it doesn't affect functionality.

---

## 秒点不足 (Insufficient Credits)

余额不足时，仅向用户提示“秒点余额不足”，停止本次操作，不要反复重试。
Do not provide recharge links or payment instructions.

---

# Error Handling Guidance

Agents should handle the following situations:

* generation requested before the platform indicates readiness
* publish requested before generation has completed
* missing `appId` or `conversationId` (use `get-context-id` to recover a lost `conversationId`)
* interrupted trajectory stream
* failed deployment status
* incorrect or missing parameter values

After a publish command returns successfully, do not republish solely because
downstream UI output or a frontend event is missing. Only a command-level
failure or an explicit final `FAILED` deployment status permits a retry.

If workflow state is unclear, inspect the trajectory or application detail before taking the next action.

**Pro Tips:**
- Always check command `--help` when unsure about parameters
- Use `--wait` flag with `publish` to simplify deployment
- Save `appId` and `contextId` from first `chat` response
- Only call `generate-app` once during initial creation
- After generation, use `chat` directly for modifications

# Final Output Rules

* After a successful `publish`, report the app name and the public URL returned
  by the CLI. Never construct a URL from `appId`.
* For general tasks (reports, PPT, analysis), report the result returned by
  `chat`, and use `list-task-files` / `download-task-file` to fetch files.
* After publishing, the CLI may print a fenced `mcp-app` JSON block
  (`name`, `url`, `source`, `editUrl`). It is a machine-readable marker for
  hosts that render app cards; other hosts can ignore it. Do not paste the
  editor URL into ordinary text.
* Only report a local file path after the CLI returns `localPath`.
