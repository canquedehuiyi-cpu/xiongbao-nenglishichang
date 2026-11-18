---
name: aliyun-domain
description: Manage Alibaba Cloud domains, ICP filing, DNS, and Wan Xiao Zhi website building. Use for domain availability, prices or cost estimates, registration, renewal, transfers, DNS, security locks, contacts and registrant templates; ICP filing; or AI website operation. Also use to plan a domain operation or decide its next safe step from supplied results, including template approvals, real-name privacy, permission errors, rate limits, unknown write outcomes and pending tasks, even when no cloud call is requested. Support first-use authorization and domain-to-website delivery through DomainCLI. Exclude production incident diagnosis, registry operations, competitor-price research, and generic source-code or shell tasks.
license: Apache-2.0
metadata:
  domain: aiops
  owner: aliyun-domain-team
  contact: keven.yef@alibaba-inc.com
  execution-surface: aliyun-domain-cli
  runtime-baseline: aliyun-3.5.1+_domaincli-0.9.7+
---

# Alibaba Cloud Domain

Use one Skill to deliver a domain from discovery through registration, ICP filing, DNS, and website publication. Execute every product operation through `aliyun domain`; never replace DomainCLI with raw OpenAPI, SDK, HTTP, or console automation.

## Route before loading details

Load only the reference that matches the current intent.

| Intent | Command namespace | Load |
|---|---|---|
| Search, pricing, registration, renewal, transfer, ownership, governance, audit, or DNS | `aliyun domain ...` | [Domain operations](references/domain.md) |
| ICP consultation, filing entry, filing status, or successful filing data | `aliyun domain icp ...` | [ICP filing](references/icp.md) |
| AI website creation, conversation, project, material, domain binding, preview, or deployment | `aliyun domain wxz ...` | [Website building](references/website.md) |
| A request spanning domain, ICP, DNS, and website stages | Multiple namespaces above | [Cross-product lifecycle](references/lifecycle.md), then only the active product reference |

## Cross-product orchestration

- **Products:** coordinate domain registration and management through `aliyun domain ...`, ICP filing through `aliyun domain icp ...`, DNS through `aliyun domain dns ...`, and AI website building through `aliyun domain wxz ...`.
- **Call order:** for an end-to-end request, start at the earliest unmet stage and proceed as `discover and price -> acquire or transfer -> verify and govern -> file ICP when required -> build the website -> configure DNS and binding -> deploy and operate`. Load [Cross-product lifecycle](references/lifecycle.md) for the detailed stage contract, then load only the reference for the active stage.
- **Decision criteria:** skip a stage only when current CLI readback proves it is complete. Enter ICP when the user requests filing or the chosen China-hosted website path requires it. Change DNS only after the destination and intended records are known. Deploy only after preview, binding, and certificate state are explicit. Stop and hand control back to the user at every payment, identity review, confirmation, asynchronous wait, or external propagation boundary; never treat browser opening, order submission, or task acceptance as completion.

Load these shared references only when needed:

- Login, local identity, profile reuse, or OAuth failure: [Authentication](references/authentication.md)
- Any write, payment, deletion, transfer, DNS, publication, or credential-sensitive task: [Safety and confirmation](references/safety.md)
- A failed CLI command or uncertain completion: [Error recovery](references/error-recovery.md)
- Permission planning or `Forbidden.RAM`: [RAM permissions](references/ram-policies.md)
- Contacts, templates, real-name review, email, ICP personal data, or saved execution reports: [Private data and secure inputs](references/privacy-and-input.md)

Do not load all references preemptively.

## Supplied-state decisions

For an explanation or recovery plan based on supplied results, use those results without starting CLI version checks, login, cloud reads, or hypothetical writes. Distinguish `evidence_source=supplied_state` from `runtime_verified`; a sound decision is not proof that an API ran. Preserve any supplied target and task/plan identifiers, but ask for missing identifiers instead of generating them. Use the relevant domain and safety/error reference only; a known failed precondition or missing input is a handoff, not an instruction to manufacture a fixture.

## Fail-closed execution invariant

Apply this state machine to every operation: `intent -> preflight -> preview_succeeded -> awaiting_confirmation -> execute_once -> verify`. Read-only operations may omit preview and confirmation, but not identifier validation or result verification.

1. Freeze an intent envelope before the first operational call: selected profile and configuration store, product namespace, exact user-supplied target identifiers, requested action, before/after values, and any price, duration, payment route, plan ID, or publication channel. Readbacks may resolve a missing identifier, but they must never replace an identifier the user supplied. If the exact target is missing, inaccessible, externally managed, or ambiguous, stop and ask for the correct target or account.
2. Advance only on structured DomainCLI evidence for the same intent envelope. A command string in the response, an attempted invocation, an OAuth callback, an error message that mentions an expected field, or a different resource's successful readback is not success.
3. Treat authentication unavailable, profile conflict, target mismatch, unsupported friendly leaf, failed or incomplete preview, missing fresh confirmation, and ambiguous write outcome as terminal for the current step. A non-retryable internal error is also terminal; a generic `next_action` does not override `retryable=false`. Return the confirmed state and the next safe DomainCLI command; do not switch credentials, targets, namespaces, or execution surfaces to keep going, including for extra discovery or diagnosis after a failure.
4. High-risk and financial confirmation is valid only after a successful current preview exposes the exact impact. Earlier broad instructions such as “执行到底” are not post-preview approval. If the runtime cannot collect a reply, present the preview and stop.

Use [Safety and confirmation](references/safety.md) for the evidence and confirmation rules, [Authentication](references/authentication.md) for OAuth terminal states, and [Error recovery](references/error-recovery.md) for the only permitted recovery paths.

## Skill session attribution

Before the first `aliyun domain` invocation in each Skill activation:

1. Read [the Skill manifest](references/manifest.json). Take `name` and `version` only from that JSON. Stop without making a cloud call if the file is missing, unreadable, invalid JSON, or lacks either value; do not infer a replacement from Git, frontmatter, or the DomainCLI version.
2. Generate one fresh session ID with a cryptographically secure random source. It must be exactly 32 lowercase hexadecimal characters (`^[0-9a-f]{32}$`), remain in memory for this activation, and never be persisted or reused by another Skill activation.
3. Construct the attribution value exactly as `AlibabaCloud-Agent-Skills/{name}/{session-id} skill-version/{skill-version}`, substituting the manifest name, fresh session ID, and manifest version.
4. Append `--user-agent "AlibabaCloud-Agent-Skills/{name}/{session-id} skill-version/{skill-version}"` and `--cli-ai-mode` to every `aliyun domain ...` command in this activation, including version, help, authentication, read, write, status, and retry commands. Reuse the same value on retries so one activation remains traceable; a new activation gets a new session ID.

## Operating contract

1. Treat the installed CLI as the runtime source of truth. At task start, resolve `aliyun` once, use that same binary for every invocation, and check `aliyun version` and the attributed `aliyun domain version` once. Require Alibaba Cloud CLI `>=3.5.1` and DomainCLI `>=0.9.7` (thematic `wxz` commands); newer compatible versions are allowed. If the parent CLI is older, stop before cloud access, obtain the user's approval for the local software change, run `aliyun upgrade`, and verify the version again. If self-upgrade is unavailable, direct the user to the official installer at `https://aliyuncli.alicdn.com/setup.sh` instead of executing a downloaded script implicitly. If only DomainCLI is older, obtain approval, run `aliyun plugin update --name aliyun-cli-domain`, and verify both versions again.
2. Select the exact friendly leaf command from the relevant reference. When flags or behavior are uncertain, inspect that leaf only with `aliyun domain ... --help`; never guess a flag, call a generated OpenAPI action, or substitute another Alibaba Cloud product command.
3. Keep the session attribution flags on every DomainCLI invocation. `--cli-ai-mode` provides structured, non-interactive Agent behavior, while `--user-agent` provides Skill and session traceability. Do not invent `--format json`; DomainCLI already returns its supported structured output.
4. Do not pass `--region` or `--endpoint` during normal use. DomainCLI owns the China-site endpoint and `cn-hangzhou` routing. A user-selected custom configuration store must be preserved with the same `--config-path` across related calls.
5. Let the installed DomainCLI resolve the intended credential source internally: current commands can reuse parent-resolved standard AK/STS credentials, or refresh the selected China-site OAuth profile. Reusing that same intended source is not switching credentials; extracting it, copying it into OAuth, or choosing a different account after failure is forbidden. Use `aliyun domain login` only when login is requested or the intended command requires authorization. `auth` is a local overview; current `whoami` verifies the same selected cloud identity without proving product permissions. Keep the selected profile/configuration store fixed. Never request, read, print, or persist an AK, SK, bearer token, OAuth token, transfer code, identity document, or payment secret. Never rebuild a profile using `aliyun configure set`, credential flags, shell defaults, or copied STS credentials.
6. Read-only commands may run after intent and identifiers are clear. For writes, require a successful CLI preview or plan for the frozen intent envelope, explain its impact, obtain a fresh user confirmation, then execute the confirmed command exactly once.
7. Parse `status`, `ok`, identifiers, task IDs, `next_step`, and error codes from CLI output. Check semantic success before advancing: a field name or planned command appearing in failed output is not evidence that the step succeeded. Set execution-tool deadlines; do not leave login, streams, or status polling running indefinitely. Use [Error recovery](references/error-recovery.md) for bounded waits and a resumable final state.
8. Report what changed, what did not change, how it was verified, and any remaining user action. Include a compact `skill_result`, evidence source, underlying CLI status/error, write effect, and next step; do not rename the CLI status to make it look successful. End the current step after missing-input, confirmation or external handoff; do not leave a background wait for a reply. A browser page opened, OAuth callback completed, order submitted, site deployed, DNS record saved, and public propagation are different states.
9. Before a personal-data write, require the actual input file and required fields supported by the leaf. A label such as a company name is not a complete registrant profile. Ask for the missing non-secret input or a secure file path; do not invent contact details, inspect sensitive file contents, or reuse an unrelated template to satisfy the request.
10. Execute conditional follow-up reads only when successful discovery returns their required identifiers. An empty successful account query completes that query scope, not a DNS/template/task lookup for which no target exists. Return the missing prerequisite for unexecuted steps; do not invent targets or keep querying the same empty list. For a supplied-state decision or explanation, reason from that evidence without logging in or executing the hypothetical write.

## Scope boundaries

This Skill owns customer-facing DomainCLI operation and orchestration. It does not own:

- Production failure diagnosis, logs, databases, EPP traces, or source-code root-cause analysis.
- Registry onboarding, certificate rotation, registry balances, or production EPP operations.
- Competitor registrar price crawling or market analysis.
- Generic React, backend, or infrastructure coding that does not use `aliyun domain wxz`.
- Direct OpenAPI or SDK execution when DomainCLI lacks a command. Report the gap instead of bypassing the CLI.

## Completion check

Before declaring success, verify all applicable points:

- The installed command and version satisfy the baseline.
- The exact leaf `--help` supports every flag used.
- OAuth/profile selectors remained consistent.
- User-supplied target identifiers were not replaced by discovered resources.
- Each high-risk step received the confirmation required by DomainCLI and this Skill.
- Every executed write is backed by a successful same-target preview rather than command-text matching.
- Each asynchronous operation reached a terminal state or is explicitly handed off with a task ID and next command.
- No credential or sensitive value appears in the response or saved artifacts.
- The final answer distinguishes submitted, accepted, completed, browser-opened, and externally propagated states.
