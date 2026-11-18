# STAROps 本地检查

Use this command to check local prerequisites for the STAROps plugin. This check must not call STAROps OpenAPI or create a STAROps thread.

## Workflow

1. Locate the skill root: `skills/starops`.
2. Install Python dependencies if they are missing:

```bash
pip3 install -r scripts/requirements.txt
```

3. Run the local setup checker from the skill root:

```bash
python3 scripts/check_starops_setup.py
```

4. If the user provides a config path, pass it explicitly:

```bash
python3 scripts/check_starops_setup.py --config ".starops/config.json"
```

## Scope

This command checks local config files, the required STAROps `employeeId` value, optional `workspace` (STAROps workspace) and `project` (SLS Project) values, Python dependencies, and direct AK/SK values in private STAROps config files. The preferred setup is a private `.starops/config.json`; the Alibaba Cloud Credentials default chain is checked only when direct config credentials are not present.

It does not verify whether credentials are valid in Alibaba Cloud, whether RAM permissions include `starops:CreateThread` and `starops:CreateChat`, or whether the configured `employeeId` can access the specified STAROps workspace / SLS Project. Those failures are reported by the real STAROps diagnosis call.
