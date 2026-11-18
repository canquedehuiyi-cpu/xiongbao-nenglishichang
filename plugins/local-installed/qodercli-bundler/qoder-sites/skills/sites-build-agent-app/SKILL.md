---
name: sites-build-agent-app
description: Add Qoder Cloud Agents to Qoder Sites for AI assistants, chat, research, agent execution, persistent conversations and streamed results. This capability skill extends sites-building; use sites-hosting for hosted delivery.
---

# Build a QCA-powered experience

Add the requested AI capability to the same website and project being built with [sites-building](../sites-building/SKILL.md). Continue that workflow rather than initializing another site or repeating its design/setup steps. Use [sites-hosting](../sites-hosting/SKILL.md) for hosted delivery.

The runtime path is **browser → same-origin Sites Function → Qoder Cloud Agents**. The Function reads the platform's `QODER_PAT`; the browser receives only application content and status. Qoder Desktop's management login is a separate credential boundary.

## 1. Define the useful interaction

Identify what the user asks the agent to do, which application users may invoke it, what tools it actually needs, and whether work continues across visits. Make the primary AI interaction visible in the site's working surface; do not replace it with an advertisement for an assistant. Keep scope, copy and visual direction aligned with the rest of the site.

Choose the smallest suitable tool set and fixed server-side Agent configuration. Preserve requested transport or interaction choices. For interactive chat, prefer incremental SSE output; polling is appropriate for background work where incremental text adds no value. Model selection, system instructions, tools and upstream destinations stay under server control.

Before implementation or resource allocation, choose a supported execution scope. For per-user or resumable conversations, verify [visitor identity](../sites-building/references/functions.md#site-access-and-visitor-identity), [private persistence](../sites-building/references/database.md#identity-and-coordination), and the [durable coordinator](references/initialization.md#resource-scopes-and-durable-intents). A ready database or qoder capability does not establish those contracts. If any required contract is missing, report that dependency and continue independent work. A fixed server-configured Session is only an explicitly agreed limited slice; it does not satisfy requested multi-user isolation, concurrent sends or history recovery. Keep fixture routes in local adapters and make the real UI use the real server endpoints.

Once scope is known, implement one executable path before extending the design. For local-only work or an unavailable dependency, skip live API setup and resource allocation. If the chosen interaction uses SSE, start with the [application stream consumer](references/streaming.md#application-stream-consumption) and a credential-free response fixture. Read further references only for the next implemented dependency. Report missing identity/persistence contracts once, then complete the independent slice without designing a replacement platform.

## 2. Establish the server connection

Before writing live requests, read [Cloud Agents API integration](references/api.md) and call `get_runtime_context` with empty arguments. Copy `cloudAgents.apiOrigin` into server-only configuration and pass it to the bundled `createCloudAgentsClient({ origin })`. Use the host-issued mapping exactly; do not infer it from language, website hostname or documentation examples. An unconfigured origin blocks live integration, not local application development.

The bundled [client](assets/cloud-agents.mjs) supplies bounded authenticated requests and safe error codes. Copy it into the Function directory and use relative imports. It is not an application HTTP API or a complete conversation service. Keep its generic request method behind the application's selected endpoints. Recheck the runtime context when resuming or changing the target; changed server configuration requires a new prepared draft.

Use Managed `/api/v1/cloud/*` consistently. Consult the current linked API contract before adding a model/tool option or operation beyond the bundled workflow. A configured route does not prove upstream reachability or token validity.

## 3. Prepare the site's AI capability

Follow [Prepare the site](references/initialization.md#prepare-the-site) within the user's backend-allocation authorization. Reuse existing Project/Site IDs. For a new site, the bootstrap draft obtains those IDs from the real built frontend and remains unpublished; only the complete AI draft is presented for publication.

Read `get_backend` first. Reuse an already-ready `qoder` capability. Before enabling it, explain in the user's language that the platform will automatically create a Qoder PAT for their account, securely configure it as the site's server-side `QODER_PAT`, and use it to authenticate the site's calls to Qoder Cloud Agents. Ask for explicit confirmation covering both enablement and PAT creation/use. For example: “开启此站点的 Qoder 后端服务时，系统会自动为你创建 Qoder PAT，并安全配置到站点后端，供 Qoder Cloud Agent 调用使用。是否确认开启并创建？” A general request to build an AI site, allocate a backend or publish is not this confirmation. Reuse an existing explicit confirmation for the same site and purpose; do not ask twice.

Wait for the user's affirmative reply before calling `ensure_backend` with `qoder` or otherwise initiating PAT creation. If declined or unanswered, continue local development with credential-free fixtures and leave live AI enablement pending. After confirmation, call `ensure_backend` for `qoder` with the actual Site ID and stable request ID. It includes Functions and provisions the platform Secret. Wait for the Operation and verify the capability through `get_backend`. Add database or Storage only when the application needs them. Backend setup, first-use Cloud resource creation and publication are separate lifecycles.

Read `Deno.env.get('QODER_PAT')` only inside the Function. Do not ask for a pasted PAT, rename it to an application Secret, write it through ordinary Secret tools, declare it in `prepare_site.secretNames`, or pass it into browser code, prompts or Session environments. The filtered Secret list cannot tell whether this platform Secret exists. A missing/invalid token produces a safe service error; it does not authorize minting a token, changing regions or reallocating the backend from the Function.

## 4. Initialize once and resume safely

Use the identity, persistence and execution scope established before implementation. Where Gateway user context is available, use the bundled `requireUser(request)` to look up durable conversation mappings by current site and user; also verify conversation ownership before sending or streaming. Identity context does not itself provide durable mapping, atomic coordination or history recovery. Anonymous Function mode alone does not prevent server-side QCA calls.

Read [First-use initialization](references/initialization.md) when creating Cloud resources or implementing persistent conversations. Reuse configured resources and implement the ownership, history and recovery behavior the requested conversation flow needs.

- Initialize on the first authorized start/message POST, after validation and quota checks. Page loads, prefetch and health checks remain read-only.
- Reuse the application's configured Agent/Environment or its unique metadata-matched resources. Persist IDs and configuration revisions. Display names alone are not ownership keys.
- Bind each application conversation to its authorized user and exact Cloud Session. Reuse that binding across visits and check ownership on sends, reads and interrupts.
- Persist creation/message intent before dispatch. Coordinate concurrent first use across Function instances. Preserve pending intents after timeouts and reconcile the original attempt; do not repeat Environment/Session creation or resend a prompt merely because the response was lost.
- Use the client's bootstrap helper only with the durable coordinator contract described in the reference. Pass the app scope as `applicationScope`; optional Agent/Environment business metadata must use non-`qsites_` keys. The helper owns the reserved resource-matching metadata. Session/message persistence and fencing remain application responsibilities.

An unknown QCA dispatch result must remain pending until reconciled; a database uniqueness check alone cannot make an external message exactly-once.

## 5. Complete the application flow

Build the smallest authorized end-to-end application slice first: browser action → deployed Function → QCA → final reply, with the ownership and persistence needed for that slice. Extend domain tools and application features after this path works. Missing optional integrations need not block a clearly scoped connectivity check; such a check does not satisfy features that depend on those integrations. Follow sites-hosting to publish the complete changed draft, honoring explicit deferral.

Expose bounded Function endpoints for start/message, conversation state and event reads. Accept prompt text, application conversation IDs and stable request IDs; resolve Cloud IDs and configuration on the server. Validate methods, content type, size and authorization before upstream calls. Never expose a generic authenticated proxy.

For SSE, read [Streaming](references/streaming.md) and reuse [sse.mjs](assets/sse.mjs). The Function authenticates upstream, projects permitted message/status content, persists history and reconnect cursors, and closes the upstream stream when done. Reconnection retrieves progress without resending the user message. Preserve explicit polling requirements.

Implement the states the chosen flow needs: initialization, running, waiting for input, completed, interrupted and failed. Keep the primary action and recovery clear. Escape Agent text or use sanitized Markdown. Include usage/input limits and cancellation for long work. Restore the active conversation by loading its authorized history on mount. Starting a new conversation clears the old active state and cancels its reader; stale responses must not update the new view. A reload must not send a prompt again; a 202 response means accepted work, not a completed answer. Do not automatically approve Agent tool actions that require user authorization.

Read [Runtime diagnosis](references/diagnostics.md) for upstream failures or application usage counts. Keep safe diagnostic IDs at request boundaries and translate errors into user-facing application text; do not relay raw upstream payloads, credentials or internal routing.

## 6. Validate and hand back to publication

Follow [sites-building's validation scope](../sites-building/SKILL.md#validation-scope) and reuse its build and main-flow results. QCA integration does not require a separate fixture suite. Add a targeted check only for initialization, ownership, persistence or transport logic changed by this task; the reference documents describe those checks on demand.

Return to the original site's [publication workflow](../sites-hosting/SKILL.md) once the complete draft and required capabilities are ready. `canPublish: true` proves draft readiness only. For hosted AI delivery, verify one real conversation through the site's Function using the authorized Site and account: message acceptance and a final reply, including saved history if requested. This is the AI main-flow check; reuse it across validation steps. For SSE, observe incremental output in that same request. Test reconnect or usage accounting separately only when that logic changes or a failure points to it. Local-only work can use credential-free fixtures and report real execution as unverified.

Before deployed acceptance, follow [Verify the target version](../sites-hosting/SKILL.md#verify-the-target-version).

Describe local fixture results, site publication and real AI execution separately. A ready backend or HTTP 200 alone is not an AI acceptance result. If the integration cannot run, deliver the working local preview and explain the exact user-visible blocker without recommending a dependent release as ready.

For application database or file implementation, use [Database access](../sites-building/references/database.md) and [Storage](../sites-building/references/storage.md). Keep private AI bindings, coordination and conversation ownership separate from public sample-data policies.
