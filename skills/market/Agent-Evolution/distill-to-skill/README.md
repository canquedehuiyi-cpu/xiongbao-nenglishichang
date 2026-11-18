# 蒸馏成技能Skill

把书 / 小说 / 视频 / 课程 / 播客 / 语音 / 知识库 / 笔记 / 规范 / 标准 / 会议纪要 / 访谈 / 图片 / 表格 / 网页 / 多语种材料 / 已有Skill / 人物 / 抖音微博内容等各类材料，蒸馏成可独立运行的技能包（A 模式）或精华文档（B/C 模式，PPT/PDF/Word/Excel/MD），上传支持技能上传的 Agent 平台即可使用。一份材料可同出多格式，支持批量整库投料与十万字级长文。

## 从哪开始

- **第一次用**：先看 [`QUICKSTART.md`](./QUICKSTART.md) —— 三步流程 ＋ 三种模式各跑一遍的实况示例（A 出技能包 · B 出精华文档 · C 定向取）。
- **装到哪、怎么装**：看 [`INSTALL.md`](./INSTALL.md)；**它能做什么**：看 [`LISTING.md`](./LISTING.md)。
- **文档怎么分**：`SKILL.md` 是给您的 Agent 读的执行手册（人不必通读）；您要读的是本文件与 `QUICKSTART.md`。

## 安装

- 本包为通用技能包，遵循通用技能包规范，不绑定特定平台。
- 上传至任意支持技能上传的 Agent 平台即可安装、加载、运行。
- 零第三方依赖·装上即跑：核心文本蒸馏只用 Python 标准库，无需 pip 安装、不污染环境，装上即用；媒体降维（视频/音频转写与 OCR）复用运行环境已有的 ffmpeg / whisper / tesseract（agent 平台天然具备或用户按需安装），二进制缺失时优雅降级、不强行编造。本包自身不连任何外部后端、不含收款环节；出网仅发生在您主动提供网页链接时的正文抓取，其余全程本地。本包运行于 Agent 平台，平台需联网通电才能工作——联网是产出标准件的前提。
- **面向终端用户的文档**：安装步骤见 `INSTALL.md`，快速上手见 `QUICKSTART.md`，能力清单见 `LISTING.md`。

## 目录

```
蒸馏成技能Skill/
  SKILL.md                       # 能力层 + 辅助层（主文件）
  README.md                      # 本文件（安装 / 目录 / 使用 / 可选增强 / 改进来源）
  INSTALL.md                     # 安装指南（面向终端用户：装到哪 / 怎么装 / 怎么用 / 常见问题）
  QUICKSTART.md                  # 快速上手（三步流程 + 唤起词 + 支持资料类型）
  LISTING.md                     # 交付能力清单（面向终端用户：能做什么 / 能装哪 / 费用说明）
  _meta.json                     # 包元数据
  requirements.txt               # 依赖声明（仅标准库）
  LICENSE.txt                    # 许可条款（专有·反向工程 / 批量提取 / 未授权商用禁止）

  references/                    # 辅助层：按需加载的规则、规格与指南
    distill-execution-rules.md   # 执行规则与质检基准
    design-tokens.md             # 设计令牌库（模板模式自由组合取值，按需加载）
    opening-script.md            # 用户侧开场白·首屏（仅 3 模式 + 选 A/B/C，Agent 触发首响必须输出，指针引用）
    mode-a-guide.md              # 选 A 后引导（直接产技能包，跳过格式/风格）
    mode-bc-guide.md             # 选 B/C 后逐级引导（全程决策≤3：① 产出模式 → ② 交付格式 1-7 多选（默认 Word=1）→ ③ 萃取方向（仅 C）；内容深度/视觉观感/用途文体已撤出菜单，改默认值 + 口头出口）
    bc-output-standards.md       # B/C 标准件规格（交付目录卫生 / 结果声明 / 来源总览硬规·按需加载）
    boundaries.md                # 客观边界 3 条（上下文触发输出，不在首屏堆）
    popup-spec.md                # 选择组件调用操作手册（弹窗优先·可照抄调用结构·文本兜底·分页切分·英文零容忍自检）
    multimodal-ingest.md         # 多模态降维细则（A0.0 / O4 对应·按需加载）
    media-output.md              # 同源媒体·档一裁剪/选择 路由说明（内部）
    agent-behavior.md            # 后台系统 Prompt 行为说明参考稿（不增删门禁，冲突以 SKILL.md 为准）
    ingest-scale.md              # 规模适配与接料细则（A0 / A0.3+ / A0.3++·体量分级/分块/防崩/多源同投/失败三分支）
    build-gate.md                # 出包验收与交付净化细则（A5 / A6 / A8·19 条硬检查逐条实跑落点）
    output-spec.md               # 标准件输出规格细则（A7·起底骨架/frontmatter/交付硬门禁逐条）
    env-and-scripts.md           # 运行环境与脚本清单（A10·零依赖声明 + 每脚本一行职责）
    rights-boundary.md           # 版权与权利边界细则（A0.6·脱敏/权属/商业内容铁律/声明题材槽）
    mode-routing.md              # 模式路由补充（B/C 衍生脚本·讲稿·二次创作）
    glossary.md                  # 辅助层：术语 / 字段 / 边界 / 示例与反例 / 输出说明

  templates/
    distill-output-skeleton.md   # 标准件起底骨架（SKILL.md + README + usage-notes 三份骨架）

  scripts/                       # 每个脚本带 --self-test 或登记豁免（tests/exempt.json）
    # 生成器（7 种格式输出）
    build_md_standard.py         # B/C 模式 Markdown 标准生成器（纯标准库）
    build_txt_standard.py        # B/C 模式 TXT 纯文本标准生成器（纯标准库）
    build_docx_standard.py       # B/C 模式 Word(DOCX) 标准生成器（纯标准库）
    build_pdf_standard.py        # B/C 模式 PDF 标准生成器（纯标准库·内嵌中文字子集·跨平台字体探测）
    build_ppt_standard.py        # B 模式 PPT 标准生成器（纯标准库）
    build_xlsx_standard.py       # B/C 模式 Excel 报表标准生成器（纯标准库）
    build_xlsx_chart_standard.py # B/C 模式「图表分析报告」标准生成器（纯标准库）
    # 常量与词表（单一事实源）
    constants.py                 # 交付口径常量库（交付目录 / 成品后缀白名单 / 落款·免责·来源总览·回执）
    design_tokens.py             # 设计令牌库（字体 / 配色 / 字号 / 序号 / 模式·版本·版式 + resolve()）
    lexicon.py                   # 禁用词表「单一事实源」（扫描侧与规范侧共用一份）
    # 接料与摄取
    intake.py                    # 统一多物料接料层（多链接/多文档/文件夹/文本/清单→materials_plan+corpus，失败隔离）
    sanitize.py                  # 接料清洗层：把不可见字符当攻击面清掉并如实报告（威胁模型）
    ingest_chunk.py              # 语义分块 + 体积分级 + 执行计划（确定性·仅标准库）
    web_ingest.py                # 网页链接降维（获取正文，标准库实现，带优雅降级/SSRF 护栏/自测）
    media_ingest.py              # 媒体降维（长媒体≤10min 真分段防崩 + --files/--dir 批量隔离编排，带自测）
    media_output.py              # 同源媒体「档一·裁剪/选择」路由层
    docx_ingest.py               # DOCX 摄取（纯标准库 UTF-8 解码，避免编码报错，带自测）
    pdf_ingest.py                # PDF 摄取（纯标准库 best-effort，FlateDecode 抽 Tj/TJ，扫描版降级，带自测）
    pptx_ingest.py               # PPTX 摄取（纯标准库解 zip+xml，抽 <a:t> 正文+笔记，带自测）
    xlsx_ingest.py               # XLSX 摄取（纯标准库抽 sharedStrings+worksheet 还原行列，带自测）
    extract_template_tokens.py   # 参考模板设计令牌提取器（纯标准库）
    # 渲染 · 装配 · 进化
    distill_skeleton.py          # B/C 单一大纲源渲染器（save_outline/load_outline/render_formats·结构保证多格式同源）
    assemble_skill.py            # A 模式技能包一键装配（目录→标准安装 zip：无顶层目录/UTF-8/mtime 统一/幂等，带自测）
    evolve.py                    # 标准件进化三动作（append/correct/rollback + 快照 + 授权门禁，带自测）
    stamp_signature.py           # 出包溯源盖戳（可选，幂等，带自测）
    # 校验与门禁
    selfcheck.py                 # 出包自检 + 一键门禁（九扫描/矩阵声明/命名门禁/清单对账/--full/--prove-gates）
    verify_baseline.py           # 内容级基线门禁（golden 指纹·--bless 留痕，带自测）
    verify_chunks.py             # A0.3 块覆盖完整性门禁（差集非空 exit≠0 不许出包，带自测）
    verify_sources.py            # A0.3+ 源完整性门禁（跨材质 uniform，门禁文件缺失/漏单元 fail-closed，带自测）
    verify_multiformat.py        # B/C 跨格式一致性门禁（模块标题集合/数量不等 exit≠0 不许交付）
    verify_contract.py           # 产物契约联测（跨格式落款/免责/回执/来源总览一致·癸组机器判据，带自测）
    verify_render_combos.py      # 多格式组合联测（含中文字体探测豁免·需渲染环境）
    verify_ppt_versions.py       # 7 版本 PPT 冒烟（配色各异 / 版式生效 / 零厂商标识）
    verify_d3.py                 # D3 只留骨架自检（扫原文长句/金句）

  hooks/                         # 写时可选护栏（默认不启用，功能照常）
    hooks.json                   # 护栏注册与开关
    install_hooks.py             # 启用 / 停用护栏（--write 写入宿主 hooks 配置）
    pre_write_guard.py           # 写前拦截（扫特定禁用词族与人群限定词）
    post_write_check.py          # 写后检查（扫本地断链）

  tests/
    exempt.json                  # 脚本接线豁免台账（since+reason + expires_in|permanent 二选一；--full 中以 WARN 可见）
    golden.json                  # 内容基线指纹（6 格式·含模块内容探针命中集·bless_log 留痕）

  release/                       # 发布清单与文件指纹（自举出包时自动生成·元数据目录·不进安装 zip）
```

## 使用

> **第一次用，先看 `QUICKSTART.md`**（三步流程 ＋ 一次跑通的实例）；装到哪里、怎么装，看 `INSTALL.md`；能做什么，看 `LISTING.md`。

1. 投料：把要蒸馏的材料交给本技能（文字/链接/口述/已有技能均可）。
2. 路由：本技能识别对象类型，分配对应适配层，走四段式内核（提取→验证→构造→自证）。
3. 出包：过出包验收门禁后，产出标准件（SKILL.md + README.md + usage-notes.md + references/ 可选 + scripts/ 可选）；**A 模式安装包由 `scripts/assemble_skill.py` 一键装配**（无顶层目录 / UTF-8 / mtime 统一），装配前会自动过 `selfcheck --full` 门禁、不通过即拒绝出包，并落 `release/` 发布清单；可上传支持技能上传的平台即用。
4. 交互：每级引导**优先用平台选择组件弹窗**让用户点选，回落时给文本编码菜单；用户只需回单个字母 / 单个数字 / 逗号分隔数字，全程零打字（编码：产出模式 A-C · 交付格式 1-7（默认 Word=1）· 视觉风格 A-H（仅选 PPT 时弹））。**内容深度 / 视觉观感 / 用途文体三级不上菜单**（默认 D1 / 标准商务 / 通用正文，用户口头一句话即切，能力没下线、只是不占决策次数）——全程菜单决策 **≤3**。弹窗单题最多 4 个选项，超出的**自动分页**、编码不变，绝不静默截断。
5. 交付：产物末行固定带**交付回执**（反馈口，只有做法标签、零用户内容）；交付说明里给一句**结果声明**（大白话说清这一趟拿到了什么）+ 一句**回钩**（随时回来继续改，不用重传材料）。

## 可选增强

- `scripts/stamp_signature.py <成品目录>`：给蒸馏成品盖**可见**溯源落款（不锁用户）；**不嵌不可见水印或指纹**，`--verify` 反向校验成品不含不可见字符。
- `scripts/web_ingest.py --urls <链接清单.txt>`：批量获取网页/链接正文（逐条 body+汇总，失败链接列原因）；`--self-test` 离线回归（含 SSRF 护栏用例）。
- `scripts/media_ingest.py --files a.mp4;b.mp3 [--out-dir ./out]`：媒体批量降维（长媒体≤10min 真分段防崩 + 逐文件隔离），写 media_plan.json+media_processed.json；`--self-test` 离线回归。
- `scripts/verify_chunks.py --plan <分块清单.json> --processed <processed_ids.txt>`：A0.3 块覆盖完整性门禁，差集非空 exit≠0 不许出包。
- `scripts/verify_sources.py --plan media_plan.json --processed media_processed.json`：A0.3+ 源完整性门禁（跨材质 uniform），门禁文件缺失/漏单元 fail-closed 不许出包。
- `scripts/docx_ingest.py <文件.docx> [--json]`：DOCX 摄取（纯标准库 UTF-8 解码），打印段落/表格正文，避免 docx 编码报错；`from docx_ingest import extract_docx` 供程序调用。
- `scripts/distill_skeleton.py`（模块·含 `--self-test` 自测）：B/C 单一大纲源渲染器——蒸馏只产一份 canonical outline，`render_formats(outline, ["md","txt","ppt","pdf","docx","xlsx"], "out/")` 同源渲染多格式、返回 `(produced, failed)` 单格式失败不影响其余；`python distill_skeleton.py --self-test` 跑回归（含 PPT 分支）；canonical outline 的 `sources` 会**透传进各格式页脚**（来源总览），自测含「来源总览必须穿过适配器」的内容级断言 —— 防这条链路静默断开。
- `scripts/verify_multiformat.py --outline <outline.json> --files <a.md> <b.txt> ...`：B/C 跨格式一致性门禁，模块标题集合/数量不等 exit≠0 不许交付（pdf 信任同源 SKIP）。
- `scripts/verify_d3.py --files <a.md> <b.txt> [--strict]`：D3 只留骨架自检，扫原文长句（>120字无引号 / >60字带引号）与金句，--strict 时命中 exit≠0。
- `scripts/intake.py --url <链接> --url <链接2> --file a.docx --file "docs/*.pdf" --dir ./slides --text note.md --out-dir runs/<任务>/.work/intake`：统一多物料接料层，一次接住多链接/多文档（txt/md/docx/pdf/pptx/xlsx/csv，支持 glob 与文件夹递归）/大文本/媒体任意组合，产出 `materials_plan.json`(全单元含失败)+`materials_processed.json`(成功单元)+`corpus.txt`(拼接正文供 `ingest_chunk.py` 分块)；`--manifest spec.json` 可预写清单；`--no-media` 跳过媒体委派。
- `scripts/pdf_ingest.py <文件.pdf> [--json]`：PDF 摄取（纯标准库 best-effort），抽 FlateDecode 内容流 Tj/TJ 文本；扫描版/无文本层返回空+状态说明，不崩。
- `scripts/pptx_ingest.py <文件.pptx> [--json]`：PPTX 摄取（纯标准库），抽 `<a:t>` 正文与笔记页。
- `scripts/xlsx_ingest.py <文件.xlsx> [--json]`：XLSX 摄取（纯标准库），抽 sharedStrings+worksheet 还原行列文本。
- `scripts/assemble_skill.py <技能包目录> [-o 输出.zip] [--gate auto|strict|off]`：A 模式技能包一键装配——把产出的技能包目录压成标准安装 zip（无顶层目录 / UTF-8 / mtime 统一 / 排除 `__pycache__`・`.pyc`・`release/` 元数据目录 / 幂等），缺 SKILL.md 即 fail-closed 拒绝出包；装配前**强制过门禁，不通过拒绝出包**——自举包跑 `selfcheck --full`，**非自举目录（含用户自己的产物包）改跑产物出厂门禁** `selfcheck <目录> --product`（红线词 / 单字 / 构思层 / 内部标记 / 换行符），**保护对象是用户最终拿走的那件东西，不再对用户产物免检**；出包成功后自动落 `release/` 发布清单与文件指纹。`--self-test` 十二用例离线回归。
- `scripts/evolve.py append|correct|rollback|log --target <标准件目录> --approve`：标准件进化三动作——追加样本（默认独立落位；加 `--slot <名> --merge` 则并入既有 `references/<名>.md`，治碎片化）/ 修正错误（唯一命中才改）/ 回退旧版；每次改动前自动打快照、写 `.evolve/evolve_log.json`，回退前再留安全快照；无 `--approve` 一律拒绝（不静默改写）；`--self-test` 七用例离线回归。
- `scripts/selfcheck.py [包根目录] [--run-selftests|--full|--prove-gates]`：安装包自检 —— **九扫描**（红线词表含单字红线 + 构思层残留 + 术语一致性 + **换行符纪律：文本文件一律 LF**，含 CRLF 即 FAIL + **不可见字符：包内文本一处不许有（零宽 / 方向控制符 / 不可见字母 / 变体选择符〔U+FE0F 除外，属 emoji 常规组成〕/ 标签块）—— 与接料清洗层共用同一判据，两边不许漂移** + **版本号残留：本包版号族只准落在版本声明字段行** + **人群限定词：不按行业 / 岗位 / 职级 / 规模 / 身份收窄；只扫考试词与人群身份词，行业名与职能名不入表以免与示例数据误撞** + **禁推销措辞：命令式购买话术与承诺收益话术一律为 0 —— 「不推销 / 不替用户决定掏钱」铁律的机器判据**）+ **矩阵与决策声明校验**（`references/mode-bc-guide.md` 的「维度 × 格式适用矩阵」须 7 列齐全、Excel 标准表 / 图表两列对「内容深度 / 用途文体」标「不适用」；「决策不过三」声明须在 SKILL.md / popup-spec.md / mode-bc-guide.md 三处一致）+ **输出命名公式门禁（癸-12）**（规范层三要件：命名公式条文 / 后缀枚举 ≥5 项 / 禁用命名声明；给 `--artifacts` 时逐份比对真实产物名 —— 后缀属枚举表、名干非空、连接符半角 `_`）+ **脚本清单对账**（每个 `scripts/*.py` 须带 `--self-test` 或在 `tests/exempt.json` 登记豁免；豁免须 `since`+`reason`，且二选一 —— `expires_in=<版本>` 或 `permanent=true`，两者皆无即 FAIL），全包 PASS 才退出 0。`--run-selftests` 自动遍历带 `--self-test` 的脚本实跑断言 exit=0；跑完立刻做**自测后残留复查** —— 比对包内文件快照（`size`+`mtime_ns`，排除元数据目录），净新增/改动/减少即 FAIL；落在包外当前目录的新文件只报 WARN；`--full` 一键门禁（九扫描→矩阵声明→**输出命名公式门禁**→清单对账→编译→实跑→残留复查→组合联测→**产物契约联测**→PPT 冒烟→内容基线→真实产物），输出 PASS/FAIL/SKIP 三态表、无 FAIL 才 exit 0；`--prove-gates` 阴性对照（**29 条**，在临时副本上逐条故意改坏，断言门禁报警；其中「产物出厂门禁」为红/绿成对两条）；对照跑完还做**元门禁自校验** —— 对「阴性对照清单自身」加条数下限（`NEG_CONTROLS_FLOOR`）+ 必需门类名单（`NEG_REQUIRED_GATES`）+ 负向演练（故意削一条 / 清空，自校验必须报出），防对照清单被删条或改小时仍照常打印 GATES PROVEN。
- `scripts/verify_baseline.py --baseline | --bless --reason "…"`：内容级基线门禁——对固定大纲的 6 个格式产物比对解析后语义指纹（模块标题序列 + **模块内容探针命中集**·强 / 文本字符数·中 ±5% / 字节区间·弱 ±10%·仅同平台）；「探针」= 各模块核心句与全部要点做子串命中。真漂移判 FAIL 阻断出包，「平台不同」等环境差异只报 WARN、不计入漂移。`--bless` 更新基线并写 bless_log 留痕（无 `--reason` 一律拒绝），落盘显式 `newline="\n"` 保证 LF；`--self-test` 七用例离线回归。**覆盖边界**：靶区是**内容本体**（模块标题序列 / 内容探针命中集 / 字符数 / 字节区间），**页眉 / 页脚 / 落款 / 页码等版式性文本不在范围内**；要纳入拦截只需把文本加进 `PROBES`，比对逻辑不动。
- `hooks/`：写时护栏（扫特定禁用词族与人群限定词、扫本地断链），默认不启用，启用方式见 `hooks/install_hooks.py --write`。

## 改进来源（谁说的，就写谁）

本工具每次改动都写明**来自哪里**——**用户开口说的、平台实测出来的、我们自己自查出来的**，三者都算来源。写在这里，给下一个用户看：**这个工具在听人说话。**

- 来自交付链自查：产物交出去之后没有回程（用户想说什么也没有那个口）→ 已补**交付回执**（用户→我方的反馈口）与**结果声明**（交付说明里说清这一趟拿到了什么）。
- 来自包内自查：同一件事在包里有两处写法（内容处理深度的口径）→ 已统一，消除"一处要求问、一处要求不问"的自相矛盾。
- 来自包内自查：材料读不出 / 料不够时没有处置话术 → 已补**接料失败三分支**（读不出给替代路径、料不足给最小清单且只问一次、超范围给替代路径）。
- 来自包内自查：蒸馏段是整个流程最耗时的一段，却全程不出声 → 已补**进度回执**（进段先报、逐段报、长静默前先出声）。
- 来自外部经验分享（2026-10-07，其他开发者）：独立实践印证「早期对齐＋人管关键节点」的路线有效 —— 本包以菜单对齐（决策≤3）与进度回执承载，无需新增确认件。

> **纪律**：每条改进必须写明来源，**不写"优化了体验"这种没有主语的句子**；条目里不写版本号（版号只落在版本声明字段与 `release/` 清单）。
