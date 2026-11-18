# 单场比赛（match_query）

## 1. 适用意图与反例

适用：用户点名某场比赛，要看数据、前瞻、或生成分析报告。"皇马这场怎么看"、"帮我分析明晚曼城"、"给我一份曼联那场的赛前报告"。

不适用：积分榜/射手榜/赛季统计（直接调 standings、topscorers 等，见 `references/api_endpoints.md`）；"今天有什么比赛"（走 today_content）。

## 2. 参数识别

需要两个参数：**日期**（默认北京时间今天）和**球队**（双方或至少一方）。

- 用户同时给了双方队名 + 日期 → 直接定位，不追问；
- 只给一方 → 用「同队同日最多一场」原则定位，不追问；
- 只给彩票编号（"周四001"）→ 走 today_content 的 digest 匹配 `lottery_id`；
- 完全无定位线索（"今晚那场德比"且当夜确有多场）→ 追问，一次问全。

## 3. 取数步骤（本地优先）

1. 定位比赛：`python scripts/fetch_match.py --date <YYYY-MM-DD>`（可加 `--team 名称` 预筛），从返回中取 `fixture_id`。脚本自动走本地缓存，命中不扣点。
2. 取全景数据：`python scripts/fetch_match.py --pack <fixture_id>`（50 点；TTL 1h 内重取命中本地）。这是主力数据源，覆盖近期战绩/赛季统计/高阶/H2H/伤停/教练，并已内置「市场波动」区块（市场参考值/官方公开参考值/赛前异动），**无需再单独调 quotes**。
3. 检查返回内容：
   - **正常**：返回里有 `pack` 对象。再看 `meta.source`——`pipeline` 字段完整；`realtime` 表示实时组装，回复时说明部分维度覆盖较少。
   - **完整包生成中**：返回里出现 `status: "generating"` 与 `next_action`。说明这场此前没有完整包，系统已在后台生成，且**本次未扣点数**。此时走第 4 步，不要报错、不要反复调用。
4. 生成中时如何回复用户（小白用户的关键体验点）：
   - 用大白话安抚并给预期，**不要说 task_id、接口、轮询、API 这类技术词**：
     「这场比赛的完整数据（预测首发、战术特点、量化指标）正在整理，大约 1 分钟就绪，刚才那次没有扣你的点数。」
   - 可先用返回的 `snapshot` 讲清基础维度（对阵、近期战绩、赛季统计、交锋、市场波动），并说明其余维度稍后补全；
   - 等待 `retry_after_seconds`（默认 30 秒）后，**重新执行** `--pack <fixture_id>` 取完整包；
   - 若本轮对话已结束，就明确告诉用户「过一分钟再问我这场比赛就行」，用户下次开口时重取；
   - 想先确认是否就绪可用 `python scripts/fetch_match.py --task <fixture_id>`（0 点）。
5. 按需补充（不要默认全调）：
   - 要阵容细节 → `GET /fixtures/{id}/lineups`（5 点）；
   - 已完赛要技术统计/事件 → `GET /fixtures/{id}/stats|events|players`（各 5 点）。
6. 落库清单：赛程与 pack 基础信息已由脚本自动落 `fixtures` 事实表；直接 HTTP 拿到的完赛数据（stats/events/players）手动落库：`python scripts/local_store.py set --endpoint "/fixtures/{id}/stats" --payload '...' --ttl forever`。

## 4. 输出规则

- 用户只要数据 → 直接给结构化数据（表格优先）；
- 用户要分析/预测报告 → 加载 `prompts/prematch_report.md`，把取到的数据作为输入，按其骨架生成；
- 用户要成稿 → 转 `content_creation.md`；
- 事实（赛程/伤停/战绩）与模型判断（倾向/评估）分层表述。

## 5. 合规红线

见 SKILL.md 第 6 节。市场参考值只用合规词；不输出投注建议。

## 6. 完成自检

- [ ] fixture_id 来自接口而非猜测？
- [ ] pack 数据命中本地时向用户说明数据时点？
- [ ] 缺失维度已注明？
