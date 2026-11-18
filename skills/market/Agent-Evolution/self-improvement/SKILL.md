---
name: self-improvement
description: "持续自我提升技能：捕获经验、错误、用户纠正、功能请求，写入 .learnings/ 学习日志，通过重复检测将高价值经验提升为记忆/规则/新技能。触发时机：(1) 用户纠正我（'不对'、'其实应该'、'你搞错了'），(2) 任务执行出错且诊断困难，(3) 发现了更好的做法，(4) 用户请求了不存在的功能，(5) 收尾/复盘时，(6) 重大任务开始前回顾学习日志。核心机制纯 Markdown 实现（.learnings/ 目录 + 重复检测 + 提升规则），不依赖任何特定 AI 平台。"
version: 1.0.0
license: MIT
---

# Self-Improvement 自我提升技能

## 平台适配

> 本技能核心机制（.learnings/ 目录、Markdown 记录格式、重复检测与提升规则）为纯文件实现，任何 AI 平台可直接使用。仅「提升动作」涉及平台接口，按平台选择：
>
> | 平台 | 提升动作 |
> |------|----------|
> | Qoder | 调用 UpdateMemory（Qoder 专属接口） |
> | Claude Code | 写入 CLAUDE.md 或项目规则文件 |
> | OpenAI / 其他 | 写入平台指令/规则文件 |
> | 无记忆接口 | 追加到 .learnings/PROMOTED.md 作为本地提升仓库 |
>
> 若平台无对应记忆接口，跳过记忆步骤不影响核心流程——记录、重复检测、验证照常执行。

## 核心原则（反过拟合护栏）

> 三条铁律，防止"越进化越蠢"：
> 1. **不拿单次任务轨迹直接改 Skill**——单次事件只记日志，绝不改规则
> 2. **重复才提升**——同一模式出现 3 次以上（跨至少 2 个不同任务）才提升为记忆/规则
> 3. **无验证不进化**——修复/改进必须验证有效后才算数，验证结果写进日志

## 学习循环

```
捕获 → 记录(.learnings/) → 重复检测 → 提升(记忆/规则/技能) → 验证
```

## 快速参考

| 场景 | 动作 |
|------|------|
| 用户纠正我 | 记 `.learnings/LEARNINGS.md`，类别 `correction` |
| 任务出错（已解决/未解决） | 记 `.learnings/ERRORS.md` |
| 发现更好做法 | 记 `.learnings/LEARNINGS.md`，类别 `best_practice` |
| 知识过时/缺失 | 记 `.learnings/LEARNINGS.md`，类别 `knowledge_gap` |
| 用户想要没有的功能 | 记 `.learnings/FEATURE_REQUESTS.md` |
| 同类条目已存在 | 链接 `See Also`，递增 `Recurrence-Count`，考虑升级优先级 |
| 重复 ≥3 次且跨任务 | **提升**：写入记忆系统 或 项目规则文档 或 新 skill |
| 重大任务开始前 | 先回顾 `.learnings/` 相关条目 |

## 文件结构

项目根目录下 `.learnings/`：

```
.learnings/
├── LEARNINGS.md          # 经验教训（correction / best_practice / knowledge_gap）
├── ERRORS.md             # 错误记录
└── FEATURE_REQUESTS.md   # 功能请求
```

首次使用：若 `.learnings/` 不存在则创建，并用下方模板初始化三个文件。

## 记录格式

### 学习条目（LEARNINGS.md）

```markdown
## [LRN-YYYYMMDD-XXX] 类别

**Logged**: 时间戳
**Priority**: low | medium | high | critical
**Status**: pending | resolved | promoted
**Area**: 领域（如 backend/frontend/ops/design）

### Summary
一句话总结

### Details
发生了什么、哪里错了、正确做法是什么

### Metadata
- Source: conversation | error | user_feedback
- Related Files: 相关文件路径
- See Also: LRN-20260725-001（若相关）
- Recurrence-Count: 1
- First-Seen / Last-Seen: 日期

---
```

### 错误条目（ERRORS.md）

```markdown
## [ERR-YYYYMMDD-XXX] 错误简述

**Logged**: 时间戳
**Priority**: high
**Status**: pending | resolved

### Summary
失败的是什么

### Error
实际错误信息

### Context
尝试了什么操作、环境细节

### Suggested Fix
可能的解法

### Resolution（解决后补）
- **Resolved**: 日期
- **Notes**: 怎么解决的、验证结果

---
```

### 功能请求（FEATURE_REQUESTS.md）

```markdown
## [FEAT-YYYYMMDD-XXX] 能力名

**Logged**: 时间戳
**Priority**: medium
**Status**: pending

### Requested Capability
用户想做什么

### User Context
为什么需要、解决什么问题

### Complexity
simple | medium | complex

---
```

## 编号规则

`TYPE-YYYYMMDD-XXX`：TYPE = LRN / ERR / FEAT；XXX = 当日递增序号（001、002…）

## 提升规则（Promotion Rule）

**同时满足以下条件才提升：**
- [ ] `Recurrence-Count >= 3`
- [ ] 跨至少 2 个不同任务出现
- [ ] 30 天内出现

**提升目标（按优先级）：**

| 目标 | 何时用 |
|------|--------|
| 记忆系统（UpdateMemory） | 用户偏好、行为规范、项目事实——跨会话必须记住的 |
| 项目规则文档（如 AGENTS.md / CLAUDE.md） | 项目内所有参与者都该知道的约定 |
| 新 skill（用 skill-creator） | 可泛化的方法论/工作流，其他项目也能复用 |

**提升格式**：写成简短的预防性规则（"做 X 之前先做 Y"），不写长篇事故报告。

## 自动技能提取

满足任一条件时，考虑提取为新 skill：
- 重复：See Also 链接 2+ 个同类问题
- 已验证：Status = resolved 且修复有效
- 非显而易见：经过真实调试/调查才发现的
- 可泛化：不限于当前项目

提取流程：用平台的技能创建工具（如 skill-creator）创建 → 填模板 → 原条目状态改 `promoted_to_skill`。

## 触发时机清单

**自动触发（任务中）：**
- 用户纠正 → 当场记一条 correction
- 命令失败/异常 → 诊断后记一条 ERR
- 踩了坑且找到解法 → 记 best_practice

**主动触发（收尾/复盘时）：**
- 会话收尾时扫描今日：有新教训？有重复模式？有该提升的？
- 重大任务开始前：grep 相关领域条目，避免重复踩坑

**禁止：**
- 单次失败就改规则/改 skill（违反护栏 1）
- 无验证就宣称改进完成（违反护栏 3）
- 把一次性的环境问题当成规律记录（污染日志）

## 与现有机制的协同

| 机制 | 分工 |
|------|------|
| 记忆系统（UpdateMemory） | 提升目标：重复 ≥3 次的跨会话知识（Qoder 平台专属；其他平台见「平台适配」章节） |
| skill-creator / create-skill | 技能提取：可泛化方法论 |
| 收尾类技能（如文档同步类，按平台可选） | 收尾时一起执行：清理文档与日志，保持仓库整洁 |
| 平台自带的复盘/进化机制（如有） | 与平台的自我进化机制互补，互不冲突 |
