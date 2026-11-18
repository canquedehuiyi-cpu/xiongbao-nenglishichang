# references/environment-matrix.md — 环境指纹与模型族差异矩阵

> 用途：L2 环境指纹采集 + L3 选型依据。**完整矩阵（9 模型族 × 5 维度 + 平台约束 + 任务映射）。**
> ⚠️ 模型能力快速变化：遇到较新模型/能力存疑时，走 §3.4 情报检索（web_search 核实，来源标注），不要依赖本表假设（防过时知识当新规则）。

## 1. 环境指纹字段（L2 必采，缺失则询问）

| 字段 | 取值 | 对提示词的影响 |
|------|------|----------------|
| model_family | claude/gpt/gemini/deepseek/doubao/glm/qwen/kimi/open | 语法方言、CoT 可用性、System Prompt 遵循度 |
| platform_form | chat/system_prompt/agent/tool_call/mcp/vision/pipeline | 结构约束（占位符/工具 schema/自检） |
| task_type | 15 类（代码/写作/分析/抽取/分类/创意/对话/agentic/RAG/图像/教育/决策/数学/逻辑/调试） | 模板选择与技术栈 |
| subtype | 可选子类（如 agentic 的 工具调用/mcp/管道/常驻；创意 的 头脑风暴） | 更精确的模板路由（SUB_ROUTE） |
| context_budget | 模型窗口 + 用户可接受用量（token） | 用词上限（§token-economy 预算） |
| user_level | novice/intermediate/expert | 输出详略 |
| language | 中/英/双语 | 措辞与示例语言 |
| goal_verifiability | 用户能否给出成功标准 | 是否反问澄清、是否生成验收条件 |

## 2. 模型族差异矩阵（9 模型族 × 5 维度）

| 维度 | Claude | GPT | Gemini | DeepSeek | 豆包 | GLM | Qwen | Kimi | 开源(Llama/Mistral) |
|------|--------|-----|--------|----------|------|-----|------|------|----------------------|
| 结构语法 | XML 标签最佳 | Markdown 标题最佳 | 清晰指令+结构化 | CoT 友好 | 中文简洁指令 | 结构化中文 | 中文简洁 | 中文简洁 | 指令格式敏感 |
| System Prompt 遵循度 | 高 | 高 | 高 | 中 | 中 | 中 | 中 | 中 | 中（弱指令模型低） |
| CoT | 支持（推荐） | **o 系禁用 CoT**，普通系可 | 支持（推荐） | 支持（推荐） | 支持 | 支持 | 支持 | 支持 | 支持 |
| 长提示词 | 处理佳 | 处理佳 | 处理佳 | 可能丢失 | 可能丢失 | 可能丢失 | 可处理 | 可处理 | 可能丢失 |
| 中文指令 | 好 | 好 | 好 | 最优 | 最优 | 最优 | 最优 | 最优 | 一般 |

**选型规则（编码进 build-prompt.mjs）**：
- `claude` → XML 标签结构 + CoT 可选
- `gpt` → Markdown 结构；**model 版本含 `o1`/`o3`/`o4` 时禁用 CoT 与显式推理指令**
- `deepseek/doubao/glm/qwen/kimi` → 中文简洁指令 + CoT 可选（DeepSeek 优先 CoT）
- `open` → 保守结构（Markdown + 显式格式约束），CoT 视任务

## 2.5 模型族 × 技法包映射表（v1.0.8，与 model-adapt.mjs 同源）

> 供 L3 快速取技法包；详细可执行取包用 `node scripts/model-adapt.mjs --model <族>`（权威，含官方来源标注）。

| model_family | 结构语法 | CoT 策略 | 输出格式 | 防幻觉 | 长上下文 |
|--------------|----------|----------|----------|--------|----------|
| claude | XML 标签分节 | Extended Thinking（budget 从 1024 起调优；不用“think”措辞） | 正向 Output format（“请”而非“不要”）+ Multishot 3-5 例 | 引用接地 | 关键前置+query 末尾 |
| gpt | Markdown 分节 | o 系禁显式 CoT；非 o 系可步骤式 | JSON mode / 结构化输出；few-shot 在指令后 | 先引用再作答 | 指令放末尾 |
| gemini | 清晰指令+结构化 | thinking 族内部推理 | JSON schema / 结构化输出 | 引用接地+低置信标注 | 大窗口可放全文，指令前置 |
| deepseek | 中文简洁 | R1 走内部推理；V 系可 CoT | 显式格式 | 引用接地+缺料兜底 | 精简+置顶+分块 |
| doubao | 中文简洁 | 支持按需 | 显式格式 | 引用接地+缺料兜底 | 精简+置顶 |
| glm | 中文结构化 | 支持按需 | 显式格式 | 引用接地+缺料兜底 | 置顶关键 |
| qwen | 中文简洁 | 支持按需 | 显式格式 | 引用接地+缺料兜底 | 分块+关键前置 |
| kimi | 中文简洁 | k2 走内部推理 | 显式格式 | 引用接地+缺料兜底 | 超长文本强，关键前置 |
| open | 保守结构+显式约束 | 弱指令模型免复杂 CoT | 显式格式+few-shot | 强防幻觉+自检 | 精简+分块 |

> 推理模型族（gpt-o 系 / gemini-thinking / deepseek-r1 / kimi-k2 / claude-extended）：少写显式推理步骤，避免干扰内部推理并省 token。

## 3. 平台形态 × 结构约束对照表

| platform_form | 结构要求 | 是否需要 | 示例 |
|---------------|----------|----------|------|
| chat | 完整指令 + 输出格式 | 无需占位符 | 一次性对话 |
| system_prompt | 角色+规则+边界，无输入占位 | 常驻指令 | 助手人格 |
| agent | 工具使用规则 + 自检 + 停止条件 | 工具 schema | ReAct |
| tool_call | 严格输出 schema | JSON schema | 函数调用 |
| mcp | 工具描述 + 参数约束 | 工具描述格式 | MCP server |
| vision | 视觉描述符 + 构图术语 | 图像要素 | 文生图 |
| pipeline | 分步处理 + 错误处理 | 每步输入输出定义 | 批量管道 |

## 4. 任务轴 A（15 类）→ 推荐模板映射

| task_type | 推荐模板 | 兜底模板 | 核心技术 |
|-----------|----------|----------|----------|
| 代码 | RISEN | CO-STAR | CoT + 防幻觉锚点 + 测试验收 |
| 写作 | CO-STAR | CRISPE | 角色 + 语气约束 + 长度预算 |
| 分析 | CO-STAR | 决策模板 | CoT + 结构输出 + 证据引用 |
| 抽取 | SCHEMA | FEWSHOT | JSON schema + Few-shot |
| 分类 | FEWSHOT | SCHEMA | Few-shot 示例 + 类别白名单 |
| 创意 | CRISPE | CO-STAR | 个性化 + 迭代约束 |
| 对话 | RTF | CO-STAR | 角色 + 语气 + 边界 |
| agentic | REACT | RISEN | 工具循环 + 停止条件 + 自检 |
| RAG | RAG | CO-STAR | 引用格式 + 无法回答兜底 + 防幻觉 |
| 图像 | VISION | RTF | 视觉描述符 + 构图 |
| 教育 | SOCRATIC | CO-STAR | 引导式提问 + 分步 |
| 决策 | DECISION | CO-STAR | RICE/Pros-Cons + 结构化权衡 |
| 数学 | COT | CO-STAR | 逐步推理 + 验证步骤 |
| 逻辑 | COT | CO-STAR | 逐步推理 + 拆解 |
| 调试 | COT | RISEN | 逐步推理 + 边界验证 |

**子类路由（SUB_ROUTE：20 模板全部可达）**：`task_type + subtype` 双键路由，subtype 未命中回退主路由表：

| task_type | subtype | 模板 |
|-----------|---------|------|
| 代码 | 推理 / 调试 | COT |
| 代码 | 常驻 | AGENT |
| 代码 | 工具调用 | TOOLCALL |
| agentic | 工具调用 | TOOLCALL |
| agentic | mcp | MCP |
| agentic | 管道 | PIPELINE |
| agentic | 常驻 | AGENT |
| 对话 | 多轮 / 客服 | DIALOGUE |
| 对话 | 快速单步 | RTF |
| 创意 | 头脑风暴 / 发散 | BRAINSTORM |
| 分析 | 多源综合 / 综合 | SYNTHESIS |
| 分类 | 有限类别 / 稳定分类 | CLASSIFY |
| 写作 | 品牌 / 个性化 | CRISPE |

**路由规则**：`subtype → 主任务类型 → 领域 → CO-STAR`；未命中回退 CO-STAR（通用安全网），记录 usage log 供覆盖检查。

**领域路由（v1.0.4 domain-ready：DOMAIN_ROUTE，任务轴未命中时按领域兜底）**：

| 领域 | 默认模板 | 领域全部模板 |
|------|----------|--------------|
| game | GAME-DEV | GAME-DEV / GAME-NPC / GAME-DESIGN / GAME-ASSET / GAME-STORE |
| visual | IMAGE-GEN | IMAGE-GEN / CHARACTER-DESIGN / UI-DESIGN / VIDEO-SCRIPT |
| ai | AGENT-SYSTEM | AGENT-SYSTEM / SKILL-PACK / MCP-DECL |
| ecommerce | PRODUCT-TITLE | PRODUCT-TITLE / DETAIL-PAGE / LIVE-SCRIPT / CS-SCRIPT |
| content | XHS-NOTE | XHS-NOTE / WECHAT-ARTICLE / SEO |

**领域子类路由（DOMAIN_SUB）**：`领域 + subtype` 精确选型（如 game+角色 → GAME-NPC、visual+界面 → UI-DESIGN）；未命中子类回退领域默认模板。领域识别由 `domain-router.mjs` 完成（关键词计分，未识别走通用）。

## 5. 版本标注与陈旧度

- 本矩阵更新频率：随模型发布季度评审；`last_reviewed` 标注在文件头。
- 使用前若模型族较新（发布 <6 个月）或用户指定具体版本号，优先走 §3.4 情报检索核实，本表仅作基线。
- 模型"已知怪癖"（如 Claude 对 think 词敏感、Opus 4.5/4.6 过度工程化倾向）见 techniques/model-techniques/ 各模型文件；精确版本号矩阵不写死（随模型发布过时，走情报检索动态核验）。
