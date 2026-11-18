# Implementation Examples

## Pseudocode

```text
if dotnet is missing:
    fail(".NET SDK is required")

jb_cmd = null

# Ordered probe sequence
if jb is on PATH:
    jb_cmd = "jb"
elif global tool path exists (~/.dotnet/tools/jb or %USERPROFILE%\.dotnet\tools\jb.exe):
    jb_cmd = full path to jb
elif local manifest (.config/dotnet-tools.json) contains resharper:
    jb_cmd = "dotnet tool run jb"

# Install only if all probes failed
if jb_cmd is null:
    try global install
    if global install fails (already installed):
        try global update
    if jb is still unavailable:
        create local tool manifest if missing
        install local tool
        jb_cmd = "dotnet tool run jb"
    else:
        jb_cmd = "jb"

ceiling = find .git directory walking upward, else filesystem root

target = find nearest .sln walking upward to ceiling
if target is missing:
    target = find nearest .csproj walking upward to ceiling
if target is missing:
    fail("No .sln or .csproj found")

ensure ./artifacts exists
warn if artifacts/ is not in .gitignore
timestamp = current datetime as YYYYMMDD-HHmmss
report = ./artifacts/inspectcode-report-{timestamp}.xml

# DotSettings is auto-loaded from solution directory — no --settings needed
severity = "ERROR"  # default
if user requests elevated review:
    severity = "WARNING"

command = jb_cmd inspectcode target --no-build --output=report --format=Xml --severity=severity --no-updates

result = run command

# If full-solution run fails with exit code 4 and target is a .sln:
if result.exit_code == 4 and target is .sln:
    main_project = stem of solution filename (e.g., "GamersLabRestAPI")
    command += --project=main_project
    result = run command

    # If scoped run also fails, fall back to .csproj
    if result.exit_code != 0:
        csproj = find main_project.csproj near target
        if csproj exists:
            command = jb_cmd inspectcode csproj --no-build --output=report --format=Xml --severity=severity
            result = run command

# Default mode: errors only
parse XML: collect ERROR issues
count unique files with errors
list all error-level issues with file, line, message
append one-line footnote with warning and suggestion counts

# Elevated review mode (user explicitly requests):
also list top 25 warnings grouped by category
include suggestion count as footnote
```

## Response Patterns

Default output (errors only):

```text
Target: <solution>.sln
Report: ./artifacts/inspectcode-report-<YYYYMMDD-HHmmss>.xml
Analysis reflects files on disk, not unsaved IDE buffers.

<N> errors found, <F> files:

1. <file>:<line> — <message>
2. <file>:<line> — <message>
3. <file>:<line> — <message>

Run with elevated review to include warnings.
```

Default output (no errors):

```text
Target: <solution>.sln
Report: ./artifacts/inspectcode-report-<YYYYMMDD-HHmmss>.xml
Analysis reflects files on disk, not unsaved IDE buffers.

No errors found.
Run with elevated review to include warnings.
```

Elevated review output:

```text
Target: <solution>.sln
Report: ./artifacts/inspectcode-report-<YYYYMMDD-HHmmss>.xml
Analysis reflects files on disk, not unsaved IDE buffers.

<N> errors found, <F> files:

1. <file>:<line> — <message>
...

Top 25 warnings (of <W> total), <FW> files:

1. <file>:<line> — <message>
...

Also: <S> suggestions. Full details in the XML report.
```

Install failure:

```text
I could not make `jb` available.
I tried <command>.
Check that the .NET SDK is installed and that the .NET tools directory is on PATH.
```

