# Qoder 多账号 Credits 余量监控（qoder-credit-watch）

## 简介

在 Qoder 里用一句话查清**多个 Qoder 账号各自的剩余 Credits**，谁快用完了一眼看见。

- 每个号各占一个独立浏览器 Profile（各自登录态），查询从**那个号自己的会话**里以只读 GET 发出，凭据不离开浏览器；IDE 里正在用的登录态完全不被碰，**不需要切号**。
- 结果按真实 `userId` 归档：A 号的数据永远不会落到 B 号名下；分发的 JSON 不含 `userId`。
- 零依赖：只用 Node 22+ 自带能力，无构建步骤、无第三方包；启动器自己找 Qoder 内置 JS 运行时，**不要求装 Node**。

## 如何使用

```
/credit-start      # 唯一入口：一键起本地服务看板
```

服务起在 `http://127.0.0.1:49788`（默认端口，`--port` 可改，或在看板「设置」页改后重启生效），终端会打印访问地址与一次性令牌。

起来后日常操作全在**看板网页**上点按钮：「刷新余量数据」采集、按号开「登录窗口」、设置页加号/改标签、CSV 导出。看板展示总剩余、日均消耗、可支撑天数、余量构成、各号套餐/资源包到期等；「今日签到」为只读反推的状态列，不代领。

## 数据与安全

- 真实数据写在插件目录之外：`~/.qoder-cn/credit-watch/`（`history.jsonl` 采集历史、`accounts.json` 配置、`credits.json` 看板数据）。包内 `dashboard/site/data/credits.json` 只是合成演示数据，永不覆盖。
- 本地服务只监听 `127.0.0.1`，带一次性令牌 + 校验 `Host`；写接口无令牌一律 401；关进程即全部失效，不驻留、不开机自启。
- 只发 GET：不代领、不下单、不改任何远端状态；不接触密码、cookie、token，不向第三方发送数据。
- 调试端口临时开放、查询结束即收回；**不支持**导出 cookie 代跑其他账号（触发风控且设计上不留接口）。
- 合规：多付费号只读监控不违反条款（试用限一号仅指试用版）；每日签到**同一控制人仅可领 1 次**，本插件只做提醒、不代领、不自动切号。

## 组成

- `scripts/probe.mjs` — 查询引擎（多 Profile CDP 轮询、归档、写历史）
- `scripts/build-site-data.mjs` — 采集记录 → 看板数据转换器
- `scripts/reward-window.mjs` — 每日签到状态的只读反推
- `scripts/serve-dashboard.mjs` — 本地服务器 + 刷新/设置/登记接口
- `bin/serve-dashboard.cmd` — 唯一启动器
- `dashboard/site/` — 看板静态站
- `skills/credit-start/` — 唯一 skill 入口
- `config/accounts.example.json` — 配置模板

## 该看哪一份

- 数据存在哪、读写哪些文件、怎么备份卸载 → `文件读写说明.md`
- 这个版本改了什么 → `CHANGELOG.md`
- 依赖哪些外部端点、配置字段什么含义 → `CONNECTORS.md`
