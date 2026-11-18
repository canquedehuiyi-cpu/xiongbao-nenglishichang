# 红线规则库（10 条核心红线）

> 触发任意一条立即标 🔴 阻塞合并。每条都附踩坑案例和修复方案。

## R1：无 watermark 的事件时间任务

**症状**：事件时间窗口任务窗口永远不触发，结果表无数据

**触发模式**：
```sql
CREATE TABLE source (
  event_time TIMESTAMP(3),
  ...
) WITH ('connector' = 'kafka', ...);
-- 缺 WATERMARK FOR event_time AS ...
```

**修复**：
```sql
CREATE TABLE source (
  event_time TIMESTAMP(3),
  ...,
  WATERMARK FOR event_time AS event_time - INTERVAL '5' SECOND
) WITH (...);
```

---

## R2：State 无 TTL

**症状**：任务跑几天后 OOM 或 checkpoint 巨大

**触发模式**：
- regular join 不配 `table.exec.state.ttl`
- group by 累计指标永久保留
- MapState / ListState 不清理

**修复**：
```sql
SET 'table.exec.state.ttl' = '7d';
```
或在业务逻辑加时间过滤窗口。

---

## R3：大流 × 大流 Regular Join

**症状**：state 爆炸，checkpoint 失败

**触发模式**：
```sql
SELECT * FROM order_stream o
JOIN payment_stream p ON o.order_id = p.order_id;  -- 两边都是大流
```

**修复**：改 interval join 控制时间窗口
```sql
SELECT * FROM order_stream o
JOIN payment_stream p ON o.order_id = p.order_id
  AND p.event_time BETWEEN o.event_time AND o.event_time + INTERVAL '30' MINUTE;
```

---

## R4：DDL 缺主键 + 下游需要去重

**症状**：下游聚合结果重复

**触发模式**：
```sql
CREATE TABLE sink (
  user_id STRING,
  pv BIGINT
) WITH (...);  -- 没主键，upsert 失效
```

**修复**：
```sql
CREATE TABLE sink (
  user_id STRING,
  pv BIGINT,
  PRIMARY KEY (user_id) NOT ENFORCED
) WITH (...);
```

---

## R5：Lookup Join 无 cache

**症状**：维表 QPS 打爆

**触发模式**：
```sql
JOIN dim_user FOR SYSTEM_TIME AS OF proctime AS d ON s.user_id = d.user_id
-- WITH 中无 lookup.cache 配置
```

**修复**：
```sql
'lookup.cache' = 'PARTIAL',
'lookup.partial-cache.max-rows' = '100000',
'lookup.partial-cache.expire-after-write' = '10min',
'lookup.partial-cache.expire-after-access' = '10min'
```

---

## R6：全局 group by 无打散

**症状**：单点 hot key，反压严重

**触发模式**：
```sql
SELECT COUNT(DISTINCT user_id) FROM source;  -- 全局聚合
```

**修复**：two-stage agg
```sql
SELECT SUM(cnt) FROM (
  SELECT MOD(HASH(user_id), 100) AS bucket, COUNT(DISTINCT user_id) AS cnt
  FROM source GROUP BY MOD(HASH(user_id), 100)
);
```

---

## R7：Window 大小 < watermark 延迟

**症状**：窗口几乎永远不闭合

**触发模式**：
```sql
WATERMARK FOR event_time AS event_time - INTERVAL '5' MINUTE
-- 窗口大小是 1 分钟
TUMBLE(event_time, INTERVAL '1' MINUTE)
```

**修复**：watermark 延迟应远小于窗口大小（建议 < 20%）。

---

## R8：Connector 版本与平台不匹配

**症状**：上线报错或部分功能失效

**修复**：核对 `QODERWORK.md` 的 `connector_version_matrix`。常见踩坑：
- VVR 6.x vs 8.x 的 Kafka connector 配置不同
- CDC connector 版本要对应 MySQL 大版本

---

## R9：时间字段类型不一致

**症状**：watermark / window 计算错误

**触发模式**：源是 BIGINT 时间戳但 DDL 声明 TIMESTAMP，或反之。

**修复**：用 `TO_TIMESTAMP_LTZ(ts_ms, 3)` 显式转换。

---

## R10：多 INSERT INTO 用同一 source

**症状**：source 被读取多次，重复计算

**触发模式**：
```sql
INSERT INTO sink_a SELECT ... FROM source;
INSERT INTO sink_b SELECT ... FROM source;  -- source 被读两次
```

**修复**：
```sql
BEGIN STATEMENT SET;
  INSERT INTO sink_a SELECT ... FROM source;
  INSERT INTO sink_b SELECT ... FROM source;
END;
```

---

## 团队额外红线

读取 `QODERWORK.md` 的 `code_review_extra_rules` 字段，团队自定义红线优先于通用红线。
