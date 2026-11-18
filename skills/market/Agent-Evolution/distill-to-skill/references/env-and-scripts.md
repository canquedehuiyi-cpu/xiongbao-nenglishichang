# env-and-scripts（自主件移出的细则册）

> **本册由主件 `SKILL.md` 按需加载。** 主件保留操作核心与一行指针；本册是细则全集，执行到对应环节时读取，不需要时不必预读（省时间与成本）。内容与主件同源。

### A10 运行环境声明（自包含·零第三方依赖）

- ① 本包零第三方依赖：包内不捆绑任何第三方库、不部署服务、不连外部服务器；核心文本蒸馏（分块 / 提取 / 构造）只用 Python 标准库，装上即用、不污染环境。本包运行于 Agent 平台，平台需联网通电才能工作——联网是产出标准件的前提。媒体降维（转写 / OCR）按方法标准处理，详见 A0.0 / O4；当无法拿到锚定文本时，如实声明并请用户提供字幕 / 文字稿。
- ② 无需额外凭证：不需要账号、密钥或接口配置，装上即可用；运行仅需 Agent 平台联网通电这一前提。
- ③ 可选脚本：包内 `scripts/` 目录脚本仅用 Python 标准库（3.8+），不启用不影响技能正常使用。当前含（每脚本一行，行式同 A6 落点表）：
  - `ingest_chunk.py`：A0.1 语义分块
  - `verify_chunks.py`：A0.3 块覆盖完整性校验·汇总前机器核对已处理块覆盖全部分块清单、差集非空 exit≠0 不许出包
  - `verify_sources.py`：A0.3+ 源完整性门禁·跨材质 uniform，蒸馏前核对 media_plan/processed 差集、漏单元 exit≠0 不许出包
  - `media_ingest.py`：A0.0 媒体降维·长媒体 ≤10min 真分段防崩 + `--files`/`--dir` 批量隔离编排
  - `web_ingest.py`：链接批量获取·`--urls` 逐条 body + 汇总
  - `stamp_signature.py`：A6#19 溯源盖戳
  - `selfcheck.py`：A5/A6/A7/A9 红线 + 脱敏 + schema 自检
  - `extract_template_tokens.py`：B/C PPT 标准版「参考模板机制」——从用户自有 PPT 抽 {palette/fonts/页型指纹} 设计令牌，只取设计特征不取文字内容
  - `build_ppt_standard.py`：B/C PPT 标准版「可执行生成器」——`render_outline(outline, out_path)` 由结构化大纲驱动、内容无关，内置通用版式原语按 section.type 自动选版式并锁死页型库/导航/令牌/层级/行距/一页一意；各平台 Agent 调用它生成 PPT，**禁止手搓 pptx 渲染代码**
  - `docx_ingest.py`：DOCX 摄取·解 zip+xml、UTF-8 解码、绝不裸读 xml/不猜编码，避免编码报错
  - `distill_skeleton.py`：B/C 单一大纲源渲染器·`save_outline`/`load_outline`/`render_formats`，六格式从同一 canonical outline 确定性渲染，结构上保证多格式同源；canonical 的 sources 透传进各格式页脚（来源总览）；**两容器映射**——`points`→各格式要点列表、`paragraphs`→各格式成段正文（md/txt/pdf 走 `paragraphs`、docx 走 `paras`）
  - `verify_multiformat.py`：B/C 跨格式一致性门禁·比对 canonical outline 模块标题集合 + **成段正文（`paragraphs`）存活**与产物，任一不等/缺失 exit≠0 不许交付
  - `verify_d3.py`：D3 只留骨架自检·扫文本类产物原文长句/金句，命中告警、`--strict` 可门禁拦截
  - `intake.py`：统一多物料接料层·一次接收多链接/多文档/文件夹/文本/清单，按类型路由各读取脚本 + 媒体委派 `media_ingest`，产出 materials_plan/materials_processed/corpus 三件套，单单元失败隔离、任意 N 路组合归一
  - `pdf_ingest.py`：PDF 摄取·best-effort FlateDecode 内容流抽 Tj/TJ 文本，扫描版/无文本层优雅降级不崩
  - `pptx_ingest.py`：PPTX 摄取·解 zip+xml、抽 `<a:t>` 正文 + 笔记页
  - `xlsx_ingest.py`：XLSX 摄取·抽 sharedStrings + worksheet 还原行列文本
- ④ 媒体处理环境限制：Windows 上 Python 3.12 的 asyncio 默认用 socketpair（回环 TCP），受限环境（沙箱 / 防火墙 / 企业策略）可能触发事件循环挂起。若媒体降维路径创建事件循环无响应，改用非 asyncio 的轮询式路径，或提示用户提供字幕 / 文字稿替代媒体降维，不依赖隐藏二进制路径临时补救。
- ⑤ 跨平台·订阅可用（双维度）：**分发维度**——用户在任意硬件（苹果手机 / 安卓手机 / 苹果电脑 / Linux / Windows）上的 Agent 平台里订阅本技能包，装后即用；实际执行由平台宿主环境完成，用户端设备只负责交互与查看，不要求本地有 Python 或特定 OS。**运行维度**——包内脚本只用标准库、按宿主系统探测字体与二进制路径，不硬编码任何系统专用绝对路径（如 `C:/Windows/...`），确保宿主为 macOS / Linux / Android 后端时同样能跑，不假设宿主是 Windows。产出格式（OOXML / PDF / MD / TXT）均为开放跨平台格式，任意标准查看器可打开。

## 辅助层
