---
source: 本 skill 技法体系汇总（techniques.md + model-techniques/* + context-management + prompt-chaining + tool-use-prompts）
verified: 2026-09-03
scope: 全平台、全任务类型技法选择
evidential: 已验证（与 techniques.md / 模板 / 评分信号一致）
---

# 技法速查表（Pattern × 场景 × Token 成本）

> 用途：L3 技术选择的快速参考——按任务场景选技法，附 token 成本提示。详细规则见 techniques.md 与各专门文件。

## 1. 核心技法速查

| 技法 | 适用场景 | Token 成本 | 关键提醒 |
|------|----------|-----------|----------|
| Zero-shot（零样本） | 简单事实/格式任务 | 低 | 指令必须清晰完整 |
| Few-shot（少样本） | 输出格式需稳定 | 中（加示例） | 3-5 例即可，重质量 |
| CoT（思维链） | 复杂推理/数学/逻辑 | 中高 | **推理模型禁用** |
| ReAct（推理+行动） | agentic/工具循环 | 高 | 适合有工具的自主任务 |
| Reflection（反思） | 生成后自查/迭代 | 中 | 二次调用，用于纠错 |
| Chaining（任务链） | 超复杂/分阶段 | 中高 | 单步单目标，需交接物 |
| Self-ask（自问自答） | 复杂多跳问答 | 中高 | 拆子问题再综合 |

## 2. 按场景选技法

| 场景 | 首选技法 | 备选 | 说明 |
|------|----------|------|------|
| 事实问答 | Zero-shot | RTF 模板 | 别过度加 CoT |
| 格式抽取 | Few-shot | SCHEMA | 稳定输出 JSON |
| 数学/逻辑 | CoT | 推理模型 | 拆步验证 |
| 长文档问答 | 上下文管理 | RAG | 置顶+引用接地 |
| 多工具自主 | ReAct | TOOLCALL | 有工具循环才用 |
| 创作发散 | 迭代反馈 | CRISPE | 多次生成修正 |
| 超长任务 | Chaining | PIPELINE | 拆链+交接物 |
| 合规敏感 | 安全前置 | safety-compose | L0 先过安全扫描 |

## 3. Token 成本原则

- 指令本身贵在"清晰"，不在"长"：一个 200 token 的清晰指令优于 2000 token 的含糊堆砌。
- 示例按需添加：格式不稳再加示例，格式已稳别堆。
- CoT/ReAct 只在需要推理链时启用，否则纯烧 token。
- 长材料先压缩（compress-verify 保分压缩）再进上下文。

## 4. 与其它模块联动

- 决策：techniques.md 的"技术×任务矩阵"为完整版，本表是快查入口。
- 模板：每技法对应模板（COT/FEWSHOT/REACT 等），见 templates.md。
- 评分：Economy 维对"该简则简、该细则细"打分。
