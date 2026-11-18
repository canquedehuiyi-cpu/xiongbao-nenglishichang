# STAROps RAM Policy Notes

This skill can use direct credentials from a private STAROps config file, or Alibaba Cloud Credentials default-chain behavior. Prefer private local config files for this plugin, and use standard Alibaba Cloud credential sources as fallback options.

## Required Access

Grant the caller the following STAROps actions:

| Action | Description |
|--------|-------------|
| `starops:CreateThread` | Create an investigation thread |
| `starops:CreateChat` | Send a message and stream the agent response |

### Example Custom Policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "starops:CreateThread",
        "starops:CreateChat"
      ],
      "Resource": "acs:starops::*:digitalemployee/*"
    }
  ]
}
```

The wildcard resource allows access to matching STAROps digital employees. For least-privilege access, replace it with the exact resource ARN used by your STAROps/RAM setup.

## Recommended Credential Sources

Recommended: put credentials in the private STAROps config file. If that is not suitable, use one of the Alibaba Cloud Credentials default-chain sources.

- Direct credentials in private STAROps config files.
- Alibaba Cloud CLI profile.
- Standard Alibaba Cloud AccessKey environment credentials.
- STS environment credentials.
- Shared credentials SDK profile.
- RAM role credentials.
- ECS instance metadata credentials, when available.

### Direct STAROps Config Credentials

Private STAROps config files may include direct credentials. The script uses these values directly instead of the default chain when both `accessKeyId` and `accessKeySecret` are present:

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

Do not commit config files containing `accessKeySecret` or `securityToken`.

### Alibaba Cloud CLI Profile

Alternative for local development:

```bash
aliyun configure
```

This creates or updates `~/.aliyun/config.json`, which the Alibaba Cloud Credentials default chain can read.

To use a non-default CLI profile:

```bash
export ALIBABA_CLOUD_PROFILE="<profile-name>"
```

### Environment Credentials

Alternatively, use environment variables directly:

```bash
export ALIBABA_CLOUD_ACCESS_KEY_ID="<access-key-id>"
export ALIBABA_CLOUD_ACCESS_KEY_SECRET="<access-key-secret>"
```

For STS credentials, include the security token:

```bash
export ALIBABA_CLOUD_ACCESS_KEY_ID="<sts-access-key-id>"
export ALIBABA_CLOUD_ACCESS_KEY_SECRET="<sts-access-key-secret>"
export ALIBABA_CLOUD_SECURITY_TOKEN="<sts-token>"
```

### Shared Credentials Profile

For a persistent local profile, create `~/.alibabacloud/credentials.ini`:

```ini
[default]
type = access_key
access_key_id = <access-key-id>
access_key_secret = <access-key-secret>
```

To use a non-default section:

```bash
export ALIBABA_CLOUD_PROFILE="<profile-name>"
```

The default chain also honors `ALIBABA_CLOUD_CREDENTIALS_FILE` when the credentials file is stored outside the default path.

For local development environments where metadata lookup causes delays, set:

```bash
export ALIBABA_CLOUD_ECS_METADATA_DISABLED=true
```

## Security Boundaries

This skill creates STAROps investigation threads and streams STAROps Agent answers. It does not directly mutate ECS, OSS, RDS, SLS, or other cloud resources. Any operational action proposed by STAROps should still be reviewed according to the user's normal change-management process.

## Permission Failure Handling

When the script returns an HTTP 401 or 403 error indicating an authorization failure:

1. Stop immediately. Do **not** retry with different credentials or fabricate diagnostic results.
2. Report the exact error message to the user, including the `Action` and `Resource` from the error response.
3. Direct the user to check that their identity has the required STAROps permissions listed in the **Required Access** section above.
4. If using STS credentials, verify that the STS token has not expired and that the assumed role's policy includes `starops:CreateThread` and `starops:CreateChat`.
5. Wait for the user to confirm that permissions have been granted before retrying.
