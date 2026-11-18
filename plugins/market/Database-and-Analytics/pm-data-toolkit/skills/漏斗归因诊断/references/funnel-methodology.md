# 漏斗归因诊断 —— 方法论参考手册

> 本文件是「漏斗归因诊断」技能的底层方法论库。
> 包含 SQL 模板、拆解清单、计算公式和分析框架。
> 执行技能时按需引用，不需要每次全部加载。

---

## 1. CASE WHEN 多事件漏斗 SQL 模板库

### 1.1 标准漏斗模板（6 步）

适用于：曝光 → 点击 → 进入 → 核心动作 → 结果展示 → 结果消费

```sql
-- ================================================
-- 标准6步漏斗模板
-- 使用前替换：<表名>、<arg1值>、<event_id>、<日期范围>
-- ================================================
SELECT
  day,
  CASE
    WHEN arg1 = '<exposure_event>'  AND event_id = '2201' THEN '01_曝光'
    WHEN arg1 = '<click_event>'     AND event_id = '2101' THEN '02_入口点击'
    WHEN arg1 = '<enter_event>'     AND event_id = '2001' THEN '03_功能进入'
    WHEN arg1 = '<action_event>'    AND event_id = '2101' THEN '04_核心动作'
    WHEN arg1 = '<result_event>'    AND event_id = '2201' THEN '05_结果展示'
    WHEN arg1 = '<consume_event>'   AND event_id = '2101' THEN '06_结果消费'
    ELSE NULL
  END AS funnel_stage,
  COUNT(1)                   AS pv,
  COUNT(DISTINCT visitor_id) AS uv
FROM <表名>
WHERE day BETWEEN '<start_date>' AND '<end_date>'
  AND arg1 RLIKE '<exposure_event>|<click_event>|<enter_event>|<action_event>|<result_event>|<consume_event>'
GROUP BY day,
  CASE
    WHEN arg1 = '<exposure_event>'  AND event_id = '2201' THEN '01_曝光'
    WHEN arg1 = '<click_event>'     AND event_id = '2101' THEN '02_入口点击'
    WHEN arg1 = '<enter_event>'     AND event_id = '2001' THEN '03_功能进入'
    WHEN arg1 = '<action_event>'    AND event_id = '2101' THEN '04_核心动作'
    WHEN arg1 = '<result_event>'    AND event_id = '2201' THEN '05_结果展示'
    WHEN arg1 = '<consume_event>'   AND event_id = '2101' THEN '06_结果消费'
    ELSE NULL
  END
HAVING funnel_stage IS NOT NULL
ORDER BY day, funnel_stage;
```

### 1.2 简化漏斗模板（3 步：曝光 → 点击 → 转化）

适用于：快速排查入口转化问题

```sql
SELECT
  day,
  CASE
    WHEN arg1 RLIKE '<exposure_pattern>' AND event_id = '2201' THEN '01_曝光'
    WHEN arg1 RLIKE '<click_pattern>'    AND event_id = '2101' THEN '02_点击'
    WHEN arg1 RLIKE '<convert_pattern>'  AND event_id IN ('2001','2101') THEN '03_转化'
    ELSE NULL
  END AS funnel_stage,
  COUNT(1)                   AS pv,
  COUNT(DISTINCT visitor_id) AS uv
FROM <表名>
WHERE day BETWEEN '<start_date>' AND '<end_date>'
  AND arg1 RLIKE '<exposure_pattern>|<click_pattern>|<convert_pattern>'
GROUP BY day,
  CASE
    WHEN arg1 RLIKE '<exposure_pattern>' AND event_id = '2201' THEN '01_曝光'
    WHEN arg1 RLIKE '<click_pattern>'    AND event_id = '2101' THEN '02_点击'
    WHEN arg1 RLIKE '<convert_pattern>'  AND event_id IN ('2001','2101') THEN '03_转化'
    ELSE NULL
  END
HAVING funnel_stage IS NOT NULL
ORDER BY day, funnel_stage;
```

### 1.3 带 nu/ou 拆分的漏斗模板

适用于：在漏斗分析中同时区分新老用户

```sql
SELECT
  day,
  CASE WHEN is_new_user = 1 THEN 'nu' ELSE 'ou' END AS user_type,
  CASE
    WHEN arg1 = '<exposure_event>'  AND event_id = '2201' THEN '01_曝光'
    WHEN arg1 = '<click_event>'     AND event_id = '2101' THEN '02_入口点击'
    WHEN arg1 = '<enter_event>'     AND event_id = '2001' THEN '03_功能进入'
    WHEN arg1 = '<action_event>'    AND event_id = '2101' THEN '04_核心动作'
    ELSE NULL
  END AS funnel_stage,
  COUNT(1)                   AS pv,
  COUNT(DISTINCT visitor_id) AS uv
FROM <表名>
WHERE day BETWEEN '<start_date>' AND '<end_date>'
  AND arg1 RLIKE '<exposure_event>|<click_event>|<enter_event>|<action_event>'
GROUP BY day,
  CASE WHEN is_new_user = 1 THEN 'nu' ELSE 'ou' END,
  CASE
    WHEN arg1 = '<exposure_event>'  AND event_id = '2201' THEN '01_曝光'
    WHEN arg1 = '<click_event>'     AND event_id = '2101' THEN '02_入口点击'
    WHEN arg1 = '<enter_event>'     AND event_id = '2001' THEN '03_功能进入'
    WHEN arg1 = '<action_event>'    AND event_id = '2101' THEN '04_核心动作'
    ELSE NULL
  END
HAVING funnel_stage IS NOT NULL
ORDER BY day, user_type, funnel_stage;
```

### 1.4 多入口对比漏斗模板

适用于：同一功能有多个入口时，对比各入口的漏斗表现

```sql
SELECT
  day,
  CASE
    WHEN arg1 RLIKE '<entry_a_pattern>' THEN '入口A'
    WHEN arg1 RLIKE '<entry_b_pattern>' THEN '入口B'
    WHEN arg1 RLIKE '<entry_c_pattern>' THEN '入口C'
    ELSE '其他'
  END AS entry_point,
  CASE
    WHEN event_id = '2201' THEN '01_曝光'
    WHEN event_id = '2101' THEN '02_点击'
    WHEN event_id = '2001' THEN '03_进入'
    ELSE NULL
  END AS funnel_stage,
  COUNT(1)                   AS pv,
  COUNT(DISTINCT visitor_id) AS uv
FROM <表名>
WHERE day BETWEEN '<start_date>' AND '<end_date>'
  AND arg1 RLIKE '<entry_a_pattern>|<entry_b_pattern>|<entry_c_pattern>'
GROUP BY day,
  CASE
    WHEN arg1 RLIKE '<entry_a_pattern>' THEN '入口A'
    WHEN arg1 RLIKE '<entry_b_pattern>' THEN '入口B'
    WHEN arg1 RLIKE '<entry_c_pattern>' THEN '入口C'
    ELSE '其他'
  END,
  CASE
    WHEN event_id = '2201' THEN '01_曝光'
    WHEN event_id = '2101' THEN '02_点击'
    WHEN event_id = '2001' THEN '03_进入'
    ELSE NULL
  END
HAVING funnel_stage IS NOT NULL
ORDER BY day, entry_point, funnel_stage;
```

### 1.5 周环比漏斗对比模板

适用于：需要对比本周和上周的漏斗数据

```sql
SELECT
  CASE
    WHEN day BETWEEN '<this_week_start>' AND '<this_week_end>' THEN '本周'
    WHEN day BETWEEN '<last_week_start>' AND '<last_week_end>' THEN '上周'
  END AS period,
  CASE
    WHEN arg1 = '<step1_event>' AND event_id = '2201' THEN '01_曝光'
    WHEN arg1 = '<step2_event>' AND event_id = '2101' THEN '02_点击'
    WHEN arg1 = '<step3_event>' AND event_id = '2001' THEN '03_转化'
    ELSE NULL
  END AS funnel_stage,
  COUNT(1)                   AS pv,
  COUNT(DISTINCT visitor_id) AS uv
FROM <表名>
WHERE day BETWEEN '<last_week_start>' AND '<this_week_end>'
  AND arg1 RLIKE '<step1_event>|<step2_event>|<step3_event>'
GROUP BY
  CASE
    WHEN day BETWEEN '<this_week_start>' AND '<this_week_end>' THEN '本周'
    WHEN day BETWEEN '<last_week_start>' AND '<last_week_end>' THEN '上周'
  END,
  CASE
    WHEN arg1 = '<step1_event>' AND event_id = '2201' THEN '01_曝光'
    WHEN arg1 = '<step2_event>' AND event_id = '2101' THEN '02_点击'
    WHEN arg1 = '<step3_event>' AND event_id = '2001' THEN '03_转化'
    ELSE NULL
  END
HAVING funnel_stage IS NOT NULL
ORDER BY period, funnel_stage;
```

---

## 2. MECE 拆解清单

### 2.1 核心原则

MECE = **M**utually **E**xclusive, **C**ollectively **E**xhaustive（互斥穷举）

- **互斥**：每个数据点只属于一个段，不存在交叉
- **穷举**：所有段加起来等于总数，没有遗漏

### 2.2 每层拆分验证清单

执行每层拆分时，逐项检查：

| 检查项 | 通过标准 | 不通过时的处理 |
|--------|---------|---------------|
| 各段之和 = 总数 | 误差 ≤ 0.5% | 排查去重逻辑、分类条件覆盖 |
| 各段互斥 | 同一 visitor_id 不出现在多个段 | 调整分类条件，确保互斥 |
| 各段样本量足够 | 每段 UV ≥ 100（统计意义） | 合并小段为"其他" |
| NULL/未知占比 | ≤ 5% | 排查数据缺失原因 |

### 2.3 常用拆分维度速查

| 维度 | 拆分方式 | 适用场景 | 注意事项 |
|------|---------|---------|---------|
| 用户类型 | nu / ou | 几乎所有指标异动 | 必须验证 UV 之和 = 总 UV |
| 入口 | 首页/搜索/push/分享/其他 | 流量分布变化 | "其他"段不要忽略 |
| 平台 | iOS / Android / Web / 其他 | 技术相关问题 | 注意版本号差异 |
| 地区 | 国内/海外 或 按省份 | 区域性变化 | 注意时区差异 |
| 时间 | 工作日 / 周末 | 周期性波动 | 先排除周末效应 |
| 版本 | 当前版本 / 上一版本 / 更早 | 版本发布影响 | 注意灰度发布 |
| 设备 | 高端机 / 中端机 / 低端机 | 性能相关问题 | 按机型内存或价格分 |
| 渠道 | 自然 / 付费 / 社交 / push | 获客渠道变化 | 注意渠道归因逻辑 |

### 2.4 拆分决策树

```
指标异动
│
├─ 第一步：nu/ou 拆分（必做）
│  ├─ nu 主导 → 第二步A：按获客渠道拆分
│  │  ├─ 某渠道主导 → 第三步A：按入口页面拆分
│  │  └─ 全渠道均匀 → 检查投放策略、竞品动态
│  │
│  └─ ou 主导 → 第二步B：按使用场景拆分
│     ├─ 某场景主导 → 第三步B：按功能模块拆分
│     └─ 全场景均匀 → 检查版本发布、系统稳定性
│
└─ nu + ou 同步 → 第二步C：检查大盘
   ├─ 大盘 DAU 下降 → 宏观因素（季节性、行业趋势）
   └─ 大盘 DAU 稳定 → 功能入口曝光变化
```

---

## 3. 贡献度计算公式

### 3.1 基本公式

当指标 = 分子 / 分母 时：

```
总指标变化(Δpp) = 本期指标 - 对比期指标
                = (本期分子 / 本期分母) - (对比期分子 / 对比期分母)
```

将分子和分母按段拆分：

```
本期分子 = Σ(段i_本期分子)    本期分母 = Σ(段i_本期分母)
对比期分子 = Σ(段i_对比期分子)  对比期分母 = Σ(段i_对比期分母)
```

### 3.2 段贡献度计算

**方法一：直接差值法（推荐，简单直观）**

```
段i贡献(pp) = 段i_本期分子/本期总分母 - 段i_对比期分子/对比期总分母
```

各段贡献之和 = 总指标变化（pp）。

**方法二：权重分解法（适用于比率指标的深度分析）**

```
指标 = Σ(段i_指标 × 段i_权重)

段i_指标 = 段i_分子 / 段i_分母（段内转化率）
段i_权重 = 段i_分母 / 总分母（段在总体中的占比）

段i贡献 = 段i_本期指标 × 段i_本期权重 - 段i_对比期指标 × 段i_对比期权重
```

可以进一步分解为：
- **率效应**：段内转化率变化带来的贡献 = (段i_本期指标 - 段i_对比期指标) × 段i_对比期权重
- **结构效应**：段权重变化带来的贡献 = 段i_对比期指标 × (段i_本期权重 - 段i_对比期权重)
- **交叉项**：率效应和结构效应的交互 = (段i_本期指标 - 段i_对比期指标) × (段i_本期权重 - 段i_对比期权重)

### 3.3 贡献度排序与 80% 区间

```
步骤：
1. 计算每段的贡献度（pp）
2. 取绝对值，按从大到小排序
3. 计算每段的贡献占比 = |段贡献| / Σ|各段贡献| × 100%
4. 从大到小累加贡献占比
5. 累加到 ≥ 80% 时停止，被纳入的段构成"最大贡献区间"
```

### 3.4 数值示例

| 段 | 对比期分子 | 对比期分母 | 对比期指标 | 本期分子 | 本期分母 | 本期指标 | 贡献(pp) | 贡献占比 |
|----|----------|----------|----------|---------|---------|---------|----------|---------|
| A  | 320      | 10000    | 3.20%    | 210     | 10000   | 2.10%   | -1.10pp  | 73.3%   |
| B  | 150      | 10000    | 1.50%    | 140     | 10000   | 1.40%   | -0.10pp  | 6.7%    |
| C  | 580      | 10000    | 5.80%    | 540     | 10000   | 5.40%   | -0.40pp  | 26.7%   |
| D  | 180      | 10000    | 1.80%    | 190     | 10000   | 1.90%   | +0.10pp  | -6.7%   |
| 合计 | 1230   | 10000    | 12.30%   | 1080    | 10000   | 10.80%  | -1.50pp  | 100%    |

排序：A(73.3%) > C(26.7%) > B(6.7%) > D(-6.7%)
80% 区间：A + C = 100% → 最大贡献区间为 [A, C]，但 A 单独已超 50%，聚焦 A。

---

## 4. nu/ou 分析框架详解

### 4.1 为什么要先做 nu/ou 拆分

nu（新用户）和 ou（老用户）的行为模式、流失原因、干预手段完全不同：

| 维度 | nu（新用户） | ou（老用户） |
|------|-------------|-------------|
| 行为特征 | 首次探索，不确定如何使用 | 有固定使用习惯，期望稳定 |
| 流失原因 | 引导不清晰、首次体验差、期望不符 | 功能退化、竞品分流、需求消失 |
| 干预策略 | 优化 onboarding、降低门槛、强化引导 | 修复问题、增强功能、召回运营 |
| 敏感度 | 对第一印象极敏感 | 对变化较敏感（尤其是负向变化） |
| 数据特征 | UV 波动大（受获客影响） | UV 相对稳定（受留存影响） |

### 4.2 nu/ou 判定逻辑

常见的 nu 判定方式（根据业务实际选择）：

```sql
-- 方式1：基于 is_new_user 字段（如果有）
CASE WHEN is_new_user = 1 THEN 'nu' ELSE 'ou' END

-- 方式2：基于首次访问日期
CASE WHEN first_visit_date = day THEN 'nu' ELSE 'ou' END

-- 方式3：基于历史窗口（过去N天无访问记录）
CASE WHEN visitor_id NOT IN (
  SELECT DISTINCT visitor_id FROM <表名>
  WHERE day BETWEEN DATE_SUB('<分析日>', N) AND DATE_SUB('<分析日>', 1)
) THEN 'nu' ELSE 'ou' END

-- 方式4：基于用户注册时间
CASE WHEN register_date >= DATE_SUB('<分析日>', 7) THEN 'nu' ELSE 'ou' END
```

### 4.3 nu/ou 拆分后的验证

```sql
-- 验证查询：nu UV + ou UV 是否等于总 UV
SELECT
  '总UV' AS category, COUNT(DISTINCT visitor_id) AS uv
FROM <表名> WHERE day = '<日期>'

UNION ALL

SELECT
  CASE WHEN is_new_user = 1 THEN 'nu' ELSE 'ou' END AS category,
  COUNT(DISTINCT visitor_id) AS uv
FROM <表名> WHERE day = '<日期>'
GROUP BY CASE WHEN is_new_user = 1 THEN 'nu' ELSE 'ou' END;
```

**验证标准：**
- `nu UV + ou UV = 总 UV`：完美（说明 visitor_id 在 nu/ou 间无交叉）
- `nu UV + ou UV > 总 UV`（误差 ≤ 0.5%）：可接受（少量用户同一天内身份切换）
- `nu UV + ou UV > 总 UV`（误差 > 0.5%）：有问题，需要排查分类逻辑
- `nu UV + ou UV < 总 UV`：分类条件有遗漏，部分 visitor_id 未被归入任何段

### 4.4 nu/ou 深入分析模板

当 nu 为主要贡献时：

```sql
-- nu 深入：按获客来源拆分
SELECT
  CASE
    WHEN utm_source = 'organic'  THEN '自然流量'
    WHEN utm_source = 'paid'     THEN '付费投放'
    WHEN utm_source = 'social'   THEN '社交分享'
    WHEN utm_source = 'push'     THEN 'Push唤醒'
    ELSE '其他'
  END AS acquisition_channel,
  COUNT(DISTINCT visitor_id) AS uv,
  -- 替换为目标指标的计算方式
  <指标计算>
FROM <表名>
WHERE day = '<日期>'
  AND is_new_user = 1
GROUP BY
  CASE
    WHEN utm_source = 'organic'  THEN '自然流量'
    WHEN utm_source = 'paid'     THEN '付费投放'
    WHEN utm_source = 'social'   THEN '社交分享'
    WHEN utm_source = 'push'     THEN 'Push唤醒'
    ELSE '其他'
  END;
```

当 ou 为主要贡献时：

```sql
-- ou 深入：按活跃度分层
SELECT
  CASE
    WHEN visit_count_7d >= 5 THEN '高活（≥5次/周）'
    WHEN visit_count_7d >= 2 THEN '中活（2-4次/周）'
    WHEN visit_count_7d >= 1 THEN '低活（1次/周）'
    ELSE '沉默（7天未访问后回流）'
  END AS activity_tier,
  COUNT(DISTINCT visitor_id) AS uv,
  <指标计算>
FROM <表名>
WHERE day = '<日期>'
  AND is_new_user = 0
GROUP BY
  CASE
    WHEN visit_count_7d >= 5 THEN '高活（≥5次/周）'
    WHEN visit_count_7d >= 2 THEN '中活（2-4次/周）'
    WHEN visit_count_7d >= 1 THEN '低活（1次/周）'
    ELSE '沉默（7天未访问后回流）'
  END;
```

---

## 5. 常见陷阱深度解析

### 5.1 PV 和 UV 为什么必须对称输出

**问题：** 只输出 PV 或只输出 UV 会导致分析盲区。

- **只看 PV**：被高频用户/刷量行为带偏。一个人刷了 100 次 PV 和 100 个人各看了 1 次
  是完全不同的情况。
- **只看 UV**：丢失频次信息。一个功能被 1000 人各点击 1 次 vs 被 100 人各点击 10 次，
  UV 不同但可能指向不同的产品问题。

**解决：** 每行数据同时输出 PV 和 UV，并计算人均 PV（= PV / UV）作为辅助指标。

### 5.2 RLIKE 优于 IN 的场景

**问题：** 在 ODPS（MaxCompute）环境下，`IN` 操作符可能遇到以下问题：
- 隐式类型转换：列是 STRING 但 IN 列表里有数字
- 特殊字符：arg1 中包含中文或特殊符号时，IN 可能匹配失败
- 编码问题：不同字符集下 IN 的行为可能不一致

**解决：** 用 `RLIKE 'value1|value2|value3'` 替代 `IN ('value1', 'value2', 'value3')`。
RLIKE 基于正则匹配，对类型和编码更宽容。

**注意：** 如果 arg1 的值本身包含正则特殊字符（如 `.`、`*`、`|`），需要转义。

### 5.3 CASE WHEN 顺序的重要性

**问题：** CASE WHEN 是短路求值——命中第一个条件后不再检查后续条件。

```sql
-- 错误写法：通用条件在前面，具体条件永远不会被执行
CASE
  WHEN event_id = '2101' THEN '点击'                    -- 通用条件先匹配
  WHEN event_id = '2101' AND arg1 = 'specific' THEN '特定点击'  -- 永远不会执行
END

-- 正确写法：具体条件在前面
CASE
  WHEN event_id = '2101' AND arg1 = 'specific' THEN '特定点击'  -- 先匹配具体
  WHEN event_id = '2101' THEN '通用点击'                       -- 再匹配通用
END
```

### 5.4 贡献度为负的解读

**问题：** 当总指标下降时，某个段的贡献为负（即该段逆势增长）。

**常见误读：**
- "这个段在增长，所以没问题" → **错误！**
- 正确理解：该段的增长在缓冲整体的下降，但可能掩盖了其他段更严重的问题。

**正确做法：**
1. 先排除该段是否数据异常（刷量、口径变化）
2. 如果数据正常，分析该段逆势增长的原因（是否有新功能上线、运营活动）
3. 评估该增长是否可持续
4. 不可持续的情况下，该段的缓冲效果会在未来消失，需要提前预防

---

## 6. 报告模板结构

### 6.1 HTML 报告骨架

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>漏斗归因诊断报告 —— [指标名]</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    /* stat cards, waterfall chart, funnel comparison, narrative */
    body { font-family: -apple-system, sans-serif; max-width: 960px; margin: 0 auto; padding: 24px; }
    .stat-cards { display: flex; gap: 16px; margin-bottom: 24px; }
    .stat-card { flex: 1; padding: 16px; border-radius: 8px; background: #f5f5f5; }
    .stat-card .value { font-size: 28px; font-weight: 700; }
    .stat-card .label { font-size: 13px; color: #666; }
    .stat-card .change { font-size: 14px; }
    .change.negative { color: #e53935; }
    .change.positive { color: #43a047; }
    /* ... additional styles ... */
  </style>
</head>
<body>
  <h1>漏斗归因诊断：[指标名]</h1>
  <p class="meta">数据日期：[start] ~ [end] | 口径：[口径来源]</p>

  <!-- 7.1 摘要卡片 -->
  <div class="stat-cards">
    <div class="stat-card">
      <div class="label">当前值</div>
      <div class="value">[当前值]</div>
    </div>
    <div class="stat-card">
      <div class="label">对比值</div>
      <div class="value">[对比值]</div>
    </div>
    <div class="stat-card">
      <div class="label">绝对变化</div>
      <div class="value change negative">[Δpp]</div>
    </div>
    <div class="stat-card">
      <div class="label">相对变化</div>
      <div class="value change negative">[Δ%]</div>
    </div>
  </div>

  <!-- 7.2 瀑布图 -->
  <h2>贡献度瀑布图</h2>
  <canvas id="waterfall"></canvas>

  <!-- 7.3 漏斗对比 -->
  <h2>漏斗对比（最大贡献区间）</h2>
  <canvas id="funnel"></canvas>

  <!-- 7.4 三段叙事 -->
  <h2>分析结论</h2>
  <div class="narrative">
    <p>[结论先行]</p>
    <p>[数据支撑]</p>
    <p>[行动建议]</p>
  </div>

  <!-- 7.5 Boss 摘要 -->
  <h2>汇报摘要</h2>
  <blockquote>[可直接复制的摘要文字]</blockquote>
</body>
</html>
```

### 6.2 Boss 汇报摘要模板

```
【[指标名]异动归因】

[指标名]从[对比值]降至[当前值]（[Δpp] / [Δ%]）。

归因：最大贡献来自[段名]（贡献占比[X%]），具体表现为[漏斗瓶颈描述]。

建议：[策略建议]，预计修复后可恢复[预期恢复值]。
```

---

## 7. 附录：公式速查

| 公式名 | 计算方式 |
|--------|---------|
| 绝对变化(pp) | 本期值 - 对比值 |
| 相对变化(%) | (本期值 - 对比值) / 对比值 × 100% |
| 漏斗转化率 | 下一步UV / 上一步UV × 100% |
| 段贡献(pp) | 段本期分子/总分母_本期 - 段对比期分子/总分母_对比期 |
| 段贡献占比 | |段贡献(pp)| / Σ|各段贡献(pp)| × 100% |
| 人均PV | PV / UV |
| 率效应 | (段本期指标 - 段对比期指标) × 段对比期权重 |
| 结构效应 | 段对比期指标 × (段本期权重 - 段对比期权重) |
| 交叉项 | (段本期指标 - 段对比期指标) × (段本期权重 - 段对比期权重) |
