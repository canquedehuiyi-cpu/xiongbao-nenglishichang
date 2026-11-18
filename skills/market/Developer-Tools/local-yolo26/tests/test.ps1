param(
    [switch]$CleanEnv,
    [switch]$CleanModels
)

$ErrorActionPreference = 'Stop'

$VenvDir   = Join-Path $env:USERPROFILE '.openvino\venv\yolo26'
$ModelsDir = Join-Path $env:USERPROFILE '.openvino\models\yolo26'
$DistDir   = Split-Path -Parent $PSScriptRoot
$RunScript = Join-Path (Join-Path $DistDir 'scripts') 'run.ps1'

if ($CleanEnv -and (Test-Path $VenvDir)) {
    Write-Host "Removing venv $VenvDir"
    Remove-Item $VenvDir -Recurse -Force
}
if ($CleanModels -and (Test-Path $ModelsDir)) {
    Write-Host "Removing models $ModelsDir"
    Remove-Item $ModelsDir -Recurse -Force
}

function Fail($msg) {
    Write-Host "  [FAIL] $msg" -ForegroundColor Red
    Write-Host 'TEST FAILED' -ForegroundColor Red
    exit 1
}

function Pass($msg) {
    Write-Host "  [PASS] $msg" -ForegroundColor Green
}

function Start-Device($device) {
    Write-Host "--- Start on $($device.ToUpper()) ---"
    & $RunScript -Device $device
    $code = $LASTEXITCODE
    if ($code -eq 0) {
        Pass "$($device.ToUpper()) start exit code = 0"
    } else {
        Fail "$($device.ToUpper()) start exit code = $code (expected 0)"
    }

    # wait for 20 seconds to allow the server to start and stabilize
    Write-Host "Waiting 20 seconds for the server to start..."
    Start-Sleep -Seconds 20
}

function Check-StatusRunning($expectedDevice) {
    Write-Host "--- Status (expect running on $expectedDevice) ---"
    $out = (& $RunScript --status 2>&1 | Out-String)
    Write-Host $out
    if ($out -match 'state:\s*running') {
        Pass 'status reports state: running'
    } else {
        Fail 'status did not report state: running'
    }
    if ($out -match "device:\s*$([regex]::Escape($expectedDevice))") {
        Pass "status reports device: $expectedDevice"
    } else {
        Fail "status did not report device: $expectedDevice"
    }
}

function Check-StatusStopped {
    Write-Host '--- Status (expect not running) ---'
    $out = (& $RunScript --status 2>&1 | Out-String)
    Write-Host $out
    if ($out -match 'shutting down' -or $out -match 'server not running' -or $out -notmatch 'state:\s*running') {
        Pass 'status reports server is not running'
    } else {
        Fail 'status still reports a running server'
    }
}

function Test-HasNpu {
    $npu = Get-PnpDevice -PresentOnly -Status OK -ErrorAction SilentlyContinue |
        Where-Object { $_.FriendlyName -match 'AI Boost' -or $_.FriendlyName -match 'NPU' -or $_.FriendlyName -match 'Neural Processing' }
    return [bool]$npu
}

# === 1. Start on CPU, check exit code ===
Write-Host '=== Step 1: start on CPU (first run may download + export; can take minutes) ==='
Start-Device 'cpu'

# === 2. Status, check output ===
Write-Host '=== Step 2: status after CPU start ==='
Check-StatusRunning 'CPU'

# === 3. Start on GPU, check exit code ===
Write-Host '=== Step 3: switch to GPU (should restart server) ==='
Start-Device 'gpu'

# === 4. Status, check output ===
Write-Host '=== Step 4: status after GPU start ==='
Check-StatusRunning 'GPU'

# === 5. If the system has an NPU, start on NPU and check exit code ===
$ranNpu = $false
if (Test-HasNpu) {
    Write-Host '=== Step 5: NPU detected, switch to NPU ==='
    Start-Device 'npu'
    $ranNpu = $true
} else {
    Write-Host '=== Step 5: no NPU detected, skipping NPU start ==='
}

# === 6. If step 5 ran, status and check output ===
if ($ranNpu) {
    Write-Host '=== Step 6: status after NPU start ==='
    Check-StatusRunning 'NPU'
} else {
    Write-Host '=== Step 6: skipped (NPU not tested) ==='
}

# === 7. Stop ===
Write-Host '=== Step 7: stop the server ==='
& $RunScript --stop
Write-Host "stop exit=$LASTEXITCODE"

# === 8. Status, check output ===
Write-Host '=== Step 8: status after stop ==='
Check-StatusStopped

# === Summary ===
Write-Host ''
Write-Host 'ALL CHECKS PASSED' -ForegroundColor Green
exit 0
