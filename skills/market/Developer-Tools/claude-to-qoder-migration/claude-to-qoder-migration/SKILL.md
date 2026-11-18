---
name: claude-to-qoder-migration
description: 安全检查、规划并协助把 Claude Code 的用户级和项目级配置迁移到 Qoder CLI。当用户要求迁移 Claude Code 的 settings、MCP servers、commands、skills、agents、hooks、memory、rules、项目 memory、output styles、permissions 或 plugins 到 Qoder CLI 时使用。
---

# Claude 到 Qoder 迁移

只用于 Claude Code -> Qoder CLI。首要目标是保护用户现有环境：只 copy，不 move；不删除源文件；不静默覆盖目标文件。

## 不可违反的规则

- 先做只读检查。展示迁移计划前，不写文件、不运行安装命令。
- 默认使用用户启动 Qoder CLI 的当前目录作为项目上下文。如果 `~/.claude.json` 里有多个项目条目匹配，先让用户选择。
- 所有写入前都要用户确认。高风险资源单独确认：permissions、hooks、MCP secrets/env/headers、插件 marketplace/install 命令，以及所有冲突。
- 迁移计划和确认问题必须按 scope 拆开说明：用户级、项目共享级、项目本地级分别迁移哪些、跳过哪些、写到哪里。
- 不迁移 auth state、OAuth/session 文件、managed settings、remote settings、trust caches 或未知 state/cache 文件。
- 只写入 `references/mapping.md` 列出的目标文件；不要创建未列出的 Qoder 配置文件。
- 允许写入迁移状态文件 `~/.qoder/migration-state.json`（inspector 的默认 `--state` 路径）。它是本 skill 的记账文件，不是 Qoder 运行时配置；只记录已迁移项的标识（scope、目标路径或 `目标#mcpServers.name`、时间戳、项目路径），绝不写入 secret / env / headers 值。inspector 只读取它，写入只发生在用户批准的迁移成功之后。
- 未知、不支持、无效和空字段默认只报告；除非 `references/mapping.md` 明确写了迁移方式。
- 无论是否实际写入，最后都要生成迁移报告。

## 工作流

1. 运行只读 inspector：

```bash
node <skill-dir>/scripts/inspect-migration.mjs --project "$PWD"
```

需要机器可读结果时使用 `--format json`。如果没有 Node.js，不要跳过检查；按 `references/mapping.md` 中列出的源文件和目标文件手动检查，并在任何写入前生成同样结构的迁移计划。

inspector 是状态感知的：它读取迁移状态文件（默认 `~/.qoder/migration-state.json`，可用 `--state` 覆盖），把「已记录迁移过且目标仍存在」的项归入「已迁移（本次跳过）」，不再当作冲突反复要求确认。这让用户在每个项目目录跑一次时，全局配置只在第一次真正处理。逃生阀：`--force` 忽略全部状态、`--force-user` 仅忽略用户级状态，用于源配置更新后想重新迁移的场景。计划里每个可迁移/需确认项都带 `identity` 字段，执行后按它回写状态。

2. 在解释 inspector 输出、提出迁移方案或执行迁移前，先阅读 `references/mapping.md`，严格按其中的 scope、字段映射和缺口处理。

3. 向用户展示：

- 发现了哪些源文件
- 将会触碰哪些目标文件
- 用户级、项目共享级、项目本地级分别计划迁移哪些内容，分别不迁移哪些内容
- 哪些内容已经在 Qoder 可读取的位置
- 哪些内容因迁移状态记录被判定为「已迁移（本次跳过）」；告知用户如需重迁可用 `--force-user` 或 `--force`
- 建议迁移的项目和目标路径
- 冲突和可选处理方式
- 只报告、不支持、未知和空字段
- 如涉及插件，列出建议命令
- 如涉及 hooks，列出事件名、matcher、命令/提示、目标文件和唯一允许的变量替换；把它作为执行风险项请用户确认
- 如涉及 rules，按顶层文件/目录粒度列出源路径和目标路径（用户级 `~/.qoder/rules/`、项目级 `<project>/.qoder/rules/`），属低风险 copy-only
- 如涉及项目 memory（当前项目的 `~/.claude/projects/<id>/memory/`），把它作为**敏感项单独确认**：memory（尤其 `MEMORY.md` 与 `team/`）可能含个人信息或凭据。列出源/目标路径，但**不打印 memory 内容**；提醒用户迁移前后自查。同时告知：`team/` 子目录会整体 copy 保留结构，但 Qoder 的 memory 管理 UI 只识别顶层 `.md`，`team/` 下嵌套文件可正常 raw 读取、但在 UI 里非一等公民

4. 请求用户确认。低风险 copy-only 项（含 rules）可以按 scope 合并确认；高风险资源必须单独确认（permissions、hooks、MCP secrets/env/headers、插件命令、项目 memory 以及所有冲突）。不要只问“是否全部迁移”，要让用户看清每个 scope 的来源、目标和资源类型。

5. 只执行用户批准的项目：

- 复制文件/目录，不移动。
- 不覆盖已有目标。遇到冲突时，让用户选择跳过、追加、重命名副本或手动合并。
- 项目级 MCP 优先使用项目根 `.mcp.json`。如果项目根已有有效 `.mcp.json`，只报告 Qoder 可直接读取，不复制。
- 插件不直接编辑状态文件。用户批准后，使用 `qodercli plugins marketplace add`、`qodercli plugins install`、`qodercli plugins enable/disable`。如果用户需要 Claude 官方插件市场，建议命令是 `qodercli plugins marketplace add anthropics/claude-plugins-official --scope user|project|local`。

6. 更新迁移状态文件（仅在有实际成功写入时）：

- 写回 inspector 计划里报告的 `stateFile.path`（即本次运行实际使用的状态文件路径；未指定 `--state` 时为默认的 `~/.qoder/migration-state.json`）。不要自行拼默认路径，否则用了 `--state` 时会写错文件。
- 读取现有状态；不存在则新建 `{ "version":1, "tool":"claude-to-qoder-migration", "userScope":{"items":[]}, "projects":{} }`。
- 把本次**成功迁移**项的 `identity`（直接取自 inspector 计划，不要自行重新推导）合并进对应 scope：用户级进 `userScope.items`；项目共享级和项目本地级进 `projects[<项目绝对路径>].items`。去重后更新对应的 `migratedAt` 为当前时间。
- 只在实际写入成功后追加。用户跳过、冲突未解决或写入失败的项不要记入。执行中断时不要写脏状态。
- 状态文件只记 identity 标识，绝不写入 secret / env / headers 值。项目根 `.mcp.json` 中 compatibleInPlace 的项不需要记（它本就无需迁移）。

7. 输出最终迁移报告，包含：

- 已迁移项目
- 已跳过项目和原因（含因状态记录而「已迁移（本次跳过）」的项）
- 迁移状态文件的位置，以及本次新记录了哪些 identity
- 冲突及用户选择的处理方式
- 不支持或未知字段
- 只报告项目
- 生成或执行过的插件命令
- 创建的新文件或备份文件
- 建议的人工后续处理
- 如迁移了项目 memory：提醒用户 memory（尤其 `MEMORY.md` 与 `team/`）可能含个人信息或凭据，请迁移后自查；`team/` 下嵌套文件在 Qoder memory 管理 UI 里非一等公民（raw 读取正常）。仅迁移了当前项目的 memory，其他项目需在对应目录分别运行本 skill。
- 收尾提醒：如果迁移过来的 skills、agents、hooks、commands、plugins 或 output styles 中写死了 Claude 模型名、provider、auth 或模型相关环境变量，需要按 Qoder CLI 支持的配置调整。

## 资源说明

- `references/mapping.md`：迁移映射和缺口的准绳。解释检查结果或改文件前必须读取。
- `scripts/inspect-migration.mjs`：确定性的只读扫描脚本。会**只读**读取迁移状态文件来识别已迁移项；不得写文件、安装插件或访问网络。
- 迁移状态文件 `~/.qoder/migration-state.json`：本 skill 的记账文件，记录已迁移项的 identity，让多次运行不重复处理全局配置。由 skill 在迁移成功后写入，inspector 只读。删除它不影响 Qoder 运行，只会让下次运行重新提示已迁移项。
