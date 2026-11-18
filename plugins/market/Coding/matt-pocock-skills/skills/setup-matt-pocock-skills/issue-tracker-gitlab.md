# Issue tracker：GitLab

本仓库的 issue 和 spec 以 GitLab issues 形式存放。所有操作使用 [`glab`](https://gitlab.com/gitlab-org/cli) CLI。

## 约定

- **创建 issue**：`glab issue create --title "..." --description "..."`。多行 description 使用 heredoc。传 `--description -` 打开编辑器。
- **阅读 issue**：`glab issue view <number> --comments`。使用 `-F json` 获取机器可读输出。
- **列出 issues**：`glab issue list -F json` 配合适当的 `--label` 过滤器。
- **评论 issue**：`glab issue note <number> --message "..."`。GitLab 称评论为 "notes"。
- **添加/移除 labels**：`glab issue update <number> --label "..."` / `--unlabel "..."`。多个 labels 可以逗号分隔或重复 flag。
- **关闭**：`glab issue close <number>`。`glab issue close` 不接受关闭评论，所以先用 `glab issue note <number> --message "..."` 发布说明，然后关闭。
- **Merge requests**：GitLab 称 PRs 为 "merge requests"。使用 `glab mr create`、`glab mr view`、`glab mr note` 等，与 `gh pr ...` 形状相同，用 `mr` 替换 `pr`，用 `note`/`--message` 替换 `comment`/`--body`。

从 `git remote -v` 推断仓库；在 clone 内运行时 `glab` 会自动处理。

## Merge requests 作为 triage 表面

**MRs 作为请求表面：否。** _(如果本仓库将外部 merge requests 视为功能请求，设为 `yes`；`/triage` 读取此标志。)_

设为 `yes` 时，MRs 使用 `glab mr` 等价命令走与 issues 相同的 labels 和状态：

- **阅读 MR**：`glab mr view <number> --comments` 和 `glab mr diff <number>` 获取 diff。
- **列出待 triage 的外部 MRs**：`glab mr list -F json`，然后只保留作者不是项目成员/所有者的 MRs（贡献者的 MR，不是维护者进行中的工作）。
- **评论/标记/关闭**：`glab mr note`、`glab mr update --label`/`--unlabel`、`glab mr close`。

与 GitHub 不同，GitLab 分别编号 issues 和 MRs，所以一旦你知道维护者指的是哪个表面，`#42` 就是明确的。

## 当技能说「发布到 issue tracker」

创建一个 GitLab issue。

## 当技能说「获取相关 ticket」

运行 `glab issue view <number> --comments`。

## Wayfinding 操作

由 `/wayfinder` 使用。**地图** 是一个带有 **子** issues 作为 tickets 的单一 issue。

- **地图**：一个标记为 `wayfinder:map` 的单一 issue，持有 Notes / Decisions-so-far / Fog body。`glab issue create --label wayfinder:map`。（在有原生 epics 的 GitLab 层级，epic 可以持有地图；标记的 issue 在所有地方都可用。）
- **子 ticket**：一个在 description 顶部携带 `Part of #<map>` 并带有 labels `wayfinder:<type>`（`research`/`prototype`/`grilling`/`task`）的 issue。认领后，ticket 分配给驱动的开发者。
- **阻塞**：GitLab 的**原生阻塞链接**，规范的、UI 可见的表示。用 `/blocked_by #<n>` quick action 添加，作为 note 发布（`glab issue note <child> --message "/blocked_by #<blocker>"`）。原生阻塞链接是 Premium/Ultimate 功能；在免费层级（或不可用时）回退到 description 顶部的 `Blocked by: #<n>, #<n>` 行。当每个阻塞者都关闭时，ticket 解除阻塞。
- **前沿查询**：`glab issue list -F json` 限定到地图的子 issues，丢弃任何有开放阻塞者的：原生 `blocked_by` 链接到开放 issue（`glab api projects/:id/issues/:iid/links`），或 `Blocked by` 行中的开放 issue，或 assignee；地图顺序中第一个的获胜。
- **认领**：`glab issue update <n> --assignee @me`，会话的第一次写入。
- **解决**：`glab issue note <n> --message "<answer>"`，然后 `glab issue close <n>`，然后将上下文指针（gist + 链接）追加到地图的 Decisions-so-far。
