# Android runtime QA

Read this reference when Android verification needs UIAutomator selector
diagnosis, scrolling, foreground readiness, package-scoped logs, or a precise
boundary around performance evidence. Use the plugin CLI from [CLI](../cli.md);
do not replace the selected Mobile Use session with an independently
chosen ADB target.

## Select through the normalized UI tree

The Android adapter normalizes one bounded UIAutomator snapshot before the
Phone Use layer resolves selectors:

| UIAutomator field | Phone Use observation | How to use it |
| --- | --- | --- |
| `resource-id` | `identifier` | Prefer an exact stable identifier. |
| `content-desc`, otherwise `text` | `label` | Use only when it resolves uniquely; localized or repeated labels are weaker than identifiers. |
| Android widget class | `type` plus a derived `role` | Combine with an identifier or label when the role/type alone is ambiguous. |
| `bounds` | `frame` in `device-logical-top-left` coordinates | Use only for an explicit low-level coordinate action from the same observation. |

Prefer selector-first `tap` or `long-press`. The host obtains a fresh snapshot,
requires one actionable match, and dispatches input from that snapshot. A
screenshot is visual evidence, not a coordinate-selection source. Do not choose
the first matching node, parse raw UIAutomator XML, or copy a coordinate helper
around the host's ambiguity and revision checks.

The adapter caps a snapshot at 2,000 elements and marks it as truncated when the
limit is reached. A missing selector in a truncated snapshot is not evidence
that the app does not contain the target.

## Scroll with a fresh observation

When a target is missing and the current observation contains a visible scroll
container indicated by its role or type, such as a scroll view or list:

1. Set a task-appropriate swipe or time bound before retrying.
2. Use low-level revision-bound `act` for the swipe, with coordinates inside the
   observed scrollable frame and away from system-gesture edges.
3. Re-run `observe` after every swipe. The previous refs and `uiRevision` are
   stale after the UI changes.
4. Refine the selector or continue only within the declared bound.

Report `not found within the bounded search` unless the observation establishes
a real end condition. Repeating an unchanged swipe or reusing stale coordinates
is not additional evidence.

## Separate launch from readiness

Use the exact application ID from the project or installed-app inventory. A
successful install or launch receipt proves that the operation completed; it
does not prove that the intended activity is foreground or ready.

After launch, use a bounded semantic `wait`, then a fresh `observe` or `assert`.
An empty or incomplete tree may belong to the launcher, a permission or system
dialog, or an app that has not reached its ready state. Preserve build, install,
launch, foreground/readiness, and assertion results as separate stages. The
current Phone Use observation does not expose UIAutomator's `package` attribute;
use an app-owned stable identifier for readiness when one exists, otherwise
report foreground ownership as not independently established.

## Read bounded logs

Use `read-logs` only when the selected Android session advertises
`device.logs.read`:

- With a bundle ID, Android resolves the live process ID and returns logs scoped
  to that process. The application must be running; launch or readiness success
  should not be inferred when the process is absent.
- Without a bundle ID, the result is a bounded device log snapshot. Use this when
  the app exited before a package-scoped PID could be resolved, and state that
  the result is not process-scoped.
- `limit` accepts 1 through 5,000 lines and defaults to 500. Preserve the
  returned `truncated` flag rather than treating a full limit as complete logs.

Logs may contain paths, identifiers, typed text, tokens, or account data. Keep
the capture bounded and redact sensitive values before sharing it outside the
local verification boundary.

## Keep profiling outside the current capability claim

The current Android session does not advertise Simpleperf, Perfetto, gfxinfo,
meminfo, heap-dump, or crash-buffer-specific operations. Do not present manual
ADB profiling output as a mobile-use operation receipt or use it to route
around a missing session capability.

If an explicitly authorized profiling workflow is run outside this Skill,
report it as out-of-band Android evidence. Bind it to one exact target and one
focused user-visible flow, record the Android version, build variant, run count,
capture boundaries, and artifact paths, and state caveats such as emulator
noise, sampling limits, missing symbols, or cold-start compilation.
