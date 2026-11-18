# Lark / 飞书 Plugin

通过 `lark-cli` 为 Qoder 提供飞书与 Lark 的消息、文档、日历、多维表格、任务、邮件、
审批、会议等能力。当前插件版本为 `0.1.1`，配套 CLI 为 `1.0.98`，包含 28 个 Skills。

## 导入 New Qoder

在「扩展 → 插件 → 添加插件」中导入 `lark-plugin-updated.zip`。ZIP 根目录直接包含 `.qoder-plugin/`、`skills/`、`bin/` 等文件，不额外套插件名与版本号目录。

需要通过 CLI 安装时，先解压到独立目录：

```bash
unzip lark-plugin-updated.zip -d lark-plugin
qodercli plugins validate ./lark-plugin --strict
qodercli plugins install ./lark-plugin
```

## 结构

- `skills/`：来自 `larksuite/cli` 的完整官方 Skill 集合。
- `bin/lark-cli`、`bin/lark-cli.cmd`：将调用路由到显式配置、本 Plugin 管理或宿主/PATH 中的 Runtime。
- `bin/lark-cli-runtime-check*`：只检查 Runtime，不执行它。
- `bin/lark-cli-install*`：通过 npm 仅安装公开版 CLI，不重复安装 Skills。
- `.qoder-plugin/plugin.json`：Qoder manifest。

## Runtime

启用 Plugin 后，`bin/` 会进入 Agent Bash 工具的 PATH。首次执行飞书任务时，Skill 会检查
`lark-cli` Runtime：

- Runtime 已存在且版本配套时直接使用，不重新安装；旧版本按 Skill 引导升级。
- 未安装时先征得用户同意，再运行 `lark-cli-install`。
- 安装入口使用 `npm install` 安装 `@larksuite/cli`，不会执行官方 `install` 向导，因而不会
  重复安装或覆盖 Plugin 内的 Skills。

Unix Runtime 查找优先级：

1. `LARK_CLI_RUNTIME_EXECUTABLE`
2. Plugin 管理的用户级 npm Runtime（使显式安装/升级生效）
3. `~/.qoder/bin/lark-cli`
4. `~/.qoder-cn/bin/lark-cli`
5. PATH 中已有的 `lark-cli`
6. `~/.local/bin/lark-cli`

Windows 使用对应的 `lark-cli.exe`，Plugin 同时提供 `.cmd` 入口。

默认用户级安装目录为 `~/.local/share/qoder/lark-cli`。可通过
`LARK_CLI_INSTALL_ROOT` 修改安装根目录。安装器默认使用与 Skill 快照一致的
`@larksuite/cli@1.0.98`，可通过 `LARK_CLI_PACKAGE_SPEC` 显式覆盖。覆盖版本后需自行确认与插件内 Skills 的兼容性。

`LARK_CLI_RUNTIME_EXECUTABLE` 无效时直接报错，不静默换用其他运行时。设置此变量时，安装器不会另装一个实际不会被使用的版本；请更新指定的运行时或取消该配置后再安装。

本插件保留官方登录与授权流程，个人凭据不包含在包中。更新时先导入新版插件，再按需要运行 `lark-cli-install`；不要使用会同时写入外部 Skills 的官方安装向导或 `lark-cli update` 替代插件更新。

## 本地验证

```bash
qodercli plugins validate ./lark-plugin --strict
lark-cli-runtime-check
lark-cli --version
```

## 条件依赖

- 安装公开版 Runtime 需要 Node.js 与 npm，以及访问 npm 和官方二进制发布源的网络；npm 包声明 Node.js >= 16。
- 部分 Sheets 辅助脚本使用 Python，个别数据分析流程可能需要 pandas。
- Whiteboard Skill 会按需调用 `@larksuite/whiteboard-cli`。

## 来源

Skill 内容同步自：

- Repository: `larksuite/cli`
- Release tag: `v1.0.98`
- Package: `@larksuite/cli` 1.0.98
- Source commit: `ac81f5056ab88f37d581d25916f3dab85abfca76`
- Retrieved: 2026-11-02

同步上游内容时，需要保留 `lark-shared/SKILL.md` 中由本 Plugin 增加的 Runtime 检查与安装引导，以及共享更新提示和应用发布流程中的插件更新适配。

本次从 `1.0.87` 更新至 `1.0.98` 发布快照，同步全部 Skill 及配套资源，新增 `lark-meeting` 统一会议入口；旧的 VC、妙记、智能纪要等 Skill 名称保留为官方兼容入口。
