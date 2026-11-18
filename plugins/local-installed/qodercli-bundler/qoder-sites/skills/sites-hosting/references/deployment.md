# Qoder deployment

## Source, identity and artifacts

Use the current conversation directory returned by `get_local_context` or a selected site subdirectory inside it; a registered workspace is optional. Work in another project requires a task there; SSH/cloud publishing is not supported by these tools. Keep source and build output in that original project. Both hosts discover cloud-verified site descriptors. Preparation reuses the descriptor’s Project after validation; conflicting IDs or inaccessible targets fail without creating a replacement site. When switching hosts, prepare a new action from the local source; a descriptor does not transfer the original action’s recovery record. Reuse known IDs; use `list_sites` and `get_project`/`get_site` only when the target needs identification or fresh resource facts.

### Switching accounts in the same source directory

`get_local_context` returns the current account's cloud-verified bindings. Explain any `unavailableSites` to the user: an inaccessible entry does not mean no site exists. Continue an existing site under its original account, or, when the user explicitly requests a new site for the current account, call `prepare_site` with `createNewSite: true`, a new `actionId`, `displayName` and `slug`, and omit `projectId`. Keep the same source directory. Preserve the flag, action and inputs on retries.

A ready draft switches the single `.qoder.site` entry. The plugin retains private bindings per directory, account and environment; opening or continuing under the original account revalidates cloud access and restores its binding. Creation failure leaves the old entry intact. Legacy entries without private action records are backed up but cannot regain missing recovery records automatically; recover from the original host or prepare a new action against the verified existing Project. Account changes and lookup failures alone never authorize creating a replacement.

`prepare_site` packages and uploads an immutable snapshot. It generates the outer `qoder-sites.json`, ZIP and private recovery record; A ready `prepare_site` writes the project-local descriptor without opening a preview; inspect `descriptorStatus` and preserve the same action on pending or local-write failure. `show_publish_confirmation` refreshes the project-local `.站点名称.qoder.site` preview descriptor. These are different artifacts, both tool-owned. Do not hand-write their fields, copy a descriptor as source recovery, or add a separate hosting manifest.

Source control is the user's workflow, not a prerequisite for this deployment API. No source repository credential, commit SHA, manual version save or direct private-deploy tool is required. The supported path is `prepare_site` → readiness checks → `publish_site` → verified status → `show_publish_confirmation`; when the user defers publication, show the complete draft and stop before `publish_site`, with `get_publish_status` for reads and recovery.

## Prepare inputs

Read the exposed tool schema before calling it. Use exact returned IDs and the current project's real paths:

| Input | Meaning |
| --- | --- |
| `actionId` | New UUID for a new frozen draft; retain for all retries of that exact intent |
| `createNewSite` | Optional explicit new-site intent for the current account; incompatible with `projectId`; preserve on retries |
| `projectRoot` | The absolute selected site directory within the `get_local_context` root; the host verifies the real path boundary |
| `webDirectory` | Relative, dedicated public output directory containing `index.html`; never the project root |
| `projectId` | Existing Project UUID for an update; omit only when intentionally creating a site |
| `displayName`, `slug` | New-site identity; choose a meaningful slug using the address rules below |
| `subdomain` | Optional explicit raw address prefix for a new site; omit for automatic slug-based allocation. Not accepted with `projectId` |
| `spa` | Whether the build needs the supported `index.html` fallback |
| `functionDirectory` | Optional relative directory with one `app` Function's `index.ts` and self-contained dependencies |
| `databaseAccess`, `requiredSchemaVersion` | Explicit `read_only`/`read_write` dependency and actual positive schema version; omit version for `none` |
| `secretNames` | Ordinary application Secret names used by the Function, never values or reserved platform names |

Use [Static output](../../sites-building/references/static-site.md) for path, routing and package limits, and [Functions and Secrets](../../sites-building/references/functions.md) for runtime requirements. The tool does not run application build commands, resolve arbitrary imports or apply migrations. Inspect public output for source maps, embedded configuration, real data and credentials before upload. Keep source control, dependencies, `.env`, private keys, symlinks and local fixture servers outside the package.

Request backend allocation only within the user's authorization. Preparation with a Function can allocate Functions; a database-dependent Function can request database and Functions but does not create the schema. Configure ordinary Secret values through Sites Settings after readiness, then verify synchronization for the dependent release. Secret names in the input are dependencies, not a way to provision their values.

For QCA, use [sites-build-agent-app](../../sites-build-agent-app/SKILL.md). The `qoder` capability includes Functions and provisions `QODER_PAT`; that reserved name is omitted from `secretNames`. The filtered Secret list cannot establish its presence or absence.

## Choose the first address

For a new site, choose one short, memorable lowercase slug from its purpose or title before the first `prepare_site`. Prefer two or three meaningful English words joined by hyphens, for example `daily-notes`, `team-weekly` or `studio-portfolio`. For a Chinese title, use a concise English rendering or readable pinyin. Use 3–51 characters, start and end with a letter or digit, and avoid reserved names and the `preview-`, `qoder-`, `qsites-` prefixes. Keep personal identifiers and private project details out of the public address. Reuse a suitable name the user supplied; ordinary naming does not need an extra question.

When the user has not required an exact prefix, pass the chosen `slug` and omit `subdomain`. AppHub tries that slug with the owner's fixed suffix and can allocate a random prefix if it is unavailable. When the user explicitly requests a particular prefix, pass it as `subdomain`; a rejected or occupied explicit name must be reported rather than silently replaced. The prefix is not a full hostname and never includes the owner's suffix. Creation does not require `check_subdomain`, which requires an existing Site ID.

After preparation, read the returned site's actual `host` and use that address in the draft summary and final handoff. Do not promise a predicted URL or add a separate rename just to replace a generated fallback. If preparation creates a bootstrap project, choose the name there and reuse the same Project/Site IDs for the complete draft. Preserve the original name and action through uncertain results; a new name cannot replace an unresolved create attempt.

For existing sites, reuse `projectId` and preserve the address. A user-requested address change follows [sites-management](../../sites-management/SKILL.md), with the server's edit fields and runtime version; publication alone does not authorize renaming.

## First publication with a database

For an existing project, reuse its IDs and begin with authorized database setup. For a new project, first build and review the actual frontend, then:

1. Prepare a static-only bootstrap draft with a new action, name and slug. Omit Function, database and Secret inputs. Retain the returned Project/Site IDs and leave this draft unpublished. Do not show its publication confirmation.
2. Use `ensure_backend` for the authorized `database` and `functions` capabilities. Wait for the Operation, read `get_database`, and apply the application's reviewed schema/access policy through [sites-management](../../sites-management/SKILL.md). The [notes migration example](../../sites-building/references/database-migration.md) shows the contract. Configure ordinary Secrets only through the supported input flow.
3. Prepare the complete website and Function with the existing `projectId`, a new action ID, explicit `databaseAccess` and actual required schema version. Present only this complete action for publication.

Keep bootstrap and complete action IDs separate, including during recovery. Initialization must not create a second project or accidentally publish the bootstrap draft. QCA has its corresponding setup in [First-use initialization](../../sites-build-agent-app/references/initialization.md#prepare-the-site); combine capabilities only when the application requires them.

## Recovery

- If preparation is interrupted, retain the original action and inputs. `get_publish_status` requires a recorded deployment; when the first preparation stopped before that exists, resume `prepare_site` with the same action and exact inputs. The private record and request keys recover the operation.
- Unchanged source with a ready frozen draft does not need another build or upload. Changed content or preparation inputs require a new action; retain the existing `projectId`.
- A publish timeout or lost response is not proof of failure. Read the same action's status before deciding whether to retry. Never generate a new action/request ID just to bypass an unknown outcome.
- A conflict requires current status and the server's actual reason. Do not assume every `sites_conflict` is a slug collision or quota problem, silently replace the target project, or overwrite an expected version. Follow the existing intent's definitive outcome and the user's current delivery scope.
- Accepted, queued and running Operations are not completion. Stop polling a terminal result; report failure or the remaining blocker. Recovery must preserve the current live release and private records.
- `published` is true only when the publish Operation succeeded and committed, and its Release is the site's current active Release. `canPublish`, upload acceptance and the Canvas preview are not interchangeable with that fact.

## Schema changes while a version is live

Use expand-and-contract changes. Add compatible tables/optional columns first, keep the live Function working, and then publish the Function that uses them. Check live and new versions against the expanded schema. After the new version is verified and old callers no longer depend on the old fields, handle removals or permission tightening as a separate reviewed change.

Use a separately authorized process for data backfill; schema tools do not accept business DML. A failed publication does not authorize reversing a migration or deleting data. Preserve the compatible schema and live release while repairing the next draft.

If an old site has no descriptor, use `show_publish_confirmation` in the original host with its known action to recreate the entry from the private record and frozen ZIP, without publishing. If those are missing, do not fabricate a descriptor or create a replacement site: confirm the existing Project, then prepare current source under a new action. Preserve an existing newer entry.
