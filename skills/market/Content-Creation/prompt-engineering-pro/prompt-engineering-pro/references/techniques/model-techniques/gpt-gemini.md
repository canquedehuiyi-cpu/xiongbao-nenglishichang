---
source: OpenAI 官方 Prompt Engineering Guide（platform.openai.com/docs/guides/prompt-engineering）+ Google Gemini 官方提示指南（ai.google.dev/gemini-api/docs/prompting-intro 等）
verified: 2026-09-03
scope: GPT 系列（GPT-4o / o 系 / GPT-4.1 等）与 Gemini 系列（Gemini 1.5 / 2.x 等）
evidential: 来源声称（官方文档为主，具体写法以官方当前版本为准）
---

# GPT / Gemini 官方 Best Practices

> 用途：为 GPT 系列（含 o 系）与 Gemini 系列编写提示词时的官方推荐做法。选型信号：目标模型族 = GPT / Gemini。

## 1. GPT 系列官方最佳实践

OpenAI 官方归纳的六条核心策略（均有实证支撑）：

1. **写清晰指令**：提供细节、说明背景、指明期望格式。模型不能读心，细节决定下限。
2. **提供参考文本**：给模型参考材料，让它基于材料回答，能显著减少虚构。
3. **把复杂任务拆成子任务**：每个子任务独立成提示（对应本 skill 的 prompt-chaining.md）。
4. **给模型时间"思考"**：复杂任务加"先推理再回答"（o 系推理模型除外，见 reasoning-models.md）。
5. **用外部工具补能力**：检索、代码执行等交给工具，提示词只做编排（对应 tool-use-prompts.md）。
6. **系统化测试变更**：用 eval 用例回归，不靠感觉调优（对应本 skill 的 run-evals / calibrate 体系）。

**结构化输出（JSON mode / Structured Outputs）**
- 需要程序化消费输出时，声明 JSON Schema 并启用 Structured Outputs。
- 策略：让模型先想清楚再填 JSON；不要让它"边生成边猜结构"。
- Schema 越严格，失败率越低；字段命名用真实语义。

## 2. Gemini 系列官方提示要点

Gemini 官方提示指南的核心：

1. **明确的任务指令**：把任务说清楚（做什么、格式、约束）。
2. **上下文与示例**：few-shot 示例帮助稳定输出格式；示例放指令之后、问题之前效果更好（位置敏感）。
3. **逐步任务**：复杂任务拆小步，或用 system 指令约束角色。
4. **提示层级**：Gemini 支持 system instruction（系统指令）+ user prompt（用户提示）+ 可选的 few-shot 示例分层组织。

**Gemini 的注意事项**
- Gemini 对**位置**敏感：关键指令与示例尽量靠近问题，避免被长上下文稀释。
- 输出结构用 Markdown / JSON / XML 均可，但要**指定一种**并给样例。
- 长上下文任务注意"中间迷失"问题（lost-in-the-middle）：关键信息放开头或结尾，不放中间（见 context-management.md）。

## 3. 两者的共同点

- 都强调"清晰指令 + 示例 + 结构化输出"三大件。
- 都支持迭代反馈：先生成，再基于错误样例修正提示词（一个错误样例胜过反复抽象描述）。
- 都建议用 eval 用例做回归（OpenAI 策略 6 / Gemini 的 prompt 调优思路一致）。

## 4. 反例（不要这样用）

- 给 GPT/Gemini 套 Claude 的 XML 标签方言 → 它们对 XML 无原生偏好，用通用结构化写法。
- 对 o 系叠显式 CoT → 见 reasoning-models.md。
- 示例位置随意放 → GPT/Gemini 对示例位置敏感，放指令后、问题前。

## 5. 与其它模块联动

- 方言：`build-prompt.mjs` 对 gpt/gemini 族走 Markdown 方言（`## ` 分节），与本文一致。
- 模板：FEWSHOT / SCHEMA 模板适配 GPT/Gemini 的 few-shot 与 JSON 输出偏好。
- 迁移：从 Claude 提示词迁移到 GPT/Gemini → 见 migration 用例（build-cases.json 迁移节）。
