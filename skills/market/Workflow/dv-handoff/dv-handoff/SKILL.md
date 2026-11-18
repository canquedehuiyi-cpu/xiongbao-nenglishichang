---
name: "dv-handoff"
description: "Da Vinci handoff direct route skill for Codex."
---

# Da Vinci Handoff

Use this direct `$dv-handoff` skill for the request.

Action: `handoff`

<!-- DA_VINCI_HOOK_CONTRACT_START -->
Shared hook and lifecycle boundary:
- treat `da-vinci workflow-status --project <path> [--change <id>] --json` and `da-vinci next-step --project <path> [--change <id>] --json` as the single routing brain; do not invent a separate routing or readiness engine
- treat `.da-vinci/state/change-state.json`, `.da-vinci/state/change-seq.json`, and `.da-vinci/state/change-lifecycle.lock` as command-owned lifecycle surfaces, not prompt-owned heuristics
- after those route checks confirm the current pending handoff gate, run `da-vinci hook-bridge --project <path> [--change <id>] --trigger-kind handoff-start --gate <gate> --json`
- `hook-bridge` is bounded to `handoff-start` preflight only; `$dv-handoff` remains manual and the hook call must not replace promotion writes
- treat hook `requires` as same-trigger dependencies only; required consumers block when a dependency is missing, disabled, stale, failed, returns `WARN`, or is ordered after the consumer, and optional consumers warn and skip execution
- preserve policy order as execution order; do not topologically sort or auto-reorder hook bindings
- treat `da-vinci hook-status` and `workflow-status` as read-only hook diagnostics for local binding identity, project declaration/default provenance, snapshot status, role metadata, latest-versus-effective run interpretation, and `hookRecovery`; they must never become route authority or a second workflow engine
- if `.da-vinci/changes/<change-id>/hook-policy.system.json` is missing, keep the story hook-local: surface `hookRecovery.status = recovery_required` with `hookRecovery.reason = system_snapshot_missing` instead of inventing an empty-policy fallback or lifecycle repair
- treat `.da-vinci/changes/<change-id>/project-profile.system.json` as a separate frozen change-local platform/locale/app-technology contract; hook or route diagnostics may reference it, but active changes must not live-read `.da-vinci/project-profile.json`
- treat `system.project-profile.ensure` as a check-only `stage:start:breakdown` validation seam: it may refresh `.da-vinci/changes/<change-id>/project-profile.system.json` only after canonical `.da-vinci/project-profile.json` is confirmed; profile collection remains owned by `da-vinci dv-change-new [change title]` / `$dv-change-new` before lifecycle creation
- treat `.da-vinci/design-source-profile.json` as the canonical project-level design-source selector; repo-owned `.da-vinci/design-sources/awesome-design-md/*/DESIGN.md` snapshots stay bounded advisory reference input and sibling `tokens.system.json` stays derived import evidence rather than route truth
- treat `.da-vinci/changes/<change-id>/candidates/product-prototype.md` and `.da-vinci/changes/<change-id>/candidates/copy-catalog.json` as generated promotion inputs; the requirement export hook may refresh them, but candidates alone never satisfy design entry
- treat `.da-vinci/changes/<change-id>/requirement-truth-promotion.system.json` as read-only paired-promotion evidence for accepted `breakdown_to_design`
- treat `.da-vinci/changes/<change-id>/product-prototype.md` and `.da-vinci/changes/<change-id>/copy-catalog.json` as promoted canonical change-local requirement-side design-entry companions; hook or route diagnostics may reference them, but only paired promotion may update them
- treat `.da-vinci/changes/<change-id>/page-design-contracts.json` and `.da-vinci/changes/<change-id>/icon-map.json` as canonical change-local design-entry contracts; hook or route diagnostics may reference them, but they are not hook-owned artifacts
- keep one canonical consumer chain for design-entry consumers: promoted product/copy truth -> page design contracts -> icon map
- when `.da-vinci/design-source-profile.json` is missing, treat confirmed `.da-vinci/DESIGN.md` as the project-local design-source baseline only when it stays rich and complete
- during breakdown, `.da-vinci/DESIGN.md` is read-only advisory if it already exists; do not create `.da-vinci/DESIGN.md` during breakdown, and leave `.da-vinci/DESIGN.md` missing until the design route materializes it through `design-confirm --confirm`
- treat `.da-vinci/changes/<change-id>/source-digests.system.json` as design-entry source freshness evidence; stale canonical artifacts block design entry instead of being auto-regenerated as recovery
- treat `.da-vinci/changes/<change-id>/icon-supply.system.json` as derived change-local icon-catalog readiness evidence; hook or route diagnostics may reference it, but it is not editable route truth
- when the shared `design_to_tasks` gate is rendered, keep design-entry readiness plus parallel `Design Review`, `Icon Verification`, and `Copy Verification` on the same fail-closed seam; `WARN` remains pending until explicit `dv-handoff` acceptance
- keep structured UI quality checks on that same seam: `uiQualityScore`, first-screen structured `.dvp` metadata, the density linter, anti-AI-look issue ids, visible text `copyKey` / `locale`, and icon `iconId` / `qualifiedName` bindings must not create a new route or workflow stage
- keep the task/build/conformance spine on existing seams: `build-packet.system.json` `artifactSpine`, derived `tasks.index.json` `contractRefs`, and `implementation-conformance.system.json` are replay evidence for task, build, and verify promotion, not new workflow stages or canonical source truth
- when `build_to_verify` replay sees missing, stale, or `BLOCK` implementation conformance, keep verification promotion blocked instead of treating the gap as advisory guidance
- treat `.da-vinci/changes/<change-id>/quality-profile.system.json` as a separate frozen change-local quality contract; hook or route diagnostics may reference it, but active changes must not live-read `.da-vinci/quality-profile.json` or `.da-vinci/quality-profiles/*.json`
- treat `.da-vinci/changes/<change-id>/prd.md` as a read-only derived summary owned by system `stage:start:design`; do not promote it to requirement truth or regenerate it from requirement handoff
- if `hook-status --json` is missing or invalid, keep recovery bounded to `hook_status_payload_invalid` or `hook_status_payload_missing`; hook policy mutation must wait until payload trust returns
- keep lifecycle commands explicit: `da-vinci dv-change-new [change title]`, `da-vinci dv-change-close`, and `da-vinci dv-change-recover <change-id> [--confirm]`
- if lifecycle repair is required, do not invent a switch-change route; point the operator to `$dv-repair` as the maintained repair surface for abnormal lifecycle recovery
<!-- DA_VINCI_HOOK_CONTRACT_END -->
<!-- DA_VINCI_OUTPUT_CONTRACT_START -->
Reply contract:
- after route work and any handoff writeback, rerun `da-vinci workflow-status --project <path> [--change <id>] --json` and `da-vinci next-step --project <path> [--change <id>] --json` so the final report reflects current truth
- keep the reply in the standard Da Vinci operator format instead of a plain work log
- summarize current truth first: active change id, title, lifecycle status, derived stage, pending handoff, and blocker or repair status
- when blocked, surface `Root cause: ...` before any maintained next command
- include `Execution detail: ...` only when the underlying CLI result or gate clarifies the blocker without replacing the maintained route
- keep `Evidence refs: ...` high-signal on terminal-style output; richer JSON payloads may keep fuller ref lists
- preserve `Failures:`, `Warnings:`, and `Notes:` when present
- if exactly one legal next action exists, emit `Next command: ...`
- if `pendingHandoff.command` or the top recommended legal next command is `$dv-handoff` because review is still missing or WARN needs explicit acceptance, emit `Next command: $dv-handoff` instead of skipping directly to the downstream stage route
- if multiple legal next actions exist, group them as `Recommended`, `Also valid`, `Mandatory rollback`, and `Rollback`
- when the legal next action is another maintained Da Vinci surface, restate it using this platform's wrapper names: `$dv-continue`, `$dv-code-context`, `$dv-change-new`, `$dv-change-close`, `$dv-change-recover`, `$dv-breakdown`, `$dv-handoff`, `$dv-design`, `$dv-tasks`, `$dv-build`, `$dv-verify`, `$dv-repair`, `$dv-illustration-list`, `$dv-illustration-prompt`, `$dv-illustration-add`
- do not recommend raw CLI or `/prompts:*` actions as the next command; mention raw CLI only as execution detail inside the current maintained surface
- do not auto-invoke the next command from inside `$dv-handoff`
<!-- DA_VINCI_OUTPUT_CONTRACT_END -->
Route discipline:
- do not create or mutate a handoff marker if the current phase is still missing required artifacts, review surfaces, or non-handoff gates
- when `design_to_tasks` coverage context is available, treat `.da-vinci/changes/<change-id>/coverage-matrix.json` as a derived-only row-first ledger; when canonical design-entry targets exist, stable `coverageRowId` expands from the approval-unit `surface + qualifier` identity to `surface + qualifier + platformTarget + localeTarget`; when those targets are unavailable, use the current surface-level `surface + qualifier` row id. Use it to report affected requirement rows, uncovered/stale/drifted rows, and evidence refs in `$dv-handoff`, but do not treat it as a new routing brain or canonical truth
- for accepted `breakdown_to_design`, run `da-vinci handoff-accept --project <path> --change <id> --gate breakdown_to_design --decision approved --json`; this maintained CLI wraps `prepareRequirementTruthPromotionForHandoffAcceptance(projectRoot, changeId)`, verifies paired promotion evidence, writes the durable `handoffs/breakdown_to_design.json` envelope, and writes the parseable `## Handoff Markers` owner marker; do not manually copy candidates and do not handwrite the breakdown handoff envelope or marker

If the current phase is not handoff-ready:
- report the current stage
- report `blockingGate`
- report missing artifacts, missing review surface requirements, and unresolved gates
- keep the workflow in the current phase

If the current phase is handoff-ready:
- present the canonical review payload for that phase
- ask for an explicit approve or reject outcome
- collect the consumed artifact paths and digests for that phase review
- write `.da-vinci/changes/<change-id>/handoffs/<gate>.json` before the final marker append
- write the parseable handoff marker back to the owning existing artifact as the last substantive edit
- generate the approval timestamp at final writeback time and keep the marker append as the final marker write
- fail closed if the accepted marker does not have a matching valid `.da-vinci/changes/<change-id>/handoffs/<gate>.json` envelope
- rerun `da-vinci workflow-status --project <path> [--change <id>] --json`
- rerun `da-vinci next-step --project <path> [--change <id>] --json`

For `design_to_tasks`, present one shared provider-free gate with parallel `Design Review`, `Icon Verification`, and `Copy Verification` sections.
`WARN` means the operator must make an explicit manual decision in `$dv-handoff`; it never auto-passes.
`BLOCK` means follow-up work is required before promotion.
Treat `design-review-report` as the bounded Design Engine v2 rubric packet on that shared gate: keep `qualityProfileId`, `reviewDimensions`, and `problematicDimensions` visible, and call out profile-critical findings such as CTA semantics, responsive behavior, trust/proof modules, and anti-AI-look when they are blocking.
Any allowed icon exception must already be explicit in `.da-vinci/DESIGN.md` under `## Iconography`; do not invent new exceptions during handoff.
Coverage-driven blocker summaries should cite affected requirement rows and evidence refs from the current `coverage-matrix` and design-review context.

For accepted `design_to_tasks` outcomes, write `.da-vinci/changes/<change-id>/handoffs/design_to_tasks.json` with this exact `approvedPackage` block:

```json
{
  "approvedPackage": {
    "schemaVersion": 1,
    "packageDigest": "...",
    "members": {
      "registeredDvpSource": {},
      "registeredDvpHash": {},
      "uiDesign": {},
      "uiBindings": {},
      "surfaceExports": [],
      "surfaceExportMetadata": [],
      "designRuntimeGate": {},
      "layoutAudit": {},
      "craftAudit": {},
      "iconValidation": {},
      "visualAssetBindings": {},
      "brandAssetBindings": {},
      "supervisorReview": {}
    },
    "activeSurfaces": [],
    "changedSurfaceKeys": [],
    "historicalEvidenceRefs": []
  }
}
```

- `members.registeredDvpSource` must capture the registered .dvp fingerprint and metadata
- `members.registeredDvpHash` must capture the accepted registered .dvp source hash used by bindings and export metadata replay
- `members.uiDesign` must capture `.da-vinci/changes/<change-id>/ui-design.md`
- `members.uiBindings` must capture `.da-vinci/changes/<change-id>/ui-bindings.json`
- `members.supervisorReview` must capture the structured current design-review evidence behind the `Design Review` section
- canonical `Icon Verification` must be evaluated from `.da-vinci/DESIGN.md#Iconography`, including only explicit surface-scoped exceptions
- `members.surfaceExports` must enumerate the required screenshot exports
- `members.surfaceExportMetadata` must enumerate the required export metadata files and source hashes
- `members.designRuntimeGate`, `members.layoutAudit`, `members.craftAudit`, `members.iconValidation`, `members.visualAssetBindings`, and `members.brandAssetBindings` must preserve PenCLI gate evidence for build and verify replay
- only changed `surface + qualifier` units need refreshed design-review evidence and screenshot exports, but package validation must still cover the full active approved set before the final marker append
- if any current approved-package member is stale, missing, mismatched, or omitted, do not append the accepted marker
- keep `references/skill-workflow-detail.md` as the owner for the stage-specific wording

For accepted `build_to_verify` outcomes, write `.da-vinci/changes/<change-id>/handoffs/build_to_verify.json` with this exact `deliveryPackage` block:

```json
{
  "deliveryPackage": {
    "schemaVersion": 1,
    "packageDigest": "...",
    "members": {
      "tasks": {},
      "approvedDesignHandoff": {},
      "specIndex": {},
      "tasksIndex": {},
      "changedFiles": []
    },
    "taskGroups": [],
    "taskItems": [],
    "traceRows": [],
    "invalidatedItemKeys": []
  }
}
```

- `deliveryPackage` is the canonical accepted implementation truth for `build_to_verify`
- `members.changedFiles` must carry changed-file digests
- `taskItems` must use `implemented`, `skipped`, and `invalidated` outcomes instead of checklist-only or name-only delivery evidence
- `traceRows` must be explicit trace rows linking changed code to requirement surfaces and approved design surfaces
- if the accepted `deliveryPackage` drifts from current tasks, code, or approved design truth, verification must block
- keep `references/skill-workflow-detail.md` as the owner for the stage-specific wording

For accepted `verify_to_complete` outcomes, write `.da-vinci/changes/<change-id>/handoffs/verify_to_complete.json` with this exact `verificationPackage` block:

```json
{
  "verificationPackage": {
    "schemaVersion": 1,
    "packageDigest": "...",
    "members": {
      "verification": {},
      "buildHandoff": {},
      "verifyBindings": {},
      "verifyImplementation": {},
      "verifyStructure": {},
      "verifyCoverage": {},
      "completionAudit": {}
    },
    "rounds": [],
    "items": [],
    "summaryCounts": {},
    "unresolvedItemKeys": [],
    "stopReasons": [],
    "reentryTarget": "verify"
  }
}
```

- `verificationPackage` is the canonical accepted verification truth for `verify_to_complete`
- `members.verification` must capture `.da-vinci/changes/<change-id>/verification.md`
- `members.buildHandoff` must capture the accepted `build_to_verify` envelope digest
- `members.verifyBindings`, `members.verifyImplementation`, `members.verifyStructure`, and `members.verifyCoverage` must capture the verification-signal surfaces consumed by completion review
- `members.completionAudit` must capture the completion audit result used for final promotion
- `rounds` must snapshot structured verification rounds, and `items` must snapshot inherited, new, changed, retired, and unresolved verification evidence rows
- completion review must preserve the bounded `verificationLoop` contract with `maxAttempts = 2`
- the only valid completion-facing stop reasons are `verification_block`, `repair_limit_reached`, `human_intervention_required`, `reentry_required`, `completion_audit_block`, and `readiness_block`
- `reentryTarget` must name the minimal unfinished stage; if the accepted `verificationPackage` drifts from current verification truth, completion must block and re-enter without deleting prior rounds
- `$dv-handoff` remains manual after verification becomes ready; do not auto-invoke it from `$dv-verify`

Canonical review payload by phase:
- `supplement requirements`: use the fixed review section in `.da-vinci/changes/<change-id>/proposal.md` and include inherited, new, changed, retired, and unresolved requirement deltas
- `design`: summarize `.da-vinci/changes/<change-id>/design.md` plus mapping completeness, orphan surfaces, rollback-required findings, and the shared `Design Review` / `Icon Verification` / `Copy Verification` gate state from `.da-vinci/changes/<change-id>/ui-design.md` / `.da-vinci/changes/<change-id>/ui-bindings.json`
- `tasks`: summarize `.da-vinci/changes/<change-id>/tasks.md`, coverage, ownership, dependencies, and open risks
- `build`: summarize implementation evidence, the accepted `build_to_verify` `deliveryPackage`, explicit trace rows, and unresolved execution/review concerns from `.da-vinci/changes/<change-id>/verification.md` and task execution signals
- `verify`: summarize verification outcomes, the accepted `verify_to_complete` `verificationPackage`, bounded `verificationLoop`, drift, remaining risks, and completion blockers from `.da-vinci/changes/<change-id>/verification.md`
