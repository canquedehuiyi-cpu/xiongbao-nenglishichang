---
name: sites-management
description: Manage an existing Qoder Site through MCP tools for resuming suspended sites, sharing and invited visitors, names and addresses, deletion, deployment/release history and audit, backend capabilities, database migrations, Storage files, Secret metadata/removal, and analytics. Use this skill to resolve requests to view stored records against the available management capabilities. Use sites-building for application code and sites-hosting for publication.
---

# Manage a Qoder Site

Use the available `sites` tools. The host chooses the account and environment and supplies authentication. Do not ask for tokens, construct another HTTP client, or select Provider tenants, buckets or credentials. Keep management operations within the available `sites` tools and report their actual results.

## Scope and communication

This is the administration path alongside [sites-building](../sites-building/SKILL.md) and [sites-hosting](../sites-hosting/SKILL.md), not another project initializer or application backend. The site-owning agent performs writes; helpers can return bounded research results. Use only the capability needed for the request.

Describe the site's behavior, changes and actual status in plain language. Keep credentials, internal routing and provider details out of user-facing output. Preserve exact link destinations and tool arguments; explain failures and unverified results accurately.

## Identify the site and authorization

Use `list_sites`, then `get_project` or `get_site`, to match the user's intended site. Preserve the existing Project and Site IDs. Read-only inspection can proceed immediately. Carry out writes covered by the user's request; ask only when the intended resource or consequential change is unclear. A request to inspect a site does not authorize allocation, migration application, overwrite, deletion or backend release.

Use a fresh UUID `requestId` for each new write intent and retain its exact parameters. For a retry of that same intent, reuse the ID and parameters. A revision conflict requires reading current state and reviewing the changed plan, not silently replacing expected versions. Never change an ID merely to bypass an uncertain result.

## Resume a suspended site

For a request to restore a suspended site's existing published version, read `get_site` and verify the target, `lifecycle`, `active_release_id`, `access_mode` and `runtime_version`. If already active, report that state without a write. If there is no published release, use [sites-hosting](../sites-hosting/SKILL.md) for publication. Resolve ambiguous requests such as “重新发布” against the conversation: restoring the existing version uses this path; delivering changed source uses the publication workflow.

Once the user's request authorizes restoring access to this site under its current audience, call `resume_site` with `siteId`, the observed `runtime_version` as `expectedRuntimeVersion`, a stable `requestId` and `confirm: true`. An explicit restore request already supplies this authorization; no repeated confirmation is needed. Preserve the current audience and release.

The response is a synchronous `{site}`, not an Operation. Re-read `get_site` and verify `lifecycle: active` and the intended `active_release_id` before reporting restoration. A replay may return a newer site that was paused again; report its actual state. On an unknown outcome retain the exact request ID and version; on a version conflict read current state and review the changed intent before a new write. Governance or project-state rejection requires resolving the reported blocker. Restoring access does not establish that Functions or database interactions work.

## Sharing and site settings

Use `list_shared_sites` when the user asks about sites shared with them; visitor access does not grant management rights.

1. Read `get_access_policy` and use its `available_modes`, limits and confirmation requirements. A missing option is unavailable; use the server's options rather than inferring them from the account.
2. For an authorized audience change, pass its policy revision as `expectedRevision` to `update_access_policy`. Set `confirmPublic: true` only when the user's request explicitly covers public access. Publication confirmation and audience changes are separate actions.
3. Use `list_access_targets` for invited visitors. `put_access_target` accepts a full email or case-sensitive Qoder UID in `email`; `remove_access_target` accepts the returned `targetId`. Both use the list's `policy_revision` as `expectedPolicyRevision`. Invitations are distinct from project management membership. Re-read policy and visitors to verify the requested result.

For a requested rename, use `update_project_name` with the revision from `get_project`. For an address change, read `subdomain_prefix` as the initial editable value and `subdomain_suffix` as the fixed, read-only suffix. Keep `host` as the current live address; for legacy sites, prefix + suffix may instead be the proposed new address. If these optional fields are absent, request a new raw prefix without guessing a suffix from the hostname. Explain that saving changes the URL and old links stop working. Check the new raw prefix with `check_subdomain`, then use the same prefix and `get_site.runtime_version` as `expectedRuntimeVersion` in `update_subdomain`. The server appends a unique suffix: do not submit the full hostname or feed `normalized_subdomain` back as a prefix. A successful check does not reserve the address. Read the updated site and report its resulting URL.

For an explicitly requested project deletion, explain the resource/data impact, read `get_project`, then pass its exact display name as `confirmDisplayName`, revision as `expectedRevision`, and `confirm: true` to `delete_project`. Preserve any dependency failure; do not delete dependencies automatically. Poll the returned operation and verify final state before reporting deletion complete.

## Cloud history and audit

Use `list_deployments` and `get_deployment` for cloud deployment history, including deployments without a local action record. Use `list_releases` and `get_release` for published versions; compare `is_active` with `get_site.active_release_id` when checking the current version. Deployment readiness alone does not prove publication. Use `list_audit_events` for who performed an action, its outcome, revisions and operation ID. Follow `pages.next_page` until zero. Concurrent changes may affect paginated history.

`get_publish_status` reads an existing local preparation's `actionId`; a cloud Operation, Deployment or Release ID is not an action ID. When no local action is available, inspect the cloud history above instead of preparing a new draft just to query status.

## Backend readiness and progress

- `get_backend` returns capabilities and status; `ensure_backend` requests authorized capabilities from `database`, `functions`, `storage`, and `qoder`. It can allocate cloud resources.
- For Cloud Agents websites, follow the [Qoder PAT disclosure and explicit confirmation](../sites-build-agent-app/SKILL.md#3-prepare-the-sites-ai-capability) before requesting `qoder`. It includes Functions and provisions the platform `QODER_PAT` Secret; verify readiness through `get_backend`, not the filtered Secret list. Reuse an already-ready capability. Keep that reserved name out of ordinary Secret writes and `prepare_site.secretNames`.
- Poll `get_operation`; use `list_operation_steps` with its sequence cursor for safe progress codes. Accepted, queued and running are not completed.
- After completion, read `get_backend`, `get_database` and `get_storage` as relevant. A ready Function does not prove database or Storage readiness.
- Use `release_backend` only for an explicitly requested release after explaining its data impact. Supply the observed `expectedRevision` and `confirm: true`. Respect dependency/nonempty-Storage failures; do not remove dependencies automatically.

## Viewing stored records

The current Sites Desktop has no database table/row browser, and Sites MCP has no business-row query or arbitrary SELECT tool. Explain this boundary when asked to view submissions or saved records; do not direct the user to a Desktop Database panel or infer rows from schema metadata. Database readiness, a table definition and a UI success message do not establish that a particular submission was saved.

Inspect whether the existing site provides an application-authorized read endpoint or management page for the requested records. If it exists, use it within the user's authorized scope and report only what the response establishes. If it does not exist, explain that a query feature must be implemented through [sites-building](../sites-building/SKILL.md); a request to inspect records alone does not authorize adding or publishing one. Resolve the application's verified identity and data policy before implementation. Keep private records private: do not grant anonymous SELECT, expose credentials or use migration tools to bypass the missing query capability.

## Database structure and migrations

Before writing migration SQL, read the supported SQL subset and access-policy guidance in [Create the notes schema and access policy](../sites-building/references/database-migration.md). For updates to a live site, follow [Schema changes while a version is live](../sites-hosting/references/deployment.md#schema-changes-while-a-version-is-live).

1. Read `get_database`. A successful response can report `disabled`; in that case, explain that the database is not enabled and stop schema inspection. A snapshot revision alone does not establish readiness. If an enabled database's catalog is stale or refresh is requested, call `refresh_database`, wait for its operation, and read the new database state.
2. Pass that `snapshot_revision` as `snapshotRevision` to `list_database_tables` and `get_database_table`. Keep it fixed while paging. A changed snapshot requires restarting inspection rather than combining incompatible pages. These tools return schema metadata, not business rows or database credentials.
3. Use `list_database_migrations` for summaries. Use `get_database_migration` with `includeSql: true` only when the task needs SQL review.
4. For a requested schema change, call `create_database_migration` with a stable client migration ID, display name, restricted DDL, expected schema version/fingerprint and declarative `accessPolicies`. AppHub validates the actual supported SQL. Do not submit data queries, DML, credentials, arbitrary procedures or business records as a migration.
5. Review the returned normalized changes, SQL hash and access policies. Policies describe the complete managed state of each touched table; omitting a grant is not an incremental no-op. Explain access changes along with schema changes.
6. Once the user's authorization covers that exact plan, call `apply_database_migration` with its migration ID, revision, expected schema version/fingerprint, SQL hash, stable request ID and `confirm: true`. Wait for the operation and verify the final database state. Creating the plan does not apply it.

Database management is separate from application runtime configuration. `prepare_site` defaults to `databaseAccess: none`; explicitly select `read_only` or `read_write` and a positive `requiredSchemaVersion` for a dependent anonymous Function. AppHub checks the required schema and runtime prerequisites. The declaration does not itself grant permissions or prove Provider enforcement. Never silently remove a dependency after a conflict. See [sites-building](../sites-building/SKILL.md).

## Storage files

Storage is one platform-managed private bucket per site. `get_storage` returns readiness, MIME/size limits and `management_available`. Proceed with file operations only when `management_available` is true; otherwise report that the requested file operation could not be completed.

- `list_storage_objects`: omit `prefix` or use `""` for the root. Directory paths accept one optional trailing slash: `uploads` and `uploads/` list the same directory. Prefixes are limited to 1024 UTF-8 bytes; leading/repeated slashes, `.`/`..` segments, backslashes, `%`, `?`, `#`, control/format characters and non-NFC Unicode are rejected. Invalid prefixes return `sites_invalid_request` with a `prefix` field and correction hint. Use `limit` and `offset`; continue only when `has_more` is true, using `next_offset`. Listings use native offset pagination and can change during concurrent writes. Prefix entries are folders, not downloadable objects; use their returned `path` as the next listing's `prefix`. Upload, download and delete still require an exact object path without a trailing slash.
- `upload_storage_file`: read the current conversation directory with `get_local_context`, then supply that `projectRoot`, a relative `localPath`, the exact `objectPath`, `contentType` and a stable request ID. The source must be an authorized regular file inside that project. The maximum is 10 MiB and the site's smaller limit/MIME policy also applies. Overwrite requires the user to authorize it and both `upsert: true` and `confirmOverwrite: true`.
- `download_storage_file`: supply the same workspace/path context and exact object path. The destination must be new and its parent directory must already exist. The plugin verifies size and SHA256 and returns a local path/receipt. It never places file bytes into the conversation or overwrites an existing file.
- `delete_storage_object`: supply one exact object path, a stable request ID and `confirm: true` after authorized deletion. It is not recursive prefix deletion and has no object revision/CAS guarantee.

Treat mutation receipts explicitly: `succeeded` confirms the recorded attempt, `rejected` reports a definitive failure, and `unknown` means the outcome cannot be established. Repeating the same request ID retrieves the saved receipt and does not resend the native mutation. For `unknown`, inspect the object and reconcile the intended state before proposing a new write. In particular, do not delete a recreated object to “retry” an old deletion.

Local transfers reject traversal, symlinks and common credential paths. Choose a different legitimate output path if a download already exists. Never work around these checks by moving Secrets into another file, returning base64 through MCP, exposing signed URLs or reading `QODER_STORAGE`. Application use of the injected Storage SDK has separate runtime and application-authorization requirements; owner management access is not visitor authorization.

## Other management and publication

Use `list_functions` for safe function metadata and `list_secrets` for application Secret names/versions/synchronization only. Enter or update values through Desktop Portal Settings. CLI has no Secret-value input tool; explain that this step needs the supported settings surface rather than collecting values in chat. Never return reserved `QODER_*` values or infer them from metadata.

For an explicitly requested environment-variable removal, use `delete_secret` with its name and version from `list_secrets` as `expectedVersion`, a stable request ID and `confirm: true`. Explain its effect on dependent Functions, poll the operation, then re-read metadata. Reserved platform names remain unavailable.

Use `get_analytics` with `window: "24h" | "7d" | "30d"` and `metric: "pv" | "uv"` (default `pv`). PV counts requests, including resources and automated traffic; UV estimates unique visitors using IP and User-Agent. Read the window-wide `total` directly; never sum UV `series` points. Preserve coverage and reasons, and keep missing partial buckets as gaps. Unavailable is not zero. Neither metric is billing traffic.

For code changes, continue in the original source workspace with [sites-building](../sites-building/SKILL.md). For publication, follow [sites-hosting](../sites-hosting/SKILL.md), including its content policy, default publication and host-specific preview handoff. Preserve explicit preview-first, no-publication and local-only requests.

## Limit errors

When a tool reports `sites_quota_exceeded`, `sites_storage_file_too_large`, or an operation reports `artifact_size_exceeded`, follow [limit messages](../sites-hosting/references/limits.md): stop the blocked operation and state the limit without questions or choice/confirmation dialogs.
