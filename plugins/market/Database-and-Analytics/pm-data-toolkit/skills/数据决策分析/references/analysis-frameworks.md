# 分析框架详解

> 本文件是 `数据决策分析` skill 的参考资料，包含 RICE/ICE 框架的完整说明、常用 PM 数据分析模式和 SQL 模板。

---

## 1. RICE 评分框架

### 1.1 框架概述

RICE 是由 Intercom 提出的需求优先级量化模型，适用于产品迭代规划阶段对多个候选需求进行横向对比。

### 1.2 四维度定义

#### Reach（触达范围）
- **定义**：在给定时间周期内，该需求能影响的用户数量
- **数据来源**：ODPS 中的目标页面/功能 UV，或 DAU/MAU 的子集
- **量化方式**：
  - 直接查数据：目标页面的日均 UV × 预估渗透率
  - 类比估算：参考已有类似功能的 UV 数据
- **时间基准**：统一使用"每月触达用户数"，便于横向对比
- **示例**：
  - 智能摘要功能：日均 UV 2,300，月 Reach = 2,300 × 30 = 69,000
  - 批量导出功能：日均 UV 150，月 Reach = 150 × 30 = 4,500

#### Impact（影响程度）
- **定义**：对目标指标（通常是转化率或留存率）的预期提升幅度
- **量化方式**：
  - 0.25 = 极低影响（微调，几乎不影响核心指标）
  - 0.5 = 低影响（小幅优化）
  - 1 = 中等影响（可感知的改善）
  - 2 = 高影响（显著提升核心指标）
  - 3 = 极高影响（战略性功能，可能改变产品格局）
- **数据来源**：
  - 历史 A/B 实验结果（最可靠）
  - 类似功能上线前后的指标变化（次可靠）
  - 产品经理经验判断（最常用，需标注信心水平）

#### Confidence（信心水平）
- **定义**：对 Reach 和 Impact 估算准确性的确信程度
- **量化方式**：
  - 100% = 有硬数据支撑（A/B 实验、历史数据）
  - 80% = 有参考数据（类似功能数据、行业基准）
  - 50% = 有定性依据（用户访谈、竞品分析）
  - 30% = 纯猜测（没有数据，凭感觉）
- **重要原则**：Confidence 低不是否定需求的理由，而是标记需要进一步验证

#### Effort（开发成本）
- **定义**：实现该需求所需的工程资源
- **量化方式**：人天（person-days）或人周（person-weeks）
- **包含内容**：
  - 后端开发
  - 前端开发
  - 测试验证
  - 部署上线
  - 后续维护（可选，视团队约定）
- **数据来源**：技术评审会议的估算，或参考类似功能的历史开发周期

### 1.3 计算公式

```
RICE Score = (Reach × Impact × Confidence) / Effort

单位：得分/人天（每投入一个人天能获得多少加权收益）
```

### 1.4 打分示例

| 需求 | Reach（月） | Impact | Confidence | Effort（人天） | RICE 得分 |
|------|-----------|--------|------------|--------------|----------|
| AI 摘要增强 | 69,000 | 2 | 80% | 15 | 7,360 |
| 批量导出 | 4,500 | 1 | 100% | 5 | 900 |
| 智能标签 | 12,000 | 1.5 | 60% | 10 | 1,080 |
| 暗色模式 | 50,000 | 0.5 | 50% | 20 | 625 |

---

## 2. ICE 评分框架

### 2.1 框架概述

ICE 是 RICE 的简化版，适用于快速头脑风暴和初步筛选，不需要精确的用户数据。

### 2.2 三维度定义

#### Impact（影响力）：1-10 分
- 1-3：低影响，改善体验但不改变核心指标
- 4-6：中等影响，可测量的指标提升
- 7-10：高影响，可能带来突破性增长

#### Confidence（信心）：1-10 分
- 1-3：没有数据支撑，基于假设
- 4-6：有间接数据或定性证据
- 7-10：有直接数据支撑（实验、历史数据）

#### Ease（容易程度）：1-10 分
- 1-3：复杂，需要大量工程资源或跨团队协作
- 4-6：中等，一个迭代内可完成
- 7-10：简单，几天内可上线

### 2.3 计算公式

```
ICE Score = Impact × Confidence × Ease

取值范围：1 ~ 1000
```

### 2.4 ICE vs RICE 选用指南

| 场景 | 推荐框架 | 理由 |
|------|---------|-----|
| 季度规划，需求超过 10 个 | ICE（先筛） → RICE（精排） | 先用 ICE 快速过滤，再对 top 5 做 RICE |
| 已有完整数据 | RICE | 数据充分时 RICE 更精确 |
| 头脑风暴阶段 | ICE | 不需要精确数字，快速比较 |
| 向管理层汇报 | RICE | RICE 的 Effort 维度更有说服力 |

---

## 3. 常用 PM 数据分析模式

### 3.1 漏斗分析（Funnel Analysis）

```
典型漏斗：
首页访问 → 功能入口点击 → 功能使用 → 完成目标行为

关键指标：
- 每步转化率 = 当前步 UV / 上一步 UV × 100%
- 整体转化率 = 最后一步 UV / 第一步 UV × 100%
- 最大流失点 = 转化率最低的那一步
```

**SQL 模板**：
```sql
WITH funnel AS (
    SELECT
        COUNT(DISTINCT CASE WHEN event IN ('page_view') THEN user_id END) AS step1_uv,
        COUNT(DISTINCT CASE WHEN event IN ('entry_click') THEN user_id END) AS step2_uv,
        COUNT(DISTINCT CASE WHEN event IN ('feature_use') THEN user_id END) AS step3_uv,
        COUNT(DISTINCT CASE WHEN event IN ('goal_complete') THEN user_id END) AS step4_uv
    FROM ${event_table}
    WHERE dt BETWEEN '${start_date}' AND '${end_date}'
)
SELECT
    step1_uv,
    step2_uv,
    ROUND(step2_uv * 100.0 / NULLIF(step1_uv, 0), 2) AS step1_to_step2_rate,
    step3_uv,
    ROUND(step3_uv * 100.0 / NULLIF(step2_uv, 0), 2) AS step2_to_step3_rate,
    step4_uv,
    ROUND(step4_uv * 100.0 / NULLIF(step3_uv, 0), 2) AS step3_to_step4_rate,
    ROUND(step4_uv * 100.0 / NULLIF(step1_uv, 0), 2) AS overall_rate
FROM funnel;
```

### 3.2 用户分层分析（Segmentation）

```
常见分层维度：
- 用户类型：新用户（注册 ≤ 7 天） / 活跃用户 / 沉默用户 / 流失用户
- 活跃度：高活（周活 ≥ 5 天） / 中活（周活 2-4 天） / 低活（周活 1 天）
- 功能使用：重度用户（日使用 ≥ 10 次） / 中度 / 轻度
```

**SQL 模板**：
```sql
WITH user_segments AS (
    SELECT
        user_id,
        DATEDIFF(CURRENT_DATE, first_use_date, 'dd') AS days_since_first,
        COUNT(DISTINCT dt) AS active_days
    FROM ${active_table}
    WHERE dt BETWEEN '${start_date}' AND '${end_date}'
    GROUP BY user_id, first_use_date
)
SELECT
    CASE
        WHEN days_since_first <= 7 THEN '新用户'
        WHEN active_days >= 20 THEN '活跃老用户'
        WHEN active_days >= 5 THEN '普通老用户'
        ELSE '沉默用户'
    END AS user_segment,
    COUNT(DISTINCT user_id) AS uv,
    ROUND(AVG(feature_use_count), 2) AS avg_usage
FROM user_segments
GROUP BY
    CASE
        WHEN days_since_first <= 7 THEN '新用户'
        WHEN active_days >= 20 THEN '活跃老用户'
        WHEN active_days >= 5 THEN '普通老用户'
        ELSE '沉默用户'
    END
ORDER BY uv DESC;
```

### 3.3 趋势分析（Trend Analysis）

```
三种核心趋势对比：
1. 环比（Period-over-Period）：当前周期 vs 上一个同等长度周期
2. 同比（Year-over-Year）：当前周期 vs 去年同期
3. MA7（7-Day Moving Average）：消除日波动，看真实趋势
```

**MA7 SQL 模板**：
```sql
SELECT
    dt,
    uv,
    pv,
    AVG(uv) OVER (ORDER BY dt ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS uv_ma7,
    AVG(pv) OVER (ORDER BY dt ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS pv_ma7
FROM (
    SELECT
        dt,
        COUNT(DISTINCT user_id) AS uv,
        COUNT(1) AS pv
    FROM ${event_table}
    WHERE dt BETWEEN '${start_date}' AND '${end_date}'
    GROUP BY dt
) daily
ORDER BY dt;
```

**环比计算 SQL 模板**：
```sql
WITH current_period AS (
    SELECT COUNT(DISTINCT user_id) AS uv, COUNT(1) AS pv
    FROM ${event_table}
    WHERE dt BETWEEN '${current_start}' AND '${current_end}'
),
prev_period AS (
    SELECT COUNT(DISTINCT user_id) AS uv, COUNT(1) AS pv
    FROM ${event_table}
    WHERE dt BETWEEN '${prev_start}' AND '${prev_end}'
)
SELECT
    c.uv AS current_uv,
    p.uv AS prev_uv,
    ROUND((c.uv - p.uv) * 100.0 / NULLIF(p.uv, 0), 2) AS uv_wow_pct,
    c.pv AS current_pv,
    p.pv AS prev_pv,
    ROUND((c.pv - p.pv) * 100.0 / NULLIF(p.pv, 0), 2) AS pv_wow_pct
FROM current_period c, prev_period p;
```

### 3.4 留存分析（Retention Analysis）

```
留存类型：
- 次日留存（Day 1 Retention）：首次使用后第 2 天仍活跃
- 7 日留存（Day 7 Retention）：首次使用后第 7 天仍活跃
- 30 日留存（Day 30 Retention）：首次使用后第 30 天仍活跃
- 周留存（Weekly Retention）：第 N 周仍有活跃行为

活跃定义（需与团队对齐）：
- 打开 App
- 有核心功能使用行为
- 有任意行为（最宽松）
```

### 3.5 归因分析（Attribution Analysis）

```
指标异动时的归因拆解路径：
1. 时间维度：异动发生在哪个时间段？是否节假日/发版日？
2. 渠道维度：哪个流量来源变化最大？
3. 用户维度：新用户还是老用户？哪个地区？
4. 功能维度：哪个功能模块受影响？
5. 技术维度：是否有性能问题、报错率上升？
```

---

## 4. SQL 最佳实践

### 4.1 性能优化
- **必须加分区过滤**：`WHERE dt BETWEEN ... AND ...`
- **必须加 LIMIT**：探索查询 `LIMIT 100`，正式查询 `LIMIT 10000`
- **避免 SELECT ***：只选需要的字段
- **优先用 COUNT(DISTINCT)**：而非子查询去重

### 4.2 数据安全
- **不在 SQL 中硬编码用户 ID**：用参数化方式传入
- **敏感字段脱敏**：手机号、邮箱等 PII 字段不出现在结果中
- **查询结果不缓存到本地**：除非用户明确要求导出

### 4.3 结果验证
- **数量级检查**：UV 不应大于 DAU，转化率不应大于 100%
- **空值检查**：检查 NULL 值比例，超过 10% 需要在报告中标注
- **日期连续性**：检查日期是否有缺失，缺失需在报告中说明

---

## 5. Chart.js 图表选用指南

| 分析类型 | 推荐图表 | Chart.js type |
|---------|---------|--------------|
| 趋势变化 | 折线图 | `line` |
| 分类对比 | 横向柱状图 | `bar`（indexAxis: 'y'） |
| 占比分布 | 环形图 | `doughnut` |
| 漏斗转化 | 横向柱状图（递减） | `bar`（indexAxis: 'y'） |
| 留存曲线 | 折线图（多系列） | `line` |
| 散点分布 | 散点图 | `scatter` |

### 配色建议
```javascript
const COLORS = {
  primary: '#667eea',    // 主指标
  secondary: '#764ba2',  // 次指标
  success: '#22c55e',    // 正向变化
  danger: '#ef4444',     // 负向变化
  warning: '#f59e0b',    // 基准线/MA7
  muted: '#94a3b8'       // 辅助信息
};
```
