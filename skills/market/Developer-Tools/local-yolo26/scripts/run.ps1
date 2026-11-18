param(
    [ValidateSet('cpu', 'gpu', 'npu', 'CPU', 'GPU', 'NPU')]
    [string]$Device = 'gpu',
    [Parameter(Position=0)]
    [string]$Command = ''
)

$ErrorActionPreference = 'Stop'

# --- Logging ---
$LogDir = Join-Path $env:USERPROFILE '.openvino\log'
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir -Force | Out-Null }
$LogTimestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$LogFile = Join-Path $LogDir "yolo26-client-$LogTimestamp.log"
Add-Content $LogFile "[$(Get-Date)] Log initialized."
function Write-Log($msg) { Add-Content $LogFile "[$(Get-Date)] $msg" }

Write-Log "run.ps1 started: Device='$Device' Command='$Command'"

$SkillRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

if ($Command -eq '--help' -or $Command -eq '-h') {
    Write-Host 'Usage:'
    Write-Host '  scripts\run.ps1                       # start detection (GPU), opens a live window'
    Write-Host '  scripts\run.ps1 -Device gpu           # choose device: cpu | gpu | npu'
    Write-Host '  scripts\run.ps1 --status              # show server status + device'
    Write-Host '  scripts\run.ps1 --stop                # stop the server (free camera + GPU/NPU)'
    exit 0
}

# --- Read venv config ---
$EnvJson = Join-Path $SkillRoot 'info.json'
if (-not (Test-Path $EnvJson)) {
    Write-Host 'ERROR: info.json not found.'
    exit 1
}
$Config = Get-Content $EnvJson -Raw | ConvertFrom-Json
$VenvName = $Config.venv_name
if (-not $VenvName) {
    Write-Host 'ERROR: venv_name not found in info.json.'
    exit 1
}
$VenvDir = Join-Path $env:USERPROFILE ".openvino\venv\$VenvName"
$VenvPy = Join-Path $VenvDir 'Scripts\python.exe'

# --- Control ops (status/stop): skip camera gate + env setup ---
if ($Command -eq '--status' -or $Command -eq '--server-status') {
    Write-Log 'Control op --status.'
    & $VenvPy "$SkillRoot\scripts\client.py" --server-status --log $LogFile
    exit $LASTEXITCODE
}
if ($Command -eq '--stop' -or $Command -eq '--server-shutdown') {
    Write-Log 'Control op --stop.'
    & $VenvPy "$SkillRoot\scripts\client.py" --server-shutdown --log $LogFile
    exit $LASTEXITCODE
}

# --- Camera detection (fail fast before provisioning the venv) ---
Write-Log 'Checking for a camera device via PnP.'
$cams = Get-PnpDevice -Class Camera -PresentOnly -Status OK -ErrorAction SilentlyContinue
if (-not $cams) {
    $cams = Get-PnpDevice -Class Image -PresentOnly -Status OK -ErrorAction SilentlyContinue
}
if (-not $cams) {
    Write-Log 'No camera detected via PnP.'
    Write-Host '无法启动服务, 未检测到摄像头设备.'
    exit 1
}
Write-Log "Camera(s) detected: $($cams.FriendlyName -join '; ')"

# --- Ensure environment ---
Write-Host 'Setting up Python environment...'
& "$SkillRoot\scripts\install-env.ps1" -SkillRoot $SkillRoot
if ($LASTEXITCODE -ne 0) { exit 1 }
Write-Log 'install-env.ps1 completed.'

# --- Launch client ---
Write-Host 'Launching detection controller...'
& $VenvPy "$SkillRoot\scripts\client.py" --device $Device --log $LogFile
$exitCode = $LASTEXITCODE
Write-Log "client.py exited with code $exitCode"
exit $exitCode
