# GitHub Knowledge Base Explorer

探索、研究和学习 GitHub 开源项目的 Claude Code 技能。

## 功能特性

- **项目探索**：克隆并分析 GitHub 仓库，理解实现细节和技术方案
- **知识库管理**：本地知识库索引，通过 CLAUDE.md 文件组织管理
- **高效查询**：先检查本地知识库，避免重复克隆
- **分类整理**：按类别（Web 框架、DevOps、机器学习等）组织项目

## 安装方式

```bash
npx skills add lecion/github-kb
```

## 配置

设置环境变量 `GITHUB_KB_ROOT` 自定义工作目录：

```bash
export GITHUB_KB_ROOT=~/my-knowledge-base/
```

## 工作目录

- 默认路径：`~/github-kb/`
- 知识库索引：`{GITHUB_KB_ROOT}/CLAUDE.md`

## 使用流程

1. **查询知识库**：先检查 CLAUDE.md 是否已存在该项目
2. **克隆新仓库**：不存在时克隆到 `{GITHUB_KB_ROOT}`
3. **探索分析**：使用 Explore agent 分析代码结构和实现
4. **更新索引**：探索完成后更新 CLAUDE.md

## CLAUDE.md 格式示例

```markdown
# Claude Code 知识库

本目录包含 X 个 GitHub 项目，涵盖...领域描述

---

## Category Name

### [project-name](/project-name)
Brief description of the project
```

## 环境变量

| 变量 | 描述 | 默认值 |
|------|------|--------|
| `GITHUB_KB_ROOT` | 仓库根目录 | `~/github-kb/` |

---

> 本技能受到小红书用户 [@小天](https://www.xiaohongshu.com/user/profile/5b208f0511be100f9c278b53) 的启发。
