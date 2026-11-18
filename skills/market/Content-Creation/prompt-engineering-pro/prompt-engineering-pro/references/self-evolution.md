---
source: AutoSkill（ECNU-ICALK）/ SkillForge / SkillMaxxing 自进化实践 + Anthropic 官方"先定义成功标准+建立评测"原则 + 本 skill 画像层（1.0.8）与技能层（1.0.9）引擎设计
verified: 2026-09-03
scope: 提示词工程系统自身的受控进化、实证评估与数据治理原则
evidential: 已验证（引擎实现 track-outcome/run-eval/output-check/diagnose-failures/skill-evo 与本文档一一对应）
---

# 自进化原则（Self-Evolution）

> 目标：让提示词工程系统"越用越懂用户、越用越好用"，但**进化必须受控、可审计、不失控**。

## 1. 三层分工（数据同源、职责不同）

| 层 | 引擎 | 职责 | 产出 |
|----|------|------|------|
| 画像层（1.0.8） | learner / recordRouteLearn | 只记录偏好与路由有效性 | habit-profile 默认值（不改评分） |
| 数据层（1.0.9） | track-outcome / run-eval / output-check | 记录执行结果 + 实证评估 | data/outcomes + technique_evidence |
| 技能层（1.0.9） | diagnose-failures / skill-evo | 从数据诊断失败 + 生成进化提案 | diff 提案（默认不落盘） |

## 2. 受控进化五原则

1. **只产出提案（diff），不自动改写**：skill-evo 默认 dry-run，应用需显式 `--apply` 且必须通过 validate 门禁。
2. **反噪音**：无稳定信号不提案——同一失败模式出现 ≥3 次才生成提案（AutoSkill"无稳定偏好就不创建"）。
3. **实证是诊断的唯一数据源**：无真实 outcomes 数据时 diagnose-failures 诚实返回"样本不足"，不空谈。
4. **人工闸门**：提案写入 references/proposals/ 供评审，不自动修改任何模板/SKILL。
5. **可回退**：版本演进走 proposals 审计流，应用前可 dry-run 校验。

## 3. 实证评估原则

- 先定义成功标准，再建立评测（Anthropic 官方）。
- run-eval 默认 dry-run（本地规则校验，零外部调用）；API 模式需用户显式密钥，仅作对比分析。
- 技法实证状态：effective（通过率 ≥80%）/ pending / no_evidence——不虚构结论。
- output-check 与契约审计互补：一个查 prompt 本身、一个查输出侧。

## 4. 数据治理（data/outcomes 规范）

- **仅存本 skill 工作区 data/**，不采集任何可识别用户身份的信息（无 user/name 字段，字段白名单校验）。
- **保留期默认 90 天**：月度文件 `data/outcomes/YYYY-MM.jsonl`，`--purge` 按保留期清理。
- **--export 导出**（json/jsonl），支持审计与迁移。
- **outcomes 不含可执行危险内容**：仅记录结构化事件（engine/ok/score/contract_hits 等）。
- 进化提案写入前必须通过 validate 门禁与敏感词扫描（scan-safety）。

## 5. 闭环图

```text
生成/评分/审计 → track-outcome 记录 outcome
   ↓
run-eval 实证评估（dry-run 本地 / api 可选）→ technique_evidence
   ↓
output-check 输出侧验证 → deviations/fixes
   ↓
diagnose-failures 聚类归因（样本 ≥3 才给置信度）
   ↓
skill-evo 进化提案（dry-run）→ --apply 写入 proposals/（人工评审）
   ↓
validate + scan-safety 门禁全绿 → 才允许进一步落模板（1.1.0 生命周期管理）
```
