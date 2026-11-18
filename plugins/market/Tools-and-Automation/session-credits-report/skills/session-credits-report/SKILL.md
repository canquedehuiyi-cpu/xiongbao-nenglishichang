---
name: session-credits-report
description: 查询本场/历史会话的 credits 与 token 消耗、下钻哪个工具或文件最烧。当用户问「这场花了多少 credits / token」「哪个文件最烧」「会话消耗分析」时使用。会话结束的自动一行报账由 Stop 钩子完成，无需调用本技能。
---

# Qoder 会话 credits 消耗分析

自包含会话消耗分析。数据源为 Qoder CN 桌面端本地转录（`~/.qoder-cn/projects/<slug>/<sessionId>.jsonl`），不依赖任何其它插件。

## 自动报账（钩子，无需调用）

Stop 钩子在每轮 Agent 结束时读转录，用 `decision:"block"`（并 exit 2 + stderr 兜底）让 Agent 续一轮，把一行**只含真值**的报账原样打印进对话：`累计Credits:（整场求和）｜Credits:（本轮）｜耗时:（本轮）｜上下文峰值:（本轮）｜模型请求-响应次数:（本轮）`。纯文本一行——CN 渲染器过滤内联 HTML，字号/颜色不可从内容控制。不报依赖窗口的推导 token 数（本地 `contextWindow=null`、`input_tokens=0`，真实窗口不可得）。`stop_hook_active` 守卫保证只续一轮。CN 桌面端不渲染 `systemMessage`，故不用该通道。

## 下钻问答（调用引擎）

引擎路径相对本技能目录：`../../scripts/engine.mjs`（需 Node.js）。

```bash
node "<plugin_root>/scripts/engine.mjs" --latest            # 最近修改的会话
node "<plugin_root>/scripts/engine.mjs" --session <id>      # 指定会话
node "<plugin_root>/scripts/engine.mjs" --transcript <path> --json
```

`<plugin_root>` = 本技能目录上两级。默认人类可读输出；`--json` 供二次分析。

## 口径（转述时必须遵守）

- `credits` 为转录真值（measured），覆盖全部计费往返；无 usage 的转录（IDE 端）credits 显示「不可用」，**不得说成「没花钱」**。
- 计费输入 = Σ `context_usage_ratio` × 窗口，为推导值；窗口优先取转录 `runtime-config.contextWindow`，读不到回退 200000，输出带「≈/窗口按 200K 估」，占比类数字随之偏大但绝对量不受影响。
- `byTool.resultTokens` / `byFile.estTokens` 为字符粗估（CJK 一字一 token、其余 4 字符一 token），**只用于排序与占比参考**，不是计费真值。
- 不统计子代理（`isSidechain` 条目跳过）；官方 UI 的一场扣费若含子代理，本地值会偏低，如实说明。
- 耗时 = 最近一条用户消息→转录末条时间戳的墙钟跨度（本轮端到端，含工具执行与等待）；整场跨度为 `durationMs`（含闲置），均非纯工作时长；时间戳缺失时省略。
- 本轮 Credits / 峰值 / 次数 = 最近一条用户消息之后的计费事件切分；本轮无计费往返时报「本轮无计费往返」，不得当 0 credits 表述。
- 不生成任何报告文件；答案直接在对话里给。
- 报账续轮是额外消耗：实测 ≈0.2–1.1 credits/轮、随上下文增大（钩子脚本本身零消耗），**不得说成「零消耗」**；国内版支持 `systemMessage` 后将更新为零额外往返。