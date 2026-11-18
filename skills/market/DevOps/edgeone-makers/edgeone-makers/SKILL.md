---
slug: edgeone-makers
name: edgeone-makers
displayName: EdgeOne Makers
license: MIT
version: 2.0.1
description: >-
  EdgeOne Makers 是腾讯 EdgeOne 提供的一站式开发与部署平台，网站和 AI Agent 都能在这里完成开发、数据存储与上线，产物托管在全球边缘节点。使用本技能，可以把页面或 Agent 写完直接发布上线、拿到可访问地址；需要留言、上传、投票、状态保存等动态功能时，用 KV/Blob 存储即可，无需自建数据库；可以把 LangGraph、CrewAI、OpenAI/Claude SDK 等框架写的 Agent，以及 Node/Go/Python 云函数、V8 边缘函数部署到 Makers。适合活动页、作品集、工具站、AI Agent 等形态。当用户说“部署到 EdgeOne”“上线”“发布”时，也使用本技能。注意：本技能是路由表，只读取与当前任务相关的子技能，不要一次全部加载。
metadata:
  author: edgeone
  version: "2.0.1"
---

# EdgeOne Makers Skills

Executing any EdgeOne CLI command in this Skill requires CLI `>= 1.7.0`. Before execution, read `references/makers-cli/makers-cli.md` for version/capability checks and release availability; if the required public package is not available yet, stop rather than repeatedly upgrading or falling back to old commands. Writing code or reading these guides alone does not require CLI installation. Standalone usage keeps `agent` interaction; MCP and expert teams are optional, not prerequisites.

When you need EdgeOne Makers platform development guidance, read the matching Skill based on the task:

| Task | Read |
|------|------|
| Web framework support — which adapter, build output, 404, and unsupported features (Next.js, Nuxt, Astro, SvelteKit, React Router, TanStack Start, Vike, Vite, Hugo) | references/makers-frameworks/makers-frameworks.md |
| AI Agent development (DeepAgents, LangGraph, Claude SDK, OpenAI Agents, CrewAI) | references/makers-agents/makers-agents.md |
| Migrate an existing agent project to EdgeOne Makers | references/makers-migration/makers-migration.md |
| Deploy project to EdgeOne | references/makers-deploy/makers-deploy.md |
| Edge Functions (V8 lightweight functions) | references/makers-edge-functions/makers-edge-functions.md |
| Cloud Functions (Node.js / Go / Python APIs) | references/makers-cloud-functions/makers-cloud-functions.md |
| KV + Blob Storage | references/makers-storage/makers-storage.md |
| Persist dynamic data for a site (messages, uploads, votes, save-state) — **no database; use Blob** | references/makers-storage/makers-storage.md |
| Middleware (auth, rewrites, routing) | references/makers-middleware/makers-middleware.md |
| CLI command reference | references/makers-cli/makers-cli.md |
| Project structure / scaffolding | references/makers-recipes/makers-recipes.md |
| Environment adaptation (WorkBuddy / sandbox / CI) | references/makers-env-adaption/makers-env-adaption.md |

⚠️ Only read the Skill relevant to the current task. Do not load all skills at once.

A full-stack framework that needs a platform adapter previews correctly and deploys
broken without one, and no gate catches it — so when a request names a framework, read
`makers-frameworks` before writing the config.
