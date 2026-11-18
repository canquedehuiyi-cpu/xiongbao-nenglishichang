---
name: word-layout-qa
description: Word(.docx) 交付的排版校核与修复流程：逐属性 pinning、程序化 census 审计、Word COM 渲染逐页 PNG、孤行/空白页 ink 检测、逐页目视与 check_document。创建/编辑/填写 Word 交付物（长篇报告、方案、模板填写）或用户反馈 Word 格式/排版问题（空白页、孤行、续表表头、目录页码、字体字号不统一）时使用；与 office-docx skill 配合，补其无页面渲染能力的缺口。
---

# Word 排版校核 (word-layout-qa)

## 适用与前提

- 任何 .docx 交付物交付前必须走完本流程。结构检查（check_document）≠ 版面检查：孤行页、表宽、编号空隙只有渲染后才暴露。
- 平台与依赖：渲染步需 Windows＋已安装 Microsoft Word（COM 自动化）＋PowerShell 5.1+；审计、pinning、ink 扫描只需 Python 3.9+（python-docx、lxml、Pillow）。macOS/Linux 或无 Word 环境可跑审计与扫描，但渲染步不可用，须先向用户说明覆盖缺口。
- Python 调用：优先 PATH 上的 `python`；不在 PATH 时用解释器绝对路径（如 Anaconda 安装目录下的 python.exe）；打印中文前设 `PYTHONIOENCODING=utf-8`。
- 系统安全策略（如 Windows Smart App Control）拦截未签名 PDF/渲染库时不要关闭策略；Word COM 是系统自带的签名路线。PowerShell 脚本仅 ASCII 字符、工作文件放 `%TEMP%` 的 ASCII 路径。

## 流程

1. **定体例**：从模板或用户要求记录正文/标题/表格/封面/目录的字体（eastAsia + ascii/hAnsi）、字号、首行缩进、行距、对齐，写入项目笔记；无模板时先问用户或沿用同类交付物体例。
2. **编辑纪律**：
   - 模板空白 run 无 rPr → 继承 Normal 默认（常 10.5pt）；填写后必须逐属性 pinning，不能只改部分段落。
   - 运行级格式手术优先 python-docx。office-docx MCP 的 blockIndexes 与 python-docx 段落索引是两套体系（存在固定偏移），严禁混用；MCP 写操作后必须回读核对。
   - MCP `replace_blocks` 会丢段尾分页 run；封面/目录分页用 `pageBreakBefore` 补。
3. **审计**：`python scripts/audit_docx.py report.docx`。看各 class 的字体/段落 census 少数派组合、RUNS_WITHOUT_RPR、半角标点、numPr、上下标、表格列宽、SPACER_BREAK、TABLES_WITHOUT_REPEAT_HEADER。按 `references/pinning_template.py` 写本项目 pinning 脚本修复，复跑审计至 0 违规。
4. **渲染**：docx 复制到 ASCII 工作目录（如 `%TEMP%`）；运行 `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/render_docx.ps1 -Docx C:\Temp\report.docx -Pdf C:\Temp\report.pdf -Prefix C:\Temp\rptpg [-AlignTable1]`（示例路径，按实际替换）。脚本更新目录域/Fields/页码 → Save → 导 PDF → 逐页 EMF→PNG(2×)。百页级约数分钟，timeout 设 600000。
5. **扫描**：`python scripts/page_scan.py C:\Temp\rptpg 81`（PNG 前缀＋页数）→ 生成 `_s.png` 并输出每页 ink 占比；`NEAR_EMPTY`(<0.5%) 与 `SPARSE`(<2%) 页必须目视判定（孤行/空白页 vs 正常目录、封面）。
6. **目视**：Read 所有 flag 页＋关键页（封面、目录、各章首页、表格页、图页、公式页、参考文献、附录首页）。核对：编号体系一致、缩进齐平、字号 uniform、表宽与单元格对齐、真上下标、无孤行、图题表题位置。长文档按"flag 页＋关键页"抽样目视，其余靠审计＋ink 扫描覆盖，并在汇报中说明覆盖方式。
7. **收尾**：MCP `check_document` 0 问题，或仅剩已核实的误报（典型：`TOC \t "题注,1"` 等图表清单条目被 `toc_stale` 判为 "match no heading"——检查器只认标题式目录；须目视清单页确认页码已刷新后才可按误报结案）。docx 与预览 PDF 拷回交付目录；汇报查了什么、怎么查的、哪些未查。修复后必须重渲染复验，不得只改不验。

## 常见坑

- 自动编号 numPr 与手动编号混排 → 制表位大空隙；统一为手动编号或统一为列表样式。
- 表格末列过窄、单元格两端对齐拉伸 → 设列宽(twips)＋COM 单元格对齐（表头 1 居中、表体 0 左）。
- 孤行页：末段溢出 1–2 字独立成页 → 微调末句措辞（语义不变）收回；勿留近空白页。
- 整页空白：空段落＋`w:br type="page"` 作章间分页时，前文恰好填满一页会把空段孤置到新页 → 空白页。改用后续标题 `pageBreakBefore=True` 并删除空段（对未孤置的边界行为不变）；审计 `SPACER_BREAK` 列出全部此类隐患，改分页会动全文 pagination，应一次清完再重渲染。
- 跨页表格续页无表头：首行 `trPr` 加 `w:tblHeader`；审计 `TABLES_WITHOUT_REPEAT_HEADER` 列出缺失表。加表头会改变续页高度，须与分页改造同批重渲染复验。
- 公式上下标用 `w:vertAlign val="subscript"` 真上下标 run，勿混用 Unicode 下标字符。
- 目录字体需 pin TOC 1/2/3 样式 rFonts；页码靠 COM `UpdatePageNumbers` 刷新。
- lxml 元素无 `.xml` 属性 → `etree.tostring(el)`。
- 加粗标签体例：段首"××："加粗须全文一致，漏一处即显杂乱。

## 资源

- `scripts/audit_docx.py`：通用 census 审计（字体/字号/缩进/行距/对齐、无 rPr run、半角标点、numPr、上下标、表格列宽、SPACER_BREAK 空白页隐患、跨页表头缺失）。
- `scripts/render_docx.ps1`：Word COM 目录刷新＋PDF 导出＋逐页渲染（参数化，ASCII）。
- `scripts/page_scan.py`：降采样＋ink 占比孤行/空白页检测。
- `references/pinning_template.py`：python-docx 逐属性 pinning、run 重建、上下标、表格与 TOC 样式固定的注解模板。