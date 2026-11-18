# references/templates.md — 模板库索引（39 模板，任务轴 A + 领域双路由选型）

> 用途：L3 模板路由。**39 模板全部可达（主路由 15 任务 + 子类路由 SUB_ROUTE + 领域路由 DOMAIN_ROUTE），无未引用模板。**

## 路由规则
`if 任务 ∈ X 且 信号 ∈ Y → 模板 T`；未命中 → 回退 **CO-STAR**（通用安全网），并记录"未命中"到 usage log 供覆盖检查。
**三级路由**：`subtype` 优先（SUB_ROUTE，见 environment-matrix.md §4）→ 主路由 TEMPLATE_ROUTE → 领域路由 DOMAIN_ROUTE（见 environment-matrix.md §4 领域节）→ CO-STAR。

## 契约要素覆盖标注（v1.0.6）
每个模板标注其**默认覆盖**的契约要素（见 prompt-contract.md 十一要素），提示构建时需人工补充的要素。

图例：O=Objective · C=Context · T=Task · Cn=Constraints · NG=Non-goals · Out=Output format · Ex=Examples · Pr=Process · V=Verification · FH=Failure handling · St=Style

## 模板清单（20 个任务轴模板 + 19 个领域模板，全部可达）

| 模板 | 路由来源 | 适用任务轴 A | 选型信号 | 契约要素 |
|------|----------|--------------|----------|----------|
| RTF | 主路由：对话；子类：快速单步 | 全部·快速单步 | 简单、一次性、要快 | O/T/Out |
| CO-STAR | 主路由：写作/分析；兜底 | 写作/分析/报告 | 专业文档、要结构完整 | O/C/T/Cn/Out/Ex/Pr/St |
| RISEN | 主路由：代码 | 代码/多步项目 | 复杂、多步骤、有终点 | O/C/T/Cn/Pr/Out/V |
| CRISPE | 主路由：创意；子类：品牌/个性化 | 创意/品牌 | 需要个性化、迭代创作 | O/C/T/Cn/Out/Ex/St |
| COT | 主路由：数学/逻辑/调试；子类：代码·推理/调试 | 数学/逻辑/调试 | 需要推理链路；**o1/o3 类禁用** | O/T/Pr/V/Out |
| FEWSHOT | 主路由：分类 | 抽取/分类/格式 | 输出格式必须稳定 | O/T/Out/Ex |
| REACT | 主路由：agentic | agentic | 自主代理、需要工具循环 | O/C/T/Cn/Pr/Out |
| RAG | 主路由：RAG | RAG | 有检索上下文、需引用 | O/C/T/Out/V/Ex |
| VISION | 主路由：图像 | 图像 | 图像生成 | O/T/Cn/Out/NG |
| SOCRATIC | 主路由：教育 | 教育 | 教学场景 | O/C/T/Pr/St |
| DECISION | 主路由：决策 | 决策 | 需要结构化权衡 | O/C/T/Cn/Out/Pr/V |
| SCHEMA | 主路由：抽取 | 抽取 | 需 JSON/结构化输出 | O/T/Out/V/Ex |
| DIALOGUE | 子类：对话·多轮/客服 | 对话 | 多轮对话、身份语气一致 | O/C/T/St/FH |
| AGENT | 子类：agentic·常驻 / 代码·常驻 | agentic | 常驻 agent 指令 | O/C/T/Cn/Out/FH |
| TOOLCALL | 子类：agentic·工具调用 / 代码·工具调用 | tool_call | 严格参数、机器可解析 | O/T/Cn/Out/V |
| MCP | 子类：agentic·mcp | MCP | MCP server 工具描述 | O/T/Cn/Out |
| PIPELINE | 子类：agentic·管道 | pipeline | 批量/分步处理 | O/T/Pr/Out/V |
| BRAINSTORM | 子类：创意·头脑风暴/发散 | 创意子类 | 发散创意、数量优先 | O/T/Cn/Out |
| SYNTHESIS | 子类：分析·多源综合/综合 | 分析子类 | 多源材料、冲突观点 | O/C/T/Out/V/Ex |
| CLASSIFY | 子类：分类·有限类别/稳定分类 | 分类子类 | 有限类别、稳定分类 | O/T/Out/Ex |

## 领域模板清单（19 个，v1.0.4 领域路由 DOMAIN_ROUTE 可达）

| 领域 | 模板 | 路由来源 | 适用场景 | 选型信号 | 契约要素 |
|------|------|----------|----------|----------|----------|
| game | GAME-DEV | 领域默认 | 游戏玩法/系统/规则文档 | 核心循环、系统规则、验收 | O/C/T/Cn/Out/V |
| game | GAME-NPC | 领域子类：角色/npc | NPC 人设与对话 | 人设、说话风格、禁止项 | O/C/T/St/NG |
| game | GAME-DESIGN | 领域子类：策划 | 玩法策划案 | 定位、玩法、数值 | O/C/T/Cn/Out/V |
| game | GAME-ASSET | 领域子类：美术/素材 | 美术资产规格（含负向约束） | 风格、负向约束、构图 | O/T/Cn/Out/NG |
| game | GAME-STORE | 领域子类：上架/商店 | 商店页文案与上架物料 | 宣传文案、合规自查、上架 | O/C/T/Cn/Out/V |
| visual | IMAGE-GEN | 领域默认 | 文生图指令 | 主体、构图、负向约束 | O/T/Cn/Out/NG |
| visual | CHARACTER-DESIGN | 领域子类：角色 | 角色设计三视图/差异化 | 三视图、差异化、衣装 | O/T/Cn/Out/NG |
| visual | UI-DESIGN | 领域子类：界面/ui | 界面/组件/按钮设计 | 布局、辨识度、组件 | O/T/Cn/Out/NG |
| visual | VIDEO-SCRIPT | 领域子类：视频/脚本 | 短视频分镜脚本 | 前3秒、分镜、台词 | O/T/Pr/Out/St |
| ai | AGENT-SYSTEM | 领域默认 | Agent 系统提示词 | 能力边界、输出契约、工具使用 | O/C/T/Cn/Out/FH |
| ai | SKILL-PACK | 领域子类：skill/技能 | Skill 包规范设计 | 触发词、参数定义、输出模板 | O/C/T/Cn/Out/V |
| ai | MCP-DECL | 领域子类：mcp | MCP server 工具声明 | 服务、工具、参数 | O/T/Cn/Out |
| ecommerce | PRODUCT-TITLE | 领域默认 | 商品标题 | 标题结构、卖点、合规 | O/T/Cn/Out/V |
| ecommerce | DETAIL-PAGE | 领域子类：详情 | 商品详情页 | 痛点、卖点、证据 | O/C/T/Cn/Out |
| ecommerce | LIVE-SCRIPT | 领域子类：直播 | 直播带货话术 | 开场、逼单、互动 | O/C/T/Pr/Out/St |
| ecommerce | CS-SCRIPT | 领域子类：客服 | 客服话术 | 场景、方案、安抚 | O/C/T/St/FH |
| content | XHS-NOTE | 领域默认 | 小红书图文笔记 | 标题、标签、互动钩子 | O/C/T/Out/St |
| content | WECHAT-ARTICLE | 领域子类：公众号/文章 | 公众号长文 | 开篇、金句、结构 | O/C/T/Out/St |
| content | SEO | 领域子类：seo | SEO 关键词与页面文案 | 关键词、标题、元信息 | O/T/Cn/Out/V |

## 模板文件位置
各模板骨架放 `references/templates/` 目录（39 个 .md 文件）。

## 完整性说明
- 39 个模板骨架文件齐全（references/templates/ 下，无占位残留）
- 每个模板均含"反例"（什么情况不该用）
- 选型信号可测化（build-prompt.mjs TEMPLATE_ROUTE + SUB_ROUTE + DOMAIN_ROUTE + references/evals/build-cases.json 24 组合 + 子类用例测试 + matrix-check 四方矩阵校验）
- 路由可达性校验（matrix-check.mjs）：每个模板文件必须被主路由或子类路由引用，无未引用模板
- 契约要素标注（v1.0.6）：每模板标注默认覆盖要素；构建时对未覆盖要素（尤其 NG/V/FH）需按任务补充
