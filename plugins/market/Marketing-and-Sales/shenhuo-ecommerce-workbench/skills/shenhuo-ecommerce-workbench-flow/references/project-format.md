# 项目交付数据格式 1.0

这是随包交付脚本的数据合同，属于本插件内部组织方式，不是Qoder或神火 API Schema。维护一份真实 `project.json`，不要直接交给 MCP 工具。

顶层必须包含以下字段，未知字段拒绝：

| 字段 | 类型与用途 |
|---|---|
| schema_version | 字符串 `1.0` |
| title / summary / updated_at | 非空字符串；时间含实际日期、时间及时区 |
| markets | 至少一个市场，每项包含 id、label、platform、region、language、currency、timezone，均为非空字符串 |
| sections | 各阶段资料数组，可以为空；每项说明见下方 |
| assets | 物料数组；无图片任务时用空数组 |
| sources | 实际读取的公开来源数组；没有时用空数组 |
| open_items | 待补项字符串数组；没有时用空数组 |

## 市场与资料

id 只使用 ASCII 字母、数字、下划线或连字符，首字符为字母/数字，总长不超过 64。各数组内部 id 唯一。`shared` 保留给共用资料，不能作为市场 id。语言使用真实语言标记，例如 zh-CN、en-US；币种使用真实币种，例如 CNY、USD；timezone 用真实地区时区，例如 Asia/Shanghai、America/New_York。尚无价格/时间要求时字段可填“待确认”，但不能把这个值当已确认信息写进成品图。

sections 每项必填 id、market_id、stage、title、revision。market_id 指某个市场或 shared；revision 为从 1 开始的整数，实际资料变更才递增。stage 为 selection/product/content/visual/campaign/review 之一。

可选 body（非空字符串）、items（字符串数组）、table（columns 字符串数组与 rows 二维字符串数组，每行列数一致）。内容均按纯文本处理，不解析 HTML 或脚本。用表格列事实、证据及确认状态，具体商品参数可按业务扩展为行，不扩展 JSON 字段。

## 物料

assets 每项必填 id、market_id、title、placement、status。status 仅可为：planned 待制作、pending 制作中、delivered 已交付、failed 未完成、outdated 待更新、reference 参考素材。

可选字段：

- file：输入 JSON 所在目录内的相对图片路径，仅 PNG/JPEG/WebP，不能用远程 URL、绝对路径或 `..`。delivered 必须有真实可读取的图片文件；参考或过期图片也可保留文件。
- copy：准确文案字符串。
- specification：实际检查到的图片格式/尺寸/比例，尚未制作时明确写“计划规格”。
- notes：失败原因、概念标识、检查结果或待补说明。
- depends_on：`{"section-id": 1}`，记录实际引用的资料版本，只能引用同市场或 shared 资料。渲染时如版本落后，会把已有/进行中物料标为 outdated，保留原文件；不会自动修改图片或生图。重新完成制作后才更新依赖版本。

不伪造 delivered 来通过脚本校验。文件头检查不能代替真实图片的视觉和像素验收。

## 来源与私有记录

sources 每项包含 title、url、accessed_at、market_id，可选 note。URL 仅公开 HTTP(S) 页面，不含账号密码或签名票据；market_id 可为 shared。商品资料若来自用户，在正文表格注明，不为它编造网站来源。

工具回执、下载签名、OAuth、报价、幂等记录和账号信息不属于本格式，另存私有执行记录。HTML 与 ZIP 不承载短期图片地址，成品使用实际下载的本地字节。

完整可运行结构见 [project.example.json](../assets/project.example.json)，其中资料是合成示例。脚本输出 index.html、copy.md、project.json、SHA256SUMS.txt、assets/ 和 deliverables.zip；ZIP 内不嵌套自身，更新不覆盖旧目录。
