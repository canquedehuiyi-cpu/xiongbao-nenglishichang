# QoderCLI 会话同步

把 `qodercli` / `qoderclicn` 的会话记录同步进 Qoder 桌面应用的会话列表。

在 CLI 里聊过的会话，默认只存在于 `~/.qoder-cn/projects/`（国际版是 `~/.qoder/projects/`）的 JSONL 记录里，
Qoder 应用的侧边栏只显示应用数据库里登记过的会话，所以这些会话在应用里看不到。
这个插件把缺失的会话登记到应用数据库，并把对话按应用自己的 `cli-import` 消息格式写入，
打开会话即可看到完整内容。

## 版本搭配（重要）

同一个系统上，国内版 QoderCN 只搭配国内版 CLI（`qoderclicn`），国际版 QoderCN 只搭配国际版 CLI（`qodercli`），
不要交叉混用：

| 应用 | CLI | 会话目录 | 应用数据库 |
| --- | --- | --- | --- |
| 国内版 QoderCN | `qoderclicn` | `~/.qoder-cn/projects` | `com.qodercn.app.stable` |
| 国际版 Qoder | `qodercli` | `~/.qoder/projects` | `com.qoder.app.stable` |

混用会让会话被登记到错误版本的应用数据库，或因会话目录不匹配而完全同步不到。

## 功能

- 扫描本机 CLI 会话记录，找出应用里还没有的会话。
- 在应用数据库中登记会话（标题、工作目录、分支、模型、时间）。
- 把 JSONL 转换成应用消息表的 `cli-import` 格式（用户消息、思考、工具调用与结果、回复），
  打开会话即显示完整对话；应用原生导入会话不会再被重复写入。
- 斜杠命令按应用的原生格式渲染：技能用 `skill://` chip，其他命令（含 MCP 命令）用
  `command://` chip；工具调用带开始/结束时间与执行状态。
- 只新增会话，修正本插件早期版本登记过的行；不碰应用原生会话，不删除任何会话，重复执行安全。
- 写入前自动备份应用数据库。
- 每轮回复结束（`Stop`）和会话结束（`SessionEnd`）时通过钩子自动同步；会话启动时检测 Python 依赖，缺失则提示安装命令。

## 安装

```bash
qoderclicn plugins install "<本目录绝对路径>"
```

安装后重启 Qoder 应用。也可以在 Qoder 应用的插件/扩展页面里从本地目录安装。

## 依赖

- **Python 3.8+**，插件脚本只使用标准库。Windows 用 `py -3` 或 `python`，macOS / Linux 用 `python3`。
  - Windows：从 <https://www.python.org/downloads/> 安装，勾选 “Add python.exe to PATH”。
  - macOS：`xcode-select --install`（自带 python3），或 `brew install python`。
  - Debian / Ubuntu：`sudo apt install python3`；Fedora：`sudo dnf install python3`。
- 自动同步钩子：Windows 由 `cmd.exe` 执行，macOS / Linux 由 `/bin/sh` 执行。两端共用
  `hooks/run-sync.cmd`（Unix 端自动转调 `hooks/run-sync.sh`），不需要额外的 shell 或构建工具。
- 插件不会自动安装 Python：安装系统级依赖需要管理员权限或交互确认（macOS 的 Xcode 命令行工具、
  Linux 的 `sudo`），钩子无法安全地静默完成。插件没有单独的“启用时”钩子，因此在每次会话启动
  （`SessionStart`）时检测；缺少依赖会输出安装提示，安装后重启 Qoder 即恢复自动同步。
- 手动同步同样依赖 Python，例如 `python3 scripts/qodercli_sync.py --cwd "<项目绝对路径>"`。
- 如果从压缩包安装后 macOS / Linux 上自动同步不触发，给钩子脚本补可执行权限：
  `chmod +x hooks/run-sync.cmd hooks/run-sync.sh`。

## 使用

在 Qoder CLI 里输入 `/qodercli-session-sync`，或在 Qoder 应用里 `@qodercli-session-sync`；
也可以直接和 Agent 说“把 CLI 的会话同步到应用里”。

命令行直接运行：

```bash
# 预览当前目录对应的项目
python scripts/qodercli_sync.py --dry-run --cwd .

# 写入指定项目（替换为你的项目绝对路径）
python scripts/qodercli_sync.py --cwd "<项目绝对路径>"

# 所有项目，只取最近 20 个
python scripts/qodercli_sync.py --all --limit 20
```

写完 **完全退出并重新打开 Qoder 应用**，会话会出现在对应工作区的列表里，
点开即可看到完整对话。

## 参数

| 参数 | 说明 |
| --- | --- |
| `--cwd <路径>` | 只同步该工作目录的会话 |
| `--cwd-only` | 只同步当前进程目录 |
| `--hook` | 从钩子通过 stdin 传入的 JSON 读取会话目录（`Stop` / `SessionEnd` 使用） |
| `--all` | 同步所有项目 |
| `--limit N` | 只处理最近更新的 N 个会话 |
| `--dry-run` | 只预览，不写数据库 |
| `--db <路径>` | 指定应用数据库（自动识别国内版/国际版） |
| `--projects-root <路径>` | 指定 CLI 会话目录（默认按应用版本自动选择） |
| `--quiet` | 只输出错误 |

## 工作原理

1. 读取 `~/.qoder-cn/projects/<项目>/<session-id>.jsonl`，解析首条真实用户消息作为标题，
   并取出工作目录、分支、模型和起止时间。
2. 打开 Qoder 应用的 `main.sqlite`（`%APPDATA%\com.qodercn.app.stable\main.sqlite`）。
3. 对应用里不存在的 `session_id`，在 `chat_sessions` 中登记一行，标记 `importedFrom = qodercli`，
   并复用或创建对应的工作区。
4. 把 JSONL 转成应用消息表能直接渲染的 `cli-import` 行：每条用户提示一条消息，
   同一轮里的思考、工具调用（含工具结果）和回复合并成一条助手消息，序号按轮次递增。
   国内版/国际版的消息表列不同，脚本按实际存在的列写入；压缩摘要等仅用于转录的记录会被跳过。
   应用只会懒加载自己创建的会话的历史，所以导入会话必须自带消息，否则打开是空的。
5. 插件注册的 `Stop` 钩子会在每轮回复结束时同步一次，`SessionEnd` 再兜底一次；钩子从 stdin 的 JSON
   取当前会话的工作目录，只处理该项目。CLI 会话继续增长时，下次同步会按 JSONL 的修改时间重写该会话的消息。

数据库备份位于 `%LOCALAPPDATA%\QoderCLISessionSync\backups\`，只保留最近 20 份。

## 限制

- 只处理与当前应用版本匹配的数据目录：国内版应用只读取 `~/.qoder-cn`，国际版只读取 `~/.qoder`；
  同一系统上不要混用两个版本的 CLI 与应用（见上文“版本搭配”）。
- 只同步顶层 `<project>/<session-id>.jsonl`；`subagents/` 子会话和旧版 `transcript/` 目录会被跳过，
  因为应用无法按会话 ID 恢复它们。
- 需要本机有 Python 3.8+（Windows 可用 `py -3`）。脚本只使用标准库。
- 自动同步钩子在 Windows 使用 `cmd.exe`、macOS / Linux 使用 `/bin/sh`；只要 Python 3.8+ 可用即生效，
  缺少依赖时由 `SessionStart` 钩子提示安装命令（见上文“依赖”）。
- 应用升级改变数据库结构后，脚本可能需要跟随调整。
- 会话内容仍以 CLI 的 JSONL 为准；删除 JSONL 后应用里也读不到历史。

## 卸载

```bash
qoderclicn plugins uninstall qodercli-session-sync
```

已同步进应用的会话不会自动删除；需要时在应用里手动删除会话。
