---
name: qodercli-session-sync
version: 0.2.0
description: Sync Qoder CLI session transcripts into the same-edition Qoder app session list (QoderCN pairs with qoderclicn, international with qodercli).
description_zh: 把同一版本的 qodercli 会话记录同步到 Qoder 应用会话列表（国内版配 qoderclicn，国际版配 qodercli，不要混用），重启应用后即可看到并打开。
user-invocable: true
argument-hint: "[项目路径 | all]"
---

# QoderCLI 会话同步

把 `qodercli` / `qoderclicn` 在本地生成的会话记录登记到 Qoder 桌面应用的会话列表里，
并把对话按应用自身的 `cli-import` 消息格式写入应用数据库，点开会话即可看到完整内容。
应用不会为外部导入的会话懒加载 CLI 历史，所以消息必须随会话一起写入。

## 何时使用

- 用户在 CLI 里聊过的会话，打开 Qoder 应用后找不到。
- 用户说“把命令行会话同步到应用里”“让 Qoder 显示 CLI 的会话”。
- 换了应用版本或工作区后，旧 CLI 会话没有出现在侧边栏。

## 步骤

1. 先预览，不写入：

   ```bash
   python "${QODER_PLUGIN_ROOT}/scripts/qodercli_sync.py" --dry-run --cwd "<项目绝对路径>"
   ```

   没有给出项目路径时用当前目录；用户要同步全部项目时把 `--cwd ...` 换成 `--all`。

2. 把预览结果用一两行告诉用户：会新增几个会话、标题分别是什么。

3. 用户确认要写入后执行（去掉 `--dry-run`）：

   ```bash
   python "${QODER_PLUGIN_ROOT}/scripts/qodercli_sync.py" --cwd "<项目绝对路径>"
   ```

   脚本会先把应用数据库备份到
   `%LOCALAPPDATA%\QoderCLISessionSync\backups\`，再逐条登记缺失的会话并写入消息；
   已存在的会话 ID 会跳过，可以重复执行。

4. 告诉用户：完全退出并重新打开 Qoder 应用后，这些会话会出现在对应工作区的会话列表里，
   点开即可看到完整对话。

## 注意

- 版本必须成对使用：同一个系统上，国内版 QoderCN 只搭配国内版 CLI（`qoderclicn`，`~/.qoder-cn/projects`，
  `com.qodercn.app.stable`），国际版只搭配国际版 CLI（`qodercli`，`~/.qoder/projects`，`com.qoder.app.stable`）。
  不要交叉混用，否则会话会被登记到错误版本的应用数据库，或因会话目录不匹配而同步不到。
- 只处理与当前应用版本匹配的数据目录：国内版应用对应 `~/.qoder-cn`，国际版对应 `~/.qoder`。
- 只同步顶层 `<project>/<session-id>.jsonl`，跳过 `subagents/` 和旧的 `transcript/` 目录，避免登记应用无法读取的会话。
- 不删除任何会话；只新增缺失的会话行，并修正本插件早期版本登记过的行（工作区、执行目标与消息）。
- 只重写本插件自己写入的 `cli-import` 消息；一旦该会话出现应用写入的消息，就不再改动它的消息。
- 只有斜杠命令、没有普通提问的会话同样会同步（命令内容作为标题）。
- 斜杠命令会转换成应用原生 chip：技能用 `skill://`，其他命令（含 MCP 命令）用 `command://`。
- 依赖 Python 3.8+（仅标准库）：Windows 用 `py -3` / `python`，macOS / Linux 用 `python3`；
  缺少时 `SessionStart` 钩子会输出安装提示，插件不会自动安装系统级依赖（需要管理员权限或交互确认）。
  手动同步同样需要 Python，如 `python3 "${QODER_PLUGIN_ROOT}/scripts/qodercli_sync.py" --cwd "<项目绝对路径>"`。
- 自动同步钩子已适配两端：Windows 走 `cmd.exe`，macOS / Linux 走 `/bin/sh`（`hooks/run-sync.cmd` 转调 `hooks/run-sync.sh`）；
  从压缩包安装后若 Unix 上不触发，执行 `chmod +x hooks/run-sync.cmd hooks/run-sync.sh`。

