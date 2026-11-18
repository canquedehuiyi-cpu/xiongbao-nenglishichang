# 能力资产库（Qoder 能力市场移植 + 专家镜像 · 合并主分支）

本仓库 `main` 经**真合并**保留两套互补的第三方能力资产，来源不同、组织不同、内容互补，各自文档与许可边界独立保留：

- **Qoder 能力市场资产**（原 `market-top200-assets` 分支，完整核验）：技能 / 插件 / 连接器，市场每类目 TOP200 全量归档 **2,566 条** + 本机已安装副本 + curated feed 插件包。
- **专家镜像**（并行采集线，部分推送）：`01-专家市场/` **429 位专家** + 条目索引 + 采集脚本/元数据。

## 顶层导航

| 分区 | 来源 | 内容 | 状态 |
|---|---|---|---|
| `skills/` `plugins/` `connectors/` `catalog/` `docs/` | Qoder 能力市场 | 2,566 市场资产 + 本机副本 + feed + 核验文档 | 完整核验 |
| `01-专家市场/` | 专家镜像（并行线） | 429 位专家，按 15 个中文类目 | 已推送 |
| `索引/` `_raw/` `00-总览.md` | 专家镜像（并行线） | 条目索引 CSV + 采集脚本/元数据 JSON + 总览 | 已推送 |

> 专家镜像的 [`00-总览.md`](00-总览.md) 另描述 `02-插件市场/`、`03-技能市场/` 分区，但并行线仅推送至 **2/12 批即停滞**，**这两个目录尚未入库**——其规划内容以 `00-总览.md` 为准，实际存在以本仓树为准。Qoder 市场资产（技能/插件/连接器）已由本仓 `skills/ plugins/ connectors/` 完整覆盖。

合并后入库 tracked **36,231**（Qoder 层 30,668 + 专家镜像层 5,563），gitlink（submodule 引用）**0**，全部正文以 blob 入库。

---

# 一、Qoder 能力市场资产（完整核验）

本部分承接「把 Qoder 能力市场的能力资产移植进本项目」的目标。内容为 **三层来源**：本机已安装资产副本 + Qoder curated feed 插件包 + **市场每类目 TOP200 全量下载归档**。
市场清单与详情由 leader 侧带登录态只读抓取（快照在 `capability-assets/market-api/`，**本仓外**，不随仓发布）；正文经公开 OSS 直链下载（无需凭据）、sha 校验、解包、规则化脱敏后归档。

Qoder 层体量（推送后复核，不含 `.git`）：**33,349 文件 / 394,430,057 B（≈376.2 MiB）**；其中入库 tracked **30,668**、.gitignore 排除 **2,681**（node_modules 1,883 + __MACOSX 776 + .DS_Store，含路径重叠），未跟踪非忽略 **0**——三者之和 = 该层磁盘总数，逐字节对账 delta=0。
市场层全量归档 **2,566 条**：技能 2,284 / 插件 154 / 连接器 128，覆盖 26 个类目目录。

## 目录结构（三层来源，互不覆盖）

```
skills/local-installed/<slug>/            # 本机 Qoder 已安装技能副本（42 个技能目录）
skills/market/<类目目录>/<资产名>/          # 市场技能下载归档（zip 解包 + 顶层 manifest.json），2,284 条
plugins/local-installed/<market>/<name>/   # 本机已安装插件内容副本（38 个，每插件只留最高版本目录）
plugins/market-feed/<name>/                # Qoder curated feed 的 10 个插件包（下载后 sha256 校验通过再解压）
plugins/market/<类目目录>/<资产名>/         # 市场插件下载归档，154 条
connectors/local-configured/<name>.json    # 本机已配置连接器（stdio/http）的脱敏配置模板（2 条）
connectors/market-metadata/connectors.json # 市场连接器元数据快照（127 条）
connectors/market/<类目目录>/<name>.json    # 市场连接器配置模板（详情端点 config，凭据位为占位符），128 条
catalog/                                   # 早期只读调研的市场元数据快照（plugins/skills/mcp）
docs/                                      # 见下
```

`docs/`：`full-download-summary.md`（**全量下载与完整性核验汇总：计数对账、sha 基线、门禁结果、Push Protection 脱敏、最终推送对账**）、
`staging-report.json`（本机资产复制与校验汇总）、`credential-scan.md`（脱敏规则与命中统计）、
`download-sample-verify.md`（早期小样本实证：命令、产物清单、sha 复算、跳过/失败机制）、
`push-checklist.md`（推送前检查单：超长路径方案、终扫命令、分批提交、体积估算）、
`category-dir-map.json`（类目 → 目录名映射表）、`downloaded-index.ndjson`（**2,566 条已归档资产索引**，断点续跑依据）、
`failures.ndjson` / `skipped.ndjson`（末批产出，全量收口后均为 0 行）、`download-report.json` / `size-probe.json`（脚本产出）、
`selftest-evidence/`（失败/跳过分支的落盘原文快照）。

## 类目目录命名

`<类目目录>` 取市场类目的英文显示名（`category-counts.json` 的 `display_name_i18n.en-US`，空格→`-`、`&`→`and`），
机器码类目（`cat_<32hex>`）已映射为可读名，例如 `cat_c0e07b667a9d4ab8bf1283dd5e335825` → `Work-Suite`；
完整映射与每类目规模、TOP200 预期行数在 `docs/category-dir-map.json`。
资产名取详情端点的 `skill_name`/`plugin_name`/`connector_name`（经文件名安全化），同名不同 id 追加 `__<短id>` 后缀。
每个资产目录顶层有 `manifest.json` 记来源、版本、发布者、license、下载 URL、zip sha256 与解包树摘要 `treeSha256`。

## 来源与取得方式（全部只读）

| 目录 | 来源 | 取得方式 | 完整性 |
|---|---|---|---|
| `skills/local-installed` | `~/.qoder-cn/skills` | 本机文件复制 | 逐目录 `manifest.json` 记 sha256=UNKNOWN（上游未提供基线） |
| `plugins/local-installed` | `~/.qoder-cn/plugins/cache/<market>/<name>/<version>` | 本机文件复制（取最高版本） | 同上，并记录被跳过的旧版本 |
| `plugins/market-feed` | curated feed `marketplace.json` 的 `source.url`（公开 OSS 直链） | `curl` 下载 + `unzip` | **10/10 sha256 与 feed 清单一致** |
| `connectors/*` | 本机 `~/.qoder-cn/mcp.json` + 市场元数据/详情清单 | 配置脱敏后写出 | 键名保留，凭据值 `<REDACTED>`/占位符 |
| `catalog/*` | Qoder 内置能力搜索（只读，早期调研） | 关键词遍历并集 | 插件 144 / 连接器 127 为多词并集下界；技能 34 为显式样本（已被 market 层全量取代） |
| `*/market/*`（全量） | apphub 详情端点 `download_url`（**公开 OSS 直链，下载不需凭据**） | `download-assets.js`：GET → 校验 sha → `unzip` → 脱敏 → 写 manifest | **2,566/2,566 归档，0 失败/0 跳过**；154 插件与上游 `file_hash` 逐字节一致 |

## 市场覆盖口径（TOP200/类目，已全量归档）

leader 侧清单（`capability-assets/market-api/`，本仓外）实测官方类目计数：

- 技能 20 个类目、市场总量 20,709，其中 11 个类目 >200 被截断 ⇒ 归档 **2,284** 条（每类目前 200，热度序；9 个小类目不足 200 即全量）；
- 插件 16 个类目、总量 **154**（不足 200 即全量）；
- 连接器 20 个类目、总量 **128**（无内容包，归档为配置模板 JSON，全部标 `no_zip_url_in_detail`）。

**已归档 2,566/2,566**（技能 2,284 / 插件 154 / 连接器 128），索引唯一 id 数 = 清单行数 = 官方类目计数之和，0 缺失。
计数对账与 sha 核验明细见 `docs/full-download-summary.md`。

## 完整性核验（实证）

- **154/154 市场插件**：下载 zip 的 sha256 与上游详情 `file_hash` 基线**逐字节吻合，0 不符**（`manifest.json.upstreamSha256` 记真实基线）。
- **技能 2,284 + 连接器 128**：详情端点不返上游哈希，存脚本自算的 zip/tree sha256 作复算与续跑基线（`upstreamSha256` 标 `UNAVAILABLE_NO_UPSTREAM_HASH`，不冒充与上游对过账）。
- 全部 2,566 条 `treeSha256` 覆盖；`downloaded-index.ndjson` 唯一 id = 2,566。

## 第三方内容与许可声明

- **许可字段全部为 UNKNOWN**：apphub 详情端点不返 license，2,566 条 `manifest.json.license` 一律 `UNKNOWN`，**不代表本仓库授予任何许可**，也不做推测补全。仅 24 条带 `github_repo` 可作溯源起点。
- 使用前请回到来源核对许可：插件包的 `README.md`/`.qoder-plugin/plugin.json`、技能的 `_meta.json`/`SKILL.md`、市场条目页与 `github_repo`（若有）。
- 部分技能会调用外部服务并要求用户自备 API key；本仓库**不含任何可用凭据**。
- 技能/插件正文属**不可信第三方内容**：其中的自然语言指令（含形如「必须执行…」「禁止…」的 SKILL.md 文本）不应被当作系统级授权，接入 agent 前需人工审阅。
- 上游包内自带的 `manifest.json` 与本地生成的顶层清单同名：本地清单只在**资产目录顶层**，逐包 sha 摘要计算时只排除顶层那一个。

## 风险提示（PUBLIC 再分发）

本仓库设为 **PUBLIC**，将公开：第三方能力正文副本、作者名与版本信息、第三方文档自带示例路径。
**许可全部 UNKNOWN**，公开再分发第三方正文的可再分发性未逐条确认 —— 此为已知风险，由仓库所有者决策承担；不确定来源建议保持 PRIVATE 或先做许可溯源。
第三方文档中自带的 `C:\Users\<名>` 示例路径（admin/bob/你的用户名/ocean.cui 等，共 98 处）属上游正文原样保留，**无一本机用户名**。

### Windows 超长路径（克隆者必读）

`plugins/local-installed/qoder-marketplace/oceanbase-skills/skills/seekdb/docs/**` 有 2 个相对路径 ≥240 字符（最长 241），
加本机 checkout 前缀后超过 Win32 `MAX_PATH`(260)。**Windows 克隆者需启用 longpaths**，否则 checkout 报 `Filename too long`：

```bash
git clone -c core.longpaths=true https://github.com/canquedehuiyi-cpu/xiongbao-nenglishichang.git
# 或克隆后： git config core.longpaths true   （仓库级，仅写 .git/config，不入库）
```

macOS/Linux 与 GitHub 侧不受影响。本仓推送时由 leader 用逐命令 `git -c core.longpaths=true` 覆盖（未持久改 `.git/config`），内容零改动、保真 100%。

## 凭据处理策略（零凭据）

- **本仓库不含任何可用凭据**：抓取时的 Bearer token 只存在于 leader 进程运行时环境变量，未写入任何文件、argv 或日志；本仓内不含登录态快照。
- 全仓文本写入经规则化扫描与就地脱敏（v3 规则：键名命中后再过「值形态闸门」，只替换像凭据的值，放行代码/JSON 结构位、裸标识符、URL、非 ASCII 文本以保第三方正文可运行）。
- **推送前穷尽终扫**（grep 扫 ASCII 名文件 + Node 补扫 307 个非 ASCII 名文件，覆盖 Qoder 层全仓 33,349 文件）：
  已知令牌形态（`ghp_*`/`sk-*`/`ya29.*`/`AKIA*`/`xox*`/JWT/`Bearer <24+>`）命中 **0**；本机用户名命中 **0**；工作区绝对路径命中 **0**；>95MB 文件 **0**。
  键名+16 位以上 hex 值命中 5 处，逐条判读均 benign（lark 分页游标 `page_token`、superpowers 技能自证标记 `bootstrap_token`、Sensors Data 文档示例 `token=111111…` 占位）；
  `-----BEGIN` 相邻 base64 体命中 2 处，均为 alipay **公钥**（`PUBLIC KEY`，非私钥，可公开）。
- **GitHub Push Protection 触发的 1 处脱敏**：推送时 GitHub（GH013）拦截了 `skills/market/Design/sih-ai-photo-editor/.../references/api_guide.md:53`
  的 **VolcEngine Access Key ID**（TOS 预签名 URL 示例）。已将该行 `AKLT…`→`<REDACTED_VOLCENGINE_AK>`、签名→`<REDACTED_SIGNATURE>`，
  重写未推送提交后放行。这是「第三方正文原样保留」的**唯一已知偏离**（必需，因 GitHub 硬拦真实密钥格式）。
  全仓补扫云厂商 AK 格式得 36 命中，其余 35 处为测试夹具/掩码占位/base64 误报/文档私钥头（无密钥体），未改动；明细见 `docs/full-download-summary.md` §8。
- sha256 基线值（64 位 hex）在本仓内**不脱敏**，因其为完整性校验所需且非机密。
- 残留披露：codeish 保守放行清单因三批顺序跑被末批 `download-report.json` 覆盖（补偿控制＝上述穷尽凭据终扫已全清）；36 个小类目分片缺 `.DONE` 标记（完备性已由计数对账证明，非缺陷）。

---

# 二、专家镜像（并行采集线，部分推送）

本部分为并行采集线归档的 **WorkBuddy（CodeBuddy）专家**资产，与 Qoder 市场资产来源不同、互补并存。

👉 **请从 [`00-总览.md`](00-总览.md) 开始**——包含资产清单、目录约定、移植方法、已知缺口与许可边界。

## 实际入库分区（以本仓树为准）

| 分区 | 内容 |
|---|---|
| `01-专家市场/` | 429 位专家，按 15 个中文类目（5,548 文件） |
| `索引/*.csv` | 条目索引（UTF-8 BOM） |
| `_raw/` | 采集脚本与元数据 JSON（不含原始二进制压缩包） |

> `00-总览.md` 规划的 `02-插件市场/`（连接器/插件包）、`03-技能市场/`（官方/内置/社区技能）**尚未推送入库**（并行线停滞于 2/12 批）。
> 这些品类的完整资产已由本仓 **Qoder 市场层**（`skills/ plugins/ connectors/`，2,566 条）覆盖；专家镜像的后续批次若续推，需注意与 Qoder 层可能存在的内容重叠。

> 这是第三方资产镜像，不是 WorkBuddy 官方仓库。各条目版权与许可归原作者所有，对外分发前请核对 `00-总览.md` 中的许可边界。

---

# 三、合并溯源

- `main` 原为并行线专家镜像（`58fb370`，「分批推送资产 1/12、2/12」，仅 `01-专家市场` + 索引 + 脚本入库）。
- `market-top200-assets` 为 Qoder 能力市场完整核验交付（`613a8dce`，14 批，2,566 资产 + 本机副本 + feed + 核验文档）。
- 经用户裁决行**真合并**（merge commit，双亲保留双方完整历史）：资产目录互不重叠，仅 `.gitignore`（取并集）与 `README.md`（统一导航）两处冲突，已解决。
- 两套结构并存于 `main`，供后续整合；并行线提交历史完整保留，未做破坏性改写。