# MCP Configuration Review

Use this reference for an explicit Customization Checkup or MCP cleanup request.
MCP gives an agent access to external systems; it does not by itself prove that
the access is useful, safe, or used.

## Evidence Ladder

Keep these states separate:

- **Configured**: a source file declares the server.
- **Effective**: Qoder resolves the server after precedence,
  enablement, and plugin ownership are applied.
- **Observed**: a bounded session or runtime snapshot shows a tool/resource from
  the server was used.
- **Healthy**: the effective server is reachable or has visible tools/resources
  and no current attention signal.
- **Unavailable**: active configuration, runtime, authentication, or session evidence
  cannot be established.

`Configured` without `Observed` is `configured-only` or `unobserved`; it is not
an unused finding.

## Classification Rules

- `healthy`: effective and observed, or effective with a healthy runtime when
  the request is configuration-only.
- `shadowed-here`: a project server with the same canonical name wins over a
  user server in this workspace. This is not global unused evidence.
- `configured-only`: configured and enabled, but runtime/session observation
  was not requested or is unavailable.
- `unobserved`: a sufficiently covered bounded window contains no mapped use;
  keep it separate from cleanup eligibility.
- `candidate`: enabled, outside the new-install grace period, not shadowed,
  owner-mapped, and unobserved in a sufficiently covered workspace or
  user-global window.
- `unavailable`: identity, active source, runtime state, or coverage is too
  ambiguous to classify.

Plugin-owned MCP servers inherit plugin ownership. Prefer disabling the owning
plugin or using a Qoder-supported override. Never patch plugin caches,
generated configuration, or runtime snapshots.

## MCP Surface And Context Economics

Separate the registered catalog from what the model actually receives:

- **Catalog surface**: effective server, tool, resource, and plugin-provided MCP
  counts, including duplicate or shadowed names.
- **Initial model-visible surface**: tool schemas, descriptions, and metadata
  loaded before the task selects a tool.
- **Deferred surface**: catalog entries discoverable through search or a
  gateway whose schemas are loaded only after selection.
- **Execution traffic**: model turns, tool calls, polling responses, retries,
  and intermediate payloads required to complete one representative workflow.
- **Result exposure**: raw bytes or rows returned to the model versus the
  bounded, filtered, or aggregated result it actually needs.

Installed tool count is not initial prompt burden when discovery is deferred.
Conversely, a small schema can still be expensive when a workflow repeatedly
polls or returns a large raw result. Do not recommend cleanup from catalog size
alone.

When the host exposes the evidence, compare the same representative task under
the same model and task conditions. Report initial schema bytes or tokens,
schemas loaded after selection, model turns, raw and model-visible result size,
latency, completion quality, and error rate. Bytes and tool counts are routing
signals, not exact token savings. External benchmark ratios are illustrative,
not proof of local savings.

## Recommendations After MCP Pressure Is Proven

Standard direct MCP integration is the comparison baseline, not one of the
recommendations below. Recommend one or more of these four optimizations only
after evidence shows excessive initially loaded schemas, poor selection in a
large catalog, repeated tool round trips, or broad SaaS exposure:

| Recommendation | Use when the review finds | Required validation |
|---|---|---|
| CLI tool resolution | Direct MCP registration preloads many schemas although each task invokes only a small subset. Project MCP tools as machine-readable CLI commands that resolve and invoke the target MCP tool dynamically, preferably through a governed gateway. | Compare initial model-visible schema and task completion; preserve structured `search`, `describe`, invocation, errors, authorization, and audit; use argv-safe cross-platform execution. |
| Tool Search | The available MCP catalog is too large for reliable or economical up-front loading. Search the catalog and load only the selected MCP tool definitions on demand. | Measure selection accuracy and loaded-schema reduction; keep search permission-aware and fresh; verify that unselected schemas stay out of model context. |
| Code Mode | MCP workflows are chatty because they poll, paginate, fan out, filter large results, or repeat calls. Run the loop in a bounded subprocess, commonly over CLI-resolved MCP calls, and return only the required structured result. | Compare model turns and raw versus model-visible payload; cap time, retries, pages, rows, and concurrency; expose cancellation and partial failure. |
| Gateway-routed SaaS MCP | Vendor Servers expose broad product catalogs, inconsistent auth boundaries, or duplicated integration plumbing. Route them through the same governed MCP gateway and expose efficient CLI and Code Mode workflows where justified. | Verify tenant and OAuth scope, tool-level policy, audit and revocation, initial schema exposure, destructive tools, and per-vendor workflow behavior. |

These recommendations are complementary, not four mandatory migration stages.
For example, Tool Search can discover an infrequently used tool, while a
repeated high-chatter workflow uses Code Mode over the CLI-resolved form. CLI
and Code Mode change how MCP is presented to the model; they do not remove the
underlying MCP Server or gateway contract.

MCP remains the access layer. A Skill may own the reusable Code Mode procedure
and validation, but do not add one for an isolated call without repeated
demand, measurable pressure, or a safety reason.

Code Mode does not weaken mutation boundaries. Reads may batch automatically,
but state-changing operations still need the workflow's plan, authorization,
idempotency, dry-run, and rollback rules. The wrapper must not hide individual
write targets, skipped items, or partial completion behind a success summary.

## SaaS MCP Review Details

Third-party servers often expose a product-wide API because the vendor cannot
predict which subset each customer needs. Review the initially model-visible
schema, tenant and account boundary, OAuth scopes, destructive tools, tool-name
quality, and result volume separately from the total vendor catalog.

When recommending gateway routing, prefer Tool Search or CLI tool resolution
when a vendor's broad catalog would otherwise be always visible. For recurring
high-chatter workflows, use Code Mode to select the required MCP tools and
return compact results. A high tool count is pressure evidence, not by itself
a reason to disable the server or replace the user's chosen integration.

## Separate Recommendation: Context Supply And Request Count

When sessions spend most turns locating owners, services, datasets, incidents,
or prior decisions, the problem is repeated search rather than an oversized
MCP surface. Recommend a maintained index, relationship graph, or context
service only when repeated search failure is visible. This is a separate
requests-per-turn optimization, not one of the four MCP-pressure
recommendations. The service should return compact candidate identities with
provenance and freshness, apply the caller's permissions, and route the agent
to authoritative sources instead of dumping a large graph into context.

Evaluate context supply on representative questions using correctness, model
turns, elapsed time, wrong-route rate, and freshness. A context graph is a
discovery layer, not proof that a live system still has the indexed state and
not a replacement for source or runtime verification.

## Security Review

A unified MCP gateway centralizes enforcement but does not by itself prove
least privilege. Verify caller identity, tenant and workspace scope, tool-level
policy, auditability, revocation, and whether search results exclude tools the
caller cannot invoke.

Never print environment values, auth headers, URL credentials, raw arguments,
tokens, or secret-looking config values. Report env key names, transport type,
package/version pinning, and redacted endpoint identity only. CLI and Code Mode
paths must keep secrets out of argv, stdout, generated scripts, temp artifacts,
and model-visible summaries.

## Remediation Order

1. Resolve the active configuration source and ownership.
2. Fix parse, authentication, or runtime attention before cleanup.
3. Measure catalog, initial model-visible, deferred, execution, and result
   surfaces separately on a representative workflow.
4. If MCP pressure is proven, choose the relevant optimization: CLI tool
   resolution, Tool Search, Code Mode, or gateway-routed SaaS MCP. Do not
   present Direct MCP or Context Graph as another item in this four-part set.
5. Validate the proposed path against completion quality, selection accuracy,
   model turns, context size, latency, errors, permissions, and mutation
   safeguards; do not optimize token count in isolation.
6. Prefer disable-first with a reviewable plan, rollback, and verification.
7. Use Qoder's supported configuration operations.
8. Leave deletion, uninstall, and cache cleanup for a separately confirmed
   later action.

Every plan names target scope, evidence status, the MCP pressure that triggered
the recommendation, expected surface reduction, chosen optimization,
validation, rollback, source fingerprints, and whether a host refresh or new
session is still required. If CLI tool resolution or Code Mode is recommended,
also name limits, error propagation, authorization, and the exact summary
returned to the model.

## Qoder Configuration Notes

Resolve one active Qoder home before comparing MCP state:

1. an explicit `--qoder-home` or injected fixture home;
2. `QODER_HOME` or a host-provided work directory when visible;
3. the active executable/product layout;
4. the platform product default.

The user-authored source is `<qoder-home>/mcp.json`. Project configuration
prefers `.qoder/mcp.json`; root `.mcp.json` is compatibility fallback. The
merged `<qoder-home>/extension/local/mcp.json`, runtime metadata/tool snapshots,
plugin cache files, and logs are evidence only and must never be edited.

Multiple historical homes may exist. Report all discovered homes, but do not
merge them into one effective inventory unless active-home evidence supports
that choice.

For managed state, use supported Qoder CLI argv operations. Do not patch
merged runtime files or plugin caches.

Read [Global Coding-Agent Assets](qoder.md#global-assets) for the shared
presence-versus-use contract and [Agent Customize Routing](routing.md)
when MCP is only a supporting access layer for a Skill, Agent, Hook, or loop.
