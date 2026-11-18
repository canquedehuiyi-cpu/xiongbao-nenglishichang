# Workflow Details

## Prerequisites

- Require `dotnet` on `PATH`.
- Expect the repository to contain either a `.sln` or a `.csproj`.
- Expect permission to install `JetBrains.ReSharper.GlobalTools` globally or inside a local tool manifest.

## Target Selection

First, walk upward from the current working directory to find a `.git` directory. If found, use that directory as the search ceiling. If no `.git` is found, fall back to the filesystem root as the ceiling.

Then, walk upward from the current working directory to the ceiling, checking each directory level one at a time. Do not perform a recursive search across the entire repo.

At each directory level:

1. Check for `*.sln` files in that directory only.
2. If multiple solution files exist, prefer one whose file name matches the current folder name.
3. If there is still a tie, choose the first lexicographic match.
4. If no solution exists at that level, check for `*.csproj` files in that directory only.
5. Move up one level and repeat.

If nothing is found by the time the ceiling is reached, stop and report that no `.sln` or `.csproj` was found.

## Defaults

- Output format: `Xml`
- Severity filter: `--severity=ERROR` (default), `--severity=WARNING` (elevated review)
- Build behavior: `--no-build`
- Report path: `./artifacts/inspectcode-report-<YYYYMMDD-HHmmss>.xml` (timestamped at run start to avoid collisions)
- Target preference: nearest `.sln`, then nearest `.csproj`
- Project scoping: `--project=<name>` to limit inspection to specific projects within a solution

Use these defaults unless the user explicitly asks for a different format, output path, or build behavior.

## Why These Defaults

- XML is more stable for downstream parsing across environments.
- `--severity=ERROR` keeps the report small and avoids wasting context on thousands of warnings and suggestions that aren't actionable in a default run.
- `--no-build` is faster for iterative inspections.
- A timestamped report path prevents collisions when multiple agents run concurrently while keeping reports in a predictable directory.

## jb Probe Sequence

Before installing anything, locate `jb` using this ordered probe sequence:

1. **PATH check** — run `Get-Command jb` (Windows) or `command -v jb` (macOS/Linux). If found, use it.
2. **Direct global tool path** — check the file directly:
   - Windows: `$env:USERPROFILE\.dotnet\tools\jb.exe`
   - macOS/Linux: `$HOME/.dotnet/tools/jb`
   If the file exists, invoke it by full path. This avoids triggering `dotnet tool list -g` which can cause first-time-use writes in sandboxed environments.
3. **Local tool manifest** — check if a `.config/dotnet-tools.json` exists in the repo and contains `jetbrains.resharper.globaltools`. If so, use `dotnet tool run jb`.
4. **Install** — only if all probes fail, proceed to install (see Failure Handling below).

## Failure Handling

If `dotnet` is missing:

- Stop and tell the user the .NET SDK is required.

If `jb` is not found after the probe sequence:

1. Try `dotnet tool install -g JetBrains.ReSharper.GlobalTools`.
2. If that fails because the tool is already installed, run `dotnet tool update -g JetBrains.ReSharper.GlobalTools` instead.
3. If `jb` is still not available after the global install, create a local tool manifest with `dotnet new tool-manifest`.
4. Install the tool locally with `dotnet tool install JetBrains.ReSharper.GlobalTools`.
5. Invoke the tool through `dotnet tool run jb`.

If installation fails:

- Report whether the global install or local manifest path was attempted.
- Include the exact command that failed.
- Suggest checking `PATH` and the .NET SDK installation.

## Sandbox Note

Avoid using `dotnet tool list -g` as a presence check. In restricted or sandboxed environments, this command can trigger first-time-use writes to the global tools directory and fail. Prefer checking the file path directly (see jb Probe Sequence above).

If inspection fails:

- Check the exit code. Exit code 4 indicates build or analysis errors within the solution.
- If the target is a `.sln` and the run failed with exit code 4, retry with `--project=<MainProjectName>` to scope inspection to the main shipping project. The main project name is typically the solution file name without the extension (e.g., `GamersLabRestAPI.sln` → `--project=GamersLabRestAPI`). This excludes test projects, generators, and other auxiliary projects that may have compilation errors.
- If the user specified a project scope and it still fails, report the target path and suggest retrying without `--no-build`.
- If the scoped retry also fails, fall back to targeting a single `.csproj` for the main project.
- Report whether `--no-build` was used.
- Suggest retrying without `--no-build` for source-generator-heavy solutions.

### Fallback chain for `.sln` failures

1. Full solution: `jb inspectcode MySolution.sln --no-build --severity=ERROR --no-updates`
2. Scoped to main project: `jb inspectcode MySolution.sln --no-build --severity=ERROR --no-updates --project=MainProject`
3. Single project file: `jb inspectcode MainProject.csproj --no-build --severity=ERROR --no-updates`

## DotSettings and EditorConfig

InspectCode automatically respects `.editorconfig` files in the project tree (walks up parent directories until `root=true`). EditorConfig severity settings override `.DotSettings` severity levels.

InspectCode **automatically loads** `SolutionName.sln.DotSettings` from the solution directory if it exists. Do not pass `--settings` for this — it happens by default. Only use `--settings=<path>` if the user wants to override with a different `.DotSettings` file.

Settings picked up from `.DotSettings`: inspection severity levels, solution-wide analysis toggle, naming rules, excluded files/folders/masks, generated code regions, cache location, and target languages.

To disable Roslyn analyzers for faster/quieter runs, use `--properties:RunAnalyzers=false`.

## Artifacts and .gitignore

After creating the `./artifacts` directory, check whether `artifacts/` is already listed in the repository's `.gitignore`. If it is not, warn the user that the report directory is not gitignored and suggest adding it.

## XML Report Structure

The InspectCode XML output has this structure:

```xml
<Report>
  <IssueTypes>
    <IssueType Id="..." Category="..." Description="..." Severity="ERROR|WARNING|SUGGESTION|HINT" />
  </IssueTypes>
  <Issues>
    <Project Name="...">
      <Issue TypeId="..." File="..." Offset="..." Line="..." Message="..." />
    </Project>
  </Issues>
</Report>
```

To summarize results, read the `Severity` attribute from each `<IssueType>`, then match `<Issue>` elements to their type by `TypeId`.

## Result Handling

There are two output modes:

### Default mode (errors only)

- Confirm the target and report file path.
- Parse the XML and collect all `ERROR`-severity issues.
- Report the error count and the number of unique files affected (e.g., "6 errors found, 5 files").
- List all error-level issues numbered, with file path, line number, and message.
- Append a one-line note: "Run with elevated review to include warnings."
- State that the analysis reflects files on disk, not unsaved IDE buffers.
- If parsing fails, tell the user where the report was written and suggest opening it manually.

### Elevated review mode

Triggered when the user explicitly asks for a deeper review, full analysis, or to include warnings.

- Include everything from the default mode.
- Additionally list the top 25 warnings (numbered, with file, line, message), noting how many total warnings exist and how many files are affected.
- Append suggestion count as a footnote, directing the user to the XML report for the full list.
