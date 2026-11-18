---
name: domain-commerce
description: Use when users need to register, renew, redeem, transfer in or out, configure automatic renewal, or manage fixed-price domain marketplace transactions through Alibaba Cloud Domain MCP.
license: Apache-2.0
metadata:
  owner: aliyun-domain-team
  role: domain-operations-expert
  connector: aliyun-domain
---

# Domain Commerce

Use the `aliyun-domain` MCP Connector for domain acquisition, retention, transfer, and marketplace workflows.

## Tool routing

- Registration and purchase: `check`, `price`, `buy`
- Renewal and expiry recovery: `renew`, `redeem`, `auto_renew`
- Transfer in: `transfer_in_check`, `transfer_in_apply`, `transfer_in_list`, `transfer_in_detail`
- Transfer out and locks: `transfer_out_request_code`, `transfer_out_apply`, `transfer_out_status`, `transfer_lock`
- Fixed-price marketplace: `trade_detail`, `trade_send_code`, `trade_publish`
- Asynchronous verification: `task_show`, `task_poll`, `task_list`, `task_history`, `task_history_detail`

## Workflow

1. Freeze the exact domain, action, duration, payment route, registrant profile, and transfer direction supplied by the user.
2. Read the current MCP tool description and input Schema. Use read tools to establish eligibility, state, and reference price.
3. Call a write tool first without confirmation fields to obtain its structured preview or handoff.
4. Show the exact target, amount or price uncertainty, irreversible effects, required identifiers, and whether the next action is browser handoff or direct submission.
5. Wait for fresh explicit confirmation. Then pass only the confirmation values returned or required by that preview and execute once.
6. Verify with the matching detail, list, task, or status tool. Stop at payment, review, SMS, asynchronous, or external handoff boundaries.

## Safety

- Never infer purchase approval from a request to check availability or price.
- Never supply payment, acknowledgement, confirmation, or plan fields before the user reviews the current preview.
- Never request or expose transfer codes, SMS codes, credentials, identity files, or payment secrets in chat.
- Never auto-retry a write or substitute a different domain, account, template, payment route, or marketplace path.
- Use only the `aliyun-domain` Connector; do not bypass it with another execution surface.

## Result

Report the exact domain, quote type, submitted action, MCP status, task or order identifier when returned, write effect, verification state, and next user action. Distinguish browser opened, order submitted, accepted, paid, transferred, and completed.
