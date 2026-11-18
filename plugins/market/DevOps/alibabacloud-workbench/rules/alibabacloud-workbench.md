# AlibabaCloud Workbench

Operate Alibaba Cloud ECS instances — especially those **without public IP addresses** — through the `workbench` CLI. No public IP, no bastion host, and no open port 22 required. The link is: CLI → local daemon → WebSocket → Workbench backend → ECS instance.

## Capabilities

- Remote command execution: `workbench exec` (non-interactive, millisecond-level)
- File distribution and retrieval: `workbench upload` / `workbench download` (up to 1GB, relayed via OSS)
- Inventory queries: `workbench list ecs` (filter by region, status, tags, instance name, etc.)
- Session and daemon lifecycle: `workbench session` / `workbench daemon`

Full flag reference, JSON schemas, exit codes, and the troubleshooting matrix live in the bundled skill `skills/alibabacloud-workbench-cli/SKILL.md`.

## Workflow

1. **Verify the environment** — run `workbench version` and `workbench config list` to confirm the binary is available and an active credential profile exists.
2. **Identify the target** — if the user did not provide an instance ID, locate it with `workbench list ecs --region <region> --output json` and confirm the target with the user.
3. **Execute** — prefer `--output json` for structured results. Each `exec` call runs in an independent shell context; chain with `&&` when shared context is needed.
4. **Verify** — check both `exit_code` and `stderr`. After a file transfer, confirm with `ls -l` and a checksum.
5. **Wrap up** — close sessions with `workbench session close --all` when a batch of work is done, and summarize what was changed.

## Rules

- **Diagnose before mutating** — troubleshooting tasks stay read-only (logs, processes, disk, config).
- **Confirm destructive actions** — restarting services, deleting files, overwriting configuration, or changing security settings requires explicit user confirmation, with a backup taken first whenever possible.
- **Never use interactive commands** — do not invoke `workbench connect`; it requires a TTY and will block.
- **Protect credentials** — never echo AccessKeySecret; `~/.workbench/config.json` must stay at `0600`.
- **Background long jobs** — for work exceeding 30 seconds use `nohup` or `systemd-run` and poll the log instead of raising `--timeout`.
- **Explain failures** — map the exit code to a cause and a next action rather than retrying blindly.
