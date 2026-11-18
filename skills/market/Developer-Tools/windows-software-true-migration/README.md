# Windows Software True Migration

Windows 开发环境/绿色软件跨盘**真实迁移**工具。把用户手动部署的工具目录（JDK、Maven、nvm、MySQL 解压版、Git 便携版、Redis 绿色版等）整体迁移到另一个磁盘，自动更新环境变量、PATH、Windows 服务、注册表、配置文件中的旧路径——不是 junction/symlink 假迁移，是改注册表/环境变量/服务路径的真迁移。

## 文件结构

| 文件 | 说明 |
|------|------|
| `SKILL.md` | Skill 描述文件（175 行）。AI agent 读这个了解怎么用脚本 |
| `migrate_template.ps1` | 迁移脚本模板（1756 行）。所有实际逻辑都在这里 |
| `README.md` | 本文件 |

核心设计：SKILL.md 是给 AI 看的"说明书"，migrate_template.ps1 是干活的"引擎"。两者分离，上下文占用低，脚本独立可用。

## 功能特性

- 自动发现源目录内所有软件及其路径引用（不硬编码软件名）
- 环境变量 / PATH / Windows 服务 / 注册表 / 配置文件全链路路径替换
- 路径变体覆盖：反斜杠、正斜杠、双反斜杠转义三种形式
- 边界匹配防误伤（`C:\work` 不会误改 `C:\work_backup`）
- 保留原文件编码（UTF-8 / GBK / ANSI 自动检测，不加 BOM）
- 只改文本配置文件（扩展名白名单），绝不触碰二进制文件
- 支持 Junction / Symlink 识别与重建
- 选择性迁移：混合目录中只迁移绿色软件，跳过安装器部署的软件
- 迁移前完整备份 + 异地备份（防单盘故障）
- 三级回滚（引用恢复 / 文件搬回 / 清理目标目录），支持断点续传
- 分级风险报告 + 验证报告（JSON / TXT / HTML 三格式）
- 4 个交互确认节点，关键操作不跳过
- 服务依赖分析与按依赖拓扑顺序启动
- 并发保护（lock file）与断点续传
- 大目录用 robocopy（>1GB 自动切换）
- 10 类隐藏引用扫描（Run/RunOnce、Startup、Task Scheduler、ODBC、IIS、PS Profile、Windows Terminal、Git config、Docker compose、WSL）

## 适用场景

**适用：**
- 用户手动部署（解压/复制）的开发工具目录整体搬到另一个磁盘
- 典型对象：JDK、Maven、Gradle、nvm/Node、Python 解压版、MySQL/Redis/RabbitMQ 解压版、Git 便携版、IDE 绿色版、绿色小工具
- 特征：目录内自带配置文件（.ini/.conf/.xml/.properties），无 uninstall.exe，无安装器残留

**不适用：**
- 通过安装器（MSI/NSIS/Inno Setup/WiX）安装的软件
- 目录内存在 uninstall.exe / unins000.exe / uninst.exe 等卸载程序
- 注册表 `HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall` 下有对应条目
- 这类软件的正确方式：卸载 → 重装到目标盘 → 恢复数据

## 使用方法

### 方式一：纯手动使用（不需要 AI）

1. 下载 `migrate_template.ps1` 到本地任意目录
2. 用文本编辑器打开，修改脚本顶部三个变量：

```powershell
$src = "C:\workSpace"            # 源目录
$dst = "D:\workSpace"            # 目标目录
$backupRoot = "D:\__migration_backup__"  # 备份目录（建议放在目标盘）
```

3. 以管理员身份运行 cmd，执行：

```
powershell -ExecutionPolicy Bypass -File migrate_template.ps1
```

4. 脚本会走完 12 个 Phase，在 4 个关键节点暂停等你确认（迁移计划、备份完成、锁定进程、旧目录清理）
5. 如需了解常见问题和排错，参考 `SKILL.md` 中的 Pitfalls 和 Troubleshooting 表格

### 方式二：在 AI 编程工具中使用（QoderWork、Claude Code、Cursor 等）

将 `SKILL.md` 和 `migrate_template.ps1` 放到对应工具的规则/技能目录下：

- **QoderWork**：将整个目录打包为 `.skill` 文件（zip 格式），在 QoderWork 中打开安装
- **Claude Code**：放入 `.claude/` 目录
- **Cursor**：放入 `.cursor/rules/` 目录
- **其他工具**：放入对应的 custom instructions / rules 目录

放好后，在对话中用自然语言描述需求即可，例如："帮我把 C:\workSpace 里的开发工具迁移到 D 盘"。AI agent 会读取 SKILL.md，按工作流复制模板、修改变量、生成 bat 启动器，然后让你以管理员身份运行。

### 方式三：生成 bat 启动器（推荐）

无论用哪种方式，最终执行时建议用 bat 启动器而非直接运行 ps1，因为 bat 可以自动检查管理员权限：

```bat
@echo off
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Please run as Administrator!
    pause
    exit /b 1
)
powershell -ExecutionPolicy Bypass -File "%~dp0migrate.ps1"
pause
```

将 `migrate_template.ps1` 重命名或复制为 `migrate.ps1` 放在 bat 同目录，右键以管理员身份运行 bat 即可。

## 迁移流程概览

| Phase | 内容 | 交互节点 |
|-------|------|----------|
| 0 | 迁移策略决策：逐子目录检测绿色/安装器，构建迁移对，发现引用 | 0.4 迁移计划确认 |
| 1 | 预检与备份：空间检查、权限检查、全量备份+异地备份 | 1.8 备份完成确认 |
| 2 | 停止服务与进程 | 2.3 锁定进程确认 |
| 3 | 文件移动（Copy → 校验 → Remove，大目录用 robocopy） | |
| 4 | 环境变量与 PATH 替换 | | 
| 5 | Windows 服务路径修复 | |
| 6 | 配置文件修复（原子修改，保持编码） | |
| 7 | 注册表修复（类型感知，WOW6432Node） | |
| 8 | 隐藏引用扫描（10 类） | |
| 9 | 源目录清理（重命名/删除/RunOnce） | 9.2 清理方式确认 |
| 10 | 全面验证 + 报告生成 | |
| 11 | 回滚（三级，条件触发，用户选择级别） | |

## 系统要求

- Windows 10/11 x64
- 管理员权限（脚本内自动检查，不足时拒绝执行）
- 目标盘有足够空间（源目录大小 x 1.2 的安全余量）
- PowerShell 5.1+（Windows 自带）

## 许可证

MIT License
