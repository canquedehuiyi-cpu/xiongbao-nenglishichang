---
name: windows-software-true-migration
description: Windows 开发环境/绿色软件跨盘真实迁移流程。适用于用户手动部署的工具目录（如 JDK、Maven、nvm、MySQL 解压版、Git 便携版、Redis 绿色版等）整体迁移到另一个磁盘，保证环境变量、服务、注册表、配置文件全部生效。不适用于通过安装器（MSI/NSIS/Inno Setup）安装的软件——这类软件应卸载后重装到目标盘。
version: 3.7.0
platform: Windows 10/11 (x64)
requires_admin: true
risk_level: high
rollback: supported
interaction: required
template_file: migrate_template.ps1
---

# Windows 开发环境/绿色软件跨盘真实迁移（v3.7.0）

## 适用场景

**适用：** 用户手动部署（解压/复制）的开发工具目录整体搬到另一个磁盘。典型对象：JDK、Maven、Gradle、nvm/Node、Python 解压版、MySQL/Redis/RabbitMQ 解压版、Git 便携版、IDE 绿色版、绿色小工具。特征：目录内自带配置文件（.ini/.conf/.xml/.properties），无 uninstall.exe，无安装器残留。不是简单复制文件，而是"真实迁移"——环境变量、PATH、Windows 服务、注册表、配置文件中的旧路径全部更新。

**不适用：** 通过安装器（MSI/NSIS/Inno Setup/WiX）安装的软件。目录内存在 uninstall.exe / unins000.exe 等卸载程序。注册表 Uninstall 下有对应条目。这类软件的正确迁移方式是：卸载 → 重装到目标盘 → 恢复数据。

## 核心原则

1. **发现驱动，非硬编码**：不假设用户安装了哪些软件，通过扫描自动发现
2. **路径替换覆盖所有变体**：反斜杠、正斜斜杠、双反斜杠转义
3. **精确匹配防误伤**：正则词边界，避免 `C:\work` 误匹配 `C:\work_backup`
4. **保留原文件编码**：修改配置文件时检测并保持原始编码（含 GBK/ANSI）
5. **只处理文本配置**：严格限定文件扩展名白名单，绝不触碰二进制文件
6. **原子操作**：所有修改先备份、写临时文件、验证后替换
7. **可回滚**：每步操作记录回滚信息，支持基于备份数据的三级回滚
8. **选择性迁移**：混合目录中只迁移绿色软件，跳过安装器软件，后续路径替换只针对已迁移子目录（$migrationPairs）

## 风险声明

本 skill 涉及修改系统/用户环境变量、Windows 服务启动路径、HKLM/HKCU 注册表、移动/删除文件、终止进程/服务。所有修改均在 Phase 1 完成备份后方可执行。如任何步骤失败，立即进入 Phase 11 回滚。

## 前置条件

- Windows 10/11 x64，管理员权限
- 目标盘有足够空间（源目录大小 × 1.2 的安全余量）
- 如果 agent shell 本身依赖待迁移目录中的工具（如 Git），需要用户手动配合
- **实现文件**：完整迁移脚本在同目录下的 `migrate_template.ps1`（~1700 行）。Agent 不需要从 SKILL.md 拼装代码，直接使用该模板。

## Agent 工作流

1. 读取本 SKILL.md 了解适用性、Phase 概览、交互节点、Pitfalls、Verification
2. 将 `migrate_template.ps1` 复制到工作目录
3. 修改脚本顶部的三个配置变量：
   - `$src` — 源目录路径
   - `$dst` — 目标目录路径
   - `$backupRoot` — 备份根目录（建议放在目标盘）
4. 生成 `migrate.bat` 启动器（见下方模板）
5. 告知用户以管理员身份运行 `migrate.bat`，脚本会在交互节点暂停等待确认
6. 迁移完成后，引导用户查看验证报告并执行 Verification 清单

### migrate.bat 模板

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

### 回滚

回滚不在主脚本中自动执行。如果迁移失败或用户要求回滚：
- 运行 `migrate_template.ps1` 的 Phase 11 部分（手动从备份目录执行）
- 或 agent 从 SKILL.md 的 Phase 11 描述生成独立的 `rollback.ps1`，使用 `migrate_template.ps1` 中的 Phase 11 代码块

## Phase 概览

### Phase 0: 迁移策略决策
逐子目录检测是否为绿色软件或安装器部署（检测卸载程序/注册表卸载项/MSI残留）。混合目录时由用户选择迁移范围。构建 `$migrationPairs`（只含已迁移子目录的 Old→New 路径对）。发现服务、进程、环境变量、注册表引用。输出迁移计划并等待用户确认。

### Phase 1: 预检与发现
检查目标盘空间（源 × 1.2）、管理员权限、杀毒软件排除。盘点源目录链接（Junction/Symlink）。备份：环境变量、服务配置、注册表（reg export）、配置文件、链接信息。关键备份额外复制到 `$env:USERPROFILE\__migration_offsite__` 防止单点故障。等待用户确认备份完整。

### Phase 2: 停止服务与进程
暂停 Windows Search 索引。按优雅→强制顺序停止引用源目录的服务和进程（排除 critical 系统进程）。残留进程需用户确认是否继续。

### Phase 3: 文件移动
只迁移 `$migrateItems` 中的子目录。跨盘复制 = Copy → 大小/数量校验 → MD5（关键文件） → Remove。大目录（>1GB）用 robocopy。断点续传：读取 manifest 跳过已成功项。重建 Junction/Symlink。残留文件写入 locked_files.{json,csv}。

### Phase 4: 环境变量与 PATH
遍历 `$migrationPairs` 替换 Machine/User 环境变量中的旧路径。验证 PATH 无残留。检查多级变量引用（%VAR% 链）。广播 WM_SETTINGCHANGE 通知所有进程。

### Phase 5: Windows 服务路径
解析服务 PathName（区分简单 exe / 复杂启动命令），遍历 `$migrationPairs` 替换路径。用 `sc.exe config binPath=` 修改。分析服务依赖关系（Win32_DependentService），保存到 service_dependencies.json。

### Phase 6: 配置文件修复
扫描目标目录中的文本配置文件。原子修改：备份 → 检测编码（含 GBK fallback） → 遍历 `$migrationPairs` 替换 → 写临时文件 → 验证（旧路径残留/大小异常） → Move 替换。空文件跳过。

### Phase 7: 注册表修复
遍历 `$migrationPairs` 过滤注册表引用。类型感知修改：String/ExpandString/MultiString 各自处理。CLSID\InProcServer32 默认值用 `reg add /ve`。WOW6432Node 同时扫描。

### Phase 8: 隐藏引用扫描与修复
10 类隐藏引用：Registry Run/RunOnce、Startup Folder（.lnk + .bat/.cmd/.vbs）、Task Scheduler（Actions + WorkingDirectory）、ODBC、IIS、PowerShell Profile、Windows Terminal settings、Git config、Docker compose、WSL config。每类修改前创建 `.migration_bak` 备份。

### Phase 9: 源目录清理
检查残留文件 → 尝试重命名旧目录为 `.migration_backup`（3 次重试）。用户选择：保留 / 立即删除 / 重启后自动删除（RunOnce）。

### Phase 10: 全面验证
恢复 Windows Search。分级扫描（Critical: 服务/PATH/启动项/计划任务；Warning: 环境变量/注册表；Info: 配置文件残留）——所有检查遍历 `$migrationPairs` 而非整个 `$src`。服务按依赖拓扑顺序启动，循环依赖检测。生成 verification_report.{json,txt,html}。Toast 通知 + Event Log。运行级验证：用全路径直接执行 CLI 工具（不依赖 PATH）。

### Phase 11: 回滚（三级）
**Level 1** — 引用恢复：恢复环境变量/服务/注册表/配置文件/链接。配置恢复顺序：.migration_bak 覆盖 → 清理 .migration_tmp → 从 configs/ 目录恢复。用户手动修改保存为 .migration_conflict_时间戳。
**Level 2** — 完整恢复：Level 1 + 按 manifest 将文件移回源目录。
**Level 3** — 清理迁移目标：Level 1 + 删除新目录和 Junction。
所有级别支持 rollback_progress.json 断点续传。Phase 8 修改的外部文件需手动用 `.migration_bak` 恢复。

## Interaction Guide

脚本在以下节点暂停等待用户确认，**不得跳过**：

| 节点 | Phase | 确认内容 |
|------|-------|----------|
| 迁移计划确认 | 0.4 | 源/目标目录、软件列表、服务/注册表引用数、风险提示 |
| 备份完成确认 | 1.8 | 备份目录、异地备份、所有备份文件列表 |
| 锁定进程确认 | 2.3 | 无法关闭的进程列表，是否继续 |
| 旧目录清理确认 | 9.2 | 保留/立即删除/重启后删除 |

规则：Critical 节点在 NonInteractive 模式下会 abort 而非自动确认。

## Pitfalls

- **PowerShell 内联 $ 被吃**：cmd.exe 中 `powershell -Command` 会吞 `$` 变量。所有代码在 .ps1 文件中，用 `-File` 执行。
- **路径变体遗漏**：配置中可能用正斜杠、双反斜杠。Replace-PathVariants 处理 3 种变体。
- **部分路径误伤**：正则边界 `(?![a-zA-Z0-9_\\])` 防止 `C:\work` 误改 `C:\work_backup`。
- **配置文件编码**：中文 Windows .ini 常为 GBK。Detect-Encoding 检测 BOM → UTF-8 严格解码 → GBK fallback。绝不用 `Set-Content -Encoding UTF8`（加 BOM）。
- **服务 binPath 引号**：`sc config binPath=` 对引号敏感。规范化为 `"exe路径" 参数`。PathName 含 `%SystemRoot%` 需先 ExpandEnvironmentVariables。
- **注册表默认值**：CLSID\InProcServer32 默认值必须用 `reg add /ve`，Set-ItemProperty 无效。
- **WOW6432Node**：64 位系统必须同时扫描 32 位注册表。
- **symlink 变实体**：Move-Item 把 junction/symlink 搬成实体目录。需先删链接再重建。
- **ConvertFrom-Json 单元素**：依赖数组单元素变字符串，需 `@()` 强制数组化。
- **Phase 8 外部文件回滚**：Phase 8 修改的 PS Profile / WT settings / Git config / 启动脚本 / docker-compose 创建了 `.migration_bak`，但 Phase 11 Level 1 的 config 恢复只覆盖 configs/ 目录内的文件。需手动恢复外部文件。
- **杀毒软件锁定**：Windows Defender 实时扫描会锁文件。Phase 1.3 尝试添加排除。
- **大目录复制**：>1GB 用 robocopy（/E /COPYALL /R:3 /W:5），exit code 0-7 成功，8+ 错误。

## Verification

1. Phase 10 验证报告 Critical = 0，Warning = 0
2. 新 CMD 窗口中已迁移软件 CLI 正常输出版本号（Phase 10.6 用全路径验证）
3. 所有受影响服务 Running（按依赖顺序启动，循环依赖已检测）
4. 源目录已重命名为 .migration_backup 或已删除
5. 重启后再次验证（壳扩展、服务从新路径加载）
6. 备份目录完整：env_backup.json、services_backup.json、registry/、configs/、links_backup.json、migration_manifest.json、migration_summary.json、phase_progress.json
7. 异地备份完整：`$env:USERPROFILE\__migration_offsite__` 下有关键文件副本
8. 回滚日志完整：registry_rollback_log.json、config_change_log.json、service_dependencies.json
9. 迁移计划所有项均已执行，跳过的安装器软件已记录在报告
10. verification_report.{json,txt,html} 已生成
11. lock file 已释放（$backupRoot\migration.lock 不存在）

## Troubleshooting

| 症状 | 可能原因 | 排查方法 |
|------|----------|----------|
| 服务启动失败 "Error 1053" | binPath 引号嵌套错误 | `sc qc <ServiceName>` 检查 BINARY_PATH_NAME |
| 软件报 "找不到文件" | 配置文件中小写路径未替换 | `Select-String -Path <config> -Pattern "c:\\work" -CaseSensitive` |
| 环境变量改了不生效 | 未广播 WM_SETTINGCHANGE / 终端未重启 | 注销重登录或重启 Explorer |
| MySQL 启动失败 | my.ini 被加 BOM / secure-file-priv 目录不存在 | 查 .err 日志；检查 BOM |
| 右键菜单消失 | CLSID InProcServer32 未修复 / WOW6432Node 遗漏 | `reg query "HKCR\CLSID\{...}\InProcServer32" /ve` |
| Phase 3 文件 "source_locked" | 杀毒软件 / Windows Search 索引 | 确认 Phase 2 已停 WSearch；关 Defender 实时保护 |
| 回滚后配置仍异常 | .migration_conflict 文件存在 | 检查 `*.migration_conflict_*` 文件，手动合并 |
| lock 文件残留 | 断电 / 强制关闭终端 | 删 `$backupRoot\migration.lock`，按 phase_progress.json 判断断点 |
| nvm use 报错 | NVM_SYMLINK 变实体目录 | 删实体目录，重新 `nvm use <version>` |
| 计划任务执行失败 | WorkingDirectory 仍指向旧路径 | `Get-ScheduledTask <name> | Select -Expand Actions` |
| robocopy exit >= 8 | 权限/文件锁/磁盘满 | 查 robocopy 日志；确认 Phase 2 已停服务 |
| Phase 8 外部文件需回滚 | Level 1 不覆盖 Phase 8 文件 | 手动找 `.migration_bak` 恢复 |
| CLI 验证全部 FAIL | 当前会话 PATH 未刷新 | Phase 10.6 用全路径；如仍失败检查目标目录完整性 |
| GBK 配置文件乱码 | 编码检测误判 UTF-8 | 用 Detect-Encoding 验证；手动指定 codepage 936 |
