# Cross-platform Runtime rules

This reference applies when `host.runtimeVariant` is `cross-platform`; when ready, the selected `cli.implementation.kind` is `common`.

## Windows invocation

Use `cmd.exe /c` for every plugin `.cmd` entry. In Git Bash, prefix it with `MSYS_NO_PATHCONV=1`:

```text
cmd.exe /c "[cd /d <project-directory> && ]<absolute .cmd entry> [arguments]"
```

```bash
MSYS_NO_PATHCONV=1 cmd.exe /c "[cd /d <project-directory> && ]<absolute .cmd entry> [arguments]"
```

This is a command pattern: the bracketed parts are optional, not literal input. For the first check, select `<plugin>\bin\devecocli-runtime-check.cmd` directly; afterward use the exact paths returned in `launcher` or `actions`. Preserve `.cmd` and do not retry with a POSIX entry. For application commands, set the command tool's cwd to the project directory, or include `cd /d ... &&` when cwd cannot be set. Quote and escape paths and arguments for the host terminal.

## macOS and Linux invocation

Invoke POSIX plugin entries directly. Use `<plugin>/bin/devecocli-runtime-check` for the first check and the returned absolute `launcher` for subsequent CLI calls.

## CLI installation and upgrades

Use `<plugin>\bin\devecocli-install.cmd` on Windows or `<plugin>/bin/devecocli-install` on macOS and Linux, following the invocation rules above. Inspect its `--help` before private setup and follow the root Skill's authorization and upgrade rules. After installation, rerun the platform Runtime check entry above and verify `--version` with the returned launcher.

## Login

Use the platform invocation above for the returned launcher. When authentication is required, check `<launcher> auth status`. If login is needed and authorized, run `<launcher> auth login --no-prompt`; the user completes authentication in the browser. Recheck authentication before resuming the task.

## Emulator agreements

When a task requires emulator agreement acceptance, use the returned launcher with the platform invocation above. First run `<launcher> emulator license view` to display the agreements. After the user authorizes acceptance, run `<launcher> emulator license accept` without terminal prompts, then resume the blocked operation after success. Do not use the interactive `<launcher> emulator license` form in an Agent terminal.
