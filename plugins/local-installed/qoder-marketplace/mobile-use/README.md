# Mobile Use

Mobile Use makes Android, HarmonyOS, and iOS projects first-class Qoder Canvas
formats under the `mobile-use` plugin identity.

The plugin provides three project viewers, their host sidecars, the shared
browser device surface, Skills, and a plugin-local CLI. It does not package a
prebuilt iOS Helper app.
It deliberately does not contribute an MCP server or `mcp.json`: agents learn
the deterministic CLI contract from the bundled Skill and call the host-owned
loopback broker without starting a second device runtime.

Version 0.7 supports two Canvas host generations through one viewer bundle. A
host that exports `CanvasSimulator` keeps using that native component and its
IDE-owned lifecycle. An older host uses the plugin's `runScript` compatibility
launcher, observes its sidecar state, and embeds the same Device Surface. The
compatibility daemon is scoped to one project target, bounds cold startup to 15
minutes, and—once ready—exits when its tokenized five-minute browser lease is
no longer refreshed. It publishes no Phone Use broker credentials into Canvas
data. The first compatibility launch may show the host's normal local-script
trust prompt.

## Project entry points

- Android Emulator: application-module `src/main/AndroidManifest.xml`.
- HarmonyOS Previewer/HDC: application-root `build-profile.json5`.
- iOS Simulator app: `<App>.xcodeproj/project.pbxproj`.
- SwiftUI Package Preview: an importable library package's `Package.swift`.

These canonical project markers avoid registering every module build file,
property list, or source file as another Canvas entry. Opening one resolves its
owning project and publishes the available device targets. Starting/building a
device remains an explicit user or CLI action.

### iOS live rebuild

After an iOS Simulator session attaches, the project viewer watches the Xcode
project root for source and resource edits. It reuses the session's stable
DerivedData directory for an incremental `xcodebuild`, then installs and
relaunches the updated `.app` on the same Simulator. Rapid saves are coalesced
and builds are serialized. A failed build leaves the last successful app and
the device frame stream running, while the Simulator surface reports the build
failure.

This application path relaunches the app process, but the Canvas device session
and its H.264/JPEG stream stay attached. Swift package previews use a separate
generated-project path: three plugin-owned Swift templates plus one generated
module configuration create a persistent preview host and reload-dylib target.
Edits build and inject only that dylib; successful reload proof includes an
unchanged host PID. Initial compilation runs after the device session is
connected, so the surface receives build/deploy status during a cold build.
Reload generations are capped at 32 per session to bound retained dylib code;
reopen the Canvas to reset the host. Set `CANVAS_IOS_LIVE_BUILD=0` only as an escape hatch when
diagnosing a project-specific watcher or toolchain issue.

Swift Package previews keep their generated project, SourcePackages checkout,
and per-Simulator DerivedData under a content-addressed cache rooted at
`$AICODING_HOME/canvas/swiftui-package-preview` or
`$QODER_HOME/canvas/swiftui-package-preview` (defaulting to
`~/.qoder/canvas/swiftui-package-preview`). Cache identity is stable across
Canvas sessions and changes when the package manifest, resolved dependencies,
preview generator/templates, Xcode, Simulator SDK, target, or filters change.
Concurrent preview processes serialize Xcode builds and publish active leases,
so cache maintenance never removes an in-use entry. Inspect or maintain the
cache through the installed Skill-local CLI:

These commands are available only on macOS, matching the iOS preview host
boundary; Windows and Linux return an explicit unsupported-host error.

```bash
node "/absolute/loaded-mobile-use-skill/scripts/mobile-use.mjs" swift-cache-status --json
node "/absolute/loaded-mobile-use-skill/scripts/mobile-use.mjs" swift-cache-prune --max-age-days 30 --max-size-mb 8192 --json
node "/absolute/loaded-mobile-use-skill/scripts/mobile-use.mjs" swift-cache-prune --max-age-days 30 --max-size-mb 8192 --apply --json
```

`swift-cache-status` also reports pre-0.7.4 session caches as `legacy` so their
disk usage is visible after an upgrade. Pruning skips those directories unless
`--include-legacy` is explicit; keep Qoder closed before applying legacy cleanup.

Prune is a dry run unless `--apply` is explicit. An exact repair can use
`swift-cache-clean --package-swift /absolute/path/to/Package.swift --confirm`;
active entries are always rejected.

The iOS interaction layer follows the Simulator Browser split. Project builds
remain owned by this viewer. The Canvas Node host prepares pinned
`serve-sim@0.1.46` through `npx` and adapts its H.264, HID, orientation, and AX
endpoints to the existing Canvas device protocol. When a desktop GUI process
does not inherit the Node installation in `PATH`, the host resolves `npx` from
the user's bounded login-shell environment and invokes that absolute launcher.
No macOS Helper app or
runtime-generated host executable is shipped. Only the iOS Swift Package
preview path generates and compiles an Xcode project in the user's writable
Qoder cache using that Mac's Xcode and selected Simulator. Annotation and Agent
automation still use one Canvas runtime. `CANVAS_IOS_INTERACTIVE_RUNTIME=0`
intentionally selects the simctl JPEG view-only fallback for diagnosis.

## Agent automation

Invoke the Skill-local launcher using the absolute directory Qoder reports for
the loaded Mobile Use Skill. The launcher resolves the sibling CLI from
its own installed location, so automation does not depend on a global npm
installation, the workspace cwd, or `QODER_PLUGIN_ROOT`:

```bash
node "/absolute/loaded-mobile-use-skill/scripts/mobile-use.mjs" list-targets --json
node "/absolute/loaded-mobile-use-skill/scripts/mobile-use.mjs" list-sessions --json
```

The workflow is:

1. `inventory` for an explicitly live-Canvas-scoped device summary
2. `list_targets` → `start_session` → `list_sessions` for low-level lifecycle
3. `tap` / `long_press` with a stable native selector; the host resolves and
   dispatches against one fresh accessibility snapshot
4. `run_plan` for a bounded multi-step workflow with one session selector
5. `observe` → low-level revision-bound `act` → `wait` / `assert` when a
   snapshot ref or coordinate action is explicitly required
6. Recovery: `restart_target`
7. Exact installed-app test: `run_native_test` on project sessions that
   advertise `device.test.run`
8. App/diagnostic operations: `manage_app`, `read_logs`, `capture_screenshot`
9. Native evidence recording: `record_screen` (initially iOS Simulator only)

Commands accept kebab-case or underscore names, structured `--params-json`,
`--plan-json`, `--action-json`, `--condition-json`, and `--selector-json`
arguments, and emit a versioned JSON envelope. Successful commands exit `0`; validation, stale
selection, revision/assertion, capability, and broker failures use stable
non-zero exit classes.

Operational commands are capability-gated. Screenshot and recording results
carry durable artifact metadata plus SHA-256 evidence. `manage_app` uninstall
requires explicit `confirm: true`.

Plans may opt into `evidence.screenshots: "on-failure"` and
`evidence.recording: "native"`. Failure screenshots are best-effort and never
mask the primary step error. Native recording is transactional: a plan that
starts recording also stops it on success or failure before session cleanup.
Media receipts prove capture and provenance; visual inspection still requires
an image/video-capable consumer of the returned artifact URI.

`run_native_test` uses Android instrumentation, iOS XCTest, or HarmonyOS
ArkXTest according to the selected project session. Its receipt separates a
completed operation from the semantic outcome and persists the bounded runner
record as digest-addressed local evidence. HarmonyOS Previewer does not expose
this capability; select an HDC target for native tests.

Refs and `uiRevision` values are observation-scoped. Re-run `observe` after the
UI changes or after a stale-revision error. The exact command schemas and safe
examples live in `skills/mobile-use/references/cli.md`.

For an Agent workflow, prefer one versioned plan over repeated shell calls:

```bash
node "/absolute/loaded-mobile-use-skill/scripts/mobile-use.mjs" run-plan \
  --plan-json '{"schemaVersion":1,"session":{"platform":"ios","targetName":"iPhone 17","policy":"reuse-or-start"},"keepSession":true,"evidence":{"screenshots":"on-failure","recording":"native"},"steps":[{"kind":"launch_app","bundleId":"dev.qoder.canvas.preview"},{"kind":"tap","selector":{"identifier":"canvas.open-annotation-workflow"}},{"kind":"wait","condition":{"kind":"present","selector":{"identifier":"canvas.workflow.canvas"}},"timeoutMs":5000},{"kind":"assert","selector":{"identifier":"canvas.workflow.canvas"}}]}' \
  --json
```

Session and target selectors must resolve uniquely. Plans never guess through
ambiguity, and a plan-started session is stopped automatically unless
`keepSession: true` is explicit.

Each Canvas sidecar publishes only its loopback broker endpoint into
`~/.qoder/canvas/phone-use-brokers/` (or `$AICODING_HOME` / the explicit
`$MOBILE_USE_REGISTRY_DIR`; the legacy `$MOBILE_SIMULATOR_REGISTRY_DIR` remains
accepted during migration). Registry directories use mode `0700` and
records containing the short-lived broker token use mode `0600`. Tokens and
broker URLs are never returned by the CLI.

The Mobile Use CLI accepts only `mobile-use-*` broker identities. A Canvas host
process started by the former Mobile Simulator plugin must be closed and its
Canvas reopened after the rename; it is deliberately not mixed into current
inventory even when the old process is still alive.

## Requirements

- A Qoder/Lingma Desktop build that supports plugin-provisioned Canvas viewers
  and Canvas `runScript`. Builds that export the newer `CanvasSimulator`
  component use it directly; older builds use the bundled compatibility
  launcher.
- Android: Android SDK, an AVD, a compatible JDK, and a project-owned Gradle
  Wrapper. The current adapter targets Android Emulator gRPC, not physical
  devices. Native verification additionally requires a buildable
  `<variant>AndroidTest` APK and instrumentation metadata in Android
  Build-Tools.
- HarmonyOS: DevEco Studio with Previewer on macOS or Windows, or an explicitly
  connected HDC target on Linux. Previewer provides
  JPEG frames across current protocol versions (with raw RGBA compatibility),
  Inspector semantics, and pointer input; each connected HDC target is
  capability-probed for HAP lifecycle, UITest PNG frames, UI tree, touch, and
  keyboard input. Native verification requires an `ohosTest` HAP and an HDC
  target plus the DevEco build toolchain; it is not advertised by Linux
  attach-only sessions. Runtime kind defaults to `remote` unless explicitly
  configured.
- iOS: Apple silicon macOS, Xcode, an installed iPhone Simulator runtime,
  and `npx` available from the inherited environment, the user's login shell,
  or explicit `CANVAS_SERVE_SIM_NPX`. Application projects need a discoverable runnable scheme. SwiftUI
  preview mode needs a regular target exported by a non-dynamic library product
  and at least one `#Preview`; set `CANVAS_IOS_PACKAGE_TARGET` when selection is
  ambiguous. The first interactive session needs registry access so the Node
  host can cache pinned `serve-sim@0.1.46`; no native Helper app or runtime
  Helper Xcode project is generated. SwiftUI Package preview mode separately
  generates its preview host/reload Xcode project. Native verification requires the selected XCTest target to be
  included in that scheme.

Implementation and release qualification are separate. The 0.7 development
candidate has live interactive plus exact native-test evidence on Android
Emulator and iOS Simulator. HarmonyOS Previewer remains interactive-only by
design; HDC/ArkXTest support is implemented but is not release-qualified until
the same installed E2E runner passes against a live HDC target.
Repository CI builds and verifies the host-local Android/HarmonyOS closure on
both `ubuntu-latest` and `windows-latest`. This catches platform-specific source
and package regressions but does not replace installed Qoder plus live-device
smoke on Windows or Linux.

## Development

The plugin source lives with its device protocol, adapters, surfaces, and
project viewers under the Canvas SDK repository. Build a verifiable plugin
closure under `dist/plugin` from this directory:

```bash
cd plugins/mobile-use
npm test
npm run verify
```

On macOS, `npm run build` builds all three viewers. The iOS host sidecar directly
manages the pinned Node interaction runtime without copying a native Helper app. On Windows and
Linux it builds and verifies the Android and HarmonyOS host-local closure while
omitting the macOS-only iOS viewer. Every host copies the plugin manifest/CLI/Skills into `dist/plugin`,
writes scoped source provenance, and generates per-viewer plus whole-bundle
SHA-256 manifests. Do not hand-edit `dist/plugin`; viewer source lives in
`packages/viewer-*`, device implementation lives in `packages/device-*`, and
the plugin-owned CLI/Skills live here.

### Local Qoder deployment

Inspect the exact old registrations and copy targets before mutating anything:

```bash
npm run install:plan
```

After explicit authorization to replace the old development copy:

```bash
npm run install:local
```

Mobile Use is externally installed as `mobile-use@local`; it is not copied into
Lingma or provisioned as a built-in `qoder-bundler` plugin. The installer first
verifies the newly installed bytes and only then removes conflicting Mobile Use
and legacy Mobile Simulator registrations. Restart the intended Qoder/Lingma
Desktop instance so its Canvas host provisions the selected external plugin,
then verify that one registration and every active viewer copy match the built
artifact:

```bash
npm run verify:installed -- --require-hosts
```

The install command is deliberately destructive only behind `--apply
--replace`; it never removes unrelated plugins or broad cache roots.
`--ide-root` is rejected because Mobile Use has no built-in/source-bundle
delivery mode.

### Installed E2E

With the target project already open as a Lingma Canvas surface, run one exact
platform selector. Pass explicit surface/target IDs whenever discovery is not
unique:

```bash
npm run e2e:installed -- \
  --platform android \
  --surface-id '<surfaceId>' \
  --target-id '<targetId>' \
  --app-bundle-id 'com.example.app' \
  --wait-condition-json '{"kind":"present","selector":{"identifier":"ready"}}' \
  --selector 'com.example.ExampleTest#testInstalledContract' \
  --assert-selector-json '{"identifier":"ready"}'
```

The runner executes the installed plugin CLI, requires the semantic native
outcome to be `passed`, records only a bounded accessibility summary, captures
a screenshot when advertised, and writes a local `qualification.json` under
`test-results/`. Combine `--app-bundle-id` with a bounded
`--wait-condition-json` so launch success and semantic UI readiness are separate
preconditions. Use `--keep-session` only when the result must remain visible.

## Package

The Qoder runtime bundle is published internally as
`@ali/qoder-mobile-use`. The npm package name is a distribution detail; the
installed plugin identity is `mobile-use`.

```bash
npm test
npm run pack:verify
npm run publish:dry-run
# Release only from a clean source closure:
npm run publish:plugin
```

`pack:verify`, dry-run publication, and publication require macOS because the
complete release must contain and validate the iOS viewer plus the source-only
SwiftUI preview compiler inputs owned by `runtime/ios/swift-package-preview`.
Plugin assembly injects those inputs into the packaged iOS Canvas; the viewer
package does not own or prebuild them. The package does not contain a prebuilt Helper
app or a generated macOS helper path. Use
`npm run verify` for Windows/Linux host-local development validation.

## Ownership and safety

- Canvas owns rendering and explicit attach/boot actions.
- On newer hosts, the IDE's native `CanvasSimulator` owns sidecar lifecycle.
  On older hosts, the plugin compatibility daemon owns that lifecycle behind a
  tokenized browser lease. The IDE still owns annotations and Canvas script
  authorization. The plugin CLI owns session discovery and forwards commands
  to the sidecar's loopback-only broker.
- Platform SDKs and native tools remain user- or host-installed dependencies.
  The iOS host is the sole exception: `npx --yes` downloads and caches the
  explicitly pinned `serve-sim@0.1.46` npm runtime on first use.
- Only local file-backed projects can start device surfaces.
- Generated build products such as DerivedData, APKs, Previewer outputs, and
  simulator data remain outside this plugin.
