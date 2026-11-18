---
source: agentskills.io（官方规范站：build once / use across any skills-compatible agent、渐进披露、frontmatter 规范）+ 各大宿主官方文档（Claude Code Skills、Codex AGENTS.md、Cursor Rules、ChatGPT Instructions）
verified: 2026-09-04
scope: 多宿主部署格式生成与 frontmatter 合规规范
evidential: 已验证（host-adapt.mjs 生成全部 5 种宿主格式，frontmatter 校验与本文档一致）
---

# 多宿主部署指南（host-deploy）

## 一、定位

本 skill 遵循 "build once, use across any skills-compatible agent"：**核心包一份，按宿主生成部署骨架**。宿主适配由 `scripts/host-adapt.mjs` 完成——只生成部署文件骨架到本工作区 `host-out/`，**不执行任何宿主侧命令、不写宿主配置目录**（部署动作由用户自行完成，避免越权与平台锁定）。

## 二、支持的宿主

| 宿主 | 目录 | 文件名 | 说明 |
|------|------|--------|------|
| Claude Code | `.claude/skills/<name>/` | `SKILL.md` | 放入后自动加载（原样核心包） |
| Codex / OpenAI | `.codex/` | `AGENTS.md` | 追加为技能段落（含核心包指针） |
| Cursor | `.cursor/rules/` | `SKILL.md.mdc` | Rules 中启用（frontmatter 含 description/globs） |
| ChatGPT | `.chatgpt/` | `instructions.txt` | 粘贴到项目 Instructions |
| 通用（默认） | `skills/<name>/` | `SKILL.md` | 随包分发或放入宿主 skills 目录 |

生成命令：

```bash
node scripts/host-adapt.mjs --host all     # 全部宿主
node scripts/host-adapt.mjs --host claude  # 单个宿主
node scripts/host-adapt.mjs --list         # 宿主列表
```

## 三、frontmatter 规范（host-adapt 强制校验）

| 字段 | 规则 | 示例 |
|------|------|------|
| `name` | 3-64 位，小写字母/数字/连字符，字母开头 | `prompt-engineering-pro` |
| `description` | 1-1024 字符，触发依据（真实能力 + 触发词） | 见 SKILL.md |
| `version` | SemVer `x.y.z` | `1.1.0` |
| `metadata` | 可选：language / type | `language: zh-CN` |
| `compatibility` | 环境要求 | `Node ≥14.18 / 零外部依赖` |

校验函数：`host-adapt.mjs` 的 `checkFrontmatter()` / `parseFrontmatter()`；与 skill-pack-check 的合规检查同口径。

## 四、渐进披露三层（metadata → core → full）

与 agentskills.io 渐进披露三阶段对齐，核心包按三层组织以降低 context 占用：

| 层 | 内容 | 位置 |
|----|------|------|
| metadata | 能力摘要 + 版本 + 引擎清单（快速决策是否调用） | SKILL.md 头部 frontmatter + 概述 |
| core | 核心指令：路由 / 安全 / 诚实边界 | SKILL.md 主体（L0-L5 阶段引用） |
| full | references 全量文档 + scripts 引擎 | references/ + scripts/（按需读取） |

三层重组**不改变 SKILL.md 语义**，仅规范引用入口；验证套件覆盖三层完整性（health-report 依赖图 + validate 门禁）。

## 五、安全边界

- host-adapt 输出固定到本工作区 `host-out/<name>/`，拒绝写入任何宿主配置目录或包外路径（safePathOut 校验）。
- 生成内容为静态骨架，不含可执行命令、不触发任何宿主侧行为。
- frontmatter 不合法时报错或降级提示，不静默生成错误格式。
