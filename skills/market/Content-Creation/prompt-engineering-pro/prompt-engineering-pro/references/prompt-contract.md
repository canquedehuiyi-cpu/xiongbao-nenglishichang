---
source: Majkey25/prompt-engineering-skill（Prompt Contract 章节）+ 本 skill 评分/诊断引擎设计（score-prompt / diagnose 规则）
verified: 2026-09-03
scope: 全平台、全行业、全任务类型提示词（创作/分析/代码/对话/工具调用/合规等）
evidential: 已验证（本 skill 评分引擎的 8 维信号与契约要素一一对应，且有多版本回归用例）
---

# Prompt Contract：契约心智模型

> 用途：把提示词视为"一份给模型的契约"——条款完整、无歧义、可验证。是 L3 决策构建与 L4 自评估的底层心智模型。任何提示词都可拆成契约要素来审视。

## 1. 一句话定义

> **契约是最短完整可验证描述**：用尽量少的 token，把任务描述到"模型无需猜测、用户可验收、失败可定位"。

## 2. 契约十一要素

| 要素 | 含义 | 缺失的后果 |
|------|------|-----------|
| Objective | 这次要达成什么（一句话目标） | 模型方向漂移 |
| Context | 背景/场景/受众/已知约束 | 输出不合语境 |
| Task | 具体要做什么（可执行动作） | 泛泛而谈 |
| Constraints | 边界：不许做什么、资源限制 | 越界/过度发挥 |
| Non-goals | 明确"这不是本任务的范围" | 范围蔓延 |
| Output format | 输出结构/格式/长度 | 不可解析 |
| Examples | 期望的样例（好的/边界） | 格式不稳定 |
| Process | 是否需要分步/如何组织 | 结构混乱 |
| Verification | 怎么算做对了（验收标准） | 无法判断好坏 |
| Failure handling | 出错/缺信息时怎么办 | 编造或僵住 |
| Style | 语气/口吻/语言 | 风格不符 |

## 3. 每要素的强 / 弱 / 缺失判例

以 Task 为例：

| 状态 | 判例 |
|------|------|
| 强 | "把用户留言按 情感/诉求/紧急度 三字段抽取，输出 JSON" |
| 弱 | "分析一下这些留言" |
| 缺失 | "帮我处理一下"（无动作、无对象） |

以 Verification 为例：

| 状态 | 判例 |
|------|------|
| 强 | "结论必须引用原文，无引用则标注'未找到依据'" |
| 弱 | "尽量准确" |
| 缺失 | 无验收标准 |

## 4. 用契约审视提示词（自检清单）

写完后逐要素自问：
1. Objective：用户拿到输出能否判断"这就是我要的"？
2. Task：有没有具体动词和明确对象？
3. Constraints：越界的可能性是否被堵住？
4. Non-goals：会不会被理解成"顺带把 X 也做了"？
5. Output format：输出能否被稳定解析？
6. Examples：有没有给出边界样例？
7. Verification：验收标准可执行吗？
8. Failure handling：缺信息时会编造还是明确说"缺"？
9. Process：需要分步的任务给了结构吗？
10. Style：语气与受众匹配吗？

## 5. 契约要素 × Q-Score 映射

本 skill 的 8 维评分与契约要素一一对应：Clarity（Objective/Task）、Specificity（Constraints/Output/Examples）、Structure（要素顺序与分节）、Robustness（Context/Failure handling/Non-goals）、Verifiability（Verification）、Economy（最短完整）、Fit（Style/Process/环境）、Safety（越权/注入/PII）。

## 6. 反例（不要这样用）

- 把十一要素全堆进提示词 → 过度膨胀，违背"最短完整"（Economy 维）。
- 只写 Objective 不写 Verification → 无法验收。
- 只写 Constraints 不写 Non-goals → 边界外仍可能蔓延。

## 7. 与其它模块联动

- 评分：`score-prompt.mjs`（结构 4 维）、`qscore-full.mjs`（8 维）按契约要素打分。
- 诊断：`diagnose.mjs` 的 11 类问题对应契约要素缺失。
- 模板：templates.md 契约要素覆盖标注，显示每个模板覆盖了哪些要素。
- 门禁：`validate.mjs` 内容 frontmatter 门禁保证新增技法文档都带来源/适用范围，防"无源契约"混入。
