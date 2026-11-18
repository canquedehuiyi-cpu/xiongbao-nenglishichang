---
name: sites-hosting
description: Deploy, publish, take live or recover a Qoder Site from its original local project. Use for website requests such as 部署、上线、发布. Use after sites-building for hosted delivery, for an existing prepared draft, or for publication status and previews. Publish validated work by default unless the user requests local-only work or defers publication.
---

# Publish a Qoder Site

Publish the exact validated website with the shortest safe sequence. Use the current `sites` tools and copy returned IDs unchanged. Qoder owns authentication, packaging, draft recovery and release state; the agent owns the selected source and the user's publication intent.

If implementation is incomplete, return to [sites-building](../sites-building/SKILL.md). Before new preparation or recovery, read [Qoder deployment](references/deployment.md) for the actual tool inputs, backend prerequisites and immutable-draft rules.

## Interpret deployment requests

When the user asks to deploy, publish or take a website live (部署、上线、发布), complete the publication workflow below. These requests have the same delivery goal; do not ask the user to restate them as “publish.” An internal Deployment is an uploaded artifact, not the completed user request. Build success, upload success, Deployment `ready` and `canPublish: true` are intermediate states. Continue through `publish_site`, verify `published: true`, then show the same action's preview. Verify runtime behavior separately when required by the requested functionality.

Reuse an existing matching draft and read its status before continuing; do not rebuild or create a second site merely because the user said “deploy.” Explicit local-only, preview-first or no-publication instructions take precedence. A deployment-status question is read-only, and deployment does not authorize changing a private site to public.

For a suspended site, restoring access to the existing release follows [Resume a suspended site](../sites-management/SKILL.md#resume-a-suspended-site). A historical `published: true` does not establish that the site is currently active. Resolve whether “重新发布” means restoring that release or publishing changed source before choosing the workflow.

## Lifecycle and audience

The site-owning agent performs preparation and publication from a selected site directory within the current local conversation directory. Asset/research helpers return results without creating projects or publishing. Preserve the existing Project/Site IDs and current access scope when updating a site. Resolve an ambiguous target before any write.

A request to build or update a hosted website authorizes publication of the completed work. Publish after validation and readiness checks without stopping for another draft confirmation. If the user requests local-only work, preview first, or no publication, honor that scope; local-only work does not prepare cloud resources. Status checks and reopening previews never authorize a new publication. New sites remain private; changing the audience and enabling capabilities that require separate authorization retain their own rules.

Browser QA is not a publication prerequisite. Reuse local validation from development, and keep any working local preview available while reviewing. The publication Canvas displays frozen static files; it does not execute Functions or prove integrations work.

## Publication content policy

Before uploading a draft or requesting publication, review the site's purpose, page content, assets, downloads and Function behavior. Publishing pornographic or sexually exploitative content, graphic violence or content promoting or inciting violence, and other unlawful content or services is prohibited. Reject prohibited publication requests, identify the content that needs removal and review the revised output before proceeding. Do not upload prohibited content or bypass platform review. Apply this policy to new sites, updates and recovered drafts; prior publication or user confirmation does not override it.

## Short publication path

Before a new `prepare_site`, use a dedicated public output directory containing `index.html` and its required static assets. For a single-file HTML site without a build step, copy those final files into `dist/` within the original project and set `webDirectory: "dist"`, keeping `projectRoot` unchanged. Never use `webDirectory: "."`. If preparation rejects the project root, correct the output directory and prepare with a new `actionId`.

1. **Reuse the current work.** For a known action, call `get_publish_status` before preparing again. If `published` is true and the draft still matches the intended source, reuse its result and continue to the preview handoff without another publish call. If this same draft is pending or ready, continue with it. Rebuild only after source changes; a new release does not require a Git commit, push or manual ZIP.
2. **Prepare once.** For a new draft, call `get_local_context` to discover existing site files in the workspace, select the intended site directory (one active site entry per directory), and inspect the actual validated output, and call `prepare_site` using the [deployment inputs](references/deployment.md#prepare-inputs). For a new site, [choose its first address](references/deployment.md#choose-the-first-address) before preparation. Reuse an existing `projectId` for updates. For an explicit request to create a new site after switching accounts in the same directory, follow [account switching](references/deployment.md#switching-accounts-in-the-same-source-directory). Retain the exact `actionId` and all inputs. Preparation can create resources and upload data; local-only work stops before this step.
3. **Resolve readiness.** Use `get_publish_status` for the same action and [sites-management](../sites-management/SKILL.md) only for the required backend or operation checks. `canPublish` describes draft readiness, not an AI reply or database query. Resolve the required capabilities before presenting a complete draft; never offer an initialization-only draft as the finished site. If a dependency remains unavailable, explain the blocker and preserve the draft.
4. **Publish or defer.** Unless the user deferred publication, read `get_publish_status` and call `publish_site` with this exact ready `actionId` if it is not already published. Changed content requires a new action. If publication is deferred, show the complete draft preview below and end the turn.
5. **Verify the result.** Read `get_publish_status` until the operation is terminal; stop on failure or an actionable blocker. Report published only when `published: true`, which includes committed Operation/Release consistency. Preserve the original action after timeout or a lost response and follow [Recovery](references/deployment.md#recovery). Complete any required real integration check before the final preview handoff. If that check leads to frontend or Function edits, rebuild and prepare a new action for the same project, publish it, and recheck the affected behavior. Earlier release results do not validate the edited source.
6. **Show the result.** Open the same action with `show_publish_confirmation` after verified publication. The tool name is retained for compatibility; it shows a preview and does not itself publish. On a failed publication, explain the failure and show the draft only if the tool's readiness checks allow it; never label it published.

## Show the preview

Call `show_publish_confirmation` with the exact completed action, after publication by default or before publication when the user requested a draft preview. Use its actual result to select the host interaction.

**CLI (no `filePreview`):** The tool writes the same `.站点名称.qoder.site` descriptor and returns `descriptorPath` for Desktop project discovery; it does not open a preview. Return the site link for `status: published`; for `status: await_user`, summarize the deferred draft and wait. Do not invent a Canvas, file link or Publish button. Existing development preview files may differ from the frozen draft.

**Desktop (`filePreview` present):** Qoder writes the project's `.站点名称.qoder.site` file and opens the frozen static preview. Published actions show their published state and site access controls; deferred drafts retain the Publish button. Reuse the same action to reopen it.

This is the final tool call of the turn. For Desktop, end with at most one short sentence and copy `deliveryMarkdown` verbatim on its own body-text line. Preserve the returned label, escapes and encoded path. Keep this descriptor as the only delivery entry; omit local preview URLs, HTML/source links, headings and repeated publishing instructions. Finish required checks before opening the preview.

If opening fails, report it accurately and retain the same action. A preview failure does not undo or retry a successful publication.

## Verify the target version

For an existing site's deployment diagnosis or integration acceptance, compare `get_site`, `get_backend` and `list_functions` with the intended local source and prepared draft. Backend readiness does not mean the Function was deployed. Verify that the current release contains the intended frontend and Function before exercising a new feature; if it is an older version, complete the missing implementation/preparation and follow the publication workflow. Do not ask the user to find controls absent from that version or retry an undeployed endpoint.

When browser testing is requested, use the verified local preview or current deployed version and inspect it yourself with available tools. Report unavailable browser access accurately. Keep draft readiness, publication and runtime integration evidence separate.

## Handoff

After verified publication, return the safe site link from the status result and briefly describe what the user can do. Preserve the actual destination and current access scope. Optional browser opening or a failed browser handoff does not change the release result; reachability and real Function behavior are separate checks. If those were not verified, say so when material to the requested outcome.

For a deferred draft, preserve its action and preview entry. For requested changes, resume development in the same project. For a failed release, retain the current live version and explain the next action rather than claiming success.

Keep credentials, routing labels, internal IDs, packaging and polling out of ordinary user-facing messages. Talk about the website, publication and any decision the user needs to make. Use [sites-management](../sites-management/SKILL.md) for backend/schema/Storage administration; use Sites Settings for access and application Secret values.

## Limit errors

When a tool reports `sites_quota_exceeded`, `sites_storage_file_too_large`, or an operation reports `artifact_size_exceeded`, follow [limit messages](references/limits.md): stop the blocked operation and state the limit without questions or choice/confirmation dialogs.
