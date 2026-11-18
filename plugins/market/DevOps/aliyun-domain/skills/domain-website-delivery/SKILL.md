---
name: domain-website-delivery
description: Use when users need Wanxiaozhi AI website creation, project and conversation management, materials, generated content or code, preview, domain binding, certificates, deployment, rollback, or analytics through Alibaba Cloud Domain MCP.
license: Apache-2.0
metadata:
  owner: aliyun-domain-team
  role: domain-operations-expert
  connector: aliyun-domain
---

# Domain Website Delivery

Use the `aliyun-domain` MCP Connector to create and operate Wanxiaozhi websites from requirements through preview and publication.

## Tool routing

- Account and projects: `wxz_account`, `wxz_project`
- Conversations and generation: `wxz_chat_start`, `wxz_chat_send`, `wxz_chat_history`, `wxz_chat_resume`, `wxz_chat_generate`, `wxz_chat_reconnect`, `wxz_conversation`
- Preview and release: `wxz_preview`, `wxz_deploy`, `wxz_site`
- Content and assets: `wxz_code`, `wxz_content`, `wxz_material_directory`, `wxz_material_file`, `wxz_skill`
- Analytics: `wxz_analytics_daily`

## Workflow

1. Freeze any user-supplied project ID, conversation ID, chat ID, domain, or channel. If no project ID is known, list projects and ask the user to choose when the result is ambiguous.
2. Read the selected MCP tool description and Schema. Keep requirement gathering, generation, preview, binding, certificate state, publication, and online state as separate stages.
3. For quota-consuming, publishing, rollback, online/offline, binding, unbinding, certificate, deletion, or persistent-state changes, call without confirmation fields to obtain a preview.
4. Show the exact project, domain, channel, operation, side effects, and returned confirmation values. Wait for fresh explicit approval, execute once, then verify with status or readback tools.
5. Stop at user-input, review, certificate issuance, DNS propagation, or pending deployment boundaries and return the identifier needed to resume.

## Safety

- Never substitute another visible project or domain for an inaccessible target.
- Domain registration, ICP approval, DNS saving, certificate binding, project preview, deployment acceptance, and public availability are independent states.
- Never read or print private-key contents, credentials, verification tokens, or other protected material.
- Never auto-confirm or auto-retry a write.
- Use only the `aliyun-domain` Connector; do not fall back to direct website APIs, a local CLI, HTTP requests, or console automation.

## Result

Report the exact project and domain, MCP status, preview or deployment URL when returned, write effect, verification state, and next action. Never label a preview as published or an accepted deployment as publicly live.
