# HarmonyOS Native Runtime

This profile applies when the plugin and CLI run natively on a HarmonyOS PC. The [root Skill](../SKILL.md) supplies the common rules; follow returned actions and instructions under this profile, which overrides conflicting installation, login and device-execution guidance in the root Skill and implementation specifications.

## Runtime check and invocation

When creating a project on HarmonyOS PC, check whether the current directory is inside a Qoder or Qoder CN application sandbox. If it is, create the project under `/storage/Users/currentUser/Documents/<project-name>` instead. Do not generate a HiShell device script for an existing project that remains in an application sandbox, because HiShell cannot access that project path.

The plugin launchers are executable files. Invoke them directly from the actual plugin directory; never assume a Qoder or Qoder CN cache path. Do not prefix `devecocli-runtime-check`, `devecocli-install`, or `devecocli` with `sh` or `bash`, or wrap them with `timeout`, `gtimeout`, a custom watchdog, `setsid` or `nohup`. This restricts Agent-authored calls, not the supplied scripts' internal process handling.

For commands executed in Qoder, use the absolute launcher path returned by the check. For generated HiShell scripts, use `cli.hishell.command` followed by every element of `cli.hishell.args`, then the requested CLI arguments; this is the explicit exception to the root Skill launcher rule. Shell redirection such as `2>&1` is allowed, but the launcher itself must not be passed as an argument to another shell.

For Qoder calls, use the returned launcher without a `node` prefix or additional Node configuration. Use POSIX shell syntax, not PowerShell or Windows Command Prompt syntax. Prefer `find` when locating files or tools.

On `EACCES`, first check the exact invocation, working directory and host execution mode, including any added wrappers. Do not immediately change file permissions, inspect or alter SELinux labels, reinstall the toolchain, or repeat a mutating operation such as signing. Report the specific failure and obtain authorization for any necessary repair.

## CLI user directories

CLI processes inherit the application process's `HOME`; only when it is missing does the plugin use `/storage/Users/currentUser`. `DEVECO_CLI_DATA_DIR` is set to `$HOME/.config/deveco-cli`. Login data, encryption root keys and signing materials therefore follow that process home and are not automatically shared across application sandboxes. The private fallback installation follows the inherited HOME; the preferred public npm prefix is independent of HOME. Existing files are not migrated automatically.

## CLI installation paths and lookup

Prefer npm global installation with the explicit prefix `/storage/Users/currentUser/npm`. This gives Qoder and Qoder CN the shared entry `/storage/Users/currentUser/npm/bin/devecocli` without changing npm configuration; the HiShell setup below may persist Node and CLI paths in its zsh startup file. Global upgrades happen in place and do not guarantee the previous version is unchanged on failure.

If the public directory or its installation lock is denied with `EACCES` or `EPERM` before npm starts, the installer reports the denial and falls back to `$HOME/.local/share/qoder/deveco-cli/installs/<UUID>` in the current application's sandbox. Do not retry npm failures or failed package verification in another location. An explicit `DEVECO_PLUGIN_INSTALL_ROOT` selects private installation directly.

An explicit `DEVECO_PLUGIN_RUNTIME_EXECUTABLE` takes priority. Otherwise check the configured user npm bin, current client's config bin, PATH and current HOME's private installation. Private lookup reads `current.json`; never search another application's sandbox or scan UUID directories. Existing files are not migrated or deleted.

## CLI execution modes

CLI installation uses foreground `<plugin>/bin/devecocli-install`. **MUST read its terminal output through completion and verify the Runtime afterward.** Do not detach installation with `nohup` or `setsid`.

Login uses `<launcher> auth login --no-prompt`, with **Agent-owned log redirection and Qoder's tool-managed background execution**, as specified below. The host tool may withhold all command output until exit; do not assume that an active foreground command will expose the authorization URL.

## CLT asynchronous task monitoring

**Only CLT installation** uses `<plugin>/bin/devecocli-clt-install-after-browser-start`. Invoke it directly without shell backgrounding or log redirection. Use its returned log, task identifiers and `completionMarker`. A `started` response is not success. Poll the same log for the returned completion marker; only an `exitCode=0` result means success. For other codes, read and report the specific error. A missing PID without the completion marker is an unknown result, not success. Do not restart an active task or end the turn while waiting.

**MUST** read the CLT log every 30 seconds throughout download, extraction and installation. Do not wait more than 30 seconds between reads. A log-reading timeout or exit 143 does not prove installer failure; immediately read the same log again without restarting the installer. After success, rerun runtime-check.

## CLT installation

When runtime-check reports `developer-mode-required`, follow its `enable-developer-mode` action and `error.message`, then rerun runtime-check. Do not continue with toolchain or CLI installation until the check advances.

Let runtime-check discover and prepare existing CLTs. When it reports `toolchain-required`, follow the toolchain choice below; do not additionally search for or probe Node, Java or other individual tools. Do not open the download page unless the check requests it. Do not rename downloaded archives, modify the user's toolchain or permissions, or perform installation cleanup yourself.

When runtime-check reports `toolchain-required`, follow `actions` and **MUST** first ask whether the user wants DevEco Studio or Command Line Tools, unless they have already chosen. Execute only the selected branch of `choose-toolchain.options`; do not open the CLT page or start its listener before the choice. On `toolchain-invalid`, read the returned `error.message` first; do not assume that a new download is needed.

- DevEco Studio: remind the user to open AppGallery, search for **DevEco Studio**, and download and install it. Do not start the CLT installer. Rerun runtime-check after installation is complete.
- Command Line Tools: follow the existing browser and asynchronous installation workflow below.

After the user chooses Command Line Tools:

1. **MUST** open the URL in the selected branch's `open-built-in-browser` action in the application's built-in browser and wait until it is open. **MUST NOT** invoke the install script before that browser step succeeds.
2. **MUST** immediately invoke `<plugin>/bin/devecocli-clt-install-after-browser-start` directly in the same turn, without waiting for user login or download activity.
3. Only after `started` or `already-running` is returned may the Agent tell the user to download in that browser. If startup fails, report the failure instead of claiming that monitoring has started.
4. Continuously monitor the same task according to the rules above. Never end the turn after opening the browser or ask the user to return after downloading.

The supplied command handles installation and extraction. The Agent must not manually run `gunzip`, `tar`, `mv`, or another extraction workflow. The user alone operates the download controls; do not click them or download using `curl`, `wget`, or a Node HTTP client.

## CLI installation

When runtime-check reports `cli-install-required`, **MUST** invoke `<plugin>/bin/devecocli-install` in the foreground and read both output streams until it exits. Follow the foreground rules above. Do not invoke an asynchronous installer or wait for a task-result marker. On a nonzero exit, report the actual output and stop. Only after exit `0`, rerun `devecocli-runtime-check` and require `ready` before continuing.

## Configure Node, CLT and DevEco CLI for HiShell

After every ready Runtime check, **MUST execute the returned `ensure-hishell-environment` action: read its `.zshrc` file first. Compare `COMMAND_LINE_TOOL_PATH`, the CLT Node bin PATH and DevEco CLI bin PATH with the exact paths returned by the check; skip writing only when all three match. If any value is missing or different, back up an existing file and add or replace only these items, or create the file if it does not exist.** This is the HarmonyOS PC exception to the root Skill's shell-profile restriction; other platforms remain unchanged.

Use `environment.toolchain.root` and `environment.runtimeNode.executable` from runtime-check for the CLT root and Node bin. For DevEco CLI, add the public npm bin `/storage/Users/currentUser/npm/bin` to PATH. This does not install or move a CLI; private-only installations still use the explicit `cli.hishell` invocation. Write actual absolute paths; expand application-sandbox aliases to the current application's physical HOME before writing. Do not put `/data/storage/el2/base/files/home/...` into the shared configuration or search another application's sandbox.

Read the file before deciding whether to edit; a missing file means configuration is missing and should be created. Other read errors must be reported rather than treated as an empty file. Existing configuration does not need rewriting. Preserve existing values and unrelated contents; if configuration is missing, back up first and add only missing items without marker comments. Configure **only `COMMAND_LINE_TOOL_PATH`, the Node bin and DevEco CLI bin on PATH**; do not change HOME, login/signing directories, npm's prefix, Java settings or system-wide profiles. Replace the placeholders below with actual paths:

```sh
export COMMAND_LINE_TOOL_PATH='<absolute CLT root>'
case ":$PATH:" in
  *":<absolute Node bin>:"*) ;;
  *) export PATH="<absolute Node bin>:$PATH" ;;
esac
case ":$PATH:" in
  *":/storage/Users/currentUser/npm/bin:"*) ;;
  *) export PATH="/storage/Users/currentUser/npm/bin:$PATH" ;;
esac
```

This step only reads configuration and writes missing items. **Do not probe HiShell's shell/HOME/ZDOTDIR, run zsh syntax checks, open a new terminal, run Node/CLI version checks or build a project as part of this step.** Report the configured file and paths without claiming that a new HiShell has been verified. On write failure, report the exact error; do not change permissions or fall back to editing Qoder's sandbox profile. Preserve the backup for rollback.

## Agent login flow

First run `<launcher> auth status`. If login is needed and authorized:

1. **BEFORE launching login, the Agent MUST choose and record a unique absolute log path inside the current application's private HOME and create its parent directory.** Prepare the path in a separate short tool call if needed. Never learn the path from the login command's output; Qoder may not return that output until login ends.
2. **MUST explicitly redirect BOTH stdout and stderr to that known file and enable the command tool's background-execution option (`run_in_background: true` in Qoder).** Do not run login as a blocking foreground tool call. The launcher itself remains a normal child process; do not add `nohup`, `setsid` or shell `&`.
3. **READ THE KNOWN LOG FILE IMMEDIATELY in another tool call, within 2 seconds. DO NOT WAIT FOR COMMAND COMPLETION, TOOL OUTPUT, A SESSION RESULT OR A “LOG READY” SIGNAL.** Use bounded reads such as `cat` or `tail -n`, never `tail -f` or a wait loop that prevents opening the browser.
4. As soon as the exact authorization URL appears in the file, use the host's built-in browser capability when available. Never construct or rewrite the URL, invoke `aa -U`, or use an external browser. If the host cannot open the built-in browser, return the exact URL for the user to open. If no URL is present yet, reread the same file every 10 seconds. Continue reading during authentication; do not end the turn or restart the active login.
5. Only the final exit marker `0` means the command succeeded. For nonzero codes, report the logged error. After completion, collect the host-managed task's result and run `<launcher> auth status`; continue only when logged in. A missing marker, quiet file or missing PID is not success.

Run this command structure with the tool's **background-execution option enabled**, replacing both paths before invocation:

```sh
umask 077
(
  login_code=0
  "<absolute launcher>" auth login --no-prompt || login_code=$?
  printf '\n[devecocli-login-result] exitCode=%s\n' "$login_code"
  exit "$login_code"
) > "<Agent-chosen absolute log path>" 2>&1
```

The Agent owns this redirection and completion marker. The plugin does not announce or manage a login log. **START THE HOST-MANAGED TASK, THEN READ THE FILE; NEVER WAIT FOR LOGIN TO RETURN BEFORE READING IT.**

## Device commands: hand off to HiShell

**MANDATORY: apply this handoff EVERY TIME a task requires device access, including follow-up queries and read-only operations. MUST NOT execute commands requiring device access from Qoder.** This covers deployment and launch, device queries and file transfers, device logs, debugging and UI inspection. Run preparation that does not access a device, such as building and signing, in Qoder. Use the selected implementation specification to determine available commands and flags; use direct system installation and launch only in the local deployment flow below.

On HarmonyOS PC, run signing and confirm it succeeds before the build. Then ask whether to deploy to this PC, multiple-device Previewer, or both. When the user chooses any deployment target, invoke the fixed [shared-signing script](../assets/prepare-shared-signing.sh) before preparing the deployment handoff. For Previewer, ask for the supported product names. Reuse an explicit choice already made in the conversation. For other device operations, confirm the necessary target before preparing the command. Do not run device discovery from Qoder to fill in the target.

Once the target is confirmed:

1. Reuse an existing script under the project's `.hvigor/deveco-cli/` when its project path, runtime paths, command arguments and deployment target still match. Otherwise create a complete task script from [the local deployment template](../assets/hishell-deploy-local.sh.template) for installing and launching on this PC, or [the general HiShell task template](../assets/hishell-task.sh.template) for other commands at a unique absolute path under the project's `.hvigor/deveco-cli/` directory. Write `environment.toolchain.root`, the parent directory of `environment.runtimeNode.executable`, the project's absolute directory, the `cli.hishell` invocation returned by runtime-check and the selected command's actual arguments into the script. Keep the template's subshell and its `COMMAND_LINE_TOOL_PATH` and Node PATH exports so these settings apply only to this execution. Replace every placeholder; remove unused example arguments. Use the returned CLI invocation directly: do not search npm directories, inspect symlinks, retry alternate installations, or run additional version checks. Replace the entire `<launcher invocation>` placeholder with the separately shell-quoted `cli.hishell.command` and all `cli.hishell.args` before appending CLI arguments. Never pass a JavaScript entry to `sh`. If `cli.hishell` is missing, report a plugin configuration error. These resolved paths do not prove HiShell access; report any actual access error without searching another installation. Do not execute the script from Qoder.
2. Open HiShell by executing **only** `aa start -a EntryAbility -b com.huawei.hmos.hishell` from Qoder. This is the sole exception for opening the terminal; it does not deploy the application or execute the prepared command. If opening fails, report the error and ask the user to open HiShell manually.
3. Display only the complete script invocation in a copyable shell block and tell the user to paste it into HiShell and press Enter. The user must not need to enter project paths, target names or CLI arguments themselves. Do not claim the command has run or succeeded. Do not send terminal keystrokes or try to execute it through Qoder.

Use this structure, replacing every placeholder before displaying it:

```sh
sh '<absolute generated task script>'
```

Quote paths and arguments for HiShell's zsh, including spaces and embedded quotes. Fill the template's Node/CLT exports with the actual paths returned by runtime-check, even when HiShell already has persistent configuration. Keep these exports inside the subshell; do not add other environment changes. Preserve its exit status and terminal output. Use a unique file for each handoff so a later task does not overwrite a command the user has not run yet.

For installing and launching an already built application on this PC, **MUST preserve the local template's mode/port branching. NEVER scan ports, select the first listed device, hide command errors, or fall back after a failed wireless connection or CLI operation.** Fill its HDC executable as `<environment.toolchain.root>/sdk/default/openharmony/toolchains/hdc`, then add the `cli.hishell` invocation and build selections. Resolve the exact signed HAP, bundleName and launch Ability from the selected build outputs and project JSON5 configuration before generating the script; do not guess EntryAbility or select the first HAP. Include all required HAPs using installation arguments supported by the actual system.

The local script **MUST first run `bm install -p <signed HAP>`, then `aa start -a <ability> -b <bundleName>` only if installation succeeds. If both succeed, exit immediately without reading mode/port or printing wireless-debugging notices.** Only after installation or launch fails, read `param get persist.hdc.mode` in HiShell. Preserve parameter-read failures, then trim leading/trailing whitespace (including carriage returns) from mode and port. Successful empty mode output stops with the original local failure code and `本机安装或启动失败，且无线调试未开启。请打开设置界面，搜索并开启无线调试。`. Mode `tcp` requires a valid port from `param get persist.hdc.port`, an explicit connection to `127.0.0.1:<port>`, then CLI `run --skip-build` with that target and the build's module/product/build-mode selections. Other modes, failed parameter reads, invalid ports, failed connections or CLI operations stop with the actual error. Do not retry bm/aa after this fallback. Keep command output and exit status; the final CLI result determines success when fallback is used. This order applies only to local installation and launch, not Previewer or other device commands.

For multiple-device Previewer, use the [Previewer script template](../assets/hishell-preview.sh.template) to create the HiShell script. Do not write a replacement Previewer script. DevEco Studio must be running. The current multi-preview flow rebuilds for application clones even with `--skip-build`; explain this instead of promising to reuse the existing package. If the user chooses both targets, combine the Previewer script with the local deployment child script using the structure below. Invoke each child with `sh`; never source or concatenate their bodies. The local child's `exit 0` must return to the combined entry, while a nonzero exit must stop it before Previewer runs. Replace both paths before writing the entry script:

```sh
#!/bin/sh
set -eu
sh '<absolute local deployment script>'
sh '<absolute Previewer script>'
```

The user copies only the invocation of this combined entry script into HiShell.

Apply the same handoff to any other supported command requiring device access, preserving its actual flags and target semantics. The user runs it in HiShell and can return its output for analysis. Do not start device/log/UI probes from Qoder afterward, or infer success from opening HiShell or displaying the command.

## HarmonyOS-native product differences

- The `emulator` command is unavailable. Never suggest emulator creation, startup, images or emulator agreements.
- `check` provides `lint`; do not use the cross-platform-only `check arkts` or `check compat` forms.
- Device operations must follow the HiShell handoff above. Do not invoke `device`, `hdc` or `hilog` from Qoder; use supported CLI device commands in the command prepared for HiShell.
- `ui` provides `layout`, `window`, `screenshot`, `click`, `doubleclick`, `longclick`, `swipe`, `fling`, `drag`, `dircfling` and `text`. Screen recording is unavailable.
- `docs` provides `search`, `read` and `catalog`; `docs update` is unavailable.
- `create` does not accept `--device-types` in this profile.
- DevEco Studio may be installed and used on HarmonyOS PC; the native profile does not imply a Command Line Tools-only environment.
