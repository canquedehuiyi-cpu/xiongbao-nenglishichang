# 推送前检查单（capability-assets/repo → GitHub）

适用对象：执行推送的 leader。本检查单只描述操作，**本批次未执行任何 `git add` / `commit` / `push` / `git config`**。
当前状态（实测）：`git log --oneline` 只有上游 `52b98d0 Initial commit`；`git status --porcelain` = 6 行
（` M README.md` + `?? catalog/ connectors/ docs/ plugins/ skills/`），**暂存区为空**；`core.longpaths` 未设置（`git config --get` 退出码 1）。

仓库现有体量（实测，不含 `.git`；本检查单与验证据落盘后的快照，此数随文档增删按 KB 级变动，推送前按 §3 末的对账命令复核）：
**4,702 个文件 / 75,036,437 B（≈71.6 MiB）**
按目录：`plugins/local-installed` 45,552,340 B（3,563 文件）、`plugins/market-feed` 25,665,347 B（642）、
`skills/market` 2,446,063 B（263）、`skills/local-installed` 772,990 B（161）、`plugins/market` 338,426 B（51）、
`catalog` 102,190 B（3）、`connectors/market-metadata` 62,168 B（1）、`connectors/market` 13,812 B（1）、
`docs` 74,816 B（13 文件，其中 11 个为本批新增：`download-sample-verify.md`、`push-checklist.md`、`category-dir-map.json`、`downloaded-index.ndjson`、`download-report.json`、`size-probe.json`、`skipped.ndjson`、`failures.ndjson`、`selftest-evidence/`×3）。
对账：4,376（批次 1 存量）+ 315（market 层样本）+ 11（本批新增 docs）= **4,702** ✓。

---

## 1. 超长路径处置（三方案对比 + 推荐）

事实（实测，路径长度按**仓库内相对路径**计）：最长 241 字符
（`plugins/local-installed/qoder-marketplace/oceanbase-skills/skills/seekdb/docs/seekdb-docs/450.reference/200.sql/…/400.json-formatted-data-type-conversion-of-syntax.md`），
相对路径 ≥240 的 2 个、≥200 的 345 个，全部集中在 `oceanbase-skills/skills/seekdb/docs/**` 这一文档树。
当前工作副本的绝对路径前缀 65 字符（本机 checkout 根，记作 `<WORKSPACE>`），241 + 65 + 1 = 307 > 260（Win32 `MAX_PATH`），
这就是批次 1 里 `git ls-files` 报 20 条 `Filename too long`、可见文件数少于磁盘实际数的成因。
market 层最深相对路径 163 字符（实测），**下载不会引入新的超长路径**。

| 方案 | 做法 | 优点 | 代价 / 风险 |
|---|---|---|---|
| **A. 仓库级 `core.longpaths=true`** | `git -C <repo> config core.longpaths true`（**只写 `.git/config`，不入库、不影响他机**），随后由 leader 在自己克隆处同样执行一次或用 `git clone -c core.longpaths=true` | 零内容改动，保真 100%；Windows 上 Git for Windows 自带 longpaths 支持 | 只保护 Windows 本地：GitHub 侧与 macOS/Linux 不受影响；**每个 Windows 克隆者都要自己设**，否则他们 checkout 报错；CI 上的 Windows runner 需显式加 `-c core.longpaths=true`；`.git/config` 不受版本控制 ⇒ 是「口头约定」而非仓库不变量 |
| **B. 缩短目录名（改名 + 原名写回 manifest）** | 把 `oceanbase-skills/.../450.reference/200.sql/…` 这段深链压平（如 `…/seekdb-docs/450-reference-200-sql-…/<短名>.md`），并在该 skill 的 `manifest.json` 增加 `pathRewrite` 表（原相对路径 → 新路径 + 每个文件 sha256） | 仓库自洽，任何客户端/CI 都能直接 checkout；不依赖用户配置；可用 manifest 无损还原原树 | 第三方正文被改动（与「原样保留上游内容」的既有承诺冲突，需在 README 显式披露）；改名脚本 + 还原脚本要维护；改后 `treeSha256` 与上游不再相等（保真证据链断在改名层） |
| **C. 排除该文档树 + README 披露** | 只留 `oceanbase-skills` 的 `SKILL.md` + `scripts/`，把 `skills/seekdb/docs/**`（≥200 字符的 345 个文件所在树）整体排除，写 `docs/EXCLUDED.md` 记被排除的原路径、文件数、字节数与「按需从上游重取」的说明 | 提交体积同时下降（这一树是 45.5 MB 的主要构成之一），路径风险与体量风险一次解决；不需要任何 git 配置 | 资产不完整（seekdb 参考文档是该 skill 的主要内容之一）；需要 leader 确认「不完整」可接受 |

**推荐：A 为主 + C 为备选，不推荐 B。**
理由：本仓库的定位是「能力资产 staging/移植源」，保真优先；`core.longpaths` 是纯本地开关，不动内容、不动历史，代价只是「每个 Windows 使用者要设一次」，可以用 README 的一句话承担。
B 会破坏「第三方正文原样保留」的既有承诺，且让 sha 保真链需要额外解释；只有在「要作为长期公开、供他人 clone 使用的资产仓」这一定位被确认时才值得付这个代价。
若 leader 希望 clone 即用、不接受任何前置配置，则退到 C（并在 `README.md` 与 `docs/EXCLUDED.md` 双处披露），**不要**为了推送临时删文件而不留记录。

执行 A 时建议（由 leader 自行执行，本批次未执行）：

```bash
git -C capability-assets/repo config core.longpaths true
git -C capability-assets/repo add -A --dry-run . 2>&1 | grep -i "Filename too long" | wc -l   # 期望 0
```

## 2. 推送前凭据终扫（逐条执行，全部期望 0 命中）

在 `capability-assets/repo/` 下执行。命令刻意**不打印命中内容**、不把凭据写进任何文件；用户名从环境变量取，避免把本机用户名写进文档。
所有命令都带 `--exclude-dir=.git`：`.git/` 里的 remote URL（含组织名）与 reflog（含提交者 name/email）是本地元数据，不随内容推送，不该算作命中。

```bash
# 2.1 已知令牌形态 + JWT（最后一道形闸；含新增 market 层）
grep -rInE --exclude-dir=.git "(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{16,}|github_pat_[A-Za-z0-9_]{16,}|sk-[A-Za-z0-9_]{16,}|xox[baprs]-[A-Za-z0-9-]{10,}|AKIA[0-9A-Z]{12,}|ya29\.[A-Za-z0-9_-]{20,}|Bearer [A-Za-z0-9._-]{24,}|\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{6,}" . | wc -l
# 2.2 本机用户名 / 主目录绝对路径（用户名从环境变量取；命中需逐个看是否为上游占位符）
grep -rIn --exclude-dir=.git -- "$USERNAME" . | wc -l ; grep -rInE --exclude-dir=.git "C:[\\\\/]Users[\\\\/]" . | grep -v "你的用户名" | wc -l ; grep -rIn --exclude-dir=.git "$(pwd -W 2>/dev/null || pwd)" . | wc -l
# 2.3 凭据文件名与凭据键（键后跟非占位值）
find . -path ./.git -prune -o -type f \( -name ".env" -o -name "*.pem" -o -name "*credentials*" -o -name "*secret*" -o -name "id_rsa*" \) -print | wc -l
grep -rInE --exclude-dir=.git "(api[_-]?key|secret|token|password|passwd|authorization)[\"']?\s*[=:]\s*[\"'\`]?[a-f0-9]{16,}" . | wc -l
# 2.4 本次注入的登录态（cookie / Bearer token）绝不可能入库——用环境变量比对，不落文本
grep -rInF --exclude-dir=.git -- "${QODER_APPHUB_COOKIE:-__none__}" . | wc -l        # 期望 0（若未设该变量则用实际注入值的 -F 匹配）
# 2.5 PEM 私钥头
grep -rIn --exclude-dir=.git -- "-----BEGIN" . | wc -l
```

- 2.3 凭据**文件名**闸门是粗筛（第三方包里本来就有叫 `secret-scan.mjs`/`secrets.md` 的脚本与文档），命中要按内容判；2.5 私钥头同理，必须跟「下一行是不是 base64 密钥体」一起看。

本检查单落盘前，成员已逐条执行 2.1–2.5（排除 `.git`），实测与判读：

| 命令 | 命中 | 判读 |
|---|---|---|
| 2.1 已知令牌形态 + JWT | **0** | 通过 |
| 2.2a 本机用户名 `$USERNAME` | **0** | 通过（`.git/` 内的 remote URL 组织名与 reflog 提交者身份不计，也不随内容推送） |
| 2.2b `C:\Users\` | 14（去占位后） | 均为**上游文档自带示例路径**：`C:\Users\admin`(6)、`bob`(3)、`xxx`、`Username`、以及作者自述路径 `ocean.cui`/`liuchao25` 等；另 1 处是本页自身写的检查命令文本。无本机用户名。**属 README「风险提示」已披露的第三方正文原样保留范围** |
| 2.2c 本机 checkout 绝对路径 | **0** | 通过（本页用 `<WORKSPACE>` 代称） |
| 2.3a 凭据类文件名 | 6 | 全部是第三方自带脚本/文档：`secret-scan.mjs`×2、`scan-secrets.js`、`credentials.md`、`secrets.md`×2。**无 `.env`、无 `.pem`、无 `id_rsa`** |
| 2.3b 键名 + 16+ 位十六进制值 | **0** | 通过 |
| 2.5 `-----BEGIN` | 19 处 / 6 个不同头（`RSA PRIVATE KEY`、`OPENSSH`、`CERTIFICATE`、`DH PARAMETERS`、`XXX`） | 逐条复查其后一行：**base64 密钥体命中 0** ⇒ 全是文档/代码里的占位与说明文本 |

补充抽查命令（把 2.5 变成可判定的）：

```bash
grep -rInA1 --exclude-dir=.git -- "-----BEGIN" . | grep -E "MII[A-Za-z0-9+/=]{30,}" | wc -l      # 期望 0（实测 0）
grep -rIoE --exclude-dir=.git "C:[\\\\/]Users[\\\\/][^\"'\\\\ ]{0,25}" . | sort | uniq -c | sort -rn | head   # 逐个看用户名是不是本机那个
```

已完成的产物级结论（实测，见 `docs/download-sample-verify.md` 第 6 节）：
market 层（315 文件，批次 2 新增内容）单独复扫：2.1/2.2 类命中 **0**；`<REDACTED` 仅剩 2 处且都在 `connectors/market/Coding/GitHub.json`
（一处是脚本自加的 `_note` 说明，一处是 leader 侧快照里 `api_key_help_url` 的原值即被键级脱敏）；
market 层唯一的 `C:\Users` 是 `skills/market/Productivity/kb-result-qoder-build-v5-1-0/references/install-guide-template.md` 里的占位符 `C:\Users\你的用户名\`（上游自带）。
**剩余风险**：v3 规则对「值不像凭据」的键值对采取放行（保代码可运行），保守放行清单在 `docs/download-report.json` 的 `codeishCandidatesKeptList`
（本批次样本 49 条：只记 `文件 + 键名 + 值长度`，不记值）——全量跑后该清单会显著变长，**推送前请按文件逐一抽查该清单**，
这是本方案唯一的、已知的人工复核点。批次 1 的 `credential-scan.md` 已记录 v2 规则的替换统计。

## 3. `git add` / commit 分批建议

前提：批次 1 是单提交 ≈72 MiB，实测可行但慢；叠加全量下载后（见第 4 节）≈455 MiB，**不要一次 `git add -A` 单提交**。

```bash
# 每批之后 git status --porcelain | wc -l 递减，git diff --cached --stat 末行核对增量
git add -A -- docs/ README.md                                    # 第 1 批：文档与索引（含本检查单）
git add -A -- catalog/ connectors/                               # 第 2 批：元数据与连接器配置模板（小）
git add -A -- skills/                                            # 第 3 批：技能（local-installed + market-feed 无 + market）
git add -A -- plugins/local-installed                            # 第 4 批：按 market 再拆，单目录 >50MB 时逐 skill 提交
git add -A -- plugins/market-feed                                # 第 5 批：feed 包（25.7MB）
git add -A -- plugins/market                                     # 第 6 批：市场插件正文
```

要点：
- 每批一个 commit（消息形如 `chore(staging): market skills batch <n>`），单 commit 控制在 **≤50 MB**，push 时可分批 `git push origin main`（同一分支多次快进推）而不是攒一个巨型提交——中断后可续，GitHub 对单 push 的体积/时长更敏感。
- 提交前用 `git diff --cached --numstat | wc -l` 与磁盘计数对账（当前磁盘 4,702 文件；方案 A 生效后 `git ls-files | wc -l` 应等于该数，批次 1 时为 4,376）。
- 单文件检查：`find . -type f -size +95M`（期望 0；GitHub 100 MB 硬拒）。全量下载后若出现 >95 MB 的包，`download-assets.js --max-file-bytes` 已会在解包阶段跳过并记 `skipped.ndjson`，不入库。
- 首次推送后核对 `git ls-files | wc -l` 与磁盘文件数（当前 4,702）；差异非 0 说明有文件被 `.gitignore` 或路径问题吞掉。
- 不启用 Git LFS：market 层与现有内容均为文本，LFS 只增加 clone 依赖与配额；zip 不入仓（只留 sha256 + size + 下载 URL）。

## 4. 全量下载体积估算（推断，附口径）

清单规模（读 leader 快照实测）：`downloads-manifest.ndjson` 2,566 行 = skill 2,284 + plugin 154 + mcp 128；
其中 128 条 mcp 全部 `note=no_zip_url_in_detail`（走配置模板，不成包）。

- **zip 传输量（不入仓）**：skill 2,284 × 抽样 HEAD 均值 32,472 B = 74,166,048 B；
  plugin 用详情端点 `file_size` 逐条求和 = 75,336,876 B ⇒ **≈149,502,924 B（143 MiB）**。
  （技能详情不返 `file_size`，只能用 110 条 HEAD 抽样的均值外推 ⇒ 这是**推断**；插件用的是权威字段求和 ⇒ 半实测。抽样明细见 `docs/size-probe.json`。）
- **解包入库量**：样本实测「解包内容 / zip」= 2,789,316 / 1,037,221 = **2.689**（8 个包，已排除脚本自身生成的 `manifest.json`）
  ⇒ 149,502,924 × 2.689 ≈ **402,046,331 B（≈383 MiB）**，再加每资产 `manifest.json`（2,438 个 × ~1.1 KB ≈ 2.7 MiB）。
- **仓库合计（推断）**：现有 71.6 MiB + 新增 ≈ 386 MiB ⇒ **≈ 458 MiB**（未计 `.git` 对象膨胀，git pack 后工作树与 `.git` 通常同量级）。

结论：**低于 500 MB 阈值但很接近**，加上 pack 膨胀与后续增量很容易越线 ⇒ 建议按下述瘦身（按性价比排序）：

1. **排除巨型文档树**（首选）：`plugins/local-installed/qoder-marketplace/oceanbase-skills/skills/seekdb/docs/**` 与 `plugins/market-feed` 中单包 >5 MB 者，
   改为「只留 `SKILL.md`/`README.md`/`scripts/` + `EXCLUDED.md` 记原路径与 sha256 + 保留 `downloadUrl`」。一次性能省下 20–35 MB，同时顺手解决第 1 节的超长路径。
2. **market 层只入 TOP-N**：每类目 TOP200 已是你选的口径；若只需可运行资产，可把 `downloads-manifest.ndjson` 过滤为 `downloads`/`installed` 前 K 名（例如每类目前 50）先入仓，其余保留在清单里按需二批补。
3. **拆仓**：`skills` / `plugins` / `connectors+catalog` 三仓，或按主类目分仓；单仓降到 100–200 MB，clone 与 CI 都轻。
4. **只入元数据不入正文**（保底方案）：market 层退化为「清单 + 每资产 manifest + 下载 URL」，正文由使用者本地跑 `download-assets.js` 自取。
   这会把 market 层新增压到 <10 MB，但「移植到项目能力」需要一步本地执行。
5. `.gitignore` 兜底：排除 `**/node_modules/**`、`**/*.zip`（zip 本就不入仓）、`capability-assets/.tmp-dl/`、`market-api/`（leader 侧快照，含大 JSON，勿入本仓）。

> 说明：`market-api/`、`phase2/`、`scripts/` 在 `capability-assets/` 下、`repo/` 之外，是否随仓发布由 leader 决定；
> `market-api/` 是带鉴权抓取的快照（已脱敏），若要公开建议先按第 2 节终扫并确认类目级计数不含内部字段。

## 5. 未完成 / 需 leader 处置（本批次范围内未做的）

1. **未跑全量下载**（非目标）：2,438 条 zip 待执行；命令见 `scripts/README.md` 的 runbook。建议先 `--limit 50 --concurrency 4` 观察失败率，再分类目跑。
2. **连接器只入 1 条样本**：其余 127 条待 `--kind mcp` 全量（无 HTTP 成本，只读快照）。
3. **leader 侧抓取缺陷（建议修 `apphub-client.js`，本批次未改该文件）**：`SECRET_VAL_RE` 含 `(\b[0-9a-fA-F]{32,64}\b)`，
   会把响应体里**值级**的 64 位十六进制一并替换 —— 实测后果是插件详情的 `file_hash`（即上游 sha256 基线）与清单 `sha256` 字段全部变成 `<REDACTED>`，
   于是下载侧**无法与上游基线对账**（只能自算 sha256，`upstreamSha256` 写 `UNAVAILABLE_REDACTED_BY_CLIENT`）。
   建议把该值级规则收窄到 `Cookie:`/`Authorization:` 形态（键级脱敏已足够），随后重取 154 条插件详情即可恢复基线。
4. **批次 1 的 v2 误伤**：`skills/local-installed/**`、`plugins/**`、`plugins/market-feed/**` 里存在把代码字面值改成 `<REDACTED>` 的文件（规则已同步为 v3，未重跑）；
   重跑 `node scripts/stage-assets.js` 可复原，注意它会覆盖 `docs/staging-report.json` 与 `docs/credential-scan.md`。
5. **许可与可再分发性**：`license` 字段大量 `UNKNOWN`（详情页不返 license 时不猜测）；仓库若设 PUBLIC，等于公开第三方正文副本 —— 该决策仍属 leader/用户。
6. **BASE 口径**：脚本内 `apiBase` 记 `https://openapi.qoder.com.cn/apphub/api/v1`（leader 更正后的可用地址），下载 URL 全部取清单原值（`qoder-cn-mind.oss-accelerate.aliyuncs.com` 公开直链，无鉴权）。
