# Issue tracker：GitHub

本仓库的 issue 和 spec 以 GitHub issues 形式存放。所有操作使用 `gh` CLI。

## 约定

- **创建 issue**：`gh issue create --title "..." --body "..."`。多行 body 使用 heredoc。
- **阅读 issue**：`gh issue view <number> --comments`，用 `jq` 过滤评论并获取 labels。
- **列出 issues**：`gh issue list --state open --json number,title,body,labels,comments --jq '[.[] | {number, title, body, labels: [.labels[].name], comments: [.comments[].body]}]'`，配合适当的 `--label` 和 `--state` 过滤器。
- **评论 issue**：`gh issue comment <number> --body "..."`
- **添加/移除 labels**：`gh issue edit <number> --add-label "..."` / `--remove-label "..."`
- **关闭**：`gh issue close <number> --comment "..."`

从 `git remote -v` 推断仓库；在 clone 内运行时 `gh` 会自动处理。

## Pull requests 作为 triage 表面

**PRs 作为请求表面：否。** _(如果本仓库将外部 PR 视为功能请求，设为 `yes`；`/triage` 读取此标志。)_

设为 `yes` 时，PRs 使用 `gh pr` 等价命令走与 issues 相同的 labels 和状态：

- **阅读 PR**：`gh pr view <number> --comments` 和 `gh pr diff <number>` 获取 diff。
- **列出待 triage 的外部 PRs**：`gh pr list --state open --json number,title,body,labels,author,authorAssociation,comments` 然后只保留 `authorAssociation` 为 `CONTRIBUTOR`、`FIRST_TIME_CONTRIBUTOR` 或 `NONE` 的（丢弃 `OWNER`/`MEMBER`/`COLLABORATOR`）。
- **评论/标记/关闭**：`gh pr comment`、`gh pr edit --add-label`/`--remove-label`、`gh pr close`。

GitHub 在 issues 和 PRs 之间共享一个数字空间，所以裸 `#42` 可能是任一：用 `gh pr view 42` 解析，失败则回退到 `gh issue view 42`。

## 当技能说「发布到 issue tracker」

创建一个 GitHub issue。

## 当技能说「获取相关 ticket」

运行 `gh issue view <number> --comments`。

## Wayfinding 操作

由 `/wayfinder` 使用。**地图** 是一个带有 **子** issues 作为 tickets 的单一 issue。

- **地图**：一个标记为 `wayfinder:map` 的单一 issue，持有 Notes / Decisions-so-far / Fog body。`gh issue create --label wayfinder:map`。
- **子 ticket**：一个链接到地图作为 GitHub sub-issue 的 issue（`gh api` 调用 sub-issues 端点）。sub-issues 未启用时，将子 ticket 添加到地图 body 的任务列表中，并在子 ticket body 顶部放 `Part of #<map>`。Labels：`wayfinder:<type>`（`research`/`prototype`/`grilling`/`task`）。认领后，ticket 分配给驱动的开发者。
- **阻塞**：GitHub 的**原生 issue 依赖**，规范的、UI 可见的表示。用 `gh api --method POST repos/<owner>/<repo>/issues/<child>/dependencies/blocked_by -F issue_id=<blocker-db-id>` 添加边，其中 `<blocker-db-id>` 是阻塞者的数字 **database id**（`gh api repos/<owner>/<repo>/issues/<n> --jq .id`，_不是_ `#number` 或 `node_id`）。GitHub 报告 `issue_dependencies_summary.blocked_by`（仅开放阻塞者，实时门控）。依赖不可用时，回退到子 ticket body 顶部的 `Blocked by: #<n>, #<n>` 行。当每个阻塞者都关闭时，ticket 解除阻塞。
- **前沿查询**：列出地图的开放子 issues（`gh issue list --state open`，限定到地图的 sub-issues / 任务列表），丢弃任何有开放阻塞者（`issue_dependencies_summary.blocked_by > 0`，或 `Blocked by` 行中的开放 issue）或 assignee 的；地图顺序中第一个的获胜。
- **认领**：`gh issue edit <n> --add-assignee @me`，会话的第一次写入。
- **解决**：`gh issue comment <n> --body "<answer>"`，然后 `gh issue close <n>`，然后将上下文指针（gist + 链接）追加到地图的 Decisions-so-far。
