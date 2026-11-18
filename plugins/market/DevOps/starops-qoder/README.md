# STAROps Qoder Plugin

This Qoder plugin packages the Alibaba Cloud STAROps Agent diagnostic skill for Qoder workflows.

## Capabilities

- Diagnose service errors and root causes.
- Query STAROps workspace topology and APM service metrics.
- Triage alerts and incident context through STAROps Agent.
- Preserve STAROps thread context for follow-up questions.

## Local Setup

Install dependencies from the skill root:

```bash
cd skills/starops
pip3 install -r scripts/requirements.txt
python3 scripts/check_starops_setup.py
```

The setup checker is local-only. It does not call STAROps OpenAPI or verify cloud-side RAM permissions.

## Configuration

Recommended: create a private JSON config file at `~/.starops/config.json`. Repository-local `.starops/config.json` and `STAROPS_AGENT_CONFIG` are also supported for local overrides.

The only required STAROps routing value is `employeeId`:

```json
{
  "employeeId": "<digital-employee-id>"
}
```

`workspace` is the optional STAROps workspace. `project` is the optional SLS Project name. When set, the script forwards these values as request variables:

```json
{
  "employeeId": "<digital-employee-id>",
  "workspace": "<optional-workspace>",
  "project": "<optional-sls-project>"
}
```

The same STAROps config file may also provide credentials directly. This is the preferred local setup because it keeps STAROps connection values and credentials in one private file. Do not commit this file or paste secret values into chat:

```json
{
  "employeeId": "<digital-employee-id>",
  "workspace": "<optional-workspace>",
  "project": "<optional-sls-project>",
  "accessKeyId": "<access-key-id>",
  "accessKeySecret": "<access-key-secret>",
  "securityToken": "<optional-sts-token>"
}
```

Alternative: provide STAROps values with environment variables:

```bash
export STAROPS_AGENT_EMPLOYEE="<digital-employee-id>"
export STAROPS_AGENT_WORKSPACE="<optional-workspace>"
export STAROPS_AGENT_PROJECT="<optional-sls-project>"
```

## Alibaba Cloud Credentials

The plugin signs STAROps requests with direct credentials from the private STAROps config file when present; otherwise it falls back to the Alibaba Cloud Credentials default chain. Configure one of these credential sources before running diagnosis.

Recommended: put `accessKeyId`, `accessKeySecret`, and optional `securityToken` in the private STAROps config file shown above. When present, the script uses those values directly instead of the default chain.

Alternative: use Alibaba Cloud CLI's standard profile flow. The credentials SDK reads the generated `~/.aliyun/config.json`.

```bash
aliyun configure
```

If you use a non-default CLI profile, select it before running setup or diagnosis:

```bash
export ALIBABA_CLOUD_PROFILE="<profile-name>"
```

Alternative: use environment variables directly:

```bash
export ALIBABA_CLOUD_ACCESS_KEY_ID="<access-key-id>"
export ALIBABA_CLOUD_ACCESS_KEY_SECRET="<access-key-secret>"
```

If you use STS credentials, also set:

```bash
export ALIBABA_CLOUD_SECURITY_TOKEN="<sts-token>"
```

Alternative: create a credentials SDK profile at `~/.alibabacloud/credentials.ini`:

```ini
[default]
type = access_key
access_key_id = <access-key-id>
access_key_secret = <access-key-secret>
```

Use another SDK profile by setting:

```bash
export ALIBABA_CLOUD_PROFILE="<profile-name>"
```

The identity must have `starops:CreateThread` and `starops:CreateChat` permissions on the target STAROps digital employee. Do not store AccessKey, Secret, or STS token values in plugin files.

## Invocation

The skill always calls STAROps with pipe output:

```bash
python3 scripts/call_starops_agent.py --question "<complete user context>" --pipe
```

For follow-up questions, reuse the `THREAD` returned by the previous call:

```bash
python3 scripts/call_starops_agent.py --thread "<thread_id>" --question "<follow-up question>" --pipe
```
