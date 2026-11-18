# STAROps Agent API Reference

This skill uses STAROps OpenAPI version `2026-04-28` with ACS3-HMAC-SHA256 signing.

## Authentication

Requests are signed with direct credentials from the private STAROps config file when `accessKeyId` and `accessKeySecret` are present. If direct config credentials are not present, the script falls back to Alibaba Cloud Credentials default-chain credentials. The Python script builds the ACS3 canonical request, signs it with `ACS3-HMAC-SHA256`, and sends HTTPS requests directly.

The default endpoint is:

```text
starops.cn-beijing.aliyuncs.com
```

Override with `STAROPS_AGENT_ENDPOINT` when a different endpoint is required.

## CreateThread

```http
POST /digitalEmployee/{employeeId}/thread
```

Body:

```json
{
  "title": "short question title",
  "idempotencyKey": "deterministic-sha256-hex",
  "variables": {
    "workspace": "optional-workspace",
    "project": "optional-sls-project"
  },
  "attributes": {
    "source": "starops-qoder"
  }
}
```

`variables` contains whichever optional context values are configured: `workspace` for the STAROps workspace and `project` for the SLS Project name.
`idempotencyKey` is a deterministic SHA-256 hex string derived from the employee, compact question title, and request variables.

Expected response field:

```json
{
  "threadId": "thread-id"
}
```

## CreateChat

```http
POST /chat
```

Body:

```json
{
  "action": "create",
  "digitalEmployeeName": "employee-id",
  "threadId": "thread-id",
  "messages": [
    {
      "messageId": "uuid",
      "role": "user",
      "contents": [
        {
          "type": "text",
          "value": "user question"
        }
      ]
    }
  ],
  "variables": {
    "workspace": "optional-workspace",
    "project": "optional-sls-project"
  }
}
```

The response is an SSE stream whose `data:` payloads contain STAROps `messages`. The script stops when the stream emits a `done` message or a `task_finished` event, and it always closes the streaming HTTP response before exiting.

## Output Modes

JSONL mode emits structured records:

```jsonl
{"type":"thread","thread_id":"thread-id","starops_url":"https://starops.console.aliyun.com/chat?threadId=thread-id&assistantId=apsara-ops"}
{"type":"message","role":"assistant","content":"answer"}
{"type":"done","thread_id":"thread-id","status":"completed"}
```

Pipe mode emits:

```text
THREAD: thread-id
STAROPS_URL: https://starops.console.aliyun.com/chat?threadId=thread-id&assistantId=apsara-ops
=== STAROPS ANSWER BEGIN ===
answer
=== STAROPS ANSWER END ===
```

The console URL uses the same digital employee ID as `assistantId`.

Pipe mode writes progress to stderr, including tool status lines such as:

```text
[tool:started] query_metrics
[tool:running] generate_diagnosis_report
[tool:done] query_metrics
```

`generate_diagnosis_report` text chunks are also mirrored to stderr for live visibility and included in the final stdout answer block.
