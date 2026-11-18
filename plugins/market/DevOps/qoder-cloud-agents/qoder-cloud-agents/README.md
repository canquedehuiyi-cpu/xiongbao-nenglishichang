# Qoder Cloud Agents Plugin

Use QCA tools in Qoder to configure cloud Agents and Templates, run conversations, manage scheduled tasks, and inspect execution results.

## Workflows

- Managed: choose a model and Environment, create or reuse an Agent, create a Session, send a message, and observe its result.
- Managed Deployment: configure on-demand or scheduled Agent runs and inspect run history.
- Forward: use an existing Identity and Template to create or continue a Session.
- Forward Schedule: configure Template tasks, manage scheduling, and inspect execution results.
- Resources: discover existing files, Skills and Vaults and bind them where supported. This plugin does not provide Vault credential management or file upload workflows.

## Contents

- [Skill entrypoint](skills/qoder-cloud-agents/SKILL.md): workflow selection and basic tool use.
- [Tool calling guide](skills/qoder-cloud-agents/references/mcp-guide.md): arguments, pagination, events and lifecycle behavior.
- [Managed workflows](skills/qoder-cloud-agents/references/workflows.md) and [tool catalog](skills/qoder-cloud-agents/references/tool-catalog.md).
- [Forward workflows](skills/qoder-cloud-agents/references/forward-workflows.md) and [tool catalog](skills/qoder-cloud-agents/references/forward-tool-catalog.md).
- `mcp.json`: the CN QCA MCP connection configuration.
- [Connection setup](CONNECTORS.md): Qoder host prerequisites.
- `assets/logo.png`: plugin logo.

## Setup and use

1. Sign in to Qoder with an account that has Cloud Agents access.
2. Install and enable the plugin. Qoder supplies the QCA connection using its shared login state; no manual PAT setup is required.
3. Ask Qoder to run a cloud task, continue a conversation, or configure a scheduled task. The Skill guides tool selection and result observation.

Use the tools and schemas exposed by the current connection; this package does not pin an internal provider version or a fixed tool count.

## Source and verification

Integrated Skill source: `cloud-agent/qca-mcp-plugin`, commit `6171be97b9bd`, directory `skills/integrated/qoder-cloud-agents/`.

The Skill files were checked against that committed package. Package content checks do not establish live connection success or marketplace approval; verify installation, tool discovery and a read-only call in the target Qoder client before release.
