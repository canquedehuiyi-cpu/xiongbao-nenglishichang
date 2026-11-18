---
source: Anthropic 官方 Prompt Engineering 文档（docs.anthropic.com/en/docs/build-with-claude/prompt-engineering）+ Anthropic Skills 生态实践
verified: 2026-09-03
scope: Claude 3.x / 4.x 全任务类型（文本、工具调用、多模态）
evidential: 来源声称（Anthropic 官方文档为主，具体数值以官方文档当前版本为准）
---

# Claude 系列模型专属技法

> 用途：为 Claude 系列（Claude 3.x / 4.x）编写提示词时的官方推荐做法。选型信号：目标模型族 = Claude。

## 1. XML 标签：结构化的首选

Claude 对 XML 标签（`<tag>...</tag>`）有原生偏好。用标签给长指令分节，能显著提升指令遵循一致性。

**基本原则**
- 标签名使用**真实语义**（`<role>`、`<task>`、`<constraints>`、`<format>`），不用任意占位词。
- 标签必须**闭合**且**正确嵌套**，嵌套层数控制在合理深度。
- 长文本放标签内，短指令放标签外；不要把一句话的指令也包进标签。
- 标签可**引用**：后续指令可用 `<example>` 里的内容定义行为，再通过 `<few-shot-example>` 等引用，减少重复。

**示例（骨架）**

```xml
<role>资深数据分析师</role>
<context>用户提供一份 2025 年销售流水，需输出月度趋势结论。</context>
<task>读取数据 → 计算环比 → 给出 3 条结论</task>
<constraints>结论不得编造数据；来源缺失时明确标注。</constraints>
<format>先给结论段，再给数据表。</format>
```

## 2. Multishot：3-5 例黄金数量

Claude 官方建议提供 3-5 个多样、相关的示例，足以稳定输出格式；更多示例边际收益递减且烧 token。

- **质量优先**：3 个能覆盖典型难点的示例，好过 8 个同质示例。
- **覆盖边界**：示例应覆盖"正常情形 + 一两个边界情形"（如空输入、异常格式），让模型学会处理边界。
- 示例放 `<few-shot-examples>` 标签内，与任务指令分开。

## 3. 思维链（CoT）三层次

按任务难度分级使用，不是所有任务都要 CoT：

| 层次 | 触发条件 | 做法 |
|------|----------|------|
| 低（不加） | 简单事实/格式任务 | 直接给结论，不需要推理过程 |
| 中（适度） | 中等推理任务 | 加一句"先说明推理过程再给结论" |
| 高（充分） | 复杂多步推理 | 明确要求"逐步推理，每步说明依据，最后单独成段给结论" |

> 注意：Claude 3.7+ 的 Extended Thinking 模式下，模型自带推理，**不要**再叠加显式 CoT 指令（会干扰或造成冗余输出）。

## 4. Extended Thinking（扩展思考）

Claude 3.7+ 提供 Extended Thinking，适用于数学、代码调试、长链规划等需要深度推理的任务。

- **min_budget_tokens**：官方最低预算 1,024 token，从最低起逐步上调找最优区间（复杂任务可从 16k+ 起步）。
- **措辞敏感**：官方提示，Claude 对 "think" 一词及其变体敏感，建议用 "consider"、"evaluate" 等替代词，避免触发弱推理。
- **高层次指令优先**：官方建议用总体性引导（如 "think thoroughly"）而非手写分步计划——模型的推理路径常优于人工预设步骤。
- 启用扩展思考后，输出会包含"思考过程 + 最终回答"，需要解析时给最终回答单独加标签（如 `<answer>`）。

## 5. Claude 4.x 控制标签（可控行为）

Claude 4.x 系列提供用户级控制标签，用于抑制过度行为（标签随官方版本迭代，以上列表来自 Anthropic 官方文档当前收录）：

| 标签 | 作用 |
|------|------|
| `<default_to_action>` | 优先行动而非提问，减少反问 |
| `<avoid_over_engineering>` | 避免过度设计/过度复杂化解决方案（官方确认 Opus 4.5/4.6 有过度工程化倾向） |
| `<code_exploration>` | 允许/抑制先探索代码再作答 |
| `<investigate_before_answering>` | 强制先调查再回答，减少臆测 |
| `<use_parallel_tool_calls>` | 允许/抑制并行工具调用 |

使用原则：**只在需要时才用**，默认不加；加太多控制标签反而引入噪声。

## 6. Output format 用正向指令

- 用"输出格式为：{明确描述}"，比"不要输出 X"更有效。
- 需要结构化输出时给出**具体结构样例**，比抽象描述稳定。
- 一次只要求一种输出格式，不要给"可 A 可 B"的模糊选项。

## 7. 反例（这些情况不要用本文件的技法）

- 目标模型不是 Claude → 用 gpt-gemini.md / reasoning-models.md 或模型无关技法。
- 推理模型（o 系 / Claude Extended Thinking 已开）→ 不叠加显式 CoT（见 reasoning-models.md）。
- 短小一次性对话 → 用 RTF 模板，XML 标签反而冗余。

## 8. 与其它模块联动

- 模型族适配：本文件是 `build-prompt.mjs` 中 `model_family=claude` 分支的技法依据之一（与 environment-matrix.md 方言规则配套）。
- 模板：构建 Claude 提示词时优先套 XML 方言模板（见 environment-matrix.md §方言表）。
