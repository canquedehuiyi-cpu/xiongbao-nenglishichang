# 凭据扫描与脱敏规则

扫描范围：staging 内所有文本文件（.md .json .txt .yaml .yml .js .ts .mjs .cjs .py .sh .ps1 .env .toml .ini .cfg .html .css .sql .csv）。

规则：
1. `KEY_RE`：`api[_-]?key|apikey|secret[_-]?key|access[_-]?key|accesskey|secret|token|access_token|refresh_token|bearer[_-]?token|password|passwd|cookie|authorization|x[_-]?api[_-]?key` 后跟 `:`/`=` 的值 → 替换为 `<REDACTED>`（键名保留）。
2. `JWT_RE`：`eyJ...` 形式的 JWT → `<REDACTED_JWT>`。
3. `PREFIXED_SECRET_RE`：已知前缀令牌（`ghp_/gho_/ghu_/ghs_/ghr_`、`github_pat_`、`sk-`、`xox[baprs]-`、`AKIA`、`ya29.`、`Bearer <24+>`）→ `<REDACTED_SECRET>`。
4. 保留不动：占位符值（`<...>`、`${...}`、`your-*`、`xxx`、`example`、`changeme`、`none`、`test`、`dummy` 等）与 64 位 sha256 基线；v1 的「40+ 位十六进制盲替换」已移除（会误伤 git commit 与文档示例）。
5. 本机主目录绝对路径（含用户名）只对**本机生成的**连接器配置模板匿名化为 `<HOME>/`；第三方技能/插件内容原样保留（内部路径不改写）。命中清单中的源路径以 `~/.qoder-cn/...` 形式显示，不含用户名。

本次实测结果：文件扫描 4026 个，命中 10 个文件；键值替换 21 处，JWT 替换 0 处，前缀令牌替换 0 处，占位符保留 10 处；本机绝对路径匿名化 3 处。

命中清单（前 40 条）：

```
~/.qoder-cn/skills/electron-app-dev/references/packaging.md kv=1 jwt=0 pfx=0
~/.qoder-cn/plugins/cache/qoder-marketplace/cloudbase/0.2.0/hooks/plugin-telemetry.mjs kv=1 jwt=0 pfx=0
~/.qoder-cn/plugins/cache/qoder-marketplace/mobile-use/0.7.5/canvases/android-project/simulator/host.cjs kv=1 jwt=0 pfx=0
~/.qoder-cn/plugins/cache/qoder-marketplace/oceanbase-skills/2.0.1/skills/seekdb/docs/seekdb-docs/200.develop/500.vector-embedding/200.ai-embed-function.md kv=1 jwt=0 pfx=0
~/.qoder-cn/plugins/cache/qoder-marketplace/oceanbase-skills/2.0.1/skills/seekdb/docs/seekdb-docs/200.develop/600.search/400.semantic-search.md kv=1 jwt=0 pfx=0
~/.qoder-cn/plugins/cache/qoder-marketplace/oceanbase-skills/2.0.1/skills/seekdb/docs/seekdb-docs/500.tutorials/100.create-ai-app-demo/600.build-a-rag-system-with-seekdb.md kv=2 jwt=0 pfx=0
~/.qoder-cn/plugins/cache/qoder-marketplace/oceanbase-skills/2.0.1/skills/seekdb/docs/seekdb-docs/500.tutorials/200.scenarios/60.experience-ai-function.md kv=11 jwt=0 pfx=0
~/.qoder-cn/plugins/cache/qoder-marketplace/oceanbase-skills/2.0.1/skills/seekdb/docs/seekdb-docs/500.tutorials/200.scenarios/70.experience-hybrid-vector-index.md kv=1 jwt=0 pfx=0
~/.qoder-cn/plugins/cache/qoder-marketplace/site-audit/1.0.0/fixtures/synthetic-site/tools/serve.js kv=1 jwt=0 pfx=0
plugins/market-feed/mobile-use/mobile-use/canvases/android-project/simulator/host.cjs kv=1 jwt=0 pfx=0
```

残留风险：非文本文件（png/wasm/exe 等）未扫描，且已被排除在 staging 之外；`.env` 类文件按规则 1 处理；无法覆盖自定义命名的凭据字段（如 `QODER_PAT=...` 之外的形态），入库前建议 leader 再做一次针对性 grep。
