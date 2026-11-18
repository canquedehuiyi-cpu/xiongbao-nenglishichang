---
name: domain-icp-filing
description: Use when users need ICP filing policy guidance, an official filing entry, filing order progress, or successful filing records through Alibaba Cloud Domain MCP.
license: Apache-2.0
metadata:
  owner: aliyun-domain-team
  role: domain-operations-expert
  connector: aliyun-domain
---

# Domain ICP Filing

Use the `aliyun-domain` MCP Connector for China ICP filing guidance, official filing handoff, and status queries.

## Tool routing

| Intent | MCP tool | Meaning |
|---|---|---|
| Ask policy, eligibility, materials, province, entity, or order-type questions | `icp_ask` | Returns guidance; creates no filing |
| Start or continue official data entry | `icp_fill` | Returns or opens an official page; does not prove submission |
| Query an in-progress order | `icp_status` | Requires a supported order, organizer, domain, or ICP identifier |
| Query successful filing data | `icp_info` | Returns successful records visible to the account |

## Workflow

1. Choose the narrowest tool matching the request and read its current description and Schema.
2. Ask only for the minimum non-secret identifier required by that tool.
3. Preserve the exact filing order, domain, organizer, or ICP number supplied by the user.
4. For non-terminal responses, report the current state, next responsible party or action, and identifier needed to resume.
5. Route website filing-number display updates to `domain-website-delivery`; they do not create or approve an ICP filing.

## Safety

- Treat organizer names, identity attributes, filing numbers, order IDs, phone numbers, and contact data as private.
- Never request identity documents, passwords, SMS codes, credentials, or OAuth tokens in chat.
- Browser opening and data entry are handoffs, not submission or approval.
- Use only the `aliyun-domain` Connector; do not bypass it with direct filing APIs or browser automation.

## Result

Report the queried identifier, MCP status, current filing state, write effect, privacy-safe evidence, and next action. Distinguish guidance returned, page opened, submitted, under review, approved, and completed.
