# Claude Code 到 Qoder CLI 迁移映射

本文件是迁移决策的准绳。没有在这里列出的字段，一律报告为 unknown，不要自动迁移。

## 目标模型

Qoder CLI 迁移目标：

| 范围 | 目标 |
|---|---|
| 用户 settings | `~/.qoder/settings.json` |
| 项目共享 settings | `<project>/.qoder/settings.json` |
| 项目本地 settings | `<project>/.qoder/settings.local.json` |
| 项目 MCP | `<project>/.mcp.json` |
| 用户 commands | `~/.qoder/commands/` |
| 项目 commands | `<project>/.qoder/commands/` |
| 用户 skills | `~/.qoder/skills/` |
| 项目 skills | `<project>/.qoder/skills/` |
| 用户 agents | `~/.qoder/agents/` |
| 项目 agents | `<project>/.qoder/agents/` |
| 用户 output styles | `~/.qoder/output-styles/` |
| 项目 output styles | `<project>/.qoder/output-styles/` |
| 用户 rules | `~/.qoder/rules/` |
| 项目 rules | `<project>/.qoder/rules/` |
| 项目 memory（当前项目） | `<qoderHome>/projects/<sanitizePath(项目根)>/memory/` |
| 用户 memory | `~/.qoder/AGENTS.md` |
| 项目 memory | `<project>/AGENTS.md` |
| 项目本地 memory | `<project>/AGENTS.local.md` |

## 迁移状态文件

为避免在多个项目目录重复运行时，全局配置被反复当作冲突要求确认，本 skill 维护一个记账文件：

- 路径：`~/.qoder/migration-state.json`（inspector `--state` 默认值，随 `--home` / `QODER_CONFIG_DIR` 解析）。
- 用途：记录已成功迁移项的 identity，inspector 只读取它，把「已记录且目标仍存在」的项归入「已迁移（本次跳过）」。
- 写入时机：只由 skill 在用户批准的迁移**成功后**写入；inspector 永不写。
- schema：

```json
{
  "version": 1,
  "tool": "claude-to-qoder-migration",
  "userScope": { "migratedAt": "ISO8601", "items": ["<identity>"] },
  "projects": { "<项目绝对路径>": { "migratedAt": "ISO8601", "items": ["<identity>"] } }
}
```

- identity 计算（读写两端必须一致，直接取 inspector 计划里的 `identity` 字段，**不要自行推导或改成绝对路径**）：
  - MCP server → `<inspector 目标标签>#mcpServers.<name>`。目标标签用符号形式，不是绝对路径：用户级 `~/.qoder/settings.json`、项目共享级 `<project>/.mcp.json`、项目本地级 `<project>/.qoder/settings.local.json`。
  - settings 字段（permissions / hooks / outputStyle）→ `<inspector 目标标签>#<字段>`，如 `~/.qoder/settings.json#permissions`。
  - commands / skills / agents / output-styles 顶层项 → 目标绝对路径。
  - 记忆文件 → 目标绝对路径。
- scope 归属：用户级进 `userScope.items`；项目共享级与项目本地级都进 `projects[<项目绝对路径>].items`。
- 只记 identity 标识，**绝不**写入 secret / env / headers 值。
- 已知限制：状态是 identity 感知、非 content 感知。若首次迁移后修改了源里某已迁移项的值，本工具不会自动重迁；用 `--force-user`（仅用户级）或 `--force`（全部）强制重新扫描。
- 状态文件自身永不作为迁移源，也永不被迁移；删除它不影响 Qoder 运行。



常见 Claude Code 源：

| 源 | 含义 |
|---|---|
| `~/.claude/settings.json` | 用户级 settings |
| `~/.claude.json` | 用户/本地 MCP、项目状态、auth/session/cache state |
| `<project>/.claude/settings.json` | 项目共享 settings |
| `<project>/.claude/settings.local.json` | 项目本地 settings |
| `<project>/.mcp.json` | 项目 MCP，已经位于标准位置 |
| `~/.claude/commands/`、`<project>/.claude/commands/` | Slash commands |
| `~/.claude/skills/`、`<project>/.claude/skills/` | Skills |
| `~/.claude/agents/`、`<project>/.claude/agents/` | Agents |
| `~/.claude/output-styles/`、`<project>/.claude/output-styles/` | Output styles |
| `~/.claude/rules/`、`<project>/.claude/rules/` | Rules（条件/全量加载的指令片段） |
| `~/.claude/projects/<sanitize(项目根)>/memory/` | 当前项目的 auto-memory（含 `MEMORY.md`、topic `.md`、`team/` 子目录） |
| `~/.claude/CLAUDE.md`、`<project>/CLAUDE.md` | Memory / instructions |
| `<project>/CLAUDE.local.md` | 项目本地 memory / instructions |
| `~/.claude/keybindings.json` | Keybindings，不兼容 |

## Scope 确认规则

迁移计划和用户确认必须按 scope 拆开：

- 用户级：来源通常是 `~/.claude/**` 或 `~/.claude.json` 顶层；目标通常是 `~/.qoder/**`。
- 项目共享级：来源通常是 `<project>/.claude/settings.json`、`<project>/.claude/**` 或 `<project>/CLAUDE.md`；目标通常是 `<project>/.qoder/**`、`<project>/AGENTS.md` 或 `<project>/.mcp.json`。
- 项目本地级：来源通常是 `<project>/.claude/settings.local.json`、`<project>/CLAUDE.local.md` 或 `~/.claude.json` 的当前项目条目；目标通常是 `<project>/.qoder/settings.local.json` 或 `<project>/AGENTS.local.md`。

确认时列出每个 scope 中要迁移的资源类型、源路径、目标路径和冲突。不要用一个模糊的“全部迁移”确认代替 scope 级说明。

## MCP

推荐目标：

| 源 | 目标 | 决策 |
|---|---|---|
| `<project>/.mcp.json` | 原文件 | 不迁移。校验并报告 Qoder 可读取。 |
| `~/.claude.json` 顶层 `mcpServers` | `~/.qoder/settings.json` 的 `mcpServers` | 写入前确认。 |
| `~/.claude.json` 的 `projects[projectPath].mcpServers` | `<project>/.qoder/settings.local.json` 的 `mcpServers` | 写入前确认。 |
| `<project>/.claude/settings.json` 的 `mcpServers` | `<project>/.mcp.json` | 确认后迁移，优先 `.mcp.json`，不要新写入 `.qoder/settings.json`。 |
| `<project>/.claude/settings.local.json` 的 `mcpServers` | `<project>/.qoder/settings.local.json` | 写入前确认。 |

支持的 MCP server 字段：

`command`、`args`、`env`、`cwd`、`url`、`headers`、`tcp`、`type`、`timeout`、`trust`、`description`、`includeTools`、`excludeTools`、`extension`、`oauth`、`disabled`、`headersHelper`、`alwaysAllow`。

规则：

- 除非有明确转换规则，否则原样保留支持字段。
- `env`、`headers` 和 `headersHelper` 视为敏感项。展示 key 名和目标位置，不主动打印完整 secret value，除非用户要求。
- 如果目标中已经存在同名 server，停止并询问：保留目标、替换目标、重命名源 server 或跳过。
- 不支持字段要列出源路径和 server 名。
- 不迁移 OAuth tokens、审批状态或连接状态。

## Settings

| 字段 | 迁移策略 |
|---|---|
| `permissions.allow`、`permissions.deny`、`permissions.ask` | 必须确认。展示目标 scope 和访问边界影响后再保留值。 |
| `permissions.additionalDirectories`、`permissions.trustDirectories` | 必须确认。这些字段会扩大 trust 或文件系统访问范围。 |
| `hooks` | 必须确认，因为 hooks 会执行命令或触发模型/agent 评估。迁移计划里列出 hook 事件名、matcher、命令/提示、目标文件和变量替换；只做下方列出的明确转换。 |
| `outputStyle` | 必须确认。只有对应 style 文件已经在 Qoder 目标位置存在后，才设置 active style。 |
| `enabledPlugins`、`extraKnownMarketplaces` | 生成插件计划和命令；不直接编辑插件状态文件。 |
| `mcpServers` | 按 MCP 规则处理。 |
| `env` | 只报告。Qoder settings 没有等价的顶层 env 注入字段。 |
| `model`、`fallbackModel`、provider/auth/model 相关字段 | 默认只报告。模型名、provider 和 auth 面不同。 |
| managed 或 policy 字段 | 不迁移，只报告。 |
| 空对象、空数组、`null` | 跳过，并列为 empty skipped。 |
| 未知字段 | 只报告。 |

## Hooks

明确支持的转换：

| Claude token | Qoder token |
|---|---|
| `$CLAUDE_PROJECT_DIR` | `$QODER_PROJECT_DIR` |

规则：

- 写入前展示 hook diff 或命令，并把 hooks 标为需要用户确认的执行风险项。
- 仅自动替换上表列出的 token。其他 `CLAUDE_*` 变量、环境变量名、插件路径变量、命令名称、matcher、timeout、type、事件名和 hook 顺序都保持原样。
- 如果 hook 含有其他 `CLAUDE_*` token、显式调用 `claude`、读取 Claude 状态文件或依赖 Claude-only 插件路径，默认只报告，不自动迁移；除非用户明确批准具体编辑方式。
- 如果目标已存在 hooks，询问追加、替换或跳过。
- 只有发现不支持字段、不可映射依赖或目标 schema 冲突时，才列为兼容性/支持性问题；其他 hook 项按执行风险处理。

## Memory

| 源 | 目标 | 默认行为 |
|---|---|---|
| `~/.claude/CLAUDE.md` | `~/.qoder/AGENTS.md` | 目标不存在时 copy；目标存在时询问。 |
| `<project>/CLAUDE.md` | `<project>/AGENTS.md` | 目标不存在时 copy；目标存在时询问。 |
| `<project>/CLAUDE.local.md` | `<project>/AGENTS.local.md` | 目标不存在时 copy；目标存在时询问。 |

目标存在时绝不覆盖。给用户选：跳过、追加、生成并列文件或手动合并。

## Commands、Skills、Agents、Output Styles

从对应 Claude 位置 copy 到 Qoder 位置。保留相对路径，不覆盖已有文件。迁移计划按顶层 item 粒度展示：一个 command 文件或 namespace、一个 skill 目录、一个 agent 文件/目录、一个 output style 文件/目录作为一项。

复制 output style 文件和设置 `outputStyle` 为 active 是两个独立动作。active setting 必须单独确认。

如果 commands、skills、agents、hooks、plugins 或 output styles 内部包含 Claude 模型名、provider、auth 或模型相关环境变量，不要自动按原值迁移为可用配置。报告这些位置，并说明需要改成 Qoder 支持的模型配置。

## Rules

| 源 | 目标 | scope |
|---|---|---|
| `~/.claude/rules/` | `~/.qoder/rules/` | 用户级 |
| `<project>/.claude/rules/` | `<project>/.qoder/rules/` | 项目共享级 |

- 直接 copy，无需转换。位置 1:1 对应，格式都是 markdown +（可选）YAML frontmatter。
- 兼容性：Claude rules frontmatter 只有 `paths`（glob 条件加载）或无 frontmatter（启动即加载）。Qoder frontmatter 是超集（`paths`/`glob` + `trigger`/`description`/`alwaysApply`），全部接受；frontmatter 差异只影响激活时机，不会报错。
- 与 commands/skills/agents/output-styles 同规则：按顶层文件/目录粒度展示；保留相对路径；不覆盖已有目标；identity = 目标路径；状态记忆自动生效。属低风险 copy-only。

## 项目 memory 目录

| 源 | 目标 | scope | 默认行为 |
|---|---|---|---|
| `~/.claude/projects/<sanitize(项目根)>/memory/`（含 `MEMORY.md`、topic `.md`、`team/` 子目录） | `<qoderHome>/projects/<sanitize(项目根)>/memory/` | 项目本地级 | 作为**敏感项**始终需用户显式确认；直接 copy，绝不覆盖。 |

- 只处理**当前项目**（`$PWD` 对应的 memory）。其他项目的 memory 需在对应目录分别运行本 skill。
- 兼容性（已多源交叉验证）：两边 auto-memory 同源 schema——`MEMORY.md` 索引（无 frontmatter）+ topic 文件（`name`/`description`/`type` frontmatter，type 取值 `user`/`feedback`/`project`/`reference`）。Qoder 解析容错：无 frontmatter / 未知 type 不报错，兜底 `type:project`。直接 copy 即可用。
- 目录名计算：源目录名与目标目录名用**同一** sanitize 规则（`[^a-zA-Z0-9]→-`，保留大小写；结果 >200 字符时取 `slice(0,200) + '-' + djb2(原始路径) 的 base36`）。因此源目录名 == 目标目录名。inspector 用同一个 `sanitizeProjectId` 同时算源和目标，保证一致。
- 敏感性：memory（尤其 `MEMORY.md` 与 `team/`）可能含个人信息或凭据。必须作为敏感项让用户**单独确认**，不得并入低风险批量确认。**不打印 memory 内容**，只展示源/目标路径。
- `team/` 子目录：作为**单个目录 item** 整体 copy 保留结构，用一个 identity（= 目标 `team` 路径）追踪。已知局限：迁移后若 `team/` 下新增文件，需 `--force` 才会重新处理；Qoder memory 管理 UI 只识别顶层 `.md`，`team/` 下嵌套文件 raw 读取正常但在 UI 里非一等公民。
- 冲突：目标 `MEMORY.md` 或 `team/` 已存在时走冲突流程（跳过 / 重命名副本 / 手动合并），保守不自动合并覆盖。
- 源缺失兜底：若 memory 目录不存在或为空，只报告期望的源路径（让用户判断是「没有 memory」还是「目录名没匹配上」），不静默跳过、不报错、不猜测其他 sanitize 规则。
- 配置目录：源用 `CLAUDE_CONFIG_DIR`、目标用 `QODER_CONFIG_DIR`/`QODER_CLI_HOME` 解析。已知全 skill 层面局限：目标目录未处理 CN brand 目录（`.qoder-cn`），本次不单独为 memory 补齐，作为独立后续项。

## Keybindings

不迁移。Claude Code keybindings 和 Qoder keybindings 使用不同 schema。报告源文件，并说明需要手动重映射。

## Plugins

默认只检测和报告。不 copy 插件 cache/state 文件，不手动编辑 `installed_plugins`、known marketplace state 或 plugin cache。

用户批准插件迁移时，使用 Qoder 命令：

```bash
qodercli plugins marketplace add <source> --scope user|project|local
qodercli plugins install <plugin-or-path> --scope user|project|local
qodercli plugins enable <plugin-id> --scope user|project|local
qodercli plugins disable <plugin-id> --scope user|project|local
```

Claude 官方插件市场可由 Qoder 直接添加：

```bash
qodercli plugins marketplace add anthropics/claude-plugins-official --scope user|project|local
```

添加后，按需安装具体插件：

```bash
qodercli plugins install <plugin-name>@claude-plugins-official --scope user|project|local
```

如果源配置里已有 `extraKnownMarketplaces` 或 `enabledPlugins`，迁移计划应列出对应 Qoder 命令，但默认不执行。不要把 Claude 的 marketplace/cache/state 文件复制到 Qoder。

报告这些风险：

- `lspServers` 和 `channels` 可能被 schema 接受，但运行时忽略。
- `monitors` 和其他未识别 contribution points 不自动迁移。
- 插件 commands/hooks/skills 可能硬编码 `CLAUDE_*` 变量或 Claude-specific 路径。
- marketplace add/install 可能下载并运行第三方代码。
- Qoder 插件安装器支持 dependencies，但依赖是否可用、是否被策略允许仍需确认。

## 永不自动迁移

- Auth/session tokens
- OAuth state
- Managed settings 和 remote settings
- Trust caches 和项目审批选择
- Runtime caches
- `~/.claude.json` 中未知的 per-project state
- Keybindings
- 顶层 `env`
- Claude 模型名、provider、auth 或模型相关环境变量
- 不支持或未知字段
- 迁移状态文件 `~/.qoder/migration-state.json` 自身（它是记账文件，不作为迁移源，也不被迁移）
