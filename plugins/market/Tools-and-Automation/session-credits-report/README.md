# Qoder 会话 credits 消耗分析（session-credits-report）

会话结束自动在对话里报一行本场 credits 消耗。自包含：计算引擎只读 Qoder CN 本地转录，零外部插件依赖；卸载其它 credits 类插件不影响本插件。

## 组件

| 组件 | 作用 |
|---|---|
| `scripts/engine.mjs` | 计算引擎：credits 求和、Σ ratio×窗口、峰值、放大倍数、轮数/工具计数、耗时跨度、按工具/文件粗估拆分 |
| `scripts/hook.mjs` + `hooks/hooks.json` | Stop 钩子：会话结束读转录，`decision:"block"` + exit 2 让 Agent 续一轮打印一行纯文本真值报账：累计Credits:（整场）｜Credits:（本轮）｜耗时:｜上下文峰值:｜模型请求-响应次数:（本轮口径；CN 渲染器过滤 HTML，字号颜色不可控）；`stop_hook_active` 防死循环；异常静默放行 |
| `skills/session-credits-report/` | 下钻问答技能：哪个工具/文件最烧、历史会话查询 |

## 依赖

- Node.js（PATH 上有 `node`）。引擎仅用 node 内置模块，无 npm 依赖。
- Qoder CN 桌面端转录：`~/.qoder-cn/projects/<slug>/<sessionId>.jsonl`。

## 安装

打包 ZIP（根目录直接含 `.qoder-plugin/plugin.json`），经 Qoder 扩展安装器本地安装；或手动放入插件缓存并注册启用。安装后重载插件/重启 Qoder，钩子即生效。

## 额外消耗说明

- 钩子脚本本身零消耗：本地 node 读转录求和，不调用模型。
- 额外消耗来自报账续轮：CN 桌面端不渲染 Stop 钩子的 `systemMessage`，只能 `decision:"block"` 让模型续一轮打印报账行；该轮把整段上下文重发为输入，故上下文越大越贵。
- 实测（2026-11-11，本地转录 `usage.credits` 真值）：上下文 10–24% 时 ≈0.2–0.3 credits/轮；60–82% 时 ≈0.9–1.1 credits/轮。某长会话报账续轮累计 ≈13.4 credits，约占该场总消耗 3%。
- 后续更新：国内版补齐 `systemMessage` 渲染（国际版已支持）后，切换零额外往返直推并发布新版本；时机取决于平台更新。

## 口径与限制

- credits 为转录真值；计费输入为 ratio×窗口推导，窗口读不到时回退 200K（报数带「≈」）。
- 耗时 = 最近一条用户消息→转录末条时间戳的墙钟跨度（本轮端到端，含工具执行与等待）；引擎同时给整场跨度（含闲置），均非纯工作时长。
- Credits/峰值/次数为本轮口径（最近一条用户消息后的计费事件）；累计为整场 credits 求和；均为转录真值，非官方账单（官方另含任务审查模型等转录外计费调用，会更大）。
- 工具/文件拆分为字符粗估，只供排序参考。
- 不统计子代理；IDE 端转录无 usage 时 credits 报「不可用」而非 0。
- 隐私：全部计算在本机完成，不上传任何数据，不写任何报告文件。

## 验证

```bash
node scripts/engine.mjs --session <某会话id>   # 与官方 UI 扣费对账
echo {"session_id":"<id>"} | node scripts/hook.mjs   # 应输出 {"decision":"block","reason":"…报账行…"} 且 exit 2
```