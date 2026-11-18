# 全量下载与完整性核验汇总

执行：leader（项目经理）会话。性质：市场正文经**公开 OSS 直链**下载（无凭据），sha 校验 → 解包 → 规则化脱敏 → 归档。
抓取快照（清单/详情/类目计数）在 `capability-assets/market-api/`（**本仓外**，不随仓发布）。

## 1. 计数对账（实测，可复算）

| kind | 清单行数 | 已归档索引 | 官方类目计数和 | 失败 | 跳过 |
|---|---|---|---|---|---|
| skill | 2284 | 2284 | 2284（11 类目×200 + 9 小类目全量） | 0 | 0 |
| plugin | 154 | 154 | 154（16 类目，均不足 200） | 0 | 0 |
| mcp/connector | 128 | 128 | 128（20 类目，配置模板无 zip） | 0 | 0 |
| **合计** | **2566** | **2566** | **2566** | **0** | **0** |

- `downloaded-index.ndjson` 唯一 id 数 = 2566 = 清单行数；清单中**无任一 id 缺失于索引**（逐条比对 = 0）。
- 下载 zip 传输量合计 **126,945,688 B（121.1 MiB）**（技能 ~46 MiB + 插件 ~75 MiB；连接器无 zip）。
- 解包入库工作树（不含 .git，含被 .gitignore 排除的打包垃圾）：**33,347 文件 / 394,418,826 B（376.1 MiB）**。

## 2. 完整性核验（sha256）

- **插件 154/154**：下载 zip 的 sha256 与上游详情 `file_hash` 基线**逐字节吻合，0 不符**。
  其中 151 条经资产 `manifest.json.upstreamSha256` 字段直接核验；3 条早期样本（moneypal / dify-canvas / external-statement-reconcile）
  因 manifest 写于 sha 回填前，经 `details/plugin/<id>.json` 的 `file_hash` 交叉核验 match=true 后回填真实基线。
- **技能 2284 + 连接器 128**：详情端点不返上游哈希，存脚本自算 zip/tree sha256 作复算与续跑基线，
  `upstreamSha256` 标 `UNAVAILABLE_NO_UPSTREAM_HASH`（不冒充与上游对过账）。
- 全部 2566 条 `treeSha256` 覆盖。`verify-sha.js` 独立复算：real-upstream-and-match=154，mismatch=**0**。

## 3. 途中修复的两类确定性故障（已收口）

1. **13 条技能详情 URL 被旧脱敏规则误抹**：旧 `SECRET_VAL_RE` 含 32–64 位 hex 盲替换，把文件名形如 32hex 的 zip URL 抹成 `<REDACTED>.zip`。
   收窄规则（只匹配 JWT / Cookie / Authorization 形态）后，删 13 条清单行+详情、用 `run-with-auth.js bulk` 重取，13/13 恢复完整 URL，全仓 URL 残留脱敏 = 0。
2. **6 个 zip 反斜杠路径分隔符致 unzip 警告性 exit=1 被误判失败**：zip 实际解包成功（54 文件等），但 Info-ZIP 对反斜杠分隔符返回 exit 1。
   修 `unzipTo`：exit=1 且已解出文件且 stderr 无致命错误签名时接受。6/6 恢复（4 技能 + 2 插件）。

## 4. 推送前门禁（全仓穷尽）

扫描覆盖：grep 扫 ASCII 名文件 + Node 补扫 **307 个非 ASCII 名文件**（合法中文名，bash 代码页无法寻址但 Node 宽 API 正常），合计覆盖全仓 33,347 文件。

| 门禁 | 结果 | 判读 |
|---|---|---|
| 已知令牌形态 + JWT（ghp/sk-/AKIA/ya29/xox/Bearer/JWT） | **0** | 通过 |
| 键名 + ≥16 位 hex 值 | 5 | 全 benign：lark `page_token` 分页游标×3、superpowers `bootstrap_token` 技能自证标记、Sensors Data 文档示例 `token=111111…` 占位 |
| `-----BEGIN` 相邻 base64 体 | 2 | 均为 alipay `PUBLIC KEY`（公钥非私钥，可公开） |
| 本机用户名 `canqu` | **0** | 通过 |
| 工作区 HOME 绝对路径 | **0** | 通过 |
| >95MB 单文件 | **0** | GitHub 100MB 硬限安全 |
| `C:\Users\<名>` | 41 种 98 处 | 全第三方文档示例路径（admin/Administrator/linxia/你的用户名/bob/xxx/ocean.cui 等），无一本机用户名 |

## 5. 入库排除项（.gitignore + 移除）

- **移除**：2 个嵌套 `.git` 目录（`fastapi-vue-fullstack-dev` 资产自带 + 其 `__MACOSX` 副本）——VCS 元数据非正文，移除以便 git 正常入库正文（否则被当 submodule gitlink 只存引用）。
- **.gitignore 排除**：`node_modules/`（office-docx/runtime，25MB/1883 文件）、`__MACOSX/`（22 目录）、`.DS_Store`（15 文件）、`*.zip`（0，正文已解包）。
- 影响披露：资产 `manifest.json.treeSha256` 是**下载时完整解包树**的摘要（含上述垃圾）；入仓正文排除垃圾后，从仓内重算 tree sha 会与 manifest 基线不同——这是有意排除，非内容篡改。zip sha256（插件对上游 file_hash）不受影响。

## 6. 落点决策（并行线停手条款）

推送前复读远端 main：发现克隆后**并行线**已向同一仓推 2 提交（`50ba80b 分批推送资产 1/12`、`58fb370 2/12`，作者 canqu，Nov 17 16:10），
采用不同结构（`01-专家市场/02-插件市场/03-技能市场` 中文编号 + `_raw/` Python 脚本链 + codebuddy-plugin 格式，5565 文件），12 批推送进行中。
本地落后 2 提交。按「推送前复读 main 固定停手」纪律停手，经用户裁决：**本套已核验结构推到独立分支 `market-top200-assets`**（基于 Initial commit 52b98d0），
不动 main、不干扰并行线，两套结构并存供后续整合。

## 7. 残留披露

- codeish 保守放行清单（`codeishCandidatesKeptList`）因 skill/plugin/mcp 三批顺序跑、`download-report.json` 被末批覆盖，未保留全量逐条清单；
  补偿控制＝第 4 节穷尽凭据终扫已全清（0 真实凭据）。
- 36 个小类目分片缺 `.DONE` 标记（cosmetic）；完备性已由第 1 节计数对账证明（2566 = 官方类目计数和），非缺陷。
- 许可：2566 条 license 全 UNKNOWN（详情端点不返），PUBLIC 再分发风险由仓库所有者承担（见 README）。