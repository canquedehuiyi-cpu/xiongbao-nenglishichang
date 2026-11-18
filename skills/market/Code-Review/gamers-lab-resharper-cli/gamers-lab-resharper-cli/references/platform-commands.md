# Platform Commands

## Windows PowerShell

Check prerequisites:

```powershell
dotnet --version
```

Probe for `jb` (ordered):

```powershell
# 1. PATH check
Get-Command jb -ErrorAction SilentlyContinue

# 2. Direct global tool path check
Test-Path "$env:USERPROFILE\.dotnet\tools\jb.exe"

# 3. Local manifest check
Test-Path ".config\dotnet-tools.json"
```

If `jb.exe` exists at the global tool path but is not on PATH, invoke it directly:

```powershell
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
& "$env:USERPROFILE\.dotnet\tools\jb.exe" inspectcode .\MySolution.sln --no-build --output=".\artifacts\inspectcode-report-$timestamp.xml" --format=Xml --severity=ERROR --no-updates
```

Install globally (only if all probes fail):

```powershell
dotnet tool install -g JetBrains.ReSharper.GlobalTools
```

Create a local manifest and install locally:

```powershell
dotnet new tool-manifest
dotnet tool install JetBrains.ReSharper.GlobalTools
```

Run InspectCode with a global install:

```powershell
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
jb inspectcode .\MySolution.sln --no-build --output=".\artifacts\inspectcode-report-$timestamp.xml" --format=Xml --severity=ERROR --no-updates
```

Run InspectCode with a local tool manifest:

```powershell
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
dotnet tool run jb inspectcode .\MySolution.sln --no-build --output=".\artifacts\inspectcode-report-$timestamp.xml" --format=Xml --severity=ERROR --no-updates
```

## macOS / Linux

Check prerequisites:

```bash
dotnet --version
```

Probe for `jb` (ordered):

```bash
# 1. PATH check
command -v jb

# 2. Direct global tool path check
test -f "$HOME/.dotnet/tools/jb"

# 3. Local manifest check
test -f ".config/dotnet-tools.json"
```

If `jb` exists at the global tool path but is not on PATH, invoke it directly:

```bash
"$HOME/.dotnet/tools/jb" inspectcode ./MySolution.sln --no-build --output=./artifacts/inspectcode-report-$(date +%Y%m%d-%H%M%S).xml --format=Xml --severity=ERROR --no-updates
```

Install globally (only if all probes fail):

```bash
dotnet tool install -g JetBrains.ReSharper.GlobalTools
```

Create a local manifest and install locally:

```bash
dotnet new tool-manifest
dotnet tool install JetBrains.ReSharper.GlobalTools
```

Run InspectCode with a global install:

```bash
jb inspectcode ./MySolution.sln --no-build --output=./artifacts/inspectcode-report-$(date +%Y%m%d-%H%M%S).xml --format=Xml --severity=ERROR --no-updates
```

Run InspectCode with a local tool manifest:

```bash
dotnet tool run jb inspectcode ./MySolution.sln --no-build --output=./artifacts/inspectcode-report-$(date +%Y%m%d-%H%M%S).xml --format=Xml --severity=ERROR --no-updates
```

## Project Scoping

When a full-solution run fails (exit code 4), retry scoped to the main project:

```powershell
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
jb inspectcode .\MySolution.sln --no-build --project=MySolution --output=".\artifacts\inspectcode-report-$timestamp.xml" --format=Xml --severity=ERROR --no-updates
```

```bash
jb inspectcode ./MySolution.sln --no-build --project=MySolution --output=./artifacts/inspectcode-report-$(date +%Y%m%d-%H%M%S).xml --format=Xml --severity=ERROR --no-updates
```

The `--project` flag accepts a project name or wildcard pattern (e.g., `--project=MyApp*`). It filters which projects within the solution get inspected.

## PATH Recovery

If `jb` still is not available after a global install, add the .NET tools directory to `PATH`.

Typical path on Linux and macOS:

```bash
export PATH="$PATH:$HOME/.dotnet/tools"
```

Typical path on Windows:

```text
%USERPROFILE%\.dotnet\tools
```
