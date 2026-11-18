---
name: domain-governance
description: Use when users need domain portfolio queries, DNS and DNSSEC management, nameserver or glue records, security locks, contacts, registrant templates, real-name verification, email verification, groups, remarks, or audit history through Alibaba Cloud Domain MCP.
license: Apache-2.0
metadata:
  owner: aliyun-domain-team
  role: domain-operations-expert
  connector: aliyun-domain
---

# Domain Governance

Use the `aliyun-domain` MCP Connector to inspect and govern domain assets, ownership data, DNS, security controls, and operational history.

## Tool routing

- Assets and audit: `list`, `detail`, `search`, `history`, `task_list`, `task_show`, `task_poll`, `task_history`, `task_history_detail`
- Organization: `group_list`, `group_create`, `group_rename`, `group_move`, `group_delete`, `remark`
- DNS records: `dns_list`, `dns_detail`, `dns_lines`, `dns_logs`, `dns_create`, `dns_update`, `dns_enable`, `dns_disable`, `dns_delete`
- Registry DNS: `dnshost_list`, `dnshost_create`, `dnshost_update`, `dnshost_delete`, `dnssec_list`, `dnssec_enable`, `dnssec_update`, `dnssec_disable`, `nameserver_set`
- Security: `transfer_lock`, `update_lock`, `server_lock_check`, `server_lock_detail`, `server_lock_list`, `server_lock_max_years`
- Identity: `contact`, `set_contact`, `template_list`, `template_create`, `template_update`, `template_delete`, `template_set_default`, `template_regions`, `template_validate`, `template_verify`, verification and email tools

## Workflow

1. Preserve the exact domain, zone, record ID, group ID, template ID, task ID, and requested before/after state.
2. Read the selected MCP tool description and Schema. Use a matching read tool before any write.
3. For writes, call without confirmation fields to obtain a preview. Show target, before/after values, side effects, and returned plan identifier.
4. Wait for fresh explicit confirmation, execute once with the preview-bound confirmation fields, then read back the same resource.
5. Report saved control-plane state separately from DNS propagation, registry completion, or identity-review completion.

## Safety

- Registrar ownership, Alidns zone hosting, nameserver delegation, Glue Records, and DNSSEC are separate resources; never substitute one as evidence for another.
- Do not expose contact details, email tokens, TXT verification values, identity documents, credentials, or private keys.
- An empty list does not authorize creation. Never invent record, group, template, task, or domain identifiers.
- Never combine contact, DNS, lock, transfer, or deletion changes under one confirmation.
- Use only the `aliyun-domain` Connector; stop if its required tool is unavailable.

## Result

Return the exact resource, MCP status, before/after state, plan or task identifier when applicable, write effect, verification result, and remaining propagation or review state.
