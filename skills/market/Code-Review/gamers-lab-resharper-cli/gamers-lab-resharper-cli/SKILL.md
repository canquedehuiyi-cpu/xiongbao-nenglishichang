---
name: resharper-inspectcode
version: 1.1.0
description: Run JetBrains ReSharper InspectCode (`jb inspectcode`) against a .NET solution or project from the terminal.
---

# ReSharper InspectCode

Install and run JetBrains ReSharper Command Line Tools (`jb inspectcode`) against a .NET solution or project, defaulting to XML output and a deterministic report path. Use when you need whole-solution ReSharper-style inspection from the terminal, a machine-readable inspection report, or must analyze current C#/.NET issues without relying on Rider UI.

Keep `SKILL.md` lean. Read only the reference file you need:

- [references/workflow-details.md](references/workflow-details.md) for assumptions, selection rules, defaults, and failure handling.
- [references/platform-commands.md](references/platform-commands.md) for exact PowerShell and Bash command forms.
- [references/implementation-examples.md](references/implementation-examples.md) for pseudocode and response patterns.
- [references/cli-reference.md](references/cli-reference.md) for the full `jb inspectcode` CLI parameter reference (offline).

## Default workflow

1. Verify the .NET SDK is available with `dotnet --version`. Stop if it is missing.
2. Locate `jb` using an ordered probe sequence: check if `jb` is on `PATH` → check the global tool path directly (`$HOME/.dotnet/tools/jb` or `%USERPROFILE%\.dotnet\tools\jb.exe`) → check for a local tool manifest. Only proceed to install if all probes fail.
3. If `jb` is not found, try `dotnet tool install -g JetBrains.ReSharper.GlobalTools`. If that fails or global tools are blocked, create a local tool manifest and install the tool locally, then invoke it with `dotnet tool run jb`.
4. Walk upward from the current working directory to find the repository root (`.git` directory). Use this as the search ceiling. If no `.git` is found, fall back to the filesystem root.
5. Within that boundary, select the nearest `*.sln`. If none exists, fall back to the nearest `*.csproj`.
6. Create `./artifacts` if needed. Generate the report filename with a timestamp to avoid collisions when multiple agents run concurrently: `./artifacts/inspectcode-report-<YYYYMMDD-HHmmss>.xml`. Use a user-specified path if provided.
7. InspectCode automatically loads `<target>.DotSettings` if it exists next to the solution (e.g., `MySolution.sln.DotSettings`). Do not pass `--settings` unless the user wants to override with a different file. The tool also respects `.editorconfig` automatically.
8. Run InspectCode with `--no-build --format=Xml --severity=ERROR --no-updates` by default. If the user requests an elevated review, use `--severity=WARNING` instead. Only omit `--severity` if the user explicitly asks for all issues. See [references/cli-reference.md](references/cli-reference.md) for all available parameters.
9. If the run fails with exit code 4 (build/analysis errors) and the target is a `.sln`, retry with `--project=<MainProjectName>` to scope inspection to the main project, excluding test and auxiliary projects. If the user specifies a project scope up front, use it directly.
10. Parse the XML report. By default, list only errors with the count of affected files. Show warning and suggestion counts as a one-line footnote. If the user requests an elevated review, also list the top 25 warnings. See [references/workflow-details.md](references/workflow-details.md) for XML structure and [references/implementation-examples.md](references/implementation-examples.md) for output format.

## Operating rules

- Prefer `.sln` over `.csproj`.
- Prefer XML over JSON unless the user explicitly requests another format.
- Prefer `--no-build` for iterative inspection.
- Be explicit when a global tool install fails and the workflow falls back to a local tool manifest.
- Stop with a clear error if no solution or project file is found.
- When targeting a `.sln`, if the full-solution run fails, retry scoped to the main project with `--project` before falling back to a single `.csproj`.
