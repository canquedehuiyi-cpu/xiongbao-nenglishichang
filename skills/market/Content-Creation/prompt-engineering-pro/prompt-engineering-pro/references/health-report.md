---
source: SkillForge（Health Monitor + Self-Diagnosis）+ skill-genesis（validation & quality scoring）+ agentskills.io（Evaluating skills 专章）
verified: 2026-09-04
scope: 技能健康诊断维度、等级判定与报告结构
evidential: 已验证（health-report.mjs 全仓扫描与本文档维度一一对应）
---

# 健康诊断报告（health-report）

## 一、定位

`scripts/health-report.mjs` 对技能包做**只读健康体检**：不删除/修改任何文件（死技能只标记不删除），输出结构化健康报告。与 `validate.mjs`（发布前门禁，P0-P10）互补：validate 管"能不能发布"，health-report 管"当前有多健康、哪里可优化"。

## 二、健康维度

| 维度 | 检查内容 | 未通过等级 |
|------|----------|-----------|
| 文档覆盖 | KEY_DOCS 清单（SKILL.md 引用链）是否存在 | critical |
| 引擎注册 | scripts/*.mjs 与 engine-catalog 双向核对（死技能 / 缺注册） | warning / critical |
| 版本一致性 | 引擎 `engine:` 标注与 red.json 版本源一致（validate §4b 同口径） | warning |
| JSON 有效性 | 全仓 .json 可解析 | critical |
| 冗余文档 | references/ 下未被 SKILL.md 引用的 .md | info |

## 三、等级判定

| 等级 | 得分 | 含义 |
|------|------|------|
| healthy | ≥90 | 全仓扫描无 critical/warning |
| warning | 70-89 | 亚健康：存在可修复 warning，不影响主流程 |
| critical | <70 | 不健康：存在 critical，修复后再发布 |

## 四、报告结构

```json
{
  "health": "warning",
  "score": 84,
  "engine_stats": { "total": 50, "unregistered": 2, "missing": 0 },
  "findings": [{ "level": "warning", "item": "..." }],
  "actions": ["..."],
  "verdict": "技能亚健康：存在可修复的 warning（不影响主流程）"
}
```

CLI：`node scripts/health-report.mjs [--json] [--dir <p>]`；管理入口：`node scripts/skill.mjs health`。

## 五、与生命周期的关系

1.1.0 将健康诊断纳入生命周期：`skill health`（体检）→ `skill check`（发布门禁 validate）→ `skill adapt`（跨宿主部署）→ `skill verify`（规范核验）→ `skill report`（汇总报告），形成"体检-发布-部署-核验-汇报"的管理闭环（见 `skill.mjs` 管理 CLI 与 SKILL.md 管理入口段）。
