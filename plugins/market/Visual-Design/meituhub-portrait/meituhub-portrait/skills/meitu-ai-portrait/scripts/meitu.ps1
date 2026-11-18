# Node-independent Windows launcher. No system installation or PATH edits.
$ErrorActionPreference = 'Stop'
$CliArgs = @($args)
$Version = '22.23.4'
function Test-Node([string]$Binary) {
    try {
        & $Binary -e 'const [a,b]=process.versions.node.split(".").map(Number);process.exit(a>20||(a===20&&b>=5)?0:1)' *> $null
        return $LASTEXITCODE -eq 0
    } catch { return $false }
}
# Windows CRT quoting preserves spaces, quotes, trailing slashes and empty argv.
function Quote-Arg([string]$Value) {
    '"' + [regex]::Replace([regex]::Replace($Value, '(\\*)"', '$1$1\"'), '(\\+)$', '$1$1') + '"'
}
try {
    $Node = $null
    $SystemNode = Get-Command node.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($SystemNode -and (Test-Node $SystemNode.Source)) { $Node = $SystemNode.Source }
    if (-not $Node) {
        $Architecture = if ($env:PROCESSOR_ARCHITEW6432) { $env:PROCESSOR_ARCHITEW6432 } else { $env:PROCESSOR_ARCHITECTURE }
        switch ($Architecture.ToUpperInvariant()) {
            'AMD64' { $Arch = 'x64'; $Hash = 'dccc52de28d8df2ee22d2062424f8c563070d95d8ad70c54c4bf01d590dec14f' }
            'ARM64' { $Arch = 'arm64'; $Hash = '64d9f6e69b4703870e8cd30a3477127df8b683ea04feb03660e439396549042a' }
            'X86' { $Arch = 'x86'; $Hash = 'aa39a7741f62832ea50daba0113c8f8b12ccde226abca931326832d5bc47d31f' }
            default { throw 'Unsupported CPU architecture for automatic Node preparation' }
        }
        $Root = Join-Path $HOME ".meituhub-qoder/runtime/tools/node-v$Version-win-$Arch"
        $Node = Join-Path $Root 'node.exe'
        if (-not ((Test-Path $Node) -and (Test-Node $Node))) {
            New-Item -ItemType Directory -Force -Path $Root | Out-Null
            $Lock = $null
            $Deadline = [DateTime]::UtcNow.AddSeconds(60)
            while (-not $Lock) {
                try { $Lock = [IO.File]::Open((Join-Path $Root 'install.lock'), 'OpenOrCreate', 'ReadWrite', 'None') }
                catch [IO.IOException] {
                    if ([DateTime]::UtcNow -ge $Deadline) { throw 'Node preparation is busy; retry later' }
                    Start-Sleep -Seconds 1
                }
            }
            $Temp = Join-Path $Root ('.prepare-' + [Guid]::NewGuid().ToString('N') + '.exe')
            try {
                if (-not ((Test-Path $Node) -and (Test-Node $Node))) {
                    [Console]::Error.WriteLine('Preparing a private Node.js runtime...')
                    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
                    Invoke-WebRequest -UseBasicParsing -TimeoutSec 180 -Uri "https://nodejs.org/dist/v$Version/win-$Arch/node.exe" -OutFile $Temp
                    if ((Get-FileHash -Algorithm SHA256 -LiteralPath $Temp).Hash.ToLowerInvariant() -ne $Hash) { throw 'Node executable SHA-256 mismatch' }
                    if ((& $Temp --version) -ne "v$Version") { throw 'Downloaded Node cannot run on this system' }
                    Move-Item -Force -LiteralPath $Temp -Destination $Node
                }
            } finally {
                if (Test-Path $Temp) { Remove-Item -LiteralPath $Temp -Force }
                $Lock.Dispose()
            }
        }
    }
    $Start = New-Object System.Diagnostics.ProcessStartInfo
    $Start.FileName = $Node
    $AllArgs = @((Join-Path $PSScriptRoot 'meitu.cjs')) + $CliArgs
    $Start.Arguments = ($AllArgs | ForEach-Object { Quote-Arg $_ }) -join ' '
    $Start.UseShellExecute = $false
    $Start.EnvironmentVariables['PATH'] = (Split-Path $Node) + ';' + $env:PATH
    $Process = [Diagnostics.Process]::Start($Start)
    $Process.WaitForExit()
    exit $Process.ExitCode
} catch {
    [Console]::Error.WriteLine($_.Exception.Message)
    exit 2
}
