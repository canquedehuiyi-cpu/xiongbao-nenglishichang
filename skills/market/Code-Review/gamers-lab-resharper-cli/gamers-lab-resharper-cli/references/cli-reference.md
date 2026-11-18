# InspectCode CLI Reference

This is the offline reference for `jb inspectcode` command-line parameters. Source: JetBrains documentation (November 2025).

## Important: Default Output Format

Starting from version 2024.1, the default output format is SARIF (`.json`), not XML. To get XML output, you must explicitly pass `--format=Xml` (or `-f=xml`). The skill always passes this flag.

## Severity Levels

The `--severity` (`-e`) parameter controls the minimum reported severity. Levels from least to most severe:

`INFO` | `HINT` | `SUGGESTION` | `WARNING` | `ERROR`

By default (without `--severity`), InspectCode reports `SUGGESTION` and higher. The skill passes `--severity=ERROR` by default to keep output focused.

Note: InspectCode never includes `HINT`-level issues in its output, even when running without `--severity`.

## Inspection Parameters

| Parameter | Description |
|---|---|
| `--project` | Analyze specific project(s) instead of the whole solution. Accepts a project name or wildcard (e.g., `--project=*Billing`). |
| `--include` | File masks defining which files to include in the report. Ant-style wildcards supported. |
| `--exclude` | File masks defining which files to exclude from the report. Takes priority over `--include` when both match. |
| `--severity` (`-e`) | Minimum severity level to report: `INFO`, `HINT`, `SUGGESTION`, `WARNING`, `ERROR`. |
| `--swea` / `--no-swea` | Explicitly enable or disable solution-wide analysis. |
| `--dumpIssuesTypes` (`-it`) | Dump all existing code inspections to output. Use without a solution argument. |

### Ant-Style Wildcards (for `--include`/`--exclude`)

- `?` — single character (not directory separator)
- `*` — zero or more characters (not directory separator)
- `**` — any number of characters including directory separators
- `/` or `\` — directory separator (OS-independent)

Example: `**Test?\**.*` matches `C:\Projects\MyTestX\data\file.txt` but not `C:\Projects\Test\data\file.txt`.

Separate multiple patterns with `;` or repeat the parameter.

Note: Excluding files does not improve performance. InspectCode still analyzes all files and applies exclusions only at the reporting stage.

## MSBuild Parameters

| Parameter | Description |
|---|---|
| `--build` / `--no-build` | Whether to build the solution before analysis. Default: builds the solution. |
| `--target` | MSBuild target to execute before analysis (e.g., `Restore`). Ignored if `--no-build` is set. |
| `--properties` | Override MSBuild properties. Use `--properties:prop=val` or `--properties:p1=v1;p2=v2`. |
| `--toolset` | Specify exact MSBuild version (e.g., `--toolset=17.0`). |
| `--toolset-path` | Full path to a custom MSBuild executable. |
| `--dotnetcore` | Path to specific .NET installation. Use without arguments to ignore .NET Core. |
| `--dotnetcoresdk` | Specific .NET SDK version to use (e.g., `--dotnetcoresdk=8.0.100`). |

### When `--no-build` Fails

If your solution uses **source generators**, InspectCode needs to build first to dump generated files to disk. When `--no-build` causes analysis failures, retry with `--build` or without the `--no-build` flag.

### Platform/Configuration Mismatches

If you get errors like `Can't resolve reference XXX`, check the build configuration. Fix with:

```
--properties:Platform=x64;Configuration=Debug
```

## Output Parameters

| Parameter | Description |
|---|---|
| `--output` (`-o`) | Path to the output file. |
| `--format` (`-f`) | Output format: `Html`, `Text`, `Xml`, or SARIF (default). Multiple formats: `-f=Html;Xml` or repeat the flag. |
| `--absolute-paths` (`-a`) | Use absolute paths in the report instead of paths relative to the solution. |

## Performance Parameters

| Parameter | Description |
|---|---|
| `--jobs` (`-j`) | Limit the number of parallel threads. Default: uses all available cores. |
| `--no-updates` | Skip checking for tool updates on each run. Faster startup. |
| `--caches-home` | Custom cache directory. Useful for SSD or centralized build data. |

## Settings Parameters

| Parameter | Description |
|---|---|
| `--settings` | Path to a `.DotSettings` file that overrides all other settings. |
| `--disable-settings-layers` (`-dsl`) | Disable specific layers: `GlobalAll`, `GlobalPerProduct`, `SolutionShared`, `SolutionPersonal`. |
| `--no-buildin-settings` | Suppress all settings from global, solution, and project layers. |

### DotSettings Auto-Loading

InspectCode **automatically** loads `SolutionName.sln.DotSettings` from the solution directory if it exists. You do NOT need to pass `--settings` for this. Only use `--settings` to point to a different/override file.

Settings the tool picks up from `.DotSettings`:
- Inspection severity levels
- Solution-wide analysis toggle
- Naming rules
- Excluded files, folders, and file masks
- Generated code regions
- Cache location
- Target languages

### Disabling Roslyn Analyzers

To skip Roslyn analyzers (faster runs, fewer noise issues):

```
--properties:RunAnalyzers=false
```

Or configure in the solution's `.DotSettings` file:

```xml
<s:Boolean x:Key="/Default/CodeInspection/Roslyn/RoslynEnabled/@EntryValue">False</s:Boolean>
```

## EditorConfig Support

InspectCode respects `.editorconfig` files in the project tree. It walks up parent directories until it finds `root=true`. EditorConfig settings override `.DotSettings` severity levels.

Format for inspection properties:

```
[inspection_property]=[error | warning | suggestion | hint | none]
```

Examples:

```editorconfig
resharper_possible_null_reference_exception_highlighting=error
resharper_redundant_argument_default_value_highlighting=none
```

## Diagnostic Parameters

| Parameter | Description |
|---|---|
| `--debug` (`-d`) | Add execution details to output. Useful for support requests. |
| `--verbosity` | Console output level: `OFF`, `FATAL`, `ERROR`, `WARN`, `INFO`, `VERBOSE`, `TRACE`. Default: `ERROR`. |
| `--LogLevel` | Log file detail level (same values as `--verbosity`). |
| `--LogFile` | Absolute path to a log file for InspectCode messages. |
| `--LogFolder` | Absolute path to a directory for logs from InspectCode, MSBuild, and Roslyn. |
| `--version` (`-v`) | Display tool version and exit. |

## Plugin Support

| Parameter | Description |
|---|---|
| `--eXtensions` (`-x`) | Install and enable plugins by their JetBrains Marketplace ID (e.g., `-x=StyleCop.StyleCop`). Separate multiple with `;`. |
| `--source` | Custom package source directory for plugin `.nupkg` files. |
