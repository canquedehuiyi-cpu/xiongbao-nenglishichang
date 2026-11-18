# 钉钉 Plugin

通过 DWS CLI 为 Qoder 提供钉钉日历、文档、消息、待办、通讯录、AI 表格等能力。

## 结构

- `skills/`：来自 DWS 仓库的 multi skill 完整集合。
- `bin/install.sh`：上游公开版 DWS 安装脚本的快照。
- `bin/dws-install`：仅安装 DWS 二进制，不重复安装 Skill。
- `bin/dws`：将调用路由到宿主管理的 DWS 或用户安装的公开版 DWS。
- `.qoder-plugin/plugin.json`：Qoder manifest。

## 本地验证

```bash
qoder plugins validate .
qoder --plugin-dir .
```

启用 plugin 后，`bin/` 会进入 Agent Bash 工具的 PATH。首次执行钉钉任务时，Skill 会检查 DWS Runtime：

- 宿主已经提供 DWS 时直接使用，不重新安装。
- 未安装时先征得用户同意，再运行 `dws-install`。
- `dws-install` 固定设置 `DWS_NO_SKILLS=1`，避免覆盖 plugin 内的 multi skills。

宿主可以将受管 DWS Runtime 放在 `~/.qoder/bin/dws` 或 `~/.qoder-cn/bin/dws`，也可以
通过 `DWS_RUNTIME_EXECUTABLE=/absolute/path/to/dws` 显式指定。受管 Runtime 的优先级高于
PATH 中的公开版 DWS。

## 来源

Skill 和安装脚本同步自：

- Repository: `DingTalk-Real-AI/dingtalk-workspace-cli`
- Source commit: `7186a69b7821f1db0760f6d1bf606571939d95e1`

同步上游内容时，需要保留 `dingtalk-shared/SKILL.md` 中由本 plugin 增加的 Runtime 安装引导。
