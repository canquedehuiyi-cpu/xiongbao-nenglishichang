# hostile-ci —— CI-1 的靶子夹具

主夹具 `synthetic-site` 里没有 `.github/workflows/`，所以 CI-1 只能走到「一个工作流都没有」那个分支；
本轮变异测试证实：**把 permissions 的值判定、块标量插值检测整块删掉，自检仍然 94/0 全绿**。
也就是说 CI-1 的这些结论从来没有被测过。这个目录就是来补这个洞的。

## leaky.yml —— 必须判红（P1）

| 植入的问题 | 为什么危险 |
| --- | --- |
| `on: issue_comment` | 不需要仓库写权限，任何人都能通过发评论触发它 |
| `permissions: write-all` | 一次被投毒的第三方 action 就能改写仓库 |
| `run: \|` 里插值 `github.event.comment.body` | 评论正文直接进 shell —— 外部提交者在 runner 上执行任意命令 |
| `run:` 里插值 `github.event.issue.title`（藏在长行中段） | 同上；只扫 `run:` 第一行的实现会漏掉它 |
| `uses: actions/checkout@v4` 等可变标签 | 上游一改，供应链就跟着变 |
| `npm ci` 未加 `--ignore-scripts`、无 `timeout-minutes` | PR 改 lockfile 即可跑安装脚本；挂住的作业长期占并发 |

## strict.yml —— 不得报红

已经按最佳实践加固：顶层与 job 级都是 `contents: read`、动作钉 40 位 SHA、有 `timeout-minutes`、
`npm ci --ignore-scripts`，不可信上下文经 `env:` 传值而不是插值进 `run:`。
把它单独放进 `fixtures/hardened-ci/` 作为「必须 pass」的对照——
**只断言抓得住、不断言不误报的检查，等于没有检查**（`INJ-1` 与 `SEC-3` 的 `MUST_NOT_FAIL` 是同一个道理）。
