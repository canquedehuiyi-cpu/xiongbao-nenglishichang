# 决策因子清单（核心方法论参考）

> 本文档是 `realtime-task-development` Skill 的灵魂。所有窗口选型、Watermark、Join、反压排查决策都从这里走，**禁止直接给阈值**。

---

## 一、窗口选型决策因子（5 项）

引导用户依次回答以下 5 个问题，**每答完一个就向用户复述确认**，最后给推荐窗口类型：

| # | 决策因子 | 引导问句 | 影响窗口选型 |
|---|---------|---------|-------------|
| F1 | **指标语义** | 这个指标是统计型（PV/UV/订单数）还是会话型（用户行为路径）？ | 统计型 → tumbling；会话型 → session |
| F2 | **是否需要重叠** | 业务是否需要"过去 N 分钟滑动统计"（如近 5min UV）？ | 需要 → sliding；否则 → tumbling |
| F3 | **业务可接受的延迟** | 结果出来需要多快？分钟级 / 秒级 / 准实时（亚秒）？ | 决定窗口大小下限 |
| F4 | **数据峰谷分布** | 高峰时段流量是平时几倍？是否有突刺？ | 影响窗口聚合状态大小 |
| F5 | **下游消费方式** | 下游是 BI 看板（容忍重复刷新）还是触发动作（不可重复）？ | 决定窗口触发器和清理策略 |

**推荐选型映射（仅供参考，最终由因子组合决定）**：
- 统计型 + 不重叠 → **Tumbling Window**
- 统计型 + 需要重叠 → **Sliding Window**
- 会话型（用户行为路径分析）→ **Session Window**
- 多流关联且需窗口约束 → **Interval Join**（不是窗口，但在此决策）

**反模式**：
- ❌ 没问业务直接给"5 分钟 tumbling"
- ❌ 把 tumbling 和 sliding 混用导致重复计算
- ❌ session window 不给 gap 上限 → 永远不闭合

---

## 二、Watermark 决策因子（4 项）

| # | 决策因子 | 引导问句 | 影响 Watermark 设置 |
|---|---------|---------|---------------------|
| W1 | **数据乱序的 P99 延迟** | 历史观察源数据从产生到入 Kafka 的乱序延迟 P99 是多少？（如不知道，先采样统计） | watermark = P99 + buffer |
| W2 | **业务严格度** | 漏数据是否会被业务方追责？还是业务能接受少量误差？ | 严格 → 加大 buffer + 侧路兜底；宽松 → 取 P95 即可 |
| W3 | **窗口大小相对值** | watermark 延迟相对窗口大小占比多大？（>20% 偏大，<5% 偏小） | 调整 buffer，避免延迟接近窗口大小 |
| W4 | **下游对迟到数据的处理能力** | 迟到数据走侧路输出后，下游能否做补偿（重写聚合结果）？ | 影响 allowed lateness 配置 |

**典型组合（仅供参考）**：
- 普通业务 + P99 已知 → watermark = P99 + 1~2s buffer
- 金融/计费 + 严格 → watermark = P99 × 1.5 + allowed lateness 30s + 侧路兜底
- 探索性场景 + 数据未知 → 先用 5s + 观察 metrics 调

**反模式**：
- ❌ "watermark 一般 5 秒" — 完全不看数据特征
- ❌ watermark 延迟设到窗口大小一半以上 → 窗口几乎永远不闭合
- ❌ 严格业务不配 allowed lateness → 迟到数据直接丢弃

---

## 三、Join 类型决策因子（4 项）

| # | 决策因子 | 引导问句 | 影响 Join 类型 |
|---|---------|---------|---------------|
| J1 | **左右流性质** | 两边都是流？还是一边是流一边是维表？ | 流-流 → interval/regular；流-维表 → lookup join |
| J2 | **时间相关性** | 关联是否有时间窗口约束（如订单和支付 30 分钟内）？ | 有 → interval join；无 → regular join（慎用） |
| J3 | **状态量级** | 两边流的累计量级（万/百万/亿）？ | 大 × 大必须 interval join 控状态 |
| J4 | **维表 QPS** | 流速 × 命中率 = 维表 QPS，存储能扛吗？ | 抗不住 → 必须配 cache/异步 join |

**推荐选型**：
- 流 × 流 + 时间约束 → **Interval Join**（首选）
- 流 × 流 + 全量关联 → **Regular Join**（仅小流，必须配 TTL）
- 流 × 维表 → **Lookup Join + Async + Cache**

**红线**：
- ❗ 大流 × 大流的 Regular Join 永远是错的
- ❗ Lookup Join 不开 cache → 维表存储被打爆

---

## 四、反压排查 6 步法

按以下顺序排查，**前一步定位不到原因再走下一步**：

### Step B1：Web UI 看上下游严重度
打开 Flink Web UI → Job Graph，看每个算子的 BackPressured 颜色：
- 找到**最上游**显示 OK 的算子的**下一个**算子 → 它就是瓶颈

### Step B2：判断瓶颈在 Source / Process / Sink
- 瓶颈在 sink → Step B3
- 瓶颈在中间算子 → Step B4
- 瓶颈在 source（极少见）→ Step B6

### Step B3：Sink 排查
- 外部存储是否限流？看 sink 的 numRecordsOutPerSecond 是否远低于 source
- 是否同步写 + 单连接？改异步 + 批量
- 外部存储 QPS 限制？降并行度或限速

### Step B4：中间算子排查（最常见瓶颈）
依次检查：
1. **数据倾斜**：看 subtask metrics，某个 subtask 的 numRecordsIn 远高于其他 → key 分布倾斜，加 salt 或 two-stage agg
2. **Hot Key**：group by 的 key 是否有 hot key（如全局 user_id=null）→ 过滤或单独处理
3. **State 过大**：checkpoint duration 持续上升 → 加 TTL、改 RocksDB、增加 slot
4. **CPU 瓶颈**：subtask CPU 100% → 加并行度

### Step B5：Checkpoint 排查
- checkpoint duration > 1 分钟 → 状态过大或反压传导
- checkpoint 失败 → 看 checkpoint timeline，定位具体算子

### Step B6：Source 排查（罕见）
- Kafka lag 已经追上但还反压 → 是下游传导上来的
- Source 并行度 < topic 分区数 → 加 source 并行度

### 排查时必看的指标
- `numRecordsInPerSecond` / `numRecordsOutPerSecond`
- `currentInputWatermark` / `currentOutputWatermark`
- `checkpointDuration` / `checkpointSize`
- `backPressuredTimeMsPerSecond`

---

## 五、乱序兜底策略

| 业务严格度 | 推荐组合 |
|-----------|---------|
| 普通（看板/分析）| watermark + allowed lateness 1×窗口 |
| 重要（运营决策）| watermark + allowed lateness 2×窗口 + 侧路输出告警 |
| 严格（计费/金融）| watermark + allowed lateness + 侧路输出 + 离线兜底重算 |

---

## 六、状态管理（State）决策

| 状态类型 | 适用 | 注意事项 |
|---------|------|---------|
| ValueState | 单值（如最新订单状态） | 必须 TTL |
| MapState | KV 集合（如用户行为字典） | 控制 size，避免单 key 状态过大 |
| ListState | 列表（如历史 N 条） | 严格控制长度，防膨胀 |

**TTL 决策**：
- 业务可重放 → TTL = 业务最长依赖时间 × 1.5
- 业务不可重放 → 评估状态量级，必要时改 RocksDB + state size 监控

---

## 严格规则

执行 Skill 时，**每次窗口/watermark/join/反压决策必须**：
1. 先读本文档对应章节
2. 引导用户回答决策因子问题（不能跳过）
3. 给推荐方案 + 理由
4. 警告反模式和红线
