# resharper-inspectcode

An agent skill that runs [JetBrains ReSharper InspectCode](https://www.jetbrains.com/help/resharper/InspectCode.html) (`jb inspectcode`) against a .NET solution or project from the terminal.

## What it does

- Installs `jb` (ReSharper Command Line Tools) if missing
- Finds the nearest `.sln` or `.csproj` within the repo boundary
- Runs `jb inspectcode` with XML output to `./artifacts/inspectcode-report.xml`
- Parses the report and summarizes errors and warnings

## Install

```bash
npx skills add Gamers-Lab/Resharper-CLI
```

## Supported agents

Works with any agent that supports the [Agent Skills](https://skills.sh/) specification, including Claude Code, Cursor, Cline, and others.

## Requirements

- [.NET SDK](https://dotnet.microsoft.com/download) on `PATH`
- A `.sln` or `.csproj` in the repository
