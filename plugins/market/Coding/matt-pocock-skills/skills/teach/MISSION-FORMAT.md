# MISSION.md Format

`MISSION.md` lives at the workspace root. It captures the _reason_ the user is learning this topic. Every teaching decision (what to teach next, which resources to surface, which exercises to design) should trace back to this document.

## Template

```md
# 使命：{主题}

## 为什么
{1-3 句。用户追求的具体现实目标。掌握这项技能后，他们的生活或工作会发生什么改变？避免「为了理解 X」这类抽象表述；追问底层的真实成果。}

## 成功标准
- {用户将能做到的一件具体、可观察的事}
- {另一件具体的事}
- {……}

## 约束
- {时间、预算、既有承诺、学习偏好，任何会限制做法的因素}

## 超出范围
- {用户此刻明确不想追逐的相邻主题，用以保护最近发展区}
```

## Rules

- **One mission per workspace.** If the user wants to learn two unrelated things, that is two workspaces.
- **Concrete over abstract.** "Run a half marathon by October" beats "get fitter." "Ship a Rust CLI to my team" beats "learn Rust."
- **Push back on vagueness.** If the user cannot articulate why, interview them before writing anything. A bad mission is worse than no mission.
- **Revise when reality shifts.** Missions change. When the user's goal moves, update this file: don't leave a stale mission steering future sessions.
- **Keep it short.** If `MISSION.md` runs past a screen, it has stopped being a compass and started being a plan.
