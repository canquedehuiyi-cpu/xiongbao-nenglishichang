# AlibabaCloud Workbench

Operate Alibaba Cloud ECS instances without public IPs via the `workbench` CLI. Run remote commands, transfer files up to 1GB, and query instances and sessions.

- **Category**: DevOps
- **Developer**: Alibaba Cloud
- **Documentation**: https://www.alibabacloud.com/help/zh/ecs/user-guide/connect-to-an-instance-through-workbench-cli

## Structure

```plaintext
alibabacloud-workbench/
├── .qoder-plugin/
│   └── plugin.json                                # Metadata manifest (must sit at the package root)
├── skills/
│   └── alibabacloud-workbench-cli/
│       └── SKILL.md                               # Bundled skill
├── rules/
│   └── alibabacloud-workbench.md                  # Role instructions / behavioural rules
├── CONNECTORS.md                                  # Connector dependencies (none)
└── README.md
```

## Prerequisites

1. The `workbench` CLI is installed locally:

   ```bash
   curl -fsSL https://workbench-cli.oss-cn-hangzhou.aliyuncs.com/install.sh | bash   # Linux / macOS
   ```

   ```powershell
   irm https://workbench-cli.oss-cn-hangzhou.aliyuncs.com/install.ps1 | iex          # Windows
   ```

2. Alibaba Cloud credentials are configured in `~/.workbench/config.json` (mode `0600`). Five authentication modes are supported: AK, StsToken, RamRoleArn, CredentialsCmd, CredentialsURI.
3. The user or role has the required RAM permissions (policy in the `RAM Permissions` section of the bundled `SKILL.md`).
4. Network access to `*.aliyuncs.com` and the Workbench backend WebSocket endpoints.

## Example prompts

- "List the running instances in cn-hangzhou."
- "Upload ./app.jar to /opt/app/ on i-bp1xxxx and restart the service."
- "nginx returns 502 on i-bp1xxxx — investigate."
- "Show disk usage and the top memory consumers on i-bp1xxxx."

## Versions

- 1.0.0 — initial release, bundles the `alibabacloud-workbench-cli` skill.
