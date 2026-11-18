# 科研 Copilot

覆盖科研全流程的一站式助手插件，把从选题、检索、实验设计、写作、配图到评审的关键工作都封装成可直接调用的技能。共内置 18 个技能，按「文献证据 → 科研构思 → 学术表达 → 协作记忆 → 工具评测」五大阶段组织，帮助科研人员、研究生和团队更高效地推进研究与成果产出。

> **免责声明：** 本插件用于辅助科研工作流，不替代专业的学术判断、同行评审或伦理审查。所有输出（含文献结论、实验方案、引用核验、审稿意见等）都应由具备资质的研究者在决策或发表前复核。

## 适用人群

- **研究生 / 博士生** —— 从开题调研、实验设计到论文写作、投稿准备的全程支持。
- **科研人员 / PI** —— 快速生成研究想法、基线方案、审稿意见与项目申请材料。
- **科研团队 / 实验室** —— 沉淀协作画像与偏好，统一评测技能与 MCP 工具质量。

## 快捷指令

| 指令 | 说明 |
|------|------|
| `/find-science-skills` | 按领域×阶段×功能，帮你找到合适的科研 Skill / MCP |
| `/giiisp-paper-search-apis` | 调用论文检索接口做文献初筛与 arXiv 定位 |
| `/sci-employee-deep-research` | Deep Research 流程，产出可核验的研究报告 |
| `/thesis-audit-reviewer` | 学位论文逐条审阅，生成标准化审阅报告 |
| `/scispark` | 从关键词/文献生成可验证的研究假设与想法 |
| `/research-baseline-builder` | 把科研问题拆成数据输入输出与基线工作流 |
| `/experiment-design` | 采集数据前的统计化、可复现实验设计 |
| `/academic-writing` | 论文写—审—改—投全流程写作 |
| `/scientific-humanization` | 去 AI 味、去模板腔的中文科研文本润色 |
| `/giiisp-scientific-image-generation` | 生成论文配图、机制图、流程示意图 |
| `/visual-deck-builder` | 图像驱动的高质量 PPT 汇报制作 |
| `/manim-agent` | 公式/概念可视化，生成带配音讲解动画 |
| `/practical-course-producer` | 基于真实操作的实操课程/教程视频 |
| `/papercheck` | 无密钥引用合规与引文真实性核验 |
| `/cognitive-profile` | 建立并维护贴合本人的用户画像与偏好 |
| `/world-threads-entry` | 连接与操作 TopicLab / 他山世界 world threads |
| `/mcp-criticagent` | 端到端评测 MCP 服务与工具质量 |
| `/skill-criticagent` | 评测 Agent Skill 是否好用、是否安全 |

## 技能清单

| 技能 | 说明 |
|------|------|
| find-science-skills | 按「资源类型×领域×阶段×功能」确定性筛选可用的 Skill / MCP，避免盲选 |
| giiisp-paper-search-apis | 调用 Giiisp/集思谱检索接口，支持 OA 与 arXiv 多字段检索、文献初筛与引用审计 |
| sci-employee-deep-research | 组织检索、关键词拆解、候选证据与最终 answer，产出可核验研究报告 |
| thesis-audit-reviewer | 基于清单逐行、带证据与 PDF 页码定位的学位论文审阅，输出标准化中文报告 |
| scispark | 基于 arXiv 的证据可追溯研究想法生成：事实抽取、可验证假设、机制分析 |
| research-baseline-builder | 明确数据输入/输出、样本标签特征，规划预处理、基线、训练与评估流程 |
| experiment-design | 采集前的研究设计：设计类型选择、随机化区组、样本量与统计功效、分析计划与预注册 |
| academic-writing | 论文/章节撰写、同行评审、rebuttal、基金申请与投稿材料的写—审—改—投闭环 |
| scientific-humanization | 在保护事实、术语、数字与引用的前提下，把中文科研文本改得更像作者本人在讲 |
| giiisp-scientific-image-generation | 把段落/图题/机制描述整理成作图简报并生成科研配图、流程图、机制通路图 |
| visual-deck-builder | 图像模型驱动的整页高质量 PPT 生成，含清单、预览与证据支撑的 QA |
| manim-agent | Manim 动画与带配音讲解视频，公式/证明/概念可视化，渲染为 mp4 |
| practical-course-producer | 基于真实终端/浏览器操作的可发布实操教程视频，含演示、纠错与校验 |
| papercheck | 本地证据抽取 + TaShan-PaperChecker 规则的无密钥引用合规与引文真实性核验 |
| cognitive-profile | 在对话中逐步形成可修正的用户画像，只记录影响后续回答的长期偏好 |
| world-threads-entry | 连接/测试/操作 TopicLab、他山世界、OpenClaw world threads 与技能安装 |
| mcp-criticagent | 从部署、协议通信、工具调用到仓库可持续性，端到端评测 MCP 服务与工具 |
| skill-criticagent | 评测 Agent Skill 的规范合规、安全扫描、有无对比与触发词，给出安装/修复/拒绝结论 |

> 所有技能均可独立使用，无需额外连接器即可运行；部分技能会调用其内置脚本或公开检索接口。
