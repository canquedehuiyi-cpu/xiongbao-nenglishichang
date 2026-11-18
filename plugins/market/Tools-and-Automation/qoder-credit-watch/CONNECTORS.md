# Connectors

本插件**不携带 MCP server、不声明外部服务、不内置凭据**。运行时依赖下列三项（+ 两项可选）。

## 1. Chromium 系浏览器（必需）

经 Chrome DevTools 协议连接带 `--remote-debugging-port` 的浏览器 Profile。
`scripts/probe.mjs` 顶部 `EDGE` 列表按 Windows 路径探测 Edge；缺失则输出"未找到 Edge"、多 Profile 轮询不可用。换 Chrome / macOS / Linux 改该列表即可。

- Profile 目录默认 `%LOCALAPPDATA%\QoderMultiAccount\p{1,2,3}`。
- 端口与数量由配置 `probePorts` 决定（缺省 `9222/9223/9224`，`pN ↔ 9221+N`）。
- **号 ↔ 端口不靠顺序猜**：每次采集把实际端口写进 `history.jsonl` 的 `debugPort`，看板取每号最后一次实测值。

## 2. 用户本人的 Qoder 登录会话（必需）

每个 Profile 由**用户本人**登录一次 `https://qoder.com.cn/account/usage`（阿里 SSO）。开窗口用看板「登录窗口 / 新增账号」（服务端直接 spawn msedge，一次一扇、只绑 loopback）。插件只读同源 GET，不碰密码/cookie/token，不发 POST、不代领。会话过期需回该 Profile 重登。

## 3. JS 运行时（必需，通常已有）

`bin/serve-dashboard.cmd` 依次尝试：Qoder CN 内置 Electron 运行时 → PATH 上的 `node.exe`。脚本需 Node 22+（自带 `fetch` 与全局 `WebSocket`）；都不满足则提示并以退出码 1 结束。

## 4. browser-use（可选兜底）

无多 Profile、只查当前登录号或临时探字段时，可在页面上下文跑同源 `fetch` 单会话查询。**一轮只查一个号、非主路径**，插件不依赖它也能完整工作，且不随包提供。

## 5. 本地预览服务器（可选，要真触发才需要）

`bin/serve-dashboard.cmd` 起一个只监听 `127.0.0.1` 的进程，伺服静态站并暴露写接口：`/api/refresh`（采集）、`/api/rebuild`（重算）、`/api/profiles`（开登录窗口）、`/api/settings`（改标签/显示名）、`/api/register/open|scan|commit`（新增账号三步）。它是插件里**唯一会拉起浏览器、也唯一会写文件**的入口，故边界收紧：

- 默认端口 49788（`--port` 可改）+ 启动时一次性令牌；写接口缺 `x-cw-token` 一律 401；校验 `Host` 必须 loopback。
- 只触发既有动作、只改 `accounts.json` 白名单字段，不接受任意命令或路径参数。
- `/api/profiles` 唯一参数 `port` 必须命中 `probePorts`，服务端换算 Profile 序号后才 spawn；窗口起来还要回查调试端口真在监听，否则如实返回失败。
- 新增账号：`--scan` 的 `userId` 只进服务端 `pendingIds`、不回传页面，页面登记只给"端口 + 标签"，凭端口回查——页面编不出号。
- `/api/settings` 只改 `label` / `accountName`（单行、限长、控制字符拒收、撞名整份拒写），写前留 `accounts.json.bak`；`userId` 永不回传。
- 令牌注入只在本地服务响应里，分发的静态包不含接口；前台运行、关进程即失效，不自启、不驻留。

不想要这个面就别启它——静态看板、命令行查询都不依赖它。

## 本地配置（用户自持，不在包内）

细节统一见 `文件读写说明.md`。要点：配置与采集结果一律在插件目录之外（`~/.qoder-cn/credit-watch/`）；包内只有 `config/accounts.example.json` 模板和一份演示看板数据（`meta.demo: true`），本机采集永不写回包内；导出的 JSON 不含 `userId`。

## 已知外部依赖端点

只读、用户主动触发时访问，均为 Qoder 自用**非公开契约**，可能随时变更（变更时表现为报错或缺字段，插件不会静默给错数字，详见 README）：

- `https://qoder.com.cn/api/v1/me`
- `https://qoder.com.cn/api/v2/me/usages/big_model_credits`
- `https://qoder.com.cn/api/v1/me/userplan`
- `https://qoder.com.cn/api/v1/me/usages/big_model_credits/histories`（可选，消耗明细）

## 外部规则来源：每日签到送 100 Credits

看板「今日签到」依赖两份外部事实，都**不是接口**：

- 条款页：<https://docs.qoder.cn/product-overview/daily-check-in-100-credits-reward-program-terms> —— 每天 0 点（UTC+8）刷新、不补签；每次领取成一个资源包，有效期 = 领取日 + 30 天（已用真实采集校对，零偏移）。判据取自此。
- 上面只读接口里的 `resource_package_quota.quota_detail[]` —— 已采字段，不新增请求。

硬边界：**不访问任何领取/签到接口**，只从读数反推；条款规定同一控制人每日仅可领 1 次、不得换号规避，故多号自动领取/自动切号**不列入计划**。实现只在 `scripts/reward-window.mjs` 做只读判定；若官方改额度或有效期，需同步更新其 `REWARD_TTL_DAYS`，否则签到列会退化成"一直未签"。
