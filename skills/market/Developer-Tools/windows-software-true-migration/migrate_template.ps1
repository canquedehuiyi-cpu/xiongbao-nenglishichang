# ============================================================
# Windows Software True Migration Script v3.6.0
# Edit this file directly for logic changes.
# ============================================================

# ============================================================
# INITIALIZATION - 必须最先执行
# ============================================================

# --- 用户配置（唯一需要修改的地方）---
$src = "C:\workSpace"       # ← 源目录
$dst = "D:\workSpace"       # ← 目标目录
$backupRoot = "D:\__migration_backup__"

# --- 执行模式 ---
# 如果通过 Agent 自动化调用，设置 $NonInteractive = $true 跳过交互确认（高风险节点仍会停止）
$NonInteractive = $false

function Confirm-Action {
    param([string]$Prompt, [string]$Default = "N", [switch]$Critical)
    if ($NonInteractive -and -not $Critical) {
        Write-Log "Non-Interactive: Auto-confirming '$Prompt' (Default=$Default)" "WARN"
        return ($Default -eq 'Y')
    }
    if ($NonInteractive -and $Critical) {
        Write-Log "Non-Interactive: CRITICAL node requires manual intervention: $Prompt" "ERROR"
        Write-Log "Aborting. Re-run interactively or set explicit choice." "ERROR"
        exit 1
    }
    $answer = Read-Host "$Prompt (Y/N) [$Default]"
    if (-not $answer) { $answer = $Default }
    return ($answer -eq 'Y' -or $answer -eq 'y')
}

# --- 日志系统（StreamWriter 缓存句柄，避免频繁 open/close）---
$backupDir = "$backupRoot\$(Get-Date -Format 'yyyyMMdd_HHmmss')"
$logFile = "$backupDir\migration.log"
$script:logWriter = $null  # 延迟初始化（backupDir 创建后再打开）

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss.fff"
    $line = "[$ts] [$Level] $Message"
    Write-Host $line
    if ($script:logWriter) { $script:logWriter.WriteLine($line) }
}

function Close-Log {
    if ($script:logWriter) { $script:logWriter.Flush(); $script:logWriter.Close(); $script:logWriter = $null }
}

function Write-LogHeader {
    $header = @"
======================================================
  MIGRATION LOG
  Start Time : $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
  Source     : $src
  Destination: $dst
  Backup     : $backupDir
======================================================
"@
    Write-Host $header
    if ($script:logWriter) { $script:logWriter.WriteLine($header) }
}

# --- 通用路径替换函数（大小写不敏感 + 边界匹配防误伤）---
function Replace-PathVariants {
    param([string]$Content, [string]$Old, [string]$New)
    $opt = [System.Text.RegularExpressions.RegexOptions]::IgnoreCase
    # 边界匹配：旧路径后不紧跟字母/数字/下划线/反斜杠，防止 C:\work 误改 C:\work_backup
    # 替换字符串中只有 $ 是特殊字符（$1/$&），用 $$ 转义；反斜杠无需转义
    $safeNew = $New.Replace('$', '$$')
    $safeNewFwd = $New.Replace('\', '/').Replace('$', '$$')
    $safeNewDbl = $New.Replace('\', '\\').Replace('$', '$$')
    $pattern1 = [regex]::Escape($Old) + '(?![a-zA-Z0-9_\\])'
    $Content = [regex]::Replace($Content, $pattern1, $safeNew, $opt)
    $pattern2 = [regex]::Escape($Old.Replace('\','/')) + '(?![a-zA-Z0-9_/])'
    $Content = [regex]::Replace($Content, $pattern2, $safeNewFwd, $opt)
    $pattern3 = [regex]::Escape($Old.Replace('\','\\')) + '(?![a-zA-Z0-9_\\])'
    $Content = [regex]::Replace($Content, $pattern3, $safeNewDbl, $opt)
    return $Content
}

# --- 通用编码检测函数（含 GBK fallback）---
function Detect-Encoding {
    param([string]$FilePath)
    $bytes = [System.IO.File]::ReadAllBytes($FilePath)
    if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
        return New-Object System.Text.UTF8Encoding($true)   # UTF-8 with BOM
    }
    if ($bytes.Length -ge 2 -and $bytes[0] -eq 0xFF -and $bytes[1] -eq 0xFE) {
        return [System.Text.Encoding]::Unicode               # UTF-16 LE
    }
    if ($bytes.Length -ge 2 -and $bytes[0] -eq 0xFE -and $bytes[1] -eq 0xFF) {
        return [System.Text.Encoding]::BigEndianUnicode      # UTF-16 BE
    }
    # 尝试 UTF-8 严格解码，失败则 fallback 到 GBK (codepage 936)
    try {
        $strictUtf8 = New-Object System.Text.UTF8Encoding($false, $true)  # throwOnInvalidBytes=true
        $strictUtf8.GetString($bytes) | Out-Null
        return New-Object System.Text.UTF8Encoding($false)   # UTF-8 no BOM
    } catch {
        return [System.Text.Encoding]::GetEncoding(936)      # GBK/GB2312
    }
}

# --- 通用注册表扫描函数（使用正则匹配，避免通配符误匹配）---
function Scan-RegistryForPath {
    param([string]$SearchPath, [int]$Depth = 5)
    $results = @()
    $escapedPath = [regex]::Escape($SearchPath)
    $regRoots = @("HKLM:\SOFTWARE","HKLM:\SOFTWARE\WOW6432Node","HKCU:\SOFTWARE")
    foreach ($root in $regRoots) {
        Get-ChildItem $root -Recurse -Depth $Depth -ErrorAction SilentlyContinue | ForEach-Object {
            $key = $_
            foreach ($name in $key.GetValueNames()) {
                $kind = $key.GetValueKind($name)
                if ($kind -in @('String','ExpandString','MultiString')) {
                    $val = $key.GetValue($name)
                    $strVal = if ($kind -eq 'MultiString') { $val -join ';' } else { "$val" }
                    if ($strVal -match $escapedPath) {
                        $results += [PSCustomObject]@{ Key=$key.Name; ValueName=$name; Kind=$kind; Value=$strVal }
                    }
                }
            }
        }
    }
    return $results
}

# --- 通用环境变量扫描函数 ---
function Scan-EnvVarsForPath {
    param([string]$SearchPath)
    $results = @()
    foreach ($scope in @('Machine','User')) {
        [System.Environment]::GetEnvironmentVariables($scope).GetEnumerator() |
            Where-Object { $_.Value -match ([regex]::Escape($SearchPath)) } |
            ForEach-Object { $results += [PSCustomObject]@{ Scope=$scope; Key=$_.Key; Value=$_.Value } }
    }
    return $results
}

# --- 通用配置文件扫描函数 ---
function Scan-ConfigFilesForPath {
    param([string]$Directory, [string]$SearchPath)
    $textExts = @('.ini','.conf','.cfg','.xml','.json','.properties','.vmoptions',
                  '.yaml','.yml','.txt','.env','.toml','.config','.settings',
                  '.cnf','.opts','.rc','.profile')
    return Get-ChildItem $Directory -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object { $textExts -contains $_.Extension.ToLower() -and $_.Length -lt 10MB } |
        Where-Object { Select-String -Path $_.FullName -Pattern ([regex]::Escape($SearchPath)) -Quiet -ErrorAction SilentlyContinue }
}

# --- 并发保护（lock file）---
$lockFile = "$backupRoot\migration.lock"
if (Test-Path $lockFile) {
    $lockContent = Get-Content $lockFile -Raw
    Write-Host "ERROR: Another migration is in progress or was interrupted." -ForegroundColor Red
    Write-Host "Lock file: $lockFile" -ForegroundColor Red
    Write-Host "Content: $lockContent" -ForegroundColor Red
    Write-Host "If no migration is running, delete the lock file and retry." -ForegroundColor Yellow
    exit 1
}

# --- Phase 进度追踪 ---
$progressFile = "$backupDir\phase_progress.json"
function Update-PhaseProgress {
    param([string]$Phase, [string]$Status = "Complete")
    $progress = if (Test-Path $progressFile) { Get-Content $progressFile | ConvertFrom-Json } else { @{ Phases=@() } }
    $progress.Phases += @{ Phase=$Phase; Status=$Status; Timestamp=(Get-Date -Format "o") }
    # 原子写入：先写临时 再 Move，防止崩溃导致 JSON 截断
    $tmpProgress = "$progressFile.tmp"
    $progress | ConvertTo-Json -Depth 10 | Set-Content $tmpProgress -Encoding UTF8
    Move-Item $tmpProgress $progressFile -Force
    Write-Log "Phase $Phase: $Status" "PHASE"
}

# --- 创建备份目录并写入 lock ---
New-Item $backupDir -ItemType Directory -Force | Out-Null
$script:logWriter = New-Object System.IO.StreamWriter($logFile, $true, [System.Text.Encoding]::UTF8)
$script:logWriter.AutoFlush = $true

# 全局 trap：任何 exit/异常都确保日志刷盘 + 释放 lock + 恢复 WSearch
trap {
    Write-Log "FATAL: $_" "ERROR"
    if ($script:wsearchWasRunning) { Start-Service WSearch -ErrorAction SilentlyContinue }
    Close-Log
    Remove-Item $lockFile -Force -ErrorAction SilentlyContinue
    break
}
Set-Content $lockFile "PID=$PID Start=$(Get-Date -Format 'o') Backup=$backupDir Src=$src Dst=$dst" -Encoding UTF8

# --- 全局错误策略 ---
$ErrorActionPreference = 'Stop'

# --- 自身路径安全检测（防止 PowerShell 从 $src 下运行导致死锁）---
$psProcess = Get-Process -Id $PID -ErrorAction SilentlyContinue
if ($psProcess -and $psProcess.Path -like "$src*") {
    Write-Host "CRITICAL: PowerShell is running from the source directory being migrated!" -ForegroundColor Red
    Write-Host "Path: $($psProcess.Path)" -ForegroundColor Red
    Write-Host "This will cause a deadlock when Phase 2 tries to stop processes." -ForegroundColor Red
    Write-Host "Please copy this script to another location (e.g., $env:TEMP\migrate.ps1) and re-run." -ForegroundColor Yellow
    exit 1
}
# 检查脚本文件本身是否在 $src 下
if ($PSCommandPath -and $PSCommandPath -like "$src*") {
    Write-Host "CRITICAL: Script file is located in the source directory!" -ForegroundColor Red
    Write-Host "Move the script outside '$src' before running." -ForegroundColor Yellow
    exit 1
}

Write-LogHeader
Write-Log "Lock acquired. Backup dir: $backupDir"

Write-Log "=== Phase 0: Migration Strategy Decision ===" "PHASE"
Write-Log "--- 0.0 Applicability Classification ---"

# 注册表卸载项索引（用于判断子目录是否为安装器部署）
$uninstallRoots = @(
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
    "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
    "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
)
$regInstalled = @{}  # InstallLocation -> DisplayName
foreach ($root in $uninstallRoots) {
    Get-ChildItem $root -ErrorAction SilentlyContinue | ForEach-Object {
        $props = Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue
        if ($props.InstallLocation) { $regInstalled[$props.InstallLocation.TrimEnd('\')] = $props.DisplayName }
    }
}

# 逐子目录分类
$greenItems = @()      # 可迁移
$installerItems = @()  # 不可迁移（安装器部署）

$topItems = Get-ChildItem $src -Force
foreach ($item in $topItems) {
    $reason = @()

    if ($item.PSIsContainer) {
        # 检测 1：子目录内是否有卸载程序
        $hasUninstaller = Get-ChildItem $item.FullName -Recurse -Depth 2 -File -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -match '(?i)(unins|uninstall|uninst)\.(exe|dat)$' } |
            Select-Object -First 1
        if ($hasUninstaller) { $reason += "含卸载程序: $($hasUninstaller.Name)" }

        # 检测 2：注册表卸载项指向此目录
        $itemPath = $item.FullName.TrimEnd('\')
        if ($regInstalled.ContainsKey($itemPath)) { $reason += "注册表卸载项: $($regInstalled[$itemPath])" }

        # 检测 3：子目录内有 .msi 残留
        $hasMsi = Get-ChildItem $item.FullName -Depth 2 -Filter "*.msi" -File -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($hasMsi) { $reason += "MSI 残留: $($hasMsi.Name)" }
    }

    if ($reason.Count -gt 0) {
        $installerItems += [PSCustomObject]@{ Name=$item.Name; Reasons=($reason -join '; ') }
    } else {
        $greenItems += $item.Name
    }
}

# 输出分类报告
Write-Log ""
Write-Log "========== 迁移适用性分类报告 ==========" "PHASE"
Write-Log ""
Write-Log "[可迁移 - 绿色/解压版] ($($greenItems.Count) 项):" "OK"
$greenItems | ForEach-Object { Write-Log "  ✓ $_" "OK" }
Write-Log ""
Write-Log "[不可迁移 - 安装器部署] ($($installerItems.Count) 项):" "ERROR"
$installerItems | ForEach-Object { Write-Log "  ✗ $($_.Name) — $($_.Reasons)" "ERROR" }
Write-Log ""
Write-Log "不可迁移项的正确处理方式：控制面板卸载 → 重装到目标盘 → 恢复数据" "WARN"
Write-Log "=========================================" "PHASE"

# 用户决策（交互节点）
if ($installerItems.Count -eq 0) {
    Write-Log "All items are green/portable. Proceeding with full migration." "OK"
    $migrateItems = $greenItems
} elseif ($greenItems.Count -eq 0) {
    Write-Log "ABORT: All items are installer-based. Nothing to migrate with this skill." "ERROR"
    Close-Log; Remove-Item $lockFile -Force -ErrorAction SilentlyContinue; exit 1
} else {
    # 混合目录：让用户选择
    Write-Log ""
    Write-Log "目录中混合了绿色软件和安装器软件。请选择：" "WARN"
    Write-Log "  [1] 只迁移绿色软件（$($greenItems.Count) 项），跳过安装器软件（推荐）"
    Write-Log "  [2] 全部跳过，终止迁移"
    Write-Log ""
    # 使用 Confirm-Action 或 Read-Host
    if ($NonInteractive) {
        Write-Log "Non-Interactive: Auto-selecting option 1 (migrate green only)" "WARN"
        $migrateItems = $greenItems
    } else {
        $choice = Read-Host "请选择 [1/2] (默认 1)"
        if (-not $choice) { $choice = "1" }
        if ($choice -eq "2") {
            Write-Log "User chose to abort." "WARN"
            Close-Log; Remove-Item $lockFile -Force -ErrorAction SilentlyContinue; exit 0
        }
        $migrateItems = $greenItems
    }
}

# 后续 Phase 使用 $migrateItems 而非整个 $src
# Phase 3 文件移动时只处理 $migrateItems 中列出的子目录
Write-Log "Migration scope: $($migrateItems.Count) items selected." "OK"

# 构建精确替换对（只替换已迁移子目录的路径，不影响被跳过的安装器软件）
$migrationPairs = $migrateItems | ForEach-Object {
    [PSCustomObject]@{ Old = "$src\$_"; New = "$dst\$_" }
}
# 记录跳过的安装器软件（Phase 10 报告中提醒用户）
$skippedItems = @($installerItems | ForEach-Object { $_.Name })
# 注：$migrationSummary 在 Phase 1.6 初始化后再写入 skippedInstallerItems

Get-ChildItem $src -Force | Select-Object Name, PSIsContainer,
    @{N='LinkType';E={$_.LinkType}},
    @{N='SizeMB';E={if($_.PSIsContainer){[math]::Round((Get-ChildItem $_.FullName -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum/1MB,1)}else{[math]::Round($_.Length/1MB,1)}}} |
    Format-Table -AutoSize

# 自动发现：服务
$services = Get-WmiObject Win32_Service | Where-Object { $_.PathName -like "*$src*" }
Write-Log "Services tied to source: $($services.Count)"
$services | Select-Object Name, State, PathName | Format-Table -AutoSize

# 自动发现：注册表引用（复用通用函数）
$regHits = Scan-RegistryForPath -SearchPath $src -Depth 5
Write-Log "Registry references found: $($regHits.Count)"
$regHits | ForEach-Object { Write-Log "  $($_.Key)\$($_.ValueName) = $($_.Value)" "DETAIL" }

# --- Phase 0.4: Migration Plan Confirmation (interaction node) ---
# 提前计算源目录大小（Phase 1.1 会复用）
$srcSize = (Get-ChildItem $src -Recurse -File -Force -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
$srcSizeGB = [math]::Round($srcSize / 1GB, 2)

Write-Log ""
Write-Log "========== MIGRATION PLAN ==========" "PHASE"
Write-Log "Source:          $src"
Write-Log "Destination:     $dst"
Write-Log "Source Size:     ${srcSizeGB} GB"
Write-Log "Items to Migrate: $($migrateItems.Count)"
$migrateItems | ForEach-Object { Write-Log "  - $_" }
Write-Log "Services Found:  $($services.Count)"
Write-Log "Links Found:     $(($linkInfo | Measure-Object).Count)"
Write-Log "Registry Hits:   $($regHits.Count)"
if ($skippedItems.Count -gt 0) {
    Write-Log "Skipped (installer): $($skippedItems.Count)" "WARN"
    $skippedItems | ForEach-Object { Write-Log "  - $_" "WARN" }
}
Write-Log "Backup Dir:      $backupDir"
Write-Log "====================================" "PHASE"
Write-Log ""
if (-not (Confirm-Action "Confirm migration plan above. Proceed?" -Default "N" -Critical)) {
    Write-Log "User chose to abort migration." "WARN"
    Close-Log; Remove-Item $lockFile -Force -ErrorAction SilentlyContinue; exit 0
}
Write-Log "Migration plan confirmed by user." "OK"

Update-PhaseProgress -Phase "0"

Write-Log "=== Phase 1: Pre-flight Checks ===" "PHASE"

$srcSize = (Get-ChildItem $src -Recurse -File -Force -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
$srcSizeGB = [math]::Round($srcSize / 1GB, 2)

$dstDriveLetter = ($dst -split ':')[0]
$drive = Get-PSDrive $dstDriveLetter
$freeGB = [math]::Round($drive.Free / 1GB, 2)
$requiredGB = [math]::Round($srcSizeGB * 1.2, 2)

Write-Log "Space: Source=${srcSizeGB}GB, Free=${freeGB}GB, Required=${requiredGB}GB"
if ($freeGB -lt $requiredGB) { Write-Log "ABORT: Insufficient space!" "ERROR"; exit 1 }

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) { Write-Log "ABORT: Must run as Administrator!" "ERROR"; exit 1 }

$testDir = "$dst\__migration_test__"
try {
    New-Item $testDir -ItemType Directory -Force | Out-Null
    [System.IO.File]::WriteAllText("$testDir\test.txt", "test")
    Remove-Item $testDir -Recurse -Force
    Write-Log "Permission check: OK"
} catch {
    Write-Log "ABORT: Cannot write to target! $_" "ERROR"; exit 1
}

Write-Log "NOTE: If Windows Defender or third-party AV is active, real-time scanning may lock files during move." "WARN"
Write-Log "Recommend: Temporarily add exclusions for '$src' and '$dst' before proceeding." "WARN"
# 尝试自动添加 Windows Defender 排除（可能因策略被拒绝）
try {
    Add-MpPreference -ExclusionPath $src -ErrorAction Stop
    Add-MpPreference -ExclusionPath $dst -ErrorAction Stop
    Write-Log "Windows Defender exclusions added." "OK"
} catch {
    Write-Log "Cannot add Defender exclusion (policy restricted?). Manual exclusion strongly recommended." "WARN"
    # 大目录迁移时 Defender 实时扫描会导致文件锁定和极慢的 I/O
    if (-not $NonInteractive) {
        Write-Log "Press Enter to continue after adding exclusions manually (or just Enter to skip)..." "WARN"
        Read-Host
    }
}

$srcItems = Get-ChildItem $src -Force
$srcItems | Select-Object Name, PSIsContainer, @{N='LinkType';E={$_.LinkType}}, @{N='Target';E={$_.Target}} | Format-Table -AutoSize

$linkInfo = $srcItems | Where-Object { $_.LinkType } | ForEach-Object {
    $target = $_.Target
    $isAbsolute = [System.IO.Path]::IsPathRooted($target)
    # 相对路径解析：基于链接所在目录（而非多拼一层链接名）
    $parentDir = Split-Path $_.FullName -Parent
    [PSCustomObject]@{
        Name = $_.Name; LinkType = $_.LinkType; Target = $target
        IsAbsolute = $isAbsolute
        ResolvedTarget = if ($isAbsolute) { $target } else { (Resolve-Path "$parentDir\$target" -ErrorAction SilentlyContinue).Path }
    }
}

# 服务
Write-Log "=== Services referencing source ===" "PHASE"
$services | Select-Object Name, State, StartMode, PathName | Format-Table -AutoSize

# 进程
Write-Log "=== Processes referencing source ===" "PHASE"
$lockedProcesses = Get-Process | Where-Object { try { $_.Path -like "*$src*" } catch { $false } }
$lockedProcesses | Select-Object Name, Id, Path | Format-Table -AutoSize

# 环境变量（复用通用函数）
$envHits = Scan-EnvVarsForPath -SearchPath $src
$envHits | ForEach-Object { Write-Log "  ENV [$($_.Scope)] $($_.Key) = $($_.Value)" }

# 注册表（已在 0.2 扫描，复用 $regHits）
Write-Log "Registry hits: $($regHits.Count) (from Phase 0.2)"

$migrationSummary = @{
    source = $src
    destination = $dst
    startTime = (Get-Date -Format "o")
    sourceSizeGB = $srcSizeGB
    detectedServices = @($services | ForEach-Object { @{ Name=$_.Name; State=$_.State; PathName=$_.PathName } })
    detectedLinks = @($linkInfo | ForEach-Object { @{ Name=$_.Name; Type=$_.LinkType; Target=$_.Target } })
    migrationStrategy = "full"
    backupDir = $backupDir
    migrateItems = $migrateItems
    skippedInstallerItems = $skippedItems
}
$migrationSummary | ConvertTo-Json -Depth 10 | Set-Content "$backupDir\migration_summary.json" -Encoding UTF8
Write-Log "Migration summary: $backupDir\migration_summary.json"

# 1. 环境变量备份
$envBackup = @{}
foreach ($scope in @('Machine','User')) {
    $vars = @{}
    [System.Environment]::GetEnvironmentVariables($scope).GetEnumerator() | ForEach-Object { $vars[$_.Key] = $_.Value }
    $envBackup[$scope] = $vars
}
$envBackup | ConvertTo-Json -Depth 10 | Set-Content "$backupDir\env_backup.json" -Encoding UTF8
Write-Log "Backup: env_backup.json"

# 2. 服务配置备份
$svcBackup = $services | Select-Object Name, PathName, StartMode, State
$svcBackup | ConvertTo-Json -Depth 10 | Set-Content "$backupDir\services_backup.json" -Encoding UTF8
Write-Log "Backup: services_backup.json"

# 3. 注册表备份
$regBackupDir = "$backupDir\registry"
New-Item $regBackupDir -ItemType Directory -Force | Out-Null
$regHits | ForEach-Object {
    $keyPath = $_.Key -replace 'HKEY_LOCAL_MACHINE\\', 'HKLM\' -replace 'HKEY_CURRENT_USER\\', 'HKCU\'
    $safeName = ($_.Key -replace '[\\:]','_') + ".reg"
    $exportErr = & { reg export "$keyPath" "$regBackupDir\$safeName" /y 2>&1 }
    if ($LASTEXITCODE -ne 0) {
        Write-Log "  REG EXPORT FAILED: $keyPath — $exportErr" "ERROR"
    }
}
$regExportCount = (Get-ChildItem $regBackupDir -Filter '*.reg' -ErrorAction SilentlyContinue).Count
Write-Log "Backup: registry/ ($regExportCount files, $($regHits.Count) expected)"
if ($regExportCount -lt $regHits.Count) {
    Write-Log "WARNING: $($regHits.Count - $regExportCount) registry keys failed to export!" "ERROR"
}

# 4. 配置文件备份
$configHits = Scan-ConfigFilesForPath -Directory $src -SearchPath $src
$configBackupDir = "$backupDir\configs"
New-Item $configBackupDir -ItemType Directory -Force | Out-Null
foreach ($f in $configHits) {
    $relPath = $f.FullName.Substring($src.Length)
    $destPath = "$configBackupDir$relPath"
    New-Item (Split-Path $destPath) -ItemType Directory -Force -ErrorAction SilentlyContinue | Out-Null
    Copy-Item $f.FullName $destPath -Force
}
Write-Log "Backup: configs/ ($($configHits.Count) files)"

# 5. 链接信息备份
$linkInfo | Select-Object Name, LinkType, Target | ConvertTo-Json | Set-Content "$backupDir\links_backup.json" -Encoding UTF8
Write-Log "Backup: links_backup.json"

# 6. 关键备份异地副本（防止目标盘单点故障）
$offsiteBackupDir = "$env:USERPROFILE\__migration_offsite__"
New-Item $offsiteBackupDir -ItemType Directory -Force | Out-Null
$criticalFiles = @('env_backup.json','services_backup.json','links_backup.json','migration_summary.json')
foreach ($f in $criticalFiles) {
    if (Test-Path "$backupDir\$f") { Copy-Item "$backupDir\$f" "$offsiteBackupDir\$f" -Force }
}
if (Test-Path $regBackupDir) { Copy-Item $regBackupDir "$offsiteBackupDir\registry" -Recurse -Force }
Write-Log "Offsite backup: $offsiteBackupDir (critical files only)"

# --- Phase 1.8: Backup Completion Confirmation (interaction node) ---
Write-Log ""
Write-Log "========== BACKUP COMPLETE ==========" "PHASE"
Write-Log "Backup Dir:   $backupDir"
Write-Log "Offsite Copy: $offsiteBackupDir"
Write-Log "  [OK] env_backup.json"
Write-Log "  [OK] services_backup.json"
Write-Log "  [OK] registry/ ($regExportCount files)"
Write-Log "  [OK] configs/ ($($configHits.Count) files)"
Write-Log "  [OK] links_backup.json"
Write-Log "  [OK] migration_summary.json"
Write-Log "  [OK] offsite backup (critical files)"
Write-Log "======================================" "PHASE"
Write-Log ""
if (-not (Confirm-Action "Backup complete. Proceed with migration?" -Default "N" -Critical)) {
    Write-Log "User chose to abort after backup." "WARN"
    Close-Log; Remove-Item $lockFile -Force -ErrorAction SilentlyContinue; exit 0
}
Write-Log "Backup confirmed by user. Starting migration." "OK"

Update-PhaseProgress -Phase "1"

Write-Log "=== Phase 2: Stop Services & Processes ===" "PHASE"

# 暂停 Windows Search 索引（避免迁移时触发大量索引重建 I/O，Phase 10 恢复）
$wsearchSvc = Get-Service WSearch -ErrorAction SilentlyContinue
if ($wsearchSvc -and $wsearchSvc.Status -eq 'Running') {
    Stop-Service WSearch -Force -ErrorAction SilentlyContinue
    Write-Log "Windows Search (WSearch) paused for migration performance" "OK"
    $script:wsearchWasRunning = $true
} else { $script:wsearchWasRunning = $false }

$lockedProcesses = Get-Process | Where-Object { try { $_.Path -like "*$src*" } catch { $false } }
$lockedServices = Get-WmiObject Win32_Service | Where-Object { $_.PathName -like "*$src*" -and $_.State -eq 'Running' }

Write-Log "Locked Process List:"
$lockedProcesses | ForEach-Object { Write-Log "  PID=$($_.Id) Name=$($_.Name) Path=$($_.Path)" }
Write-Log "Running Services:"
$lockedServices | ForEach-Object { Write-Log "  $($_.Name) [$($_.State)]" }

$timeout = 30

foreach ($svc in $lockedServices) {
    Write-Log "Stopping service: $($svc.Name) ..."
    $service = Get-Service $svc.Name

    # Step 1: 正常停止请求
    $service.Stop()

    # Step 2: 等待退出
    $elapsed = 0
    while ($service.Status -ne 'Stopped' -and $elapsed -lt $timeout) {
        Start-Sleep -Seconds 2
        $elapsed += 2
        $service.Refresh()
    }

    # Step 3: 检查
    if ($service.Status -eq 'Stopped') {
        Write-Log "  $($svc.Name): Stopped gracefully (${elapsed}s)" "OK"
    } else {
        # Step 4: 强制
        Write-Log "  $($svc.Name): TIMEOUT, forcing..." "WARN"
        Stop-Service $svc.Name -Force -ErrorAction SilentlyContinue
        Start-Sleep 3
        $service.Refresh()
        if ($service.Status -eq 'Stopped') { Write-Log "  $($svc.Name): Force stopped" "WARN" }
        else { Write-Log "  $($svc.Name): CANNOT STOP!" "ERROR" }
    }
}

$critical = @('explorer','svchost','csrss','wininit','services','lsass','dwm')

$procs = $lockedProcesses | Where-Object { $_.Name -notin $critical }
foreach ($p in $procs) {
    if ($p.CloseMainWindow()) {
        $waited = $p.WaitForExit(10000)
        if ($waited) { Write-Log "  $($p.Name): Closed gracefully" "OK"; continue }
    }
    Write-Log "  $($p.Name) (PID $($p.Id)): Force killing" "WARN"
    Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
    Start-Sleep 2
}

# 残留检查
$remaining = Get-Process | Where-Object { try { $_.Path -like "*$src*" } catch { $false } }
if ($remaining) {
    Write-Log "WARNING: Processes still locking source:" "ERROR"
    $remaining | ForEach-Object { Write-Log "  $($_.Name) PID=$($_.Id)" "ERROR" }
    # ⚠️ 交互确认：询问用户是否继续
    if (-not (Confirm-Action "Processes still locking source. Continue anyway?" -Default "N" -Critical)) {
        Write-Log "User chose to abort due to locked processes." "WARN"
        Close-Log
        Remove-Item $lockFile -Force -ErrorAction SilentlyContinue
        exit 1
    }
    Write-Log "User chose to continue despite locked processes." "WARN"
}

Update-PhaseProgress -Phase "2"

Write-Log "=== Phase 3: File Migration ===" "PHASE"

if (-not (Test-Path $dst)) { New-Item -ItemType Directory -Path $dst -Force }

# 只迁移 $migrateItems 中的子目录（Phase 0.0 用户确认的范围）
if (-not $migrateItems -or $migrateItems.Count -eq 0) {
    Write-Log "ABORT: No items selected for migration." "ERROR"
    Close-Log; Remove-Item $lockFile -Force -ErrorAction SilentlyContinue; exit 1
}
$items = $migrateItems | ForEach-Object { Get-Item "$src\$_" -Force -ErrorAction SilentlyContinue } |
    Where-Object { $_ -and -not $_.LinkType }
$total = $items.Count; $i = 0; $failed = @()
$manifest = @()

# 断点续传：如果上次中断，读取已有 manifest 跳过已成功项
$existingManifest = @()
if (Test-Path "$backupDir\migration_manifest.json") {
    $existingManifest = @(Get-Content "$backupDir\migration_manifest.json" | ConvertFrom-Json)
    $successNames = @($existingManifest | Where-Object { $_.status -eq 'success' } | ForEach-Object { Split-Path $_.originalPath -Leaf })
    if ($successNames.Count -gt 0) {
        Write-Log "Resuming: $($successNames.Count) items already migrated, skipping." "OK"
        $items = $items | Where-Object { $_.Name -notin $successNames }
        $manifest = @($existingManifest | ForEach-Object { @{ originalPath=$_.originalPath; newPath=$_.newPath; sizeBytes=$_.sizeBytes; timestamp=$_.timestamp; status=$_.status; isContainer=$_.isContainer } })
    }
}

foreach ($item in $items) {
    $i++
    $itemSize = if ($item.PSIsContainer) {
        (Get-ChildItem $item.FullName -Recurse -File -Force -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
    } else { $item.Length }

    Write-Log "[$i/$total] Moving $($item.Name) ($([math]::Round($itemSize/1MB,1)) MB)..."

    $status = "success"
    $targetPath = "$dst\$($item.Name)"
    try {
        # 跨盘移动 = Copy → Verify → Remove（Move-Item 跨盘非原子，中断会丢数据）
        if ($item.PSIsContainer) {
            if ($itemSize -gt 1GB) {
                # 大目录用 robocopy（自带重试、进度、权限保持）
                Write-Log "  Large directory, using robocopy..." "WARN"
                robocopy $item.FullName $targetPath /E /COPYALL /R:3 /W:5 /NFL /NDL /NJH /NJS 2>&1 | Out-Null
                if ($LASTEXITCODE -ge 8) { $status = "robocopy_error: exit=$LASTEXITCODE"; throw "robocopy failed with exit code $LASTEXITCODE" }
            } else {
                Copy-Item $item.FullName $targetPath -Recurse -Force -ErrorAction Stop
            }
        } else {
            Copy-Item $item.FullName $targetPath -Force -ErrorAction Stop
        }

        # 完整性校验：大小必须一致
        $copiedSize = if (Test-Path $targetPath -PathType Container) {
            (Get-ChildItem $targetPath -Recurse -File -Force -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
        } else { (Get-Item $targetPath).Length }

        if ($copiedSize -ne $itemSize) {
            $status = "size_mismatch (src=$itemSize dst=$copiedSize)"
            Write-Log "  SIZE MISMATCH: $($item.Name) src=$itemSize dst=$copiedSize" "ERROR"
            $failed += $item.Name
        } elseif ($item.PSIsContainer) {
            # 容器目录额外校验文件/子目录数量（防止部分子目录因权限被跳过但总大小恰好为0的情况）
            $srcCount = (Get-ChildItem $item.FullName -Recurse -Force -ErrorAction SilentlyContinue).Count
            $dstCount = (Get-ChildItem $targetPath -Recurse -Force -ErrorAction SilentlyContinue).Count
            if ($srcCount -ne $dstCount) {
                $status = "count_mismatch (src=$srcCount dst=$dstCount)"
                Write-Log "  COUNT MISMATCH: $($item.Name) src=$srcCount dst=$dstCount" "ERROR"
                $failed += $item.Name
            } else {
                # 容器目录校验通过，删除源
                Remove-Item $item.FullName -Recurse -Force -ErrorAction SilentlyContinue
                if (Test-Path $item.FullName) { $status = "copied_but_source_locked" }
            }
        } else {
            # 关键文件（数据库、jar）额外 MD5 校验
            if ($item.Extension -and $item.Extension -in @('.jar','.ibd','.ibdata1','.frm','.myd','.myi','.dat','.db','.sqlite') -and $item.Length -lt 100MB) {
                $srcHash = (Get-FileHash $item.FullName -Algorithm MD5).Hash
                $dstHash = (Get-FileHash $targetPath -Algorithm MD5).Hash
                if ($srcHash -ne $dstHash) {
                    $status = "hash_mismatch"
                    Write-Log "  HASH MISMATCH: $($item.Name)" "ERROR"
                    $failed += $item.Name
                }
            }
            # 校验通过，删除源
            if ($status -eq "success") {
                Remove-Item $item.FullName -Recurse -Force -ErrorAction SilentlyContinue
                if (Test-Path $item.FullName) { $status = "copied_but_source_locked" }
            }
        }
    } catch {
        $status = "error: $_"
        $failed += $item.Name
        Write-Log "  FAILED: $($item.Name) - $_" "ERROR"
    }

    $manifest += @{
        originalPath = $item.FullName; newPath = "$dst\$($item.Name)"
        sizeBytes = $itemSize; timestamp = (Get-Date -Format "o")
        status = $status; isContainer = $item.PSIsContainer
    }
}

$manifest | ConvertTo-Json -Depth 10 | Set-Content "$backupDir\migration_manifest.json" -Encoding UTF8
Write-Log "Manifest saved: $($manifest.Count) items, $($failed.Count) failed"
if ($failed.Count -gt 0) { Write-Log "FAILED: $($failed -join ', ')" "ERROR" }

foreach ($link in $linkInfo) {
    $linkPath = "$src\$($link.Name)"

    if ($link.LinkType -eq 'Junction') { cmd /c "rmdir `"$linkPath`"" }
    else { (Get-Item $linkPath -Force).Delete() }

    $newLink = "$dst\$($link.Name)"
    $newTarget = if ($link.IsAbsolute) { $link.Target.Replace($src, $dst) } else { $link.Target }

    if ($link.LinkType -eq 'Junction') { cmd /c "mklink /J `"$newLink`" `"$newTarget`"" }
    else { New-Item -ItemType SymbolicLink -Path $newLink -Target $newTarget -Force }
    Write-Log "  Link rebuilt: $($link.Name) -> $newTarget ($($link.LinkType))"
}

$srcRemaining = Get-ChildItem $src -Force -Recurse -ErrorAction SilentlyContinue
Write-Log "Source remaining: $($srcRemaining.Count), Destination: $((Get-ChildItem $dst -Force).Count)"

if ($srcRemaining) {
    $lockedFiles = $srcRemaining | ForEach-Object {
        @{ Path=$_.FullName; LastWriteTime=$_.LastWriteTime.ToString("o"); IsContainer=$_.PSIsContainer; SizeBytes=$(if($_.PSIsContainer){0}else{$_.Length}) }
    }
    $lockedFiles | ConvertTo-Json | Set-Content "$backupDir\locked_files.json" -Encoding UTF8
    $csv = "Path,LastWriteTime,IsContainer,SizeBytes`n" + (($lockedFiles | ForEach-Object { "$($_.Path),$($_.LastWriteTime),$($_.IsContainer),$($_.SizeBytes)" }) -join "`n")
    [System.IO.File]::WriteAllText("$backupDir\locked_files.csv", $csv)
    Write-Log "WARNING: $($srcRemaining.Count) items still locked (see locked_files.csv)" "WARN"
    Write-Log "Recommend: reboot then re-run Phase 3 for remaining items only." "WARN"
}

$dstSize = (Get-ChildItem $dst -Recurse -File -Force -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
Write-Log "Destination size: $([math]::Round($dstSize/1GB, 2)) GB (expected ~${srcSizeGB} GB)"

Update-PhaseProgress -Phase "3"

Write-Log "=== Phase 4: Environment Variables ===" "PHASE"

# 只替换已迁移子目录的路径（$migrationPairs），不影响被跳过的安装器软件
if (-not $migrationPairs -or $migrationPairs.Count -eq 0) {
    Write-Log "No migration pairs defined, skipping env var replacement." "WARN"
} else {
foreach ($scope in @('Machine','User')) {
    $allVars = [System.Environment]::GetEnvironmentVariables($scope)
    foreach ($key in @($allVars.Keys)) {
        $val = $allVars[$key]
        $changed = $false
        foreach ($mp in $migrationPairs) {
            if ($val -match ([regex]::Escape($mp.Old) + '(?![a-zA-Z0-9_\\])')) {
                $val = Replace-PathVariants -Content $val -Old $mp.Old -New $mp.New
                $changed = $true
            }
        }
        if ($changed) {
            [System.Environment]::SetEnvironmentVariable($key, $val, $scope)
            Write-Log "  [$scope] $key -> $val"
        }
    }
}

# PATH 展开验证（只检查已迁移路径）
foreach ($scope in @('Machine','User')) {
    $pathVal = [System.Environment]::GetEnvironmentVariable('Path', $scope)
    ($pathVal -split ';' | Where-Object { $_ }) | ForEach-Object {
        $expanded = [System.Environment]::ExpandEnvironmentVariables($_)
        foreach ($mp in $migrationPairs) {
            if ($expanded -like "*$($mp.Old)*") { Write-Log "PATH STILL OLD [$scope]: $_ -> $expanded" "ERROR" }
        }
        if ($expanded -like "*$dst*" -and -not (Test-Path $expanded)) { Write-Log "PATH MISSING [$scope]: $expanded" "WARN" }
    }
}

# 多级变量引用检查（只关注已迁移路径）
$merged = @{}
[System.Environment]::GetEnvironmentVariables('Machine').GetEnumerator() | ForEach-Object { $merged[$_.Key] = $_.Value }
[System.Environment]::GetEnvironmentVariables('User').GetEnumerator() | ForEach-Object { $merged[$_.Key] = $_.Value }
foreach ($kv in $merged.GetEnumerator()) {
    if ($kv.Value -match '%([^%]+)%') {
        [regex]::Matches($kv.Value, '%([^%]+)%') | ForEach-Object {
            $ref = $_.Groups[1].Value
            if ($merged.ContainsKey($ref)) {
                foreach ($mp in $migrationPairs) {
                    if ($merged[$ref] -like "*$($mp.Old)*") {
                        Write-Log "INDIRECT REF: $($kv.Key) -> %$ref% -> $($merged[$ref])" "WARN"
                    }
                }
            }
        }
    }
}
} # end else ($migrationPairs non-empty)

Update-PhaseProgress -Phase "4"

# 广播环境变量变更（让 Explorer 和其他进程立即感知，无需注销）
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public class WinAPI {
    [DllImport("user32.dll", SetLastError = true, CharSet = CharSet.Auto)]
    public static extern IntPtr SendMessageTimeout(IntPtr hWnd, uint Msg, UIntPtr wParam, string lParam, uint fuFlags, uint uTimeout, out UIntPtr lpdwResult);
    public static readonly IntPtr HWND_BROADCAST = new IntPtr(0xffff);
    public const uint WM_SETTINGCHANGE = 0x001A;
    public const uint SMTO_ABORTIFHUNG = 0x0002;
}
"@
$dummy = [UIntPtr]::Zero
[WinAPI]::SendMessageTimeout([WinAPI]::HWND_BROADCAST, [WinAPI]::WM_SETTINGCHANGE, [UIntPtr]::Zero, "Environment", [WinAPI]::SMTO_ABORTIFHUNG, 5000, [ref]$dummy) | Out-Null
Write-Log "WM_SETTINGCHANGE broadcast sent (Environment)"

Write-Log "=== Phase 5: Service Path Fix ===" "PHASE"

# 只匹配引用了已迁移子目录的服务（不影响被跳过的安装器软件的服务）
$affectedServices = Get-WmiObject Win32_Service | Where-Object {
    $pn = $_.PathName
    ($migrationPairs | Where-Object { $pn -like "*$($_.Old)*" }).Count -gt 0
}

foreach ($svc in $affectedServices) {
    $rawPath = $svc.PathName
    Write-Log "Service: $($svc.Name) | RAW: $rawPath"

    # 展开环境变量（处理 %SystemRoot% 等形式）
    $expandedPath = [System.Environment]::ExpandEnvironmentVariables($rawPath)

    # 智能解析：区分"纯 exe 路径"和"复杂启动命令"
    $exePath = ""; $svcArgs = ""; $isSimpleExe = $false

    if ($expandedPath -match '^\s*"([^"]+\.exe)"\s+(.*)$') {
        # 格式: "path.exe" args
        $exePath = $matches[1]; $svcArgs = $matches[2]; $isSimpleExe = $true
    } elseif ($expandedPath -match '^\s*"([^"]+\.exe)"\s*$') {
        # 格式: "path.exe" (无参数)
        $exePath = $matches[1]; $svcArgs = ""; $isSimpleExe = $true
    } elseif ($expandedPath -match '^\s*([^\s"]+\.exe)\s+(.*)$') {
        # 格式: path.exe args (无引号)
        $exePath = $matches[1]; $svcArgs = $matches[2]; $isSimpleExe = $true
    } elseif ($expandedPath -match '^\s*([^\s"]+\.exe)\s*$') {
        # 格式: path.exe (无引号无参数)
        $exePath = $matches[1]; $svcArgs = ""; $isSimpleExe = $true
    }

    if ($isSimpleExe) {
        # 精细处理：分别替换 exe 路径和参数（遍历 migrationPairs 防止误改未迁移子目录路径）
        $newExePath = $exePath
        $newArgs = $svcArgs
        foreach ($mp in $migrationPairs) {
            $newExePath = Replace-PathVariants -Content $newExePath -Old $mp.Old -New $mp.New
            $newArgs = Replace-PathVariants -Content $newArgs -Old $mp.Old -New $mp.New
        }
        $newBinPath = if ($newArgs) { "`"$newExePath`" $newArgs" } else { "`"$newExePath`"" }
    } else {
        # 复杂启动命令（cmd /c xxx.bat、java -jar、脚本启动器等）
        # 不强行拆分，直接对整串做路径替换，保持原格式
        Write-Log "  Complex PathName (not simple exe), doing whole-string replace" "WARN"
        $newBinPath = $rawPath
        foreach ($mp in $migrationPairs) {
            $newBinPath = Replace-PathVariants -Content $newBinPath -Old $mp.Old -New $mp.New
        }
    }

    Write-Log "  NEW: $newBinPath" "OK"
    sc.exe config $svc.Name binPath= "$newBinPath"
    $verify = sc.exe qc $svc.Name | Select-String "BINARY_PATH_NAME|二进制路径名称"
    Write-Log "  VERIFY: $($verify.Line)"
}

$allAffected = Get-WmiObject Win32_Service | Where-Object { $_.PathName -like "*$src*" -or $_.PathName -like "*$dst*" }
$serviceDeps = @()

foreach ($svc in $allAffected) {
    $wmiSvc = Get-WmiObject Win32_Service -Filter "Name='$($svc.Name)'"
    $deps = $wmiSvc.GetRelated('Win32_Service', 'Win32_DependentService', $null, $null, 'PartComponent', 'Antecedent', $false, $null)
    $serviceDeps += @{
        Name = $svc.Name; StartType = $svc.StartMode; ServiceAccount = $svc.StartName
        DependsOn = @($deps | ForEach-Object { $_.Name }); State = $svc.State
    }
    Write-Log "  $($svc.Name): DependsOn=[$(@($deps | ForEach-Object { $_.Name }) -join ', ')]"
}

$serviceDeps | ConvertTo-Json -Depth 10 | Set-Content "$backupDir\service_dependencies.json" -Encoding UTF8
Update-PhaseProgress -Phase "5"

Write-Log "=== Phase 6: Config File Fix ===" "PHASE"

# 扫描目标目录中的配置文件（复用通用函数）
$hits = Scan-ConfigFilesForPath -Directory $dst -SearchPath $src
$hits | ForEach-Object { Write-Log "CONFIG HIT: $($_.FullName)" }

$configChangeLog = @()

foreach ($file in $hits) {
    # 空文件特判：无内容可替换，跳过（避免 origSize=0 导致校验逻辑异常）
    if ($file.Length -eq 0) { Write-Log "  SKIP (empty): $($file.FullName)"; continue }

    Write-Log "Processing: $($file.FullName)"

    # 备份
    $bakPath = "$($file.FullName).migration_bak"
    Copy-Item $file.FullName $bakPath -Force

    # 检测编码（含 GBK fallback）
    $encoding = Detect-Encoding -FilePath $file.FullName

    # 读取并替换（只替换已迁移子目录的路径对）
    $contentBefore = [System.IO.File]::ReadAllText($file.FullName, $encoding)
    $contentAfter = $contentBefore
    foreach ($mp in $migrationPairs) {
        $contentAfter = Replace-PathVariants -Content $contentAfter -Old $mp.Old -New $mp.New
    }

    # 写临时文件
    $tmpPath = "$($file.FullName).migration_tmp"
    [System.IO.File]::WriteAllText($tmpPath, $contentAfter, $encoding)

    # 验证临时文件（先检查存在性，防止写操作因磁盘满/权限失败）
    if (-not (Test-Path $tmpPath)) {
        Write-Log "  FAILED (tmp file not created, disk full or permission?)" "ERROR"
        continue
    }
    $tmpContent = [System.IO.File]::ReadAllText($tmpPath, $encoding)
    $tmpSize = (Get-Item $tmpPath).Length
    $origSize = $file.Length

    # 只检查已迁移子目录的路径是否残留（不影响未迁移的安装器软件引用）
    $hasOldPath = $false
    foreach ($mp in $migrationPairs) {
        if ($tmpContent -match ([regex]::Escape($mp.Old) + '(?![a-zA-Z0-9_\\])')) { $hasOldPath = $true; break }
    }
    if ($hasOldPath) {
        Write-Log "  FAILED (old path remains)" "ERROR"; Remove-Item $tmpPath -Force; continue
    }
    if ($tmpSize -lt ($origSize * 0.5) -or $tmpSize -gt ($origSize * 2)) {
        Write-Log "  FAILED (size anomaly: $origSize -> $tmpSize)" "ERROR"; Remove-Item $tmpPath -Force; continue
    }

    # 原子替换
    Move-Item $tmpPath $file.FullName -Force
    Write-Log "  OK (encoding: $($encoding.EncodingName))" "OK"

    $configChangeLog += @{
        file=$file.FullName; encoding=$encoding.EncodingName; timestamp=(Get-Date -Format "o")
        changesCount=(($migrationPairs | ForEach-Object { ([regex]::Matches($contentBefore, [regex]::Escape($_.Old))).Count } | Measure-Object -Sum).Sum); backupFile=$bakPath
    }
}

$configChangeLog | ConvertTo-Json -Depth 10 | Set-Content "$backupDir\config_change_log.json" -Encoding UTF8
Write-Log "Config changes: $($configChangeLog.Count) files"

# 环境变量引用形式检查
$hits | ForEach-Object {
    $content = Get-Content $_.FullName -Raw
    $m = [regex]::Matches($content, '%[A-Za-z_]+%')
    if ($m.Count -gt 0) { Write-Log "  NOTE: $($_.Name) uses env vars: $($m.Value -join ', ') - auto-resolves via Phase 4" }
}

Update-PhaseProgress -Phase "6"

Write-Log "=== Phase 7: Registry Fix ===" "PHASE"

# 修改前备份（已在 Phase 1.7 完成，此处补充 CLSID 部分）
$regLog = @()

# 复用 Phase 1 的扫描结果（$regHits），但只处理涉及已迁移子目录的条目
# 过滤：注册表值必须包含 $migrationPairs 中某个 Old 路径才处理（不影响被跳过的安装器软件）
$currentRegHits = $regHits | Where-Object {
    $val = $_.Value
    ($migrationPairs | Where-Object { $val -like "*$($_.Old)*" }).Count -gt 0
}
Write-Log "Registry hits relevant to migrated items: $($currentRegHits.Count) (total scanned: $($regHits.Count))"

foreach ($hit in $currentRegHits) {
    # 统一用 Registry:: 前缀 + 原始 key 名，避免路径格式转换不一致
    try {
        $key = Get-Item "Registry::$($hit.Key)" -ErrorAction Stop
    } catch {
        Write-Log "  REG SKIP (cannot open key): $($hit.Key)" "WARN"
        continue
    }

    # 只替换涉及已迁移子目录的路径对
    $newVal = $hit.Value
    foreach ($mp in $migrationPairs) {
        $newVal = Replace-PathVariants -Content $newVal -Old $mp.Old -New $mp.New
    }
    $regLog += @{ Key=$hit.Key; ValueName=$hit.ValueName; Kind="$($hit.Kind)"; OldValue=$hit.Value; NewValue=$newVal; Timestamp=(Get-Date -Format "o") }

    switch ($hit.Kind) {
        'String'       { $key.SetValue($hit.ValueName, $newVal, 'String') }
        'ExpandString' { $key.SetValue($hit.ValueName, $newVal, 'ExpandString') }
        'MultiString'  {
            $arr = $key.GetValue($hit.ValueName) | ForEach-Object {
                $line = $_
                foreach ($mp in $migrationPairs) { $line = $line -replace [regex]::Escape($mp.Old), $mp.New }
                $line
            }
            $key.SetValue($hit.ValueName, [string[]]$arr, 'MultiString')
        }
    }
    Write-Log "  REG FIXED [$($hit.Kind)]: $($hit.Key)\$($hit.ValueName)"
}

# CLSID 默认值特殊处理（必须用 reg add /ve）
$clsidRoots = @(
    "Registry::HKEY_CLASSES_ROOT\CLSID",
    "Registry::HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\Classes\CLSID"
)
foreach ($clsidRoot in $clsidRoots) {
    Get-ChildItem $clsidRoot -Recurse -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -like "*InProcServer32" } |
        ForEach-Object {
            $defVal = $_.GetValue("")
            $clsidMatch = $null
            foreach ($mp in $migrationPairs) { if ($defVal -like "*$($mp.Old)*") { $clsidMatch = $mp; break } }
            if ($clsidMatch) {
                $newDefVal = $defVal.Replace($clsidMatch.Old, $clsidMatch.New)
                $regPath = $_.Name -replace 'HKEY_LOCAL_MACHINE', 'HKLM' -replace 'HKEY_CLASSES_ROOT', 'HKCR'
                reg add "$regPath" /ve /t REG_SZ /d "$newDefVal" /f
                Write-Log "  CLSID FIXED: $regPath"
                $regLog += @{ Key=$regPath; ValueName="(Default)"; Kind="String"; OldValue=$defVal; NewValue=$newDefVal; Timestamp=(Get-Date -Format "o") }
            }
        }
}

$regLog | ConvertTo-Json -Depth 10 | Set-Content "$backupDir\registry_rollback_log.json" -Encoding UTF8
Write-Log "Registry changes: $($regLog.Count) values"
Update-PhaseProgress -Phase "7"

Write-Log "=== Phase 8: Hidden Reference Scan & Fix ===" "PHASE"

# 1. Registry Run/RunOnce
$runKeys = @(
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce",
    "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
    "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce"
)
foreach ($rk in $runKeys) {
    if (Test-Path $rk) {
        $props = Get-ItemProperty $rk
        $props.PSObject.Properties | Where-Object {
            $v = $_.Value
            ($migrationPairs | Where-Object { $v -like "*$($_.Old)*" }).Count -gt 0
        } | ForEach-Object {
            $newVal = $_.Value
            foreach ($mp in $migrationPairs) { $newVal = Replace-PathVariants -Content $newVal -Old $mp.Old -New $mp.New }
            Set-ItemProperty $rk -Name $_.Name -Value $newVal
            Write-Log "  STARTUP FIXED: $rk\$($_.Name)" "OK"
        }
    }
}

# 2. Startup Folder (.lnk / .bat / .cmd / .vbs)
$startupFolders = @([Environment]::GetFolderPath('CommonStartup'), [Environment]::GetFolderPath('Startup'))
$shell = New-Object -ComObject WScript.Shell
foreach ($folder in $startupFolders) {
    Get-ChildItem $folder -File -ErrorAction SilentlyContinue | ForEach-Object {
        if ($_.Extension -eq '.lnk') {
            $shortcut = $shell.CreateShortcut($_.FullName)
            $lnkModified = $false
            foreach ($mp in $migrationPairs) {
                if ($shortcut.TargetPath -like "*$($mp.Old)*") { $shortcut.TargetPath = $shortcut.TargetPath.Replace($mp.Old, $mp.New); $lnkModified = $true }
                if ($shortcut.Arguments -like "*$($mp.Old)*") { $shortcut.Arguments = $shortcut.Arguments.Replace($mp.Old, $mp.New); $lnkModified = $true }
            }
            if ($lnkModified) {
                $shortcut.Save()
                Write-Log "  STARTUP LNK FIXED: $($_.FullName)" "OK"
            }
        } elseif ($_.Extension -in @('.bat','.cmd','.vbs')) {
            $content = Get-Content $_.FullName -Raw -ErrorAction SilentlyContinue
            $scriptModified = $false
            foreach ($mp in $migrationPairs) { if ($content -like "*$($mp.Old)*") { $scriptModified = $true; break } }
            if ($scriptModified) {
                Copy-Item $_.FullName "$($_.FullName).migration_bak" -Force
                $enc = Detect-Encoding -FilePath $_.FullName
                $newContent = $content
                foreach ($mp in $migrationPairs) { $newContent = Replace-PathVariants -Content $newContent -Old $mp.Old -New $mp.New }
                [System.IO.File]::WriteAllText($_.FullName, $newContent, $enc)
                Write-Log "  STARTUP SCRIPT FIXED: $($_.FullName)" "OK"
            }
        }
    }
}

# 3. Task Scheduler（合并 Actions + WorkingDirectory 处理，只匹配已迁移子目录）
Get-ScheduledTask | ForEach-Object {
    $task = $_
    $modified = $false
    foreach ($action in $task.Actions) {
        foreach ($mp in $migrationPairs) {
            if ($action.Execute -like "*$($mp.Old)*") { $action.Execute = $action.Execute.Replace($mp.Old, $mp.New); $modified = $true }
            if ($action.Arguments -like "*$($mp.Old)*") { $action.Arguments = $action.Arguments.Replace($mp.Old, $mp.New); $modified = $true }
        }
        try {
            if ($action.WorkingDirectory) {
                foreach ($mp in $migrationPairs) {
                    if ($action.WorkingDirectory -like "*$($mp.Old)*") { $action.WorkingDirectory = $action.WorkingDirectory.Replace($mp.Old, $mp.New); $modified = $true }
                }
            }
        } catch { <# Action 类型不支持 WorkingDirectory，跳过 #> }
    }
    if ($modified) {
        $task | Set-ScheduledTask -ErrorAction SilentlyContinue
        Write-Log "  TASK FIXED: $($task.TaskName)" "OK"
    }
}

# 4. ODBC
@("HKLM:\SOFTWARE\ODBC\ODBC.INI","HKLM:\SOFTWARE\WOW6432Node\ODBC\ODBC.INI") | ForEach-Object {
    if (Test-Path $_) {
        Get-ChildItem $_ -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
            $key = $_
            foreach ($name in $key.GetValueNames()) {
                $v = $key.GetValue($name)
                $odbcModified = $false
                foreach ($mp in $migrationPairs) {
                    if ($v -like "*$($mp.Old)*") { $v = $v.Replace($mp.Old, $mp.New); $odbcModified = $true }
                }
                if ($odbcModified) {
                    $key.SetValue($name, $v)
                    Write-Log "  ODBC FIXED: $($key.Name)\$name" "OK"
                }
            }
        }
    }
}

# 5. IIS
if (Get-Module -ListAvailable WebAdministration -ErrorAction SilentlyContinue) {
    Import-Module WebAdministration
    Get-Website | Where-Object {
        $pp = $_.PhysicalPath
        ($migrationPairs | Where-Object { $pp -like "*$($_.Old)*" }).Count -gt 0
    } | ForEach-Object {
        $newPath = $_.PhysicalPath
        foreach ($mp in $migrationPairs) { $newPath = $newPath.Replace($mp.Old, $mp.New) }
        Set-ItemProperty "IIS:\Sites\$($_.Name)" -Name physicalPath -Value $newPath
        Write-Log "  IIS FIXED: $($_.Name)" "OK"
    }
}

# 6. PowerShell Profile（只替换已迁移子目录路径）
@($PROFILE.AllUsersAllHosts, $PROFILE.AllUsersCurrentHost, $PROFILE.CurrentUserAllHosts, $PROFILE.CurrentUserCurrentHost) | ForEach-Object {
    if (Test-Path $_) {
        $content = Get-Content $_ -Raw
        $psModified = $false
        foreach ($mp in $migrationPairs) { if ($content -like "*$($mp.Old)*") { $psModified = $true; break } }
        if ($psModified) {
            Copy-Item $_ "$_.migration_bak" -Force
            $enc = Detect-Encoding -FilePath $_
            $newContent = $content
            foreach ($mp in $migrationPairs) { $newContent = Replace-PathVariants -Content $newContent -Old $mp.Old -New $mp.New }
            [System.IO.File]::WriteAllText($_, $newContent, $enc)
            Write-Log "  PS PROFILE FIXED: $_" "OK"
        }
    }
}

# 7. Windows Terminal settings.json（只替换已迁移子目录路径）
@(
    "$env:LOCALAPPDATA\Packages\Microsoft.WindowsTerminal_8wekyb3d8bbwe\LocalState\settings.json",
    "$env:LOCALAPPDATA\Microsoft\Windows Terminal\settings.json"
) | ForEach-Object {
    if (Test-Path $_) {
        $content = Get-Content $_ -Raw
        $wtModified = $false
        foreach ($mp in $migrationPairs) { if ($content -like "*$($mp.Old)*") { $wtModified = $true; break } }
        if ($wtModified) {
            Copy-Item $_ "$_.migration_bak" -Force
            $enc = Detect-Encoding -FilePath $_
            $newContent = $content
            foreach ($mp in $migrationPairs) { $newContent = Replace-PathVariants -Content $newContent -Old $mp.Old -New $mp.New }
            [System.IO.File]::WriteAllText($_, $newContent, $enc)
            Write-Log "  WINDOWS TERMINAL FIXED: $_" "OK"
        }
    }
}

# 8. Git config（只替换已迁移子目录路径）
@("$env:USERPROFILE\.gitconfig", "$env:USERPROFILE\.config\git\config") | ForEach-Object {
    if (Test-Path $_) {
        $content = Get-Content $_ -Raw
        $gitModified = $false
        foreach ($mp in $migrationPairs) { if ($content -like "*$($mp.Old)*") { $gitModified = $true; break } }
        if ($gitModified) {
            Copy-Item $_ "$_.migration_bak" -Force
            $enc = Detect-Encoding -FilePath $_
            $newContent = $content
            foreach ($mp in $migrationPairs) { $newContent = Replace-PathVariants -Content $newContent -Old $mp.Old -New $mp.New }
            [System.IO.File]::WriteAllText($_, $newContent, $enc)
            Write-Log "  GIT CONFIG FIXED: $_" "OK"
        }
    }
}

# 9. Docker compose（扫描已迁移到目标目录的 compose 文件）
foreach ($mp in $migrationPairs) {
    Get-ChildItem $mp.New -Filter "docker-compose*.yml" -Recurse -Depth 3 -ErrorAction SilentlyContinue | ForEach-Object {
        $content = Get-Content $_.FullName -Raw
        $dcModified = $false
        foreach ($p in $migrationPairs) { if ($content -like "*$($p.Old)*") { $dcModified = $true; break } }
        if ($dcModified) {
            Copy-Item $_.FullName "$($_.FullName).migration_bak" -Force
            $enc = Detect-Encoding -FilePath $_.FullName
            $newContent = $content
            foreach ($p in $migrationPairs) { $newContent = Replace-PathVariants -Content $newContent -Old $p.Old -New $p.New }
            [System.IO.File]::WriteAllText($_.FullName, $newContent, $enc)
            Write-Log "  DOCKER FIXED: $($_.FullName)" "OK"
        }
    }
}
# 注：如果用户有源目录外的 docker-compose 引用了 $src 路径，Phase 10 验证会报出，手动处理

# 10. WSL 配置文件（只替换已迁移子目录路径的 /mnt/ 和 Windows 变体）
$wslConfigs = @(
    "$env:USERPROFILE\.wslconfig",
    "$env:USERPROFILE\.config\wsl\wsl.conf"
)
foreach ($wslCfg in $wslConfigs) {
    if (Test-Path $wslCfg) {
        $content = Get-Content $wslCfg -Raw
        $wslModified = $false
        foreach ($mp in $migrationPairs) {
            $wslOld = "/mnt/" + ($mp.Old -replace ':','') -replace '\\','/'
            if ($content -like "*$($mp.Old)*" -or $content -like "*$wslOld*") { $wslModified = $true; break }
        }
        if ($wslModified) {
            $enc = Detect-Encoding -FilePath $wslCfg
            $newContent = $content
            foreach ($mp in $migrationPairs) {
                $newContent = Replace-PathVariants -Content $newContent -Old $mp.Old -New $mp.New
                $wslOld = "/mnt/" + ($mp.Old -replace ':','') -replace '\\','/'
                $wslNew = "/mnt/" + ($mp.New -replace ':','') -replace '\\','/'
                $newContent = [regex]::Replace($newContent, [regex]::Escape($wslOld), $wslNew, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
            }
            [System.IO.File]::WriteAllText($wslCfg, $newContent, $enc)
            Write-Log "  WSL CONFIG FIXED: $wslCfg" "OK"
        }
    }
}
# WSL 内部的 /etc/wsl.conf 需要在 WSL 环境中修改，此处仅提示
Write-Log "NOTE: If WSL distros reference migrated paths internally (e.g. /mnt/d/...), run 'wsl' and fix /etc/wsl.conf manually" "WARN"

Update-PhaseProgress -Phase "8"

Write-Log "=== Phase 9: Source Cleanup ===" "PHASE"

# 重命名前再次检查残留（Phase 3 后可能有新的锁定产生）
$remaining = Get-ChildItem $src -Force -Recurse -ErrorAction SilentlyContinue
if ($remaining) {
    Write-Log "Source still has $($remaining.Count) items. Blocking files:" "WARN"
    $remaining | Select-Object -First 20 | ForEach-Object { Write-Log "  $($_.FullName)" "WARN" }
    if ($remaining.Count -gt 20) { Write-Log "  ... and $($remaining.Count - 20) more" "WARN" }
    Write-Log "Cannot rename. Recommend: reboot then retry." "WARN"
} else {
    # 尝试重命名（可能因目录句柄被持有而失败）
    $renamed = $false
    for ($attempt = 1; $attempt -le 3; $attempt++) {
        try {
            Rename-Item $src "$src.migration_backup" -Force -ErrorAction Stop
            $renamed = $true
            Write-Log "Source renamed to: $src.migration_backup" "OK"
            break
        } catch {
            Write-Log "  Rename attempt $attempt failed: $_" "WARN"
            Start-Sleep 3
        }
    }
    if (-not $renamed) {
        Write-Log "Cannot rename source (directory handle held by a process). Reboot required." "ERROR"
    }
}

# --- Phase 9.2: Source Cleanup Choice (interaction node) ---
Write-Log ""
Write-Log "========== SOURCE CLEANUP ==========" "PHASE"
if (Test-Path "$src.migration_backup") {
    Write-Log "Renamed source: $src.migration_backup"
} else {
    Write-Log "Source not renamed (files may still exist at $src)"
}
Write-Log "Options:"
Write-Log "  [1] Keep as-is (recommended, delete manually after confirming stability)"
Write-Log "  [2] Delete now (may fail if shell extension DLLs are locked)"
Write-Log "  [3] Delete on next reboot (via RunOnce registry)"
Write-Log "====================================" "PHASE"

if ($NonInteractive) {
    Write-Log "Non-Interactive: Defaulting to option 1 (keep)." "WARN"
    $cleanupChoice = "1"
} else {
    $cleanupChoice = Read-Host "Choose [1/2/3] (default 1)"
    if (-not $cleanupChoice) { $cleanupChoice = "1" }
}

$cleanupTarget = "$src.migration_backup"
switch ($cleanupChoice) {
    "2" {
        Write-Log "Attempting immediate cleanup..." "WARN"
        if (Test-Path $cleanupTarget) {
            Remove-Item -LiteralPath $cleanupTarget -Recurse -Force -ErrorAction SilentlyContinue
            if (Test-Path $cleanupTarget) { Write-Log "  Cannot delete (files locked). Use option [3] instead." "ERROR" }
            else { Write-Log "  Source backup deleted." "OK" }
        }
    }
    "3" {
        Write-Log "Registering RunOnce cleanup..." "WARN"
        $cleanupCmd = "powershell -ExecutionPolicy Bypass -Command `"Remove-Item -LiteralPath '$cleanupTarget' -Recurse -Force; Stop-Process -Name explorer -Force; Start-Sleep 2; Start-Process explorer.exe`""
        Set-ItemProperty "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce" -Name "MigrationCleanup" -Value $cleanupCmd
        Write-Log "RunOnce cleanup registered for: $cleanupTarget" "OK"
        Write-Log "Reboot to complete cleanup." "WARN"
    }
    default {
        Write-Log "Keeping source backup at: $cleanupTarget" "OK"
        Write-Log "Delete manually after confirming migration stability." "INFO"
    }
}

Update-PhaseProgress -Phase "9"

Write-Log "=== Phase 10: Verification ===" "PHASE"

# 恢复 Windows Search（Phase 2 中暂停的）
if ($script:wsearchWasRunning) {
    Start-Service WSearch -ErrorAction SilentlyContinue
    Write-Log "Windows Search (WSearch) restored" "OK"
}

$report = @{ Critical=@(); Warning=@(); Info=@() }

# Critical: 服务、PATH、启动项、计划任务（只检查已迁移子目录路径）
$allOldPaths = $migrationPairs | ForEach-Object { $_.Old }

foreach ($mp in $migrationPairs) {
    # 服务
    Get-WmiObject Win32_Service | Where-Object { $_.PathName -like "*$($mp.Old)*" } |
        ForEach-Object { $report.Critical += "SERVICE: $($_.Name) = $($_.PathName)" }

    # PATH
    foreach ($scope in @('Machine','User')) {
        if ([System.Environment]::GetEnvironmentVariable('Path', $scope) -like "*$($mp.Old)*") {
            $report.Critical += "PATH [$scope] still references $($mp.Old)"
        }
    }

    # 启动项
    $runKeys | ForEach-Object {
        if (Test-Path $_) {
            (Get-ItemProperty $_).PSObject.Properties | Where-Object { $_.Value -like "*$($mp.Old)*" } |
                ForEach-Object { $report.Critical += "STARTUP: $($_.Name)" }
        }
    }
}

# 计划任务（修复 TaskName 作用域问题）
Get-ScheduledTask | ForEach-Object {
    $taskName = $_.TaskName
    $_.Actions | Where-Object {
        $exec = $_.Execute
        ($allOldPaths | Where-Object { $exec -like "*$_*" }).Count -gt 0
    } | ForEach-Object { $report.Critical += "TASK: $taskName" }
}

# Warning: 环境变量、注册表（遍历已迁移路径检查残留）
foreach ($mp in $migrationPairs) {
    $envRemaining = Scan-EnvVarsForPath -SearchPath $mp.Old
    $envRemaining | Where-Object { $_.Key -ne 'Path' } | ForEach-Object { $report.Warning += "ENV [$($_.Scope)]: $($_.Key)" }
}

foreach ($mp in $migrationPairs) {
    $regRemaining = Scan-RegistryForPath -SearchPath $mp.Old -Depth 5
    $regRemaining | ForEach-Object { $report.Warning += "REG: $($_.Key)\$($_.ValueName)" }
}

# Info: 配置文件残留（只检查已迁移路径）
foreach ($mp in $migrationPairs) {
    $configRemaining = Scan-ConfigFilesForPath -Directory $dst -SearchPath $mp.Old
    $configRemaining | ForEach-Object { $report.Info += "CONFIG: $($_.FullName)" }
}

$serviceDeps = Get-Content "$backupDir\service_dependencies.json" | ConvertFrom-Json

$started = @()
$maxRounds = 5
for ($round = 1; $round -le $maxRounds; $round++) {
    foreach ($svc in $serviceDeps) {
        if ($svc.Name -in $started) { continue }
        # 强制数组化（ConvertFrom-Json 单元素会变成字符串）
        $deps = @($svc.DependsOn)
        $depsReady = ($deps | Where-Object { $_ -and $_ -notin $started -and $_ -ne $svc.Name }).Count -eq 0
        if ($depsReady) {
            Write-Log "Starting service: $($svc.Name) (round $round)"
            Start-Service $svc.Name -ErrorAction SilentlyContinue
            $started += $svc.Name
        }
    }
}

# 循环依赖检测：如果仍有服务未启动，说明存在循环依赖
$notStarted = @($serviceDeps | Where-Object { $_.Name -notin $started })
if ($notStarted.Count -gt 0) {
    Write-Log "CIRCULAR DEPENDENCY DETECTED: $($notStarted.Name -join ', ') could not be started in $maxRounds rounds" "ERROR"
    $notStarted | ForEach-Object {
        $blockingDeps = @($_.DependsOn) | Where-Object { $_ -and $_ -notin $started }
        $report.Critical += "CIRCULAR DEP: $($_.Name) blocked by unstarted deps: [$($blockingDeps -join ', ')]"
    }
}

foreach ($svc in $serviceDeps) {
    $status = (Get-Service $svc.Name -ErrorAction SilentlyContinue).Status
    if ($status -ne 'Running') {
        Write-Log "SERVICE NOT RUNNING: $($svc.Name) [$status]" "ERROR"
        $report.Critical += "SERVICE DOWN: $($svc.Name)"
    }
}

$report | ConvertTo-Json -Depth 10 | Set-Content "$backupDir\verification_report.json" -Encoding UTF8

$txtReport = @"
========== MIGRATION VERIFICATION REPORT ==========
Generated: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
Source: $src -> Destination: $dst

[CRITICAL] ($($report.Critical.Count) issues)
$(($report.Critical | ForEach-Object { "  !! $_" }) -join "`n")

[WARNING] ($($report.Warning.Count) issues)
$(($report.Warning | ForEach-Object { "  ! $_" }) -join "`n")

[INFO] ($($report.Info.Count) issues)
$(($report.Info | ForEach-Object { "  - $_" }) -join "`n")

RESULT: $(if ($report.Critical.Count -eq 0 -and $report.Warning.Count -eq 0) { "CLEAN" } else { "ACTION REQUIRED" })
==================================================
"@
[System.IO.File]::WriteAllText("$backupDir\verification_report.txt", $txtReport)

$htmlReport = @"
<html><head><style>body{font-family:Segoe UI,sans-serif;margin:40px}.critical{color:#d32f2f;font-weight:bold}.warning{color:#f57c00}.info{color:#616161}</style></head><body>
<h1>Migration Verification Report</h1>
<p>$(Get-Date -Format "yyyy-MM-dd HH:mm:ss") | $src &rarr; $dst</p>
<h2 class="critical">Critical ($($report.Critical.Count))</h2><ul>$(($report.Critical | ForEach-Object { "<li class='critical'>$_</li>" }) -join '')</ul>
<h2 class="warning">Warning ($($report.Warning.Count))</h2><ul>$(($report.Warning | ForEach-Object { "<li class='warning'>$_</li>" }) -join '')</ul>
<h2 class="info">Info ($($report.Info.Count))</h2><ul>$(($report.Info | ForEach-Object { "<li class='info'>$_</li>" }) -join '')</ul>
</body></html>
"@
[System.IO.File]::WriteAllText("$backupDir\verification_report.html", $htmlReport)
Write-Log "Reports: verification_report.{json,txt,html}"

# 未迁移的安装器软件提醒
if ($skippedItems -and $skippedItems.Count -gt 0) {
    Write-Log "" "WARN"
    Write-Log "========== 未迁移的安装器软件（需手动处理）==========" "WARN"
    $skippedItems | ForEach-Object { Write-Log "  - $_（建议：卸载后重装到 $dst）" "WARN" }
    Write-Log "这些软件仍留在 $src，其注册表/环境变量引用未被修改。" "WARN"
    Write-Log "如果后续删除 $src 目录，这些软件将无法启动。" "WARN"
    Write-Log "=================================================" "WARN"
    # 写入报告 JSON
    $report.SkippedInstallerItems = $skippedItems
}

if ($report.Critical.Count -eq 0 -and $report.Warning.Count -eq 0) {
    Write-Log "======== MIGRATION COMPLETE - ALL CLEAN ========" "OK"
} else {
    Write-Log "======== MIGRATION COMPLETE - ISSUES: C=$($report.Critical.Count) W=$($report.Warning.Count) ========" "ERROR"
}

# Windows Toast（仅 Desktop 版 Windows 10 1703+ 可用，Server 版无 WinRT 支持）
$osInfo = [System.Environment]::OSVersion
$isDesktop = ($osInfo.Version.Major -ge 10) -and ($osInfo.Version.Build -ge 15063) -and ((Get-WmiObject Win32_OperatingSystem).ProductType -eq 1)
if ($isDesktop) {
    try {
        [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
        $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent(0)
        $textNodes = $template.GetElementsByTagName("text")
        $textNodes.Item(0).AppendChild($template.CreateTextNode("Migration Complete")) | Out-Null
        $textNodes.Item(1).AppendChild($template.CreateTextNode("C=$($report.Critical.Count) W=$($report.Warning.Count)")) | Out-Null
        [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Migration").Show(
            [Windows.UI.Notifications.ToastNotification]::new($template))
    } catch { Write-Log "Toast failed (non-critical): $_" "DETAIL" }
} else {
    Write-Log "Toast skipped (Server OS or version < 1703)" "DETAIL"
}

# Event Log
try {
    New-EventLog -LogName Application -Source "SoftwareMigration" -ErrorAction SilentlyContinue
    Write-EventLog -LogName Application -Source "SoftwareMigration" -EventId 1000 -EntryType Information `
        -Message "Migration $src -> $dst completed. Critical=$($report.Critical.Count) Warning=$($report.Warning.Count)"
} catch {}

# 磁盘写入速度
$testFile = "$dst\__perf_test__.tmp"
$sw = [System.Diagnostics.Stopwatch]::StartNew()
[System.IO.File]::WriteAllBytes($testFile, (New-Object byte[] 100MB))
$sw.Stop()
Remove-Item $testFile -Force
Write-Log "Disk write: ~$([math]::Round(100 / $sw.Elapsed.TotalSeconds, 1)) MB/s"

# 服务启动耗时（仅测量未运行服务的启动时间，不重启已运行的服务）
foreach ($svc in $serviceDeps) {
    $svcObj = Get-Service $svc.Name -ErrorAction SilentlyContinue
    if ($svcObj -and $svcObj.Status -ne 'Running') {
        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        Start-Service $svc.Name -ErrorAction SilentlyContinue
        $sw.Stop()
        Write-Log "  $($svc.Name) start: $([math]::Round($sw.Elapsed.TotalSeconds, 1))s"
    }
}

Write-Log "--- 10.6 Runtime Verification ---"

# 自动检测已迁移目录中的 CLI 工具并验证
$runtimeChecks = @()
foreach ($mp in $migrationPairs) {
    $binDir = "$($mp.New)\bin"
    if (Test-Path $binDir) {
        # 常见开发工具 CLI 验证
        $knownTools = @{
            'java.exe'    = @('-version')
            'javac.exe'   = @('-version')
            'mvn.cmd'     = @('--version')
            'node.exe'    = @('--version')
            'npm.cmd'     = @('--version')
            'python.exe'  = @('--version')
            'git.exe'     = @('--version')
            'redis-server.exe' = @('--version')
            'mysql.exe'   = @('--version')
            'docker.exe'  = @('version','--format','{{.Server.Version}}')
        }
        foreach ($tool in $knownTools.Keys) {
            $toolPath = "$binDir\$tool"
            if (Test-Path $toolPath) {
                $runtimeChecks += @{ Name=$tool; ExePath=$toolPath; Args=$knownTools[$tool] }
            }
        }
    }
}

foreach ($check in $runtimeChecks) {
    try {
        # 用全路径直接执行，不依赖 PATH（当前会话 PATH 可能尚未刷新）
        $output = & $check.ExePath $check.Args 2>&1
        if ($LASTEXITCODE -eq 0 -or $output) {
            Write-Log "  RUNTIME OK: $($check.Name) -> $($output | Select-Object -First 1)" "OK"
        } else {
            Write-Log "  RUNTIME FAIL: $($check.Name) (exit=$LASTEXITCODE)" "ERROR"
            $report.Critical += "RUNTIME: $($check.Name) failed after migration"
        }
    } catch {
        Write-Log "  RUNTIME ERROR: $($check.Name) - $_" "ERROR"
        $report.Critical += "RUNTIME: $($check.Name) threw exception"
    }
}

# 服务端口监听验证（针对已迁移的服务）
foreach ($svc in $serviceDeps) {
    $status = (Get-Service $svc.Name -ErrorAction SilentlyContinue).Status
    if ($status -eq 'Running') {
        Write-Log "  SERVICE RUNNING: $($svc.Name)" "OK"
    } else {
        Write-Log "  SERVICE NOT RUNNING: $($svc.Name) [$status]" "ERROR"
        $report.Critical += "SERVICE DOWN: $($svc.Name)"
    }
}

if ($runtimeChecks.Count -eq 0) {
    Write-Log "  No known CLI tools detected in migrated directories. Manual verification recommended." "WARN"
}

Update-PhaseProgress -Phase "10"

# 释放 lock + 关闭日志
Remove-Item $lockFile -Force -ErrorAction SilentlyContinue
Close-Log
Write-Host "Lock released. Migration session complete."

# --- Phase 11: Rollback (only if user chooses) ---
Write-Host ""
Write-Host "Migration completed. If there are issues, you can roll back."
$wantRollback = Read-Host "Roll back? Enter rollback level [1=refs only / 2=full restore / 3=clean target / Enter=skip]"
if (-not $wantRollback) {
    Write-Host "No rollback. Migration complete."
    exit 0
}
Write-Host "Starting Rollback Level $wantRollback..."

# Re-open log for rollback
$script:logWriter = New-Object System.IO.StreamWriter($logFile, $true, [System.Text.Encoding]::UTF8)
$script:logWriter.AutoFlush = $true
Write-Log ""
Write-Log "=== Phase 11: Rollback (Level $wantRollback) ===" "PHASE"

# 从 migration_summary.json 动态读取路径（不硬编码）
$summary = Get-Content "$backupDir\migration_summary.json" | ConvertFrom-Json
$rbSrc = $summary.source
$rbDst = $summary.destination

# 验证备份完整性
$required = @('env_backup.json','services_backup.json','links_backup.json','registry_rollback_log.json')
foreach ($f in $required) {
    if (-not (Test-Path "$backupDir\$f")) { Write-Log "ROLLBACK ABORT: Missing $f" "ERROR"; exit 1 }
}

# 回滚进度追踪（防中断）
$rbProgressFile = "$backupDir\rollback_progress.json"
$rbProgress = if (Test-Path $rbProgressFile) { Get-Content $rbProgressFile | ConvertFrom-Json } else { @{ Steps=@() } }

# 1. 环境变量
if ('env' -notin $rbProgress.Steps) {
    $envBackup = Get-Content "$backupDir\env_backup.json" | ConvertFrom-Json
    foreach ($scope in @('Machine','User')) {
        $envBackup.$scope.PSObject.Properties | ForEach-Object {
            [System.Environment]::SetEnvironmentVariable($_.Name, $_.Value, $scope)
        }
    }
    $rbProgress.Steps += 'env'; $rbProgress | ConvertTo-Json -Depth 10 | Set-Content $rbProgressFile
    Write-Log "Rollback: env restored" "OK"
}

# 2. 服务
if ('svc' -notin $rbProgress.Steps) {
    $svcBackup = Get-Content "$backupDir\services_backup.json" | ConvertFrom-Json
    foreach ($svc in $svcBackup) { sc.exe config $svc.Name binPath= "$($svc.PathName)" }
    $rbProgress.Steps += 'svc'; $rbProgress | ConvertTo-Json -Depth 10 | Set-Content $rbProgressFile
    Write-Log "Rollback: services restored" "OK"
}

# 3. 注册表
if ('reg' -notin $rbProgress.Steps) {
    Get-ChildItem "$backupDir\registry" -Filter "*.reg" | ForEach-Object { reg import $_.FullName 2>$null }
    $rbProgress.Steps += 'reg'; $rbProgress | ConvertTo-Json -Depth 10 | Set-Content $rbProgressFile
    Write-Log "Rollback: registry restored" "OK"
}

# 4. 配置文件恢复（正确顺序：先 bak 覆盖 → 再清理 tmp → 最后从备份目录恢复）
if ('cfg' -notin $rbProgress.Steps) {
    # Step A: 用 .migration_bak 强制恢复原文件（优先级最高，防止 Phase 6 中途崩溃导致文件损坏）
    Get-ChildItem $rbDst -Recurse -Filter "*.migration_bak" -ErrorAction SilentlyContinue | ForEach-Object {
        $target = $_.FullName -replace '\.migration_bak$', ''
        # 保护用户迁移后的手动修改：当前文件另存为 .migration_conflict_时间戳
        if (Test-Path $target) {
            $conflictName = "$target.migration_conflict_$(Get-Date -Format 'yyyyMMddHHmmssfff')"
            Copy-Item $target $conflictName -Force
            Write-Log "  Conflict saved: $conflictName"
        }
        Copy-Item $_.FullName $target -Force
        Remove-Item $_.FullName -Force
    }
    # Step B: 清理残留的 .migration_tmp（Phase 6 原子替换未完成的中断产物）
    Get-ChildItem $rbDst -Recurse -Filter "*.migration_tmp" -ErrorAction SilentlyContinue | Remove-Item -Force
    # Step C: 从备份目录恢复原始配置（覆盖可能已损坏的文件）
    $configBackupDir = "$backupDir\configs"
    if (Test-Path $configBackupDir) {
        Get-ChildItem $configBackupDir -Recurse -File | ForEach-Object {
            $relPath = $_.FullName.Substring($configBackupDir.Length)
            $destPath = "$rbDst$relPath"
            if (Test-Path (Split-Path $destPath)) { Copy-Item $_.FullName $destPath -Force }
        }
    }
    $rbProgress.Steps += 'cfg'; $rbProgress | ConvertTo-Json -Depth 10 | Set-Content $rbProgressFile
    Write-Log "Rollback: configs restored (bak→clean→backup order)" "OK"
}

# 5. 链接
if ('links' -notin $rbProgress.Steps) {
    $linksBackup = Get-Content "$backupDir\links_backup.json" | ConvertFrom-Json
    foreach ($link in $linksBackup) {
        $linkPath = "$rbDst\$($link.Name)"
        if (Test-Path $linkPath) { Remove-Item $linkPath -Force -ErrorAction SilentlyContinue }
        if ($link.LinkType -eq 'Junction') { cmd /c "mklink /J `"$linkPath`" `"$($link.Target)`"" }
        else { New-Item -ItemType SymbolicLink -Path $linkPath -Target $link.Target -Force }
    }
    $rbProgress.Steps += 'links'; $rbProgress | ConvertTo-Json -Depth 10 | Set-Content $rbProgressFile
    Write-Log "Rollback: links restored" "OK"
}

# Level 1 回滚验证
Write-Log "--- Rollback L1 Verification ---"
$rbVerifyFailed = @()
# 验证环境变量已恢复
foreach ($mp in $migrationPairs) {
    $envStillNew = Scan-EnvVarsForPath -SearchPath $mp.New
    if ($envStillNew.Count -gt 0) { $rbVerifyFailed += "ENV still references $($mp.New): $($envStillNew.Key -join ', ')" }
}
# 验证服务路径已恢复
foreach ($svc in $svcBackup) {
    $current = (Get-WmiObject Win32_Service -Filter "Name='$($svc.Name)'").PathName
    if ($current -ne $svc.PathName) { $rbVerifyFailed += "SERVICE $($svc.Name) path not restored" }
}
if ($rbVerifyFailed.Count -gt 0) {
    $rbVerifyFailed | ForEach-Object { Write-Log "  RB VERIFY FAIL: $_" "ERROR" }
} else {
    Write-Log "  Rollback L1 verified: all references restored." "OK"
}

# Level 2: 完整恢复（Level 1 + 文件移回）
if ($wantRollback -ge 2 -and 'files' -notin $rbProgress.Steps) {
    $manifest = Get-Content "$backupDir\migration_manifest.json" | ConvertFrom-Json
    if (-not (Test-Path $rbSrc)) { New-Item $rbSrc -ItemType Directory -Force }
    foreach ($item in $manifest) {
        if (Test-Path $item.newPath) {
            Move-Item $item.newPath $item.originalPath -Force -ErrorAction SilentlyContinue
            Write-Log "  Moved back: $($item.newPath) -> $($item.originalPath)"
        }
    }
    $rbProgress.Steps += 'files'; $rbProgress | ConvertTo-Json -Depth 10 | Set-Content $rbProgressFile
    Write-Log "Rollback L2: files moved back" "OK"
    # Level 2 验证：确认文件确实回到源目录
    $l2Failed = @()
    foreach ($item in $manifest) {
        if (-not (Test-Path $item.originalPath)) { $l2Failed += $item.originalPath }
    }
    if ($l2Failed.Count -gt 0) {
        Write-Log "  RB L2 VERIFY FAIL: $($l2Failed.Count) items not back in source" "ERROR"
        $l2Failed | Select-Object -First 10 | ForEach-Object { Write-Log "    $_" "ERROR" }
    } else {
        Write-Log "  Rollback L2 verified: all files back in source." "OK"
    }
}

# Level 3: 清理迁移目标（Level 1 + 删除新目录）
if ($wantRollback -eq 3 -and 'clean' -notin $rbProgress.Steps) {
    Get-ChildItem $rbDst -Force -ErrorAction SilentlyContinue | Where-Object { $_.LinkType } | ForEach-Object {
        if ($_.LinkType -eq 'Junction') { cmd /c "rmdir `"$($_.FullName)`"" } else { $_.Delete() }
    }
    Remove-Item $rbDst -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item "$rbDst.migration_backup" -Recurse -Force -ErrorAction SilentlyContinue
    $rbProgress.Steps += 'clean'; $rbProgress | ConvertTo-Json -Depth 10 | Set-Content $rbProgressFile
    Write-Log "Rollback L3: target cleaned" "OK"
    # Level 3 验证：确认目标目录已删除
    if (Test-Path $rbDst) {
        Write-Log "  RB L3 VERIFY FAIL: $rbDst still exists" "ERROR"
    } else {
        Write-Log "  Rollback L3 verified: target directory removed." "OK"
    }
}

# 释放 lock
Remove-Item $lockFile -Force -ErrorAction SilentlyContinue
Close-Log
Write-Host "Rollback Level $wantRollback complete."

