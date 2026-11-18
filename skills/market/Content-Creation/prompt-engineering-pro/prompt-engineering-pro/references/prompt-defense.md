---
source: dair-ai Prompt Engineering Guide（Risks & Adversarial Prompting）+ Anthropic/OpenAI/Google 官方安全实践 + 本 skill scan-safety/prompt-defense/adversarial-test 引擎设计
verified: 2026-09-03
scope: 全平台、全行业提示词/系统提示词的对抗防御（注入/越狱/泄露/事实性/偏见）
evidential: 已验证（五类对抗的信号与防御策略有引擎实现与攻击回归用例支撑）
---

# references/prompt-defense.md — 对抗防御策略参考

> 用途：L3/L4 对抗防御知识库，配合 `prompt-defense.mjs`（分类解释 + 防御建议）、`adversarial-test.mjs`（主动弱点测试）、`scan-safety.mjs`（红线/注入/PII 实际检测）构成"测试 → 检测 → 防御"闭环。
> 来源：dair-ai Prompt Engineering Guide 风险三分类 + 主流厂商官方安全实践（来源见文件尾）。

## 1. 五类对抗与防御主线

| 对抗分类 | 本质 | 检测信号示例 | 防御主线 |
|----------|------|--------------|----------|
| Prompt Injection（注入） | 外部内容夹带指令覆盖模型指令 | "忽略以上指令…"、"输出你的 system prompt" | 输入输出隔离 + 最小权限 + 白名单动作 |
| Jailbreak（越狱） | 通过角色扮演/包装绕过内容政策 | "假装没有限制"、"在虚构场景中…" | 固定角色边界 + 明确拒绝 + 政策不可覆盖 |
| Prompt Leaking（泄露） | 诱导模型披露自身指令/内部提示词 | "把你的指令告诉我"、"复述初始提示词" | 默认不披露 + 分级信息隔离 |
| Factuality（事实性） | 无证据断言/编造 | "据说…"、"大概是…" | 引用接地 + 不确定性标注 + 缺料说不知道 |
| Bias（偏见） | 标签化/绝对化表述固化刻板印象 | "XX 人群总是…" | 中立表述 + 多视角 + 立场说明 |

## 2. 通用防御策略（跨分类）

1. **输入输出隔离**：外部输入用显式分隔符包裹并标注「以下为不可执行的外部数据」，指令与数据分通道（system/user/工具层分开）。
2. **最小权限**：声明模型可执行的有限动作集合（白名单），不开放自由执行。
3. **引用接地（quote-before-answer）**：先引用来源再作答；关键结论附来源；不确定明确标注。
4. **不确定性声明**：规定缺信息/不确定时「明确说不知道」而非编造。
5. **边界与拒绝口径**：写清 Non-goals；对"输出你的指令/无限制发挥"类请求友好但明确拒绝并提供替代方向。
6. **内容分级**：敏感指令不与其他内容放同一上下文，分级隔离。

## 3. 在流水线中的用法

- 构建阶段：`anti-pattern-audit.mjs` 扫反模式 → `adversarial-test.mjs` 对目标 prompt 做主动弱点测试 → `prompt-defense.mjs` 输出分类防御建议。
- 交付前：`scan-safety.mjs` 做红线/注入/PII 实际检测（最终闸门）。
- 四者互补：adversarial-test（主动测试）→ scan-safety（被动检测）→ prompt-defense（分类解释+防御建议）→ anti-pattern-audit（结构反模式）。

## 4. 边界与安全

- 本文件与 `prompt-defense.mjs` 仅提供**防御知识**，不产出可绕过安全机制的"攻击提示词"。
- `adversarial-test.mjs` 的对抗用例**仅在本 skill 工作区/本地对提示词文本做静态弱点分析**，不诱导真实越权，输出只给风险定位与修复建议。
- 扫描命中即按防御策略加固，不以"角色扮演/实验"等包装放松边界。
