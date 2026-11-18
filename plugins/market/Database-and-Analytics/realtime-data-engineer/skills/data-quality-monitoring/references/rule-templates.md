# 5 类 DQC 规则模板

## 1. 空值检查（Null Check）

**SQL 模板**：
```sql
SELECT COUNT(*) AS null_cnt
FROM ${target_table}
WHERE ${field} IS NULL
  AND dt = '${bizdate}';
```

**阈值决策**：
| 字段类型 | 推荐阈值 | 备注 |
|---------|---------|------|
| 业务主键 | = 0 | 任何空值都是 P0 |
| 关联外键 | < 0.1% 或历史 P95 | 容忍少量延迟 |
| 业务字段 | < 1% 或历史 P95 | 看业务严格度 |
| 描述字段 | < 5% | 可容忍 |

## 2. 重复检查（Duplicate Check）

**SQL 模板**：
```sql
SELECT ${unique_key}, COUNT(*) AS cnt
FROM ${target_table}
WHERE dt = '${bizdate}'
GROUP BY ${unique_key}
HAVING COUNT(*) > 1;
```

**阈值决策**：
- 强唯一（订单号、支付流水号）→ = 0
- Kafka at-least-once 源（含天然重复）→ < 历史 P95 重复率
- 复合键（user_id + date）→ = 0（业务设计层面就该唯一）

## 3. 波动检查（Volume Fluctuation）★关键

**两种方式**：

### 方式 A：环比波动（推荐用于稳定业务）
```sql
WITH today AS (SELECT COUNT(*) c FROM t WHERE dt = '${bizdate}'),
     yesterday AS (SELECT COUNT(*) c FROM t WHERE dt = '${bizdate-1}')
SELECT (today.c - yesterday.c) / yesterday.c AS dod_rate FROM today, yesterday;
```

### 方式 B：同比波动（推荐用于有周末/节假日效应业务）
```sql
-- 与上周同一天对比
WITH today AS (SELECT COUNT(*) c FROM t WHERE dt = '${bizdate}'),
     last_week AS (SELECT COUNT(*) c FROM t WHERE dt = '${bizdate-7}')
SELECT ABS(today.c - last_week.c) / last_week.c AS wow_rate FROM today, last_week;
```

**阈值决策因子（必须分场景）**：

| 业务场景 | 推荐方式 | 阈值参考 |
|---------|---------|---------|
| 稳定 to-B 业务 | 方式 A | 历史 P95 ± 10% |
| 有周末效应 to-C | 方式 B | 历史 P95 ± 20% |
| 大促/节假日 | 临时屏蔽或单独阈值 | 走变更流程 |
| 新业务（< 30 天） | 暂不配波动检查 | 数据基线不稳 |

**反模式**：
- ❌ 全场景写"10% 波动告警"
- ❌ 不区分工作日/周末
- ❌ 大促当天不调阈值

## 4. 枚举值检查（Enum Check）

**SQL 模板**：
```sql
SELECT ${enum_field}, COUNT(*) AS cnt
FROM ${target_table}
WHERE dt = '${bizdate}'
  AND ${enum_field} NOT IN ('valid_v1', 'valid_v2', 'valid_v3')
GROUP BY ${enum_field};
```

**阈值决策**：
- 严格枚举（如订单状态：1/2/3/4）→ 出现新值立即 P1
- 半开放枚举（如 city、source）→ 新值占比 > 1% 告警
- 完全开放（如 device_model）→ 不配枚举检查，配 cardinality 检查

**维护策略**：
- 枚举清单和业务系统同步——业务上新枚举值前必须先报备数据
- 枚举清单纳入版本管理（Git）

## 5. 主外键关联检查（Reference Integrity）

**SQL 模板**：
```sql
SELECT COUNT(*) AS miss_cnt
FROM ${fact_table} f
LEFT JOIN ${dim_table} d ON f.${fk} = d.${pk}
WHERE f.dt = '${bizdate}'
  AND d.${pk} IS NULL;
```

**阈值决策**：
| 关联类型 | 推荐阈值 | 备注 |
|---------|---------|------|
| 实时事实 × 离线维表 | < 1% | 容忍维表迟到 |
| 实时事实 × 实时维表 | < 0.1% | 都是实时应几乎全命中 |
| 历史回刷场景 | 暂时屏蔽 | 维表刷新顺序问题 |

## 反模式集锦

- ❌ 配了一堆规则但全是 P0 → 告警疲劳
- ❌ 阈值定了不写理由 → 半年后维护人不敢动
- ❌ 大促前不调阈值 → 当天告警风暴
- ❌ 枚举清单不维护 → 业务上新值后持续告警
- ❌ 只配数量层不配业务层 → 数据"看起来对"但业务逻辑错
