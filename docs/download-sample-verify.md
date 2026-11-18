# download-assets.js 小样本验证证据（执行批次 2 · B）

生成时间：2026-11-18（Windows / Git Bash / Node v24.22.1）。工作目录统一 `capability-assets/`。
样本量：**9 条**（清单 2566 条中的 0.35%），覆盖 skill / plugin / mcp 三种 kind 与 4 个类目目录。
本文所有数字为**实测**；标注「推断」的只有全量体积外推一节。

## 1. 实际执行的命令

```bash
node --check scripts/download-assets.js                      # 语法闸门
# 样本下载（公开 OSS 直链，无鉴权；--force 表示忽略断点索引重下）
node scripts/download-assets.js --kind skill --ids 812e60c0-5224-4bc3-a487-f740a4465cc3,9b6abf95-7eb2-4d72-a0ab-286b2360ca02,a389825d-886f-413b-9832-1c6ad135f59b,c9d76b69-0324-443e-ac14-d882f6f7920a,official_69VS2FFY --force
node scripts/download-assets.js --kind plugin --ids 1b69a031-e493-4936-b474-5cea9dfa24ee,e7de27b0-f08c-4893-8144-4419ae1aad42,e830da1b-8d75-4b40-ad52-aa103f780eea --force
node scripts/download-assets.js --kind mcp --ids github --force
# 断点续跑（第二次不带 --force，应全部 resumed，0 次下载）
node scripts/download-assets.js --kind skill --ids 812e60c0-...,9b6abf95-... --limit 2
# 失败/跳过机制自检（只写 .tmp-dl/selftest-docs/，不污染 repo/docs/）
node scripts/download-assets.js --manifest scripts/fixtures/selftest-manifest.ndjson --selftest
```
脚本只读取 leader 侧快照 `market-api/downloads-manifest.ndjson`、`market-api/details/**`、`market-api/catalog-top/**`，**无任何写入 `market-api/` 的代码路径**
（写入目标只有三类：`repo/{skills,plugins,connectors}/market/**`、`repo/docs/*`（`--selftest` 时改到 `.tmp-dl/selftest-docs/`）、以及 `.tmp-dl/run-*/` 里的临时 zip，逐资产 `finally` 删除 + 运行末清理），
故与 leader 正在增长的抓取文件零冲突。读到的快照规模（本次实测，`market-api/downloads-manifest.ndjson` 最后写入 11-18 17:35）：
清单 **2,566 行**、`catalog-top/**` 23 个类目目录共 **2,566 行**、`details/**` **2,571** 个文件；
leader 侧抓取若继续增长，重跑本脚本会读到新行，本文所有清单类数字随之作废。

## 2. 样本产物清单（实测）

| kind | id | 归档目录（repo/ 下） | files | zip 字节 | zip sha256（前 16） | tree sha256（前 16） |
|---|---|---|---|---|---|---|
| skill | 812e60c0-5224-… | `skills/market/Finance/moomoo-skill` | 1 | 5,255 | `496a9b6238b7a057` | `6afe51e35fafd89e` |
| skill | 9b6abf95-7eb2-… | `skills/market/Productivity/ego-browser` | 23 | 27,523 | `ef5662a2584c60c1` | `91594a2866a465c4` |
| skill | a389825d-886f-… | `skills/market/Finance/multi-strategy-quant-research-pro` | 99 | 326,623 | `e18b3e87ea44ac7e` | `3f98c1611886dc6b` |
| skill | c9d76b69-0324-… | `skills/market/Productivity/kb-result-qoder-build-v5-1-0` | 29 | 83,498 | `e858d293cc398d48` | `8a59bfa15acdda9e` |
| skill | official_69VS2FFY | `skills/market/Finance/alipay-aipay` | 106 | 445,144 | `ca24dd1d69b3b9e4` | `bb6f850c1ea712a2` |
| plugin | 1b69a031-e493-… | `plugins/market/Finance/moneypal` | 15 | 39,321 | `dcba81fb59ed32d0` | `0c41793e0d40b16f` |
| plugin | e7de27b0-f08c-… | `plugins/market/Tools-and-Automation/dify-canvas` | 4 | 5,031 | `64afb9a1c58c88fb` | `989a76eb7abcb73a` |
| plugin | e830da1b-8d75-… | `plugins/market/Finance/external-statement-reconcile` | 29 | 104,826 | `b112e25ce0855706` | `cb20a99adc81fb73` |
| mcp | github | `connectors/market/Coding/GitHub.json` | 1（配置模板） | — | — | `5d27abc4a1fc2c10` |

合计（实测 `du -sb` + 逐文件统计）：market 层 **315 个文件 / 2,798,301 字节**，其中解包内容 2,789,316 字节（脚本自身生成的 9 个 `manifest.json` 共 8,985 字节另计），8 个 zip 下载量 1,037,221 字节。
`files` 列 = 归档目录文件数 − 顶层 `manifest.json`（脚本按设计排除自身生成的清单，磁盘计数逐条一致）。
索引 `repo/docs/downloaded-index.ndjson` 9 行 / 9 唯一 id；`failures.ndjson`、`skipped.ndjson` 各 0 行（真实状态，非未运行）。

## 3. sha 可复算（两条独立路径）

1. **重下同一个包算 sha**：moomoo-skill
   `496a9b6238b7a057716e0b9051ae63a7d9224861d044cebe7204f05bb95c82d2`，5,255 字节 → 与 `manifest.json.zipSha256` 与索引逐字符相同。
2. **字节级保真对照**：把 a389825d 的 zip 重新下载并解到 `capability-assets/.tmp-dl/msq/`（脚本外的独立路径，验证后已清理，可复算），
   用同一 tree 摘要算法（排序后的 `相对路径:文件sha256` 串接再 sha256，只排除顶层 `manifest.json`）计算：

   | 对象 | files | tree sha256（前 16） |
   |---|---|---|
   | 新鲜上游解包 `.tmp-dl/msq` | 99 | `3f98c1611886dc6b` |
   | 归档 `repo/skills/market/Finance/multi-strategy-quant-research-pro` | 99 | `3f98c1611886dc6b` |
   | 索引记录 `downloaded-index.ndjson` | 99 | `3f98c1611886dc6b` |

   三者相同 ⇒ 归档内容与上游包**逐字节一致**（zip 本身不入仓，只留 sha256 与 size）。
3. 上游清单侧 sha 基线不可核：`downloads-manifest.ndjson` 的 `sha256` 字段与插件详情的 `file_hash` 已在 leader 侧抓取时被值级脱敏吃掉（见第 6 节），
   因此每个 `manifest.json` 写 `upstreamSha256: "UNAVAILABLE_REDACTED_BY_CLIENT"`，不冒充「已校验上游基线」。

## 4. 断点续跑 / 覆盖 / 体积闸门

- `--force` 后（第 1 节末三段）再跑一次不带 `--force` 的同 ids：`SUMMARY ok=0 resumed=2 skipped=0 fail=0 bytes=0 files=0`，无 HTTP 下载。
- zip sha 与索引一致才 SKIP（`archivePackage` 先比对 `zipSha256`，再比对 `treeSha256`），不一致则重取。
- `--max-file-bytes`（默认 95 MiB，GitHub 单文件硬上限 100 MB）：**实测触发**（把闸门压到 1 字节跑两条未归档资产，产物写临时目录，`repo/docs/` 未受影响，见 `docs/selftest-evidence/extracted-over-limit-skip.ndjson`）：

  ```
  SKIP skill official_kDUYwDw7 extracted_file_over_limit_4939B>cap_1B (skills/market/Agent-Evolution/majiayu000-skillsmith/majiayu000-skillsmith/SKILL.md)
  SKIP skill official_PpCTOekX extracted_file_over_limit_8291B>cap_1B (skills/market/Agent-Evolution/self-improving-agent-next/self-improving-agent-next/references/examples.md)
  SUMMARY ok=0 resumed=0 skipped=2 fail=0 bytes=0 files=0
  ```

  两条均**下载并解包后**才发现超限 ⇒ 脚本删除该资产目录后只记 `skipped.ndjson`（实测 `repo/skills/market/` 下无残留，脚本另建的空类目目录 `Agent-Evolution/` 已手工回收），
  索引与 9 条样本状态保持不变（`downloaded-index.ndjson` 仍 9 行 / `skipped.ndjson` 0 行 / `failures.ndjson` 0 行）。

## 5. skipped / failures 机制实证（`--selftest`）

```
SKIP skill selftest_no_url no_zip_url_in_detail
SKIP skill selftest_bad_status detailStatus_500_not_200
FAIL skill selftest_sha_mismatch sha256_mismatch
FAIL skill selftest_404 fetch_failed
SUMMARY ok=0 resumed=0 skipped=2 fail=2 bytes=0 files=0
```

落盘原文已快照到 `docs/selftest-evidence/`（运行期临时目录 `.tmp-dl/` 已清理，重跑上面命令可复现）：

```
skipped.ndjson : {"id":"selftest_no_url", "reason":"no_zip_url_in_detail"}
                 {"id":"selftest_bad_status","reason":"detailStatus_500_not_200"}
failures.ndjson: {"id":"selftest_sha_mismatch","reason":"sha256_mismatch","expected":"0000...（故意错值）"}
                 {"id":"selftest_404","reason":"fetch_failed","err":"HTTP_403"}
```

要点：清单里 `note=no_zip_url_in_detail` 的行**不发起下载**（连接器 128 条全部走配置模板分支，不经 zip）；
`detailStatus≠200` 同理；sha 校验发生在**解包之前**，不匹配时不写任何资产文件；OSS 对缺失对象返回 **403**（不是 404），重试 2 次后记 failure 并继续下一 id（`--retries` 可调，`--concurrency` 上限 4，脚本内强制 clamp）。
真实样本运行的 `skipped.ndjson`/`failures.ndjson` 为 0 行，与 selftest 的两个文件分开存放。

## 6. 脱敏规则 v3 修正（重要披露，影响批次 1 的 staging）

首版沿用批次 1 的 `KEY_RE`（键名 + `:`/`=` + 值）对第三方包体做替换，实测**误伤源代码**：

| 上游原文（真实样本，来自 `repo` 内文件） | v2 规则产出（破坏语义） |
|---|---|
| `week_key = date_str[:10]` | `week_key=<REDACTED>]` |
| `config.app_private_key = ALIPAY_CONFIG['privateKey']` | `config.app_private_key=<REDACTED>'privateKey']` |
| `def prompt_missing(..., *, secret: bool = False)` | `secret:<REDACTED> = False` |
| `"temporaryUrlAllowlist": {"host": ...}`（JSON） | `"authorization":<REDACTED>"host":...` → **整份 policy-rules.json 无法解析** |

v2 下 8 个包 297 个文本文件里替换了 **25 个文件**；判定为凭据密度极低但破坏面高（移植目标要求资产可用）。
新增 `looksSecret()` 值形态闸门（拒绝：引号字面量、`{[(`/`)]>` 结构位、裸标识符与类型关键字、URL、非 ASCII 文本、含 `()[]{}|;:&<>?*~\` 等代码语法；接受：PEM 私钥头、≥12 字符且字母+数字混合的高熵串）后：

- 重跑同样 8 个包：`textFilesScanned=297 filesRedacted=0 kvRedactions=0 jwtRedactions=0 prefixedSecretRedactions=0 codeishCandidatesKept=49`；
- 上述 4 行全部恢复上游原文，`policy-rules.json` 等 **23 个 JSON 全部可解析**（实测 `unparseable=0`），第 3 节 tree 摘要与上游一致；
- 「宁可漏脱敏、不可误改代码」的补偿措施：**保守放行的候选键名清单**写入 `repo/docs/download-report.json` 的 `codeishCandidatesKeptList`
  （只记 `文件 + 键名 + 值长度`，不记值），推送前由人抽查。抽查最长两条：`seller_unique_id_key=seller_id`（文档正文）、`const token = argv[index]`（CLI 解析），均非凭据；
- 已知令牌形态（`ghp_`/`github_pat_`/`sk-`/`xox*`/`AKIA`/`ya29.`/`Bearer <24+>`）与 JWT 的规则**未放宽**，market 层实测命中 0；
- 连接器配置模板另走白名单 + 键名脱敏（`MCP_KEEP`/`MCP_DROP`），凭据位保留空串或 `<REDACTED>` 并加 `_note`，不受此放宽影响。

**遗留**：`stage-assets.js` 已同步 v3 规则，但批次 1 已产出的 `skills/local-installed/**`、`plugins/local-installed/**`、
`plugins/market-feed/**` 是 v2 规则产物，其中含同类误伤（例如上游代码里的 `xxx_key=<REDACTED>` 形态）。
要按 v3 重出 staging 只需 `node scripts/stage-assets.js`（C 盘只读、只写 repo/），属批次 1 范围，本批次未执行——由 leader 决定。

## 7. 抽样限制

样本 9 条来自 `devops`/`Finance`/`Productivity`/`Coding` 等类目的头部条目（含 1 条 mcp、3 条 plugin、5 条 skill），
最大包 445 KB、最深路径 163 字符，**未覆盖**：>95 MiB 单文件、含二进制的包、同名冲突需 `__<短id>` 后缀的包、非 ASCII 资产名、
连接器 127 条中除 `github` 之外的 126 条。全量跑（2566 条）按非目标要求未执行。
