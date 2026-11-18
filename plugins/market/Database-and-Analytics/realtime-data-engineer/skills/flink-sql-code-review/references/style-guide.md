# Flink SQL 代码风格指南

## 命名规范

### 表 / topic
| 类型 | 规范 | 示例 |
|------|------|------|
| ODS | `ods_<业务域>_<实体>_<频度>` | `ods_trade_order_realtime` |
| DWD | `dwd_<业务域>_<实体>_<动作>` | `dwd_user_behavior_click` |
| DWS | `dws_<业务域>_<指标>_<粒度>_<时间>` | `dws_trade_gmv_user_1d` |
| ADS | `ads_<业务方>_<场景>_<指标>` | `ads_bi_dashboard_dau` |
| 维表 | `dim_<业务域>_<实体>` | `dim_user_basic` |

### 字段
- 蛇形命名：`order_id` 而非 `OrderId`
- 时间字段统一：`create_time`、`update_time`、`event_time`
- 布尔：`is_xxx`，1/0 而非 true/false（兼容性）
- 金额：`<name>_amount`，类型 `DECIMAL(18,2)`

### 任务
- `rt_<业务域>_<目的>_<版本>`，例：`rt_trade_dws_gmv_v1`

## SQL 格式

### 关键字大写
```sql
SELECT
  user_id,
  COUNT(*) AS pv
FROM ods_user_log
WHERE dt = '2026-06-23'
GROUP BY user_id;
```

### CTE 优于嵌套子查询
```sql
-- 推荐
WITH base AS (
  SELECT user_id, event_time FROM source
),
agg AS (
  SELECT user_id, COUNT(*) AS pv FROM base GROUP BY user_id
)
SELECT * FROM agg;
```

### 缩进与对齐
- 4 空格缩进
- ON 子句换行对齐
- 长 IN 列表每行一个

## 注释要求

| 位置 | 必填 | 内容 |
|------|------|------|
| 任务头 | ✓ | 任务名、负责人、需求方、上线日期、版本 |
| DDL 表头 | ✓ | 表用途、数据源、负责人 |
| 字段 | △ | 业务含义不直观的必加 |
| 复杂逻辑 | ✓ | "为什么这么写"而非"在做什么" |
| 边界处理 | ✓ | 异常 case / null 处理逻辑 |

## 分层规范

- **ODS 层**：原始数据，最小加工（脱敏/类型对齐）
- **DWD 层**：明细宽表，多源 join 后的事实
- **DWS 层**：轻度聚合，按时间/维度
- **ADS 层**：业务直接消费

跨层 join 限制：DWS 不应直接 join ODS（应通过 DWD）

## 禁用项

- ❌ `SELECT *`（除调试）
- ❌ 写死的常量（如固定日期），应该用变量
- ❌ 无意义别名（如 `t1`、`a`）
- ❌ 过深嵌套子查询（用 CTE 替代）
- ❌ 单行超过 120 字符
- ❌ 无注释的复杂 CASE WHEN

## 团队规范覆盖

`QODERWORK.md` 配置 `flink_sql_naming_convention` 路径时，**优先**读团队规范，本文档作为 fallback。
