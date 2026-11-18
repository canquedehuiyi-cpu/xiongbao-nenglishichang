# STAROps 诊断

Use this command when the user wants to diagnose service errors, root causes, alerts, APM metrics, workspace topology, or STAROps-related incidents.

## Workflow

1. Use the `starops` skill.
2. Before the first real diagnosis, ensure dependencies are installed:

```bash
pip3 install -r scripts/requirements.txt
```

3. Send the complete user context to STAROps. Configured STAROps workspace / SLS Project values are forwarded as request variables; still include the time range, service, region, and symptom details. Always run from the skill root and always pass `--pipe`:

```bash
python3 scripts/call_starops_agent.py --question "<complete user context>" --pipe
```

4. For follow-up questions in the same investigation, reuse the previous `THREAD` value:

```bash
python3 scripts/call_starops_agent.py --thread "<thread_id>" --question "<follow-up question>" --pipe
```

5. Base the final answer only on text between `=== STAROPS ANSWER BEGIN ===` and `=== STAROPS ANSWER END ===`.

## Guardrails

- Do not fabricate root causes when STAROps returns an error or empty answer.
- Do not print Alibaba Cloud AccessKey, Secret, or STS token values.
- Report HTTP 401/403/404 errors directly and ask the user to check credentials, RAM permissions, the STAROps digital employee ID, and optional STAROps workspace / SLS Project context.
