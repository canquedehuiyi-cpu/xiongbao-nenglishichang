# Mobile Use CLI

## Invoke the loaded launcher

The launcher is `scripts/mobile-use.mjs` under the directory containing
the loaded `SKILL.md`. Derive that concrete absolute path once and pass it
directly to `node`:

```bash
node "/absolute/loaded-skill/scripts/mobile-use.mjs" inventory --json
```

Replace the illustrative path with the actual loaded Skill path. Do not declare
or export `MOBILE_USE_SKILL_DIR` or `QODER_PLUGIN_ROOT`, guess a plugin
cache path, search for another copy, or depend on the workspace cwd. If this
loaded Skill's launcher is missing, report that the installed plugin is
incomplete; do not install another copy or expose broker credentials.

In PowerShell, use the same direct form; do not route the JavaScript launcher
through `cmd.exe` or a generated `.cmd` wrapper:

```powershell
node "C:\absolute\loaded-skill\scripts\mobile-use.mjs" inventory --json
```

Every successful command writes one versioned JSON object to stdout. Failures
write one versioned JSON object to stderr. Inspect structured error codes rather
than human-readable messages:

```json
{"schemaVersion":1,"ok":false,"command":"act","error":{"code":"phone.ui-revision.stale","message":"...","retry":"observe"}}
```

Stable exit classes are `0` success, `2` invalid command/arguments, `3` missing
or stale surface/session/target, `4` revision/assertion failure, `5` unsupported
capability, `6` broker failure, and `1` other failure. Command and flag names
accept kebab-case or underscore form. Prefer `--params-json` for complete nested
arguments; use `--help` for the current flag catalog.

## Choose the smallest workflow

- Device question: use `inventory`. Its scope is `live_canvas_surfaces`; an
  unpublished platform is not evidence that its SDK or machine-wide target is
  absent.
- One semantic input: use selector-first `tap` or `long-press` so resolution and
  input share one fresh snapshot.
- Multiple interactions or verification steps: use one `run-plan` invocation.
- Explicit lifecycle, coordinate/ref input, text, keys, or swipe: use the
  lower-level lifecycle and observation commands.
- Native test: use `run-native-test` only when the selected session advertises
  `device.test.run`.
- Operational action: invoke it only when the selected target/session advertises
  the required capability.
- Swift Package preview cache diagnosis: use `swift-cache-status`; plan bounded
  cleanup with `swift-cache-prune`, which is non-mutating until `--apply` is
  explicit.

Selector-first example:

```bash
node "/absolute/loaded-skill/scripts/mobile-use.mjs" tap \
  --surface-id '<surfaceId>' --session-id '<sessionId>' \
  --selector-json '{"identifier":"<native-identifier>"}' --json
```

Replace all illustrative paths, IDs, and selectors with values from the loaded
Skill, current inventory/observation, and project contract.

Selectors accept `ref`, `identifier`, `label`, `role`, and `type` and must
resolve uniquely. Prefer stable native identifiers, then a uniquely resolved
semantic label. Native accessibility/Inspector nodes are not DOM elements.

## Run one versioned plan

An exact `surfaceId`/`sessionId` pair or a `platform` selector is required.
`policy: "existing"` is the default; `reuse-or-start` may start one uniquely
matched target. A plan-started session is stopped on completion or failure
unless `keepSession: true`.

```bash
node "/absolute/loaded-skill/scripts/mobile-use.mjs" run-plan \
  --plan-json '{
    "schemaVersion": 1,
    "session": {
      "platform": "harmony",
      "runtimeKind": "previewer",
      "policy": "reuse-or-start"
    },
    "keepSession": true,
    "evidence": {
      "screenshots": "on-failure",
      "recording": "off"
    },
    "steps": [
      {"kind":"observe"},
      {"kind":"tap","selector":{"identifier":"<native-identifier>"}},
      {"kind":"wait","condition":{"kind":"present","selector":{"label":"<ready-label>"}},"timeoutMs":5000},
      {"kind":"assert","selector":{"label":"<ready-label>"}},
      {"kind":"capture_screenshot"}
    ]
  }' --json
```

Step kinds are `observe`, `tap`, `long_press`, `wait`, `assert`, `launch_app`,
`capture_screenshot`, and `run_native_test`. Selection ambiguity, unknown steps,
invalid selectors, unsupported capabilities, and stale surfaces fail closed.
Step errors include `details.stepIndex` and `details.stepKind`.

Evidence defaults to off:

- `screenshots` is `off` or `on-failure`. Failure capture is best-effort and
  never replaces the primary step error.
- `recording` is `off` or `native`. Native recording must be advertised; a plan
  that starts it also stops it before session cleanup on success or failure.
- Use explicit `capture_screenshot` steps for named milestones or a final frame.

Read [Visual evidence](visual-evidence.md) before claiming that returned media
was visually inspected.

## Lower-level commands

| Command | Use when | Required binding |
| --- | --- | --- |
| `list-targets` | Inspect targets published by live surfaces | none |
| `start-session` | Start one exact published target | `surfaceId`, `targetId` |
| `list-sessions` | Refresh live session identity | none |
| `stop-session` | Stop one exact session | `surfaceId`, `sessionId` |
| `observe` | Obtain a current semantic snapshot | `surfaceId`, `sessionId` |
| `act` | Use ref/coordinates/text/key/swipe from a known snapshot | session plus matching `uiRevision` |
| `wait` | Bound UI readiness or stable/present/absent state | exact session and condition |
| `assert` | Check current semantic UI state | exact session and selector |

Low-level `act` supports tap/long-press refs, text, keys, and coordinate swipes.
Observation refs and revisions become stale after UI change. Re-observe and use
only the new revision/refs; never silently retry the same stale action.

`assert` proves semantic UI state only. It does not run Android instrumentation,
XCTest, ArkXTest, or Hypium and must not be reported as a native target-test
pass.

## Native and operational commands

Exact native selector forms are:

| Platform | Selector |
| --- | --- |
| Android | `com.example.ExampleTest#testLogin` |
| iOS | `Target/Class/testMethod` |
| HarmonyOS | `Suite#test` with repository-owned target/module overrides |

Use `run-native-test` only for a project-backed session advertising
`device.test.run`. A completed operation may still report `assertion_failed`,
`build_failed`, `runner_mismatch`, or `timeout`; require
`data.output.outcome == "passed"`. Read
[Installed-app verification](installed-app-verification.md) for repair-grade or
native E2E claims.

Operational commands are `restart-target`, `manage-app`, `read-logs`,
`capture-screenshot`, and `record-screen`. `manage-app uninstall` requires
explicit `confirm: true`. `record-screen` accepts `start`, `status`, and `stop`
only where `device.recording.native` is advertised.

Preserve artifact URI, digest, media type, size, source, target/session, and
revision. Never inline media bytes into CLI JSON. Capturing an artifact and
inspecting its content are separate operations.

For a local `file:` artifact, the Skill-local
`scripts/verify-artifact-receipt.mjs` helper can independently check the file's
reported byte size and SHA-256 digest. Read [Tools and
boundaries](tools.md#verify-a-local-artifact-receipt) before using it. The
helper does not open or visually inspect media.

## Swift Package preview cache

The iOS preview compiler reuses a content-addressed generated project,
SourcePackages checkout, and DerivedData across Canvas sessions. Inspect that
local cache without requiring a live device surface. These commands are macOS
only; Windows and Linux must report the host as unsupported rather than showing
an unrelated empty cache:

```bash
node "/absolute/loaded-skill/scripts/mobile-use.mjs" swift-cache-status --json
node "/absolute/loaded-skill/scripts/mobile-use.mjs" swift-cache-prune \
  --max-age-days 30 --max-size-mb 8192 --json
```

Status includes recognized pre-0.7.4 cache directories as `legacy`. Normal
pruning skips them. Add `--include-legacy` only for an explicit cleanup pass,
and close Qoder before using it together with `--apply`.

`swift-cache-prune` returns candidates only. Add `--apply` to remove inactive
entries. Use `swift-cache-clean` with
`--package-swift /absolute/path/to/Package.swift --confirm` only for an exact
broken-package cache; it refuses active preview
leases and build locks. Never delete the broad Qoder or Canvas cache root.
