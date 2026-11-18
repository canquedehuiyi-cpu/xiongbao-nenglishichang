---
name: domain-discovery
description: Use when users need domain availability checks, registration or renewal price estimates, public WHOIS data, suffix pricing, or general domain-industry guidance through Alibaba Cloud Domain MCP.
license: Apache-2.0
metadata:
  owner: aliyun-domain-team
  role: domain-operations-expert
  connector: aliyun-domain
---

# Domain Discovery

Use the `aliyun-domain` MCP Connector to research domain candidates without creating orders or changing cloud resources.

## Tool routing

| Intent | MCP tool |
|---|---|
| Check whether an exact domain can be registered | `check` |
| Query an exact-domain or suffix reference price | `price` |
| Query public registration data | `whois` |
| Ask domain policy or lifecycle questions | `ask` |

## Workflow

1. Require an exact domain or suffix when the selected tool needs one; never invent candidates unless the user asks for ideation.
2. Read the current MCP tool description and input Schema before calling it.
3. Keep availability, price, marketplace status, and public registration data separate.
4. Report the returned source and status. `available=false` does not prove a marketplace listing exists, and a reference price is not a final charge.
5. Stop after the requested read-only result. Route purchasing, renewal, transfer, or listing work to `domain-commerce`.

## Safety

- Use only tools from the `aliyun-domain` Connector. Do not fall back to a local CLI, raw OpenAPI, SDK, HTTP request, or console automation.
- Do not request credentials or private account data for public checks.
- Treat empty results as valid evidence; do not broaden filters or fabricate identifiers to force a match.
- If the Connector is unavailable, report the dependency failure and stop.

## Result

Return the exact target, availability or price semantics, evidence source, MCP status, write effect (`none`), and the next optional Skill.
