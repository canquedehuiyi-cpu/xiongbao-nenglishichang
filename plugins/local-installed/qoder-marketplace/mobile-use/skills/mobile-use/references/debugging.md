# Mobile Use debugging

Read this reference when project source, the installed plugin, a live Canvas
surface, semantic interaction, and native-test evidence disagree. For a missing
SDK or machine-wide target scan, use `$setup-mobile-use`. For repair-grade
or exact native-test evidence, also read
[Installed-app verification](installed-app-verification.md).

## Locate the failing layer

Do not jump from a visible symptom to a platform command. Identify the first
layer whose evidence is missing:

| Layer | Minimum evidence | Important boundary |
| --- | --- | --- |
| Project | One canonical entry resolves the intended project | Opening a file does not boot a target |
| Live Canvas discovery | `list-targets` publishes the exact surface and target | Discovery covers live Canvas surfaces, not every device installed on the machine |
| Session | One exact `surfaceId` and `targetId` resolve to one `sessionId` | Never select the first result when discovery is ambiguous |
| Capability | The selected target/session advertises the requested operation | Missing capability is an unsupported boundary, not permission to fall back |
| Semantic UI | `observe`, revision-bound `act`, `wait`, or `assert` succeeds against the current snapshot | Native accessibility nodes are not DOM nodes |
| Native behavior | `run-native-test` returns `data.output.outcome == "passed"` | A completed operation or Phone Use assertion is not a native-test pass |
| Installed host | The installed Skill/CLI and provisioned viewers match the intended plugin build | Source and package tests cannot prove the enabled-host path |

Use [CLI](cli.md) for command schemas. Read the matching
[Android](android.md), [HarmonyOS](harmonyos.md), or [iOS](ios.md) reference only
after the failing platform is known.

## Triage loop

1. Use `list-targets` and `list-sessions` to learn which live Canvas surfaces
   have published targets and sessions. Treat that scope as live Canvas state,
   not a machine-wide toolchain or device scan.
2. Pin the exact surface, target, and session. Re-run discovery instead of
   reusing identifiers from an earlier host or Canvas tab.
3. Inspect the structured error code and advertised capabilities before
   changing source or invoking a platform tool.
4. Run `observe` before revision-bound `act`; re-observe after any UI change.
   Keep refs, coordinates, swipe, text, and key input bound to that observation.
5. For a multi-step workflow, keep one exact session binding and record bounded
   step evidence and cleanup status.
6. Separate application launch from UI readiness. Launch explicitly when
   needed, then use a bounded `wait` before `assert` or native testing.
7. Stop only sessions started by the current workflow unless the user asked to
   keep them.

## Symptom routing

| Symptom or error | Interpretation and next action |
| --- | --- |
| A project entry is known but no matching Canvas surface exists | Reading the file is not the same as opening its Format Viewer. Use a supported host Canvas-open action when available; otherwise report the host-open boundary and provide the canonical entry. Do not substitute a platform shell command. |
| Source changed but the viewer exposes no supported refresh/rebuild | Runtime verification is unavailable. Preserve the source change, stop before runtime claims, and do not edit Previewer caches or generated build output. |
| Loaded Skill launcher is missing | The installed plugin is incomplete. Stop and report it; do not guess another cache path. |
| `list-targets` omits a platform | No live Canvas surface published it. This does not prove that its SDK or device is absent; use the setup Skill for a machine-wide probe. |
| Target or session selection is ambiguous | Supply exact IDs or refine selection until it is unique. Never silently choose the first target. |
| `phone.surface.*`, `phone.target.*`, or `phone.session.*` | Refresh live inventory and bind identifiers from the same surface. Do not copy broker records or credentials into commands. |
| `device.capability.unsupported` | Report the selected runtime and missing capability. Check the platform reference; do not route around the adapter with arbitrary shell commands. |
| `phone.selector.not-found` | Re-observe and verify the app is foreground and ready, then refine the selector. |
| `phone.selector.ambiguous` | Add a native identifier, role, type, or another semantic constraint. Do not choose a match by array position. |
| `phone.ui-revision.stale` or stale ref | Re-run `observe` and use only its revision and refs. |
| Launch succeeded but `wait` timed out | Preserve launch as a completed stage and UI readiness as a separate failure; capture bounded logs or a screenshot when advertised. |
| Operation receipt succeeded but native test did not pass | Inspect `data.output.outcome`; keep assertion, build, install, runner, target, crash, and timeout outcomes distinct. |
| Source/build/package checks pass but Canvas still fails | Verify the installed artifact and provisioned viewer closure, then reproduce in the real enabled Canvas host. Do not repair the symptom with generated output. |
| Frames are blank, stale, or decoded with an implausible size | Distinguish screenshot from stream capabilities and inspect the platform transport. For Previewer JPEG/RGBA diagnosis, use the HarmonyOS reference. |

Retry only after changing the discriminating condition: a newly published
surface, supported rebuild/refresh, fresh observation, unique selector, exact
live identifier, restored capability, completed app readiness condition, or
corrected installed artifact. Repeating an unchanged command is not additional
evidence.

## Report the strongest proven layer

- **Build:** the selected project or target compiled.
- **Package:** the intended plugin closure was assembled and verified.
- **Installed:** the active plugin and Canvas host copies matched that closure.
- **Interactive:** the real surface completed the requested semantic workflow.
- **Native test:** one exact instrumentation, XCTest, or ArkXTest selector ran
  and returned `outcome == "passed"`.
- **Repair:** the same frozen plan failed for the intended behavior before the
  fix and passed after it.

Name every unverified platform and layer. Infrastructure outcomes such as
missing toolchains, offline targets, build/install/launch failures, crashes,
and timeouts must not be reported as behavioral pass or failure.
