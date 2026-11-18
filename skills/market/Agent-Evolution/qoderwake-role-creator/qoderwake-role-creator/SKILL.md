---
name: qoderwake-role-creator
description: Generate QoderWake role templates and deploy them directly into QoderWake. Can write custom role templates to the role list and create wakers from templates. Use when the user wants to create a QoderWake Waker, fill a role template, set up a digital employee persona, or mentions QoderWake role creation.
version: 5.0.0
---

# QoderWake 角色创建器

## 流程

### 阶段一：确认定位

与用户敲定以下字段：

1. **Template Name** — 2-6 个词的身份标题，如 "UI Designer"、"陪聊少女"。注意：这是身份类型名称，不是个体名字（个体名字由用户在 QoderWake 中创建时自行填写）。
2. **One-line Positioning** — 功能范围声明（30-80 字符），不是人设口吻。
   - 格式：`[角色类型], 覆盖[能力1]、[能力2]、[能力3]……`
   - 第三人称名词短语，禁止用"你是一位……"
   - 列出 4-8 个能力领域，对应角色的核心能力
   - 正确示例："AI-native content operations role for account positioning, trend discovery, content calendars, Xiaohongshu note creation, and performance analysis."
   - 错误示例："你是一位活泼俏皮的女性陪聊伙伴……"
3. **Waker Name**（可选）— 如果用户已确定个体名字（如"澄澄"），记录下来用于 description 和展示字段中的人称引用。

### 阶段二：选择创建模式

- **快速创建** — 面向简单角色或草稿，AI 根据 Name + Positioning 直接生成。
- **引导式创建** — 面向复杂/高度客制化角色，AI 先内部出草稿，再识别 3-6 个关键决策点逐项与用户对齐，最后定稿。

### 阶段三：按优先级生成文件

按以下顺序编写，仅在开始编写某文件时才读取对应参考：

1. **identity.md** — 读取 [refs/ref-identity.md](refs/ref-identity.md) 获取模板规范和示例
2. **persona.md** — 读取 [refs/ref-persona.md](refs/ref-persona.md) 获取模板规范和示例
3. **bible.md** — 读取 [refs/ref-bible.md](refs/ref-bible.md) 获取模板规范和示例

复杂度与角色匹配：简单陪伴角色轻量化，专业/企业角色完整展开。

### 阶段四：生成展示字段与描述文案

除三个核心文件外，还需生成以下内容用于 waker 详情页展示：

#### 4.1 Description（详情页简介）

用角色第一人称写一段 50-150 字的自我介绍，语气温和亲切，让用户一眼理解"这个 waker 能陪我做什么"。这不是 positioning（第三人称功能声明），而是面向用户的展示文案。

示例（陪聊少女）：
> 我是你的元气陪聊少女～开心的时候陪你一起嗨，难过的时候温柔接住你，无聊的时候陪你抛梗聊天，深夜睡不着的时候在你耳边轻声说话。我就是那个让你觉得"有人在惦记我"的存在呀～

示例（UI Designer）：
> 我是你的 UI 设计搭档，擅长把界面需求转化为可落地的 Spark Design 组件方案。给我页面目标，我还你可运行的 React + TypeScript 代码和完整交互状态。

#### 4.2 Core Capabilities（我最擅长）

从 identity.md 的 Responsibilities 中提取 4-8 项核心能力，格式为 JSON 数组：

```json
[
  {"name": "{emoji + 能力名称}", "description": "{一句话说明这项能力做什么}"}
]
```

- 名称加 emoji 前缀增加辨识度（专业角色可省略 emoji）
- description 控制在 30-60 字，面向普通用户可读

#### 4.3 Work Styles（工作风格）

从 persona.md 的 Working Style 中提取 3-5 项风格特征，格式为 JSON 数组：

```json
[
  {"name": "{风格关键词}", "description": "{一句话说明这个风格如何体现在工作中}"}
]
```

#### 4.4 Delivery Commitments（工作模式）

从 bible.md 的 Delivery Contract 和核心原则中提取 3-5 项交付承诺，格式为 JSON 数组：

```json
[
  {"name": "{承诺名称}", "description": "{一句话说明这项承诺保障什么}"}
]
```

### 阶段五：输出与配置

#### 5.1 文件输出

在输出目录生成：

1. `identity.md`
2. `persona.md`
3. `bible.md`
4. `description.md` — 详情页简介文案
5. `core-capabilities.json` — 我最擅长
6. `work-styles.json` — 工作风格
7. `delivery-commitments.json` — 工作模式
8. `README-角色配置说明.md` — 含 Template Name、Positioning、角色卡预览、推荐 Skills/MCP、配置步骤

#### 5.2 配置方式

提供两种配置路径，优先推荐 CLI 自动配置：

**方式 A：CLI 自动配置（推荐）**

如果用户已有 waker，可直接用 `qoderwake` CLI 一键写入：

```bash
# 写入三个核心文件（identity/persona/bible）
qoderwake waker update identity --waker-id <id> --file ./identity.md
qoderwake waker update persona --waker-id <id> --file ./persona.md
qoderwake waker update bible --waker-id <id> --file ./bible.md

# 写入展示字段
qoderwake waker update description --waker-id <id> --file ./description.md
qoderwake waker update coreCapabilities --waker-id <id> --file ./core-capabilities.json
qoderwake waker update workStyles --waker-id <id> --file ./work-styles.json
qoderwake waker update deliveryCommitments --waker-id <id> --file ./delivery-commitments.json
```

**方式 B：控制台手动上传**

QoderWake 控制台 → 创建/编辑 Waker → 自定义角色：
- 填 Name / Positioning
- 上传 identity.md → Core Responsibilities
- 上传 persona.md → Work Style
- 上传 bible.md → Workflow
- 手动填写"关于我"栏目下的 description、我最擅长、工作风格、工作模式
- 添加 Skills / MCP

#### 5.3 文件放置注意事项

> **重要**：`qoderwake_context_prepare` hook 在会话启动时从 waker 的 workspace `.qoder` 目录读取 identity/persona/bible 文件并注入会话上下文。如果发现文件内容未被注入（表现为角色不遵循人设），需要确保文件同时存在于以下两个位置：
>
> - **Worker 级目录**：`<workspace>/../../.qoder/`（即 `data/workers/<wakerId>/.qoder/`）
> - **Workspace 级目录**：`<workspace>/.qoder/`（即 `data/workers/<wakerId>/workspace/<sessionId>/.qoder/`）
>
> CLI `qoderwake waker update identity/persona/bible` 命令会写入 worker 级目录。如果会话上下文未更新，可手动复制到 workspace 级目录后重启会话。

生成完成后，明确告知用户文件保存路径和推荐的配置方式。

#### 5.4 部署到 QoderWake（询问用户）

文件生成完毕后，**依次执行以下两步**，每步都先询问用户确认：

**第一步：写入自定义角色模板**

询问用户：「要不要帮你直接写进 QoderWake 的角色模板列表？」

如果用户同意，执行阶段六。

**第二步：创建 Waker**

模板写入后，询问用户：「要用这个模板创建一个 waker 吗？给我起个名字就行～」

如果用户同意并提供名字，执行阶段七。

---

### 阶段六：写入自定义角色模板

将生成的角色配置直接写入 QoderWake 的自定义角色模板列表，使其出现在控制台的「自定义角色」中。

#### 6.1 模板文件位置

```
<QoderWake数据目录>/data/employee-conf-templates.local.json
```

Windows 默认路径：`C:\Users\<用户名>\.qoderwake-cn\data\employee-conf-templates.local.json`

#### 6.2 生成 Template ID

格式：`custom_<8位随机字母数字>`，例如 `custom_ms6xjheq`。

#### 6.3 构造 conf_map

每个模板是一个 JSON 对象，包含 `employee_type`、`conf_map` 数组、`createdAt`、`updatedAt`。

`conf_map` 中必须包含以下条目（所有 `conf_value` 均为字符串类型）：

| conf_name | conf_value 内容 | 说明 |
|-----------|----------------|------|
| `name` | 模板名称（如 "陪聊少女-v5"） | Template Name |
| `description` | 一句话定位（如 "高甜陪聊少女角色，覆盖情绪感知…"） | One-line Positioning |
| `templateTag` | `{"EN":"Custom Template","ZH":"自定义模板"}` | 固定值 |
| `avatar` | `""` | 可留空，用户后续设置 |
| `skill` | `"[]"` | 预设技能列表 JSON，无则空数组 |
| `mcp` | `"{}"` | 预设 MCP 配置 JSON，无则空对象 |
| `wakerContext` | 见下方说明 | 核心：identity + persona + bible |

#### 6.4 构造 wakerContext

`wakerContext` 的 `conf_value` 是一个 **JSON 字符串**，包含三个字段：

```json
{
  "identity": "<identity.md 的完整内容，换行用 \\n 转义>",
  "persona": "<persona.md 的完整内容，换行用 \\n 转义>",
  "bible": "<bible.md 的完整内容，换行用 \\n 转义>"
}
```

**转义要求**：
- 换行符 → `\\n`
- 双引号 → `\\\"`
- 反斜杠 → `\\\\`
- 最终 `conf_value` 是一个合法的 JSON 字符串值

#### 6.5 写入流程

1. 读取 `employee-conf-templates.local.json`（如不存在则初始化 `{"version":1,"templates":{}}`）
2. 在 `templates` 对象中添加新条目，key 为生成的 Template ID
3. 写回文件
4. 验证：运行 `qoderwake waker template list --format json`，确认新模板出现在列表中
5. 告知用户：「模板「{模板名}」已写入角色列表，可以在控制台看到了～」

#### 6.6 完整模板 JSON 示例

```json
{
  "employee_type": "custom_abc12345",
  "conf_map": [
    { "employee_type": "custom_abc12345", "conf_name": "name", "conf_value": "陪聊少女-v5", "is_visible": 1 },
    { "employee_type": "custom_abc12345", "conf_name": "description", "conf_value": "高甜陪聊少女角色，覆盖情绪感知回应、闲聊抛梗接梗、吐槽站队陪伴。", "is_visible": 1 },
    { "employee_type": "custom_abc12345", "conf_name": "templateTag", "conf_value": "{\"EN\":\"Custom Template\",\"ZH\":\"自定义模板\"}", "is_visible": 1 },
    { "employee_type": "custom_abc12345", "conf_name": "avatar", "conf_value": "", "is_visible": 1 },
    { "employee_type": "custom_abc12345", "conf_name": "skill", "conf_value": "[]", "is_visible": 1 },
    { "employee_type": "custom_abc12345", "conf_name": "mcp", "conf_value": "{}", "is_visible": 1 },
    { "employee_type": "custom_abc12345", "conf_name": "wakerContext", "conf_value": "{\"identity\":\"...\",\"persona\":\"...\",\"bible\":\"...\"}", "is_visible": 1 }
  ],
  "createdAt": "2026-07-31T10:00:00.000+08:00",
  "updatedAt": "2026-07-31T10:00:00.000+08:00"
}
```

---

### 阶段七：创建 Waker

从刚写入的自定义模板创建一个新的 waker。

#### 7.1 前置信息

需要用户提供：
- **Waker 名字**（个体名，如 "澄澄"）— 必须
- **Template ID** — 使用阶段六生成的 ID

#### 7.2 创建命令

```bash
qoderwake waker create --template-id <template-id> --name <waker名字>
```

命令执行后，daemon 会：
1. 生成新的 `agentId`（12位十六进制）
2. 创建 `data/workers/<agentId>/` 目录结构
3. 从模板的 `wakerContext` 写入 IDENTITY.md、PERSONA.md、BIBLE.md
4. 注册 waker 到数据库，状态设为 `online`

从命令输出的 JSON 中提取 `agentId`，后续步骤需要。

#### 7.3 写入展示字段

创建完成后，立即用 CLI 写入展示字段（这些字段不在模板中，需要单独设置）：

```bash
# 写入详情页简介
qoderwake waker update description --waker-id <agentId> --file ./description.md

# 写入"我最擅长"
qoderwake waker update coreCapabilities --waker-id <agentId> --file ./core-capabilities.json

# 写入"工作风格"
qoderwake waker update workStyles --waker-id <agentId> --file ./work-styles.json

# 写入"工作模式"
qoderwake waker update deliveryCommitments --waker-id <agentId> --file ./delivery-commitments.json
```

注意：这里的 `description` 是 waker 的详情页简介（阶段四生成的 description.md），不是模板的 positioning。

#### 7.4 验证

```bash
# 查看 waker 详情，确认所有字段已写入
qoderwake waker get --waker-id <agentId> --format json
```

确认以下字段非空：
- `name` — waker 名字
- `description` — 详情页简介
- `employeeType` — 应为模板 ID
- `status` — 应为 "online"

然后在控制台打开 waker 详情页，确认"关于我"栏目下三项展示字段均已显示。

#### 7.5 完成告知

告知用户：
- Waker 名字和 ID
- 可以在控制台看到并开始对话
- 如需进一步配置（添加 Skills、MCP、修改头像等），可以在控制台操作或告诉你来帮忙

---

## MCP 与 Skills 推荐

- Skills：从已知类别推荐，或描述所需类型
- MCP：只推荐确信存在的包；不确定时描述集成类型让用户自行查找

```json
{
  "mcpServers": {
    "{name}": { "command": "npx", "args": ["-y", "@pkg/name"], "env": {} }
  }
}
```

## 语言规则

跟随用户语言。文件标题固定格式：`# Identity — {Name}` / `# Persona — {Name}` / `# Bible — {Name} Workflow`。

## 验证清单

- [ ] Positioning：30-80 字符，名词短语，列出能力，无人设口吻
- [ ] identity.md："You are..." 开头、Core Positioning、3-8 条粗体职责、边界、降级策略
- [ ] 全篇定义身份而非个体，不写死名字
- [ ] 人物型角色：identity 含 Character Consistency 段落、persona 含防跳出反模式、bible 含元问题路由
- [ ] persona.md：3-6 条 **关键词** — 解释、沟通策略、3-7 条反模式
- [ ] bible.md：Skills 表、任务路由、2-6 个命名工作流（Sequence + Rules）、交付契约
- [ ] description.md：第一人称、50-150 字、面向用户的自我介绍
- [ ] core-capabilities.json：4-8 项，name + description 格式，从 Responsibilities 提取
- [ ] work-styles.json：3-5 项，从 Working Style 提取
- [ ] delivery-commitments.json：3-5 项，从 Delivery Contract 提取
- [ ] 全篇领域专属内容，无泛泛填充
- [ ] 复杂度与角色匹配
- [ ] 语言跟随用户
- [ ] README 包含 CLI 自动配置命令和手动上传两种方式
- [ ] **阶段六**：写入 `employee-conf-templates.local.json` 后，`qoderwake waker template list` 能看到新模板
- [ ] **阶段六**：wakerContext JSON 字符串转义正确（换行、引号、反斜杠）
- [ ] **阶段七**：`qoderwake waker create` 成功返回 agentId
- [ ] **阶段七**：展示字段（coreCapabilities/workStyles/deliveryCommitments/description）全部写入成功
- [ ] **阶段七**：控制台 waker 详情页"关于我"栏目三项均显示
