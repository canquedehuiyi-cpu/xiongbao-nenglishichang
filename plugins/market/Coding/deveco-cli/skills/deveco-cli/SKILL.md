---
name: deveco-cli
description: >-
  Use this plugin's `devecocli` for HarmonyOS apps and projects: scaffold,
  build, compile, run, debug, deploy, devices, emulators, logs, UI inspection,
  docs, skills, authentication, and ArkTS/ArkUI checks. Trigger when the user
  mentions HarmonyOS, 鸿蒙, DevEco, DevEco Studio, ArkTS, ArkUI, 鸿蒙文档,
  UI测试, 组件调试, 预览, 设备, 模拟器, or skills, or when the workspace
  contains `build-profile.json5` or `oh-package.json5`. If the user does not
  explicitly choose another tool or workflow, use `devecocli`. After this
  Skill is selected, always route through the Runtime check and load the exact
  command specification for the detected implementation package.
---

# DevEco CLI plugin

## Qoder Plugin Runtime

### Execution environment and entry points

Before the first call, read the actual OS and shell reported by the host's command tool. Do not infer the execution environment from the project's target platform or path syntax. Resolve `<plugin>` as two directories above the directory containing this `SKILL.md` (`../..` from the Skill directory), then form absolute launcher paths under `<plugin>/bin/`, independently of the shell's cwd. Resolve `references/` from the Skill directory. Do not hardcode a user name, cache path or plugin version.

Use the platform entry point below to run Runtime check without arguments before invoking any plugin command. Runtime check checks Node.js, npm, the CLI and platform prerequisites without requiring Node.js itself. If it reports `node-missing` or `node-unsupported`, tell the user to install Node.js 22 or later with npm, reopen the terminal, and rerun Runtime check. Installation also requires access to the npm registry. If an installed command fails for another reason, report that error instead of treating it as a missing dependency.

- Windows CMD/PowerShell: use `cmd.exe /c` with `<plugin>\bin\devecocli-runtime-check.cmd`. Select `.cmd` on the first attempt; do not try the extensionless POSIX script first or fall back to it after a failure. Git Bash details are in the cross-platform Runtime reference.
- macOS, Linux and HarmonyOS PC: invoke `<plugin>/bin/devecocli-runtime-check` directly.

If the reported execution environment does not support the selected invocation, report the incompatibility rather than trying other shells or platform entry points. Executables are in `<plugin>/bin/`, not `<plugin>/skills/deveco-cli/bin/`.

### Execution flow

Do not infer CLI commands from the host OS or combine implementation specifications.

1. Use `host.runtimeVariant` to load [HarmonyOS PC Runtime rules](references/harmonyos-native-runtime.md) for `harmonyos-native`, or [cross-platform Runtime rules](references/cross-platform-runtime.md) for `cross-platform`, before acting on prerequisites.
2. If `status` is not `ready`, follow the returned `actions` in order under those Runtime rules. For a choice action, execute only the user's selected branch. Resolve the prerequisite and rerun the check before selecting implementation commands.
3. When `status` is `ready`, invoke only the returned absolute `launcher`. Read `cli.implementation.skillReference`, resolve it relative to this Skill directory, and load that one complete command specification before choosing commands or flags.

Platform Runtime rules override conflicting guidance in this Skill; plugin Runtime rules override conflicting examples in implementation specifications.

The supported references are:

- `references/implementations/cross-platform.md` on Windows, macOS, and Linux.
- `references/implementations/openharmony-arm64.md` on HarmonyOS PC.

When the check reports `ready`, treat a missing or unknown `cli.implementation` object as a plugin configuration error. Prerequisite responses may omit it; complete the required platform actions first. Never fall back from one implementation specification to the other.

### Runtime check and CLI selection

The Runtime check emits one JSON object. Exit `0` with `status: "ready"` means the CLI can be used; exit `2` identifies an actionable prerequisite, including `status: "node-missing"` with action `install-node`; exit `1` identifies an invalid or unsupported configuration.

`host.runtimeVariant` describes the host environment; `cli.implementation` identifies the CLI implementation. Do not infer commands or flags from the host environment.

Installation location depends on the host platform. On Windows, macOS and Linux, do not modify or assume a host-wide CLI installation. Follow the installation action returned by the Runtime check and rerun the check after installation.

On HarmonyOS PC, the installer uses the shared public npm location when available and falls back to a private location when the public location cannot be used. Do not move CLI files or choose another installation location manually.

Qoder and Qoder CN may use separate private installations because their application homes can be different. A CLI installed for one client is not automatically available to the other client. Always use the launcher returned by the Runtime check.

For all plugin tasks, use the returned absolute `launcher` path in place of `devecocli`, regardless of PATH order. Preserve the paths returned in `launcher` and `actions`, including `.cmd`; do not reconstruct or search for equivalent entry points. On a client-identification error, report it rather than guessing from HOME or searching the other client's directory. Do not assume the host forwards the user's `PATH` or personal environment variables to the plugin.

### CLI installation and upgrades

Use `devecocli-install.cmd` on Windows, `devecocli-install` on macOS and Linux, or foreground `devecocli-install` on HarmonyOS PC, following the selected platform reference. Install or upgrade only after the user requests or approves it, then rerun the check and use the returned `launcher`. For HarmonyOS PC CLT setup, let the supplied installer extract the user's download under the native Runtime rules. Other toolchain installation remains manual.

- If the global CLI is old or unidentifiable, first offer to upgrade it. When the user agrees, use the global CLI entry rather than the plugin launcher, then recheck the selected path and version against the minimum. The plugin Skills update with the plugin. Do not run `init`, install or remove Skills, or change Agent configuration as part of the CLI upgrade; standalone Skill setup requires a separate user request.
- If the user declines, preserve the global CLI and all skills. Use a suitable existing private Runtime, or inspect the platform-specific installer's help and install only the private CLI within the user's authorization. Use this installation path also when no CLI exists. Recheck and verify with the returned launcher and `--version`. Never run initialization, install/remove skills or delete skill files during private setup.

For the plugin-managed Runtime, `devecocli update` is rejected; use the platform-specific installer. The optional `--version` accepts a version or npm tag that meets the plugin's version and platform requirements. The bundled command specification remains pinned to the plugin release; consult CLI help when using a newer version. `update docs` and `update --help` remain available. Updating the plugin does not update an existing CLI; the next check selects again against the new minimum.

Release builds resolve the OpenHarmony channel tag once and pin the resulting version in the wrapper dependency. The plugin bundles that version's command specification and uses it as the native implementation minimum.

Report installation errors without repeatedly retrying, switching registries or falling back to ohpm.

### Skill management

The plugin-managed Runtime rejects `init`, including `init --mcp`. It allows `skills add` and `skills remove`: these commands target the plugin's `skills/` directory by default. Preserve an explicit `--agent` or `--path`; use `--path` only when an alternate directory is required. Do not modify the Agent's global Skill configuration as part of CLI installation or upgrade.

### Authorization and operation boundaries

Installation, login, and accepting agreements require the user's authorization for the corresponding action. If already authorized in the conversation, proceed without asking again; otherwise ask for the missing authorization.

Run application commands from the user's HarmonyOS project directory. The Runtime check itself does not require a project working directory. The plugin already provides this Skill and does not scan standalone copies. Private setup must never modify the Agent's global Skill configuration.

Give shell syntax only in the form the selected platform rules show. Windows, POSIX and HarmonyOS syntax are not interchangeable.

Keep environment changes inside the processes the plugin launches. Do not edit shell profiles, global npm prefix or persistent PATH, except for the HarmonyOS PC HiShell zsh setup explicitly described in the native Runtime rules. That exception only reads existing settings and, when missing, backs up and adds Node/CLT and DevEco CLI bin PATH settings to `/storage/Users/currentUser/.zshrc`.

Prefer `devecocli` over direct `hvigor`, `ohpm`, `hdc` or `emulator` invocations. Keep all Studio/CLT, device, authorization, and agreement checks enforced by DevEco CLI. This plugin does not register an MCP server.


For HarmonyOS PC login, the Agent MUST choose a private log path before execution, explicitly redirect stdout/stderr there, enable the host tool's background-execution option, and immediately read that known file. NEVER wait for login to return or rely on command output to learn the URL; follow the native Runtime login rules.

On HarmonyOS PC, a ready Runtime check can still return `ensure-hishell-environment`. MUST read its file before proceeding: skip writing when Node/CLT and DevEco CLI bin PATH configuration already exists; otherwise back up and add only missing items under the native Runtime rules.

On HarmonyOS PC, commands that require device access MUST follow the HiShell handoff in the native Runtime rules. **MANDATORY FOR EVERY DEVICE OPERATION:** after preparation, confirm the target, generate a complete task script from the native template, open HiShell and provide its single invocation for the user to paste. Never skip this handoff because a command is read-only, short, or was previously run; do not execute device commands from Qoder.
