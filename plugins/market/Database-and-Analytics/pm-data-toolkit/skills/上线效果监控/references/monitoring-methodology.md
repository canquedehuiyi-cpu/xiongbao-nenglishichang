# 上线效果监控方法论参考

> 本文档为「上线效果监控」skill 的补充参考资料，包含 SPC 统计过程控制的完整公式、趋势检测规则、异动分级标准、告警文案模板库和星期对齐算法。

---

## 一、SPC 统计过程控制（Statistical Process Control）

### 1.1 核心概念

SPC 源自制造业质量管理，核心思想：一个稳定过程的输出服从正态分布，当输出超出控制限时，过程可能已经发生了变化。

在上线监控中：
- **稳定过程** = 上线前的指标日常波动
- **过程变化** = 上线后指标偏离了原有波动范围

### 1.2 基线期参数计算

设基线期数据为 $x_1, x_2, \ldots, x_n$（通常取上线前 14 天，排除最后 2 天灰度期，实际使用 12 个数据点）。

**均值（μ）**：

$$\mu = \frac{1}{n} \sum_{i=1}^{n} x_i$$

**标准差（σ）**：

$$\sigma = \sqrt{\frac{1}{n-1} \sum_{i=1}^{n} (x_i - \mu)^2}$$

> 注意：使用样本标准差（除以 n-1），不是总体标准差（除以 n），因为基线期是对"稳定状态"的抽样估计。

**控制限**：

| 控制限 | 公式 | 含义 |
|--------|------|------|
| UCL（Upper Control Limit） | μ + 2σ | 上限，约覆盖 95.4% 的正常波动 |
| LCL（Lower Control Limit） | μ - 2σ | 下限，约覆盖 95.4% 的正常波动 |
| UWL（Upper Warning Limit） | μ + 1.5σ | 预警上限，约覆盖 86.6% |
| LWL（Lower Warning Limit） | μ - 1.5σ | 预警下限，约覆盖 86.6% |

### 1.3 控制限选择依据

- **2σ（默认）**：平衡灵敏度和误报率，适合大多数产品指标
- **1.5σ（敏感模式）**：适合核心收入指标、资损相关指标，宁可误报不可漏报
- **3σ（宽松模式）**：适合天然波动大的指标（如 UGC 内容发布量），减少误报噪音

如果用户未指定，默认使用 2σ。可以在报告中同时标注 1.5σ 预警线和 2σ 告警线。

### 1.4 SPC 判异规则（Western Electric Rules 简化版）

以下任一条件满足即判定为"过程失控"：

| 规则编号 | 规则描述 | 严重度 | 业务含义 |
|----------|----------|--------|----------|
| R1 | 单日超出 2σ | 中 | 单日异常波动，可能是数据问题或突发事件 |
| R2 | 单日超出 3σ | 高 | 极端异常，必须立即排查 |
| R3 | 连续 2 天超出 1.5σ（同侧） | 中 | 持续性偏移，非随机波动 |
| R4 | 连续 3 天单调递增或递减 | 中 | 趋势信号，指标在持续变化 |
| R5 | 连续 5 天在均值同侧 | 低 | 均值偏移信号，可能是基线已漂移 |
| R6 | 连续 7 天在均值同侧 | 中 | 强偏移信号，过程均值可能已改变 |

### 1.5 SQL 实现示例

```sql
-- 计算基线期均值和标准差
WITH baseline AS (
    SELECT
        metric_value,
        ds
    FROM metric_daily_table
    WHERE ds BETWEEN '{上线前16天}' AND '{上线前3天}'
        AND {过滤条件}
),
stats AS (
    SELECT
        AVG(metric_value) AS mu,
        STDDEV_SAMP(metric_value) AS sigma,
        AVG(metric_value) + 2 * STDDEV_SAMP(metric_value) AS ucl,
        AVG(metric_value) - 2 * STDDEV_SAMP(metric_value) AS lcl,
        AVG(metric_value) + 1.5 * STDDEV_SAMP(metric_value) AS uwl,
        AVG(metric_value) - 1.5 * STDDEV_SAMP(metric_value) AS lwl
    FROM baseline
)
-- 上线后每天的值与控制限对比
SELECT
    t.ds,
    t.metric_value,
    s.mu,
    s.sigma,
    s.ucl,
    s.lcl,
    s.uwl,
    s.lwl,
    CASE
        WHEN t.metric_value > s.ucl THEN '超出UCL'
        WHEN t.metric_value < s.lcl THEN '超出LCL'
        WHEN t.metric_value > s.uwl THEN '超出UWL'
        WHEN t.metric_value < s.lwl THEN '超出LWL'
        ELSE '正常'
    END AS status
FROM metric_daily_table t
CROSS JOIN stats s
WHERE t.ds BETWEEN '{上线日期}' AND '{上线后N天}'
ORDER BY t.ds;
```

---

## 二、趋势检测规则详解

### 2.1 连续单调变化检测

**定义**：如果指标值连续 N 天单调递增或递减（N ≥ 3），则发出趋势信号。

**检测方法**：

```
设 day[i] 为第 i 天的指标值
diff[i] = day[i] - day[i-1]  （日环比变化）

如果 diff[i], diff[i+1], diff[i+2] 全部 > 0 → 连续 3 天上升趋势
如果 diff[i], diff[i+1], diff[i+2] 全部 < 0 → 连续 3 天下降趋势
```

**SQL 实现**：

```sql
WITH daily_diff AS (
    SELECT
        ds,
        metric_value,
        metric_value - LAG(metric_value, 1) OVER (ORDER BY ds) AS diff
    FROM metric_daily_table
    WHERE ds BETWEEN '{start_date}' AND '{end_date}'
),
trend_flag AS (
    SELECT
        ds,
        metric_value,
        diff,
        CASE
            WHEN diff > 0 AND LAG(diff, 1) OVER (ORDER BY ds) > 0 AND LAG(diff, 2) OVER (ORDER BY ds) > 0
                THEN '连续3天上升'
            WHEN diff < 0 AND LAG(diff, 1) OVER (ORDER BY ds) < 0 AND LAG(diff, 2) OVER (ORDER BY ds) < 0
                THEN '连续3天下降'
            ELSE '无趋势'
        END AS trend
    FROM daily_diff
)
SELECT * FROM trend_flag WHERE trend != '无趋势';
```

### 2.2 MA7 斜率检测

**7 日移动平均（MA7）**：

$$MA7_t = \frac{1}{7} \sum_{i=t-6}^{t} x_i$$

> 要求：至少 7 个数据点。上线后前 6 天 MA7 = N/A，不要强行计算。

**MA7 斜率**：

$$slope_t = \frac{MA7_t - MA7_{t-2}}{MA7_{t-2}} \times 100\%$$

- |slope| > 5% → 显著趋势
- |slope| > 10% → 强趋势
- |slope| ≤ 5% → 平稳

### 2.3 趋势强度评估

| 趋势天数 | 累计变化 | 强度判定 |
|----------|----------|----------|
| 3 天 | < 5% | 弱趋势，持续观察 |
| 3 天 | 5%-15% | 中等趋势，值得关注 |
| 3 天 | > 15% | 强趋势，需要关注 |
| 5+ 天 | 任意 | 持续趋势，建议分析原因 |

---

## 三、异动严重度分级标准

### 3.1 分级矩阵

| 严重度 | 偏离程度 | 持续性 | 颜色标记 | 建议动作 |
|--------|----------|--------|----------|----------|
| **P0 - 严重** | 超出 3σ | 连续 2 天+ | 深红色 | 立即排查，可能需要回滚 |
| **P1 - 重要** | 超出 2σ | 单日 | 红色 | 当天内完成初步归因 |
| **P2 - 一般** | 超出 1.5σ | 连续 2 天 | 橙色 | 记录并持续观察 |
| **P3 - 提示** | 超出 1.5σ | 单日 | 黄色 | 记录，次日复查 |
| **P4 - 趋势** | 未超控制限，但连续 3 天趋势 | 连续 3 天+ | 蓝色 | 分析趋势原因 |

### 3.2 正负向区分

异动不等同于问题，需区分方向：

- **正向异动（↑）**：指标上升，通常是好结果（如转化率提升）
  - 示例："渗透率上线后第 4 天正向异动，环比 +12%，超出 UCL"
- **负向异动（↓）**：指标下降，通常需要关注（如留存下降）
  - 示例："次日留存上线后第 3 天负向异动，环比 -5pp，低于 LCL"

> 注意：某些指标下降是好的（如耗时、错误率），需要根据指标语义判断正负向。

### 3.3 综合健康度评分

为每个指标计算 0-100 分健康度：

| 状态 | 分数范围 | 标签 |
|------|----------|------|
| 稳定 | 80-100 | 健康 |
| 趋势 | 60-79 | 关注 |
| 预警 | 40-59 | 预警 |
| 异动 | 0-39 | 异常 |

**计算公式**：
- 基础分 = 100
- 超出 1.5σ → -10 分/天
- 超出 2σ → -25 分/天
- 超出 3σ → -50 分/天
- 连续趋势（3 天+） → -15 分
- 连续偏移（5 天+） → -10 分
- 最低 0 分

---

## 四、告警文案模板库

### 4.1 标准告警（完整模板）

```
【上线效果监控告警】
━━━━━━━━━━━━━━━━━━━━
需求名称：{需求名称}
上线日期：{上线日期}
监控天数：第 {N} 天（{具体日期}）

异动指标：{指标名}
当前值：{当前值}
基线均值：{μ}（σ = {σ}）
环比变化：{WoW 变化}%
同比变化：{YoY 变化}%
偏离程度：超出 {X}σ（{UCL/LCL}）
异动方向：{正向/负向}
严重度：{P0/P1/P2/P3/P4}

建议动作：{立即排查 / 初步归因 / 持续观察 / 次日复查}
后续建议：{建议运行 /漏斗归因诊断 进行根因分析}
━━━━━━━━━━━━━━━━━━━━
```

### 4.2 精炼告警（钉钉/飞书群发）

```
📊 {需求名}上线第{N}天监控
{指标名}：{当前值}（环比{WoW变化}%）
状态：{稳定 ✅ / 趋势 ⚠️ / 异动 🚨}
{如有异动：超出{X}σ，建议进一步归因}
```

### 4.3 一切正常模板

```
📊 {需求名}上线第{N}天监控报告
━━━━━━━━━━━━━━━━━━━━
监控指标：{指标数}个
整体状态：全部稳定 ✅

各指标概况：
{指标1}：{当前值}，环比 {WoW}%，MA7 {方向}
{指标2}：{当前值}，环比 {WoW}%，MA7 {方向}
{指标3}：{当前值}，环比 {WoW}%，MA7 {方向}

结论：上线 {N} 天，核心指标均在正常波动范围内，效果符合预期。
```

### 4.4 多指标汇总告警

```
📊 {需求名}上线第{N}天 — {M}项异动
━━━━━━━━━━━━━━━━━━━━
🚨 异动指标（{M}个）：
  1. {指标1}：{值}，环比 {%}，超出 {X}σ
  2. {指标2}：{值}，环比 {%}，超出 {X}σ

✅ 正常指标（{K}个）：
  1. {指标3}：{值}，环比 {%}
  2. {指标4}：{值}，环比 {%}

建议：优先排查 {异动最严重的指标}，建议运行漏斗归因诊断。
```

### 4.5 趋势预警模板

```
⚠️ {需求名}趋势预警
{指标名} 连续 {N} 天{上升/下降}
累计变化：{累计变化}%
当前值：{当前值}（基线 {μ}）
MA7 斜率：{斜率}%
建议：分析{上升/下降}原因，确认是否为上线效果还是外部因素。
```

---

## 五、星期对齐算法

### 5.1 问题说明

很多产品指标有明显的周内规律：
- 工作日 vs 周末差异大（如 B 端产品工作日活跃高）
- 周一通常有特殊模式（如周末积压后的反弹）
- 周五通常有下降趋势（如临近周末活跃度下降）

**不对齐的后果**：拿本周日的数据和上周一对比，可能因为周末效应产生假阳性异动。

### 5.2 环比星期对齐

```python
# 伪代码：环比对齐
def get_wow_baseline(current_date):
    """获取上周同一天（星期几对齐）"""
    return current_date - timedelta(days=7)

# 示例
# 今天是 2026-06-11（周四）
# 环比基线 = 2026-06-04（上周四）
```

### 5.3 同比星期对齐

```python
# 伪代码：同比对齐（星期几对齐）
def get_yoy_baseline(current_date):
    """获取去年同期，星期几对齐"""
    # 去年同一天
    last_year_same_day = current_date.replace(year=current_date.year - 1)

    # 计算星期几差异
    weekday_diff = current_date.weekday() - last_year_same_day.weekday()

    # 偏移到相同星期几
    yoy_date = last_year_same_day + timedelta(days=weekday_diff)

    return yoy_date

# 示例
# 今天是 2026-06-11（周四）
# 去年同一天 = 2025-06-11（周三）
# 星期差异 = 周四 - 周三 = 1 天
# 同比基线 = 2025-06-12（周四）
```

### 5.4 SQL 实现星期对齐

```sql
-- 环比：上周同一天
SELECT
    a.ds AS current_date,
    a.metric_value AS current_value,
    b.ds AS wow_date,
    b.metric_value AS wow_value,
    ROUND((a.metric_value - b.metric_value) / b.metric_value * 100, 2) AS wow_pct
FROM metric_daily a
LEFT JOIN metric_daily b
    ON b.ds = DATEADD(a.ds, -7, 'dd')  -- 上周同一天
WHERE a.ds BETWEEN '{上线日期}' AND '{上线后N天}'
ORDER BY a.ds;

-- 同比：去年同期星期几对齐
-- ODPS 中 DAYOFWEEK 返回 1(周日) ~ 7(周六)
SELECT
    a.ds AS current_date,
    a.metric_value AS current_value,
    b.ds AS yoy_date,
    DAYOFWEEK(a.ds) AS current_dow,
    DAYOFWEEK(b.ds) AS yoy_dow
FROM metric_daily a
LEFT JOIN metric_daily b
    ON b.ds = DATEADD(
        DATEADD(a.ds, -1, 'yyyy'),  -- 去年同一天
        (DAYOFWEEK(a.ds) - DAYOFWEEK(DATEADD(a.ds, -1, 'yyyy'))),  -- 星期偏移
        'dd'
    )
WHERE a.ds BETWEEN '{上线日期}' AND '{上线后N天}'
ORDER BY a.ds;
```

---

## 六、分位数分析指南

### 6.1 为什么要看分位数

均值容易被极端值拉偏。以页面加载耗时为例：

| 统计量 | 值 | 解读 |
|--------|-----|------|
| 均值 | 2.5s | 看起来还行 |
| P50 | 1.2s | 一半用户体验很好 |
| P90 | 6.8s | 但有 10% 用户要等近 7 秒 |
| P99 | 15s | 1% 用户要等 15 秒 |

只看均值会错过 P90 的严重问题。

### 6.2 推荐分位数组合

| 指标类型 | 推荐分位数 | 原因 |
|----------|------------|------|
| 耗时/延迟类 | P50, P90, P99 | 长尾效应明显，P90/P99 反映最差体验 |
| 转化率/比率类 | P25, P50, P75 | 关注中位数和四分位距 |
| 金额/收入类 | P25, P50, P75, P90 | 头部用户贡献大，需看 P90 |
| 计数类（PV/UV） | P50, P90 | 关注中位数和头部 |

### 6.3 ODPS SQL 分位数查询

```sql
SELECT
    ds,
    AVG(metric_value) AS mean_value,
    PERCENTILE(CAST(metric_value AS BIGINT), 0.50) AS p50,
    PERCENTILE(CAST(metric_value AS BIGINT), 0.90) AS p90,
    PERCENTILE(CAST(metric_value AS BIGINT), 0.99) AS p99
FROM metric_detail_table
WHERE ds BETWEEN '{start_date}' AND '{end_date}'
GROUP BY ds
ORDER BY ds;
```

---

## 七、节假日效应处理

### 7.1 节假日清单（需维护）

| 节假日 | 日期范围（示例） | 影响类型 |
|--------|-----------------|----------|
| 春节 | 1月底-2月中 | 全量影响，指标大幅波动 |
| 清明/端午/中秋 | 3天假期 | 局部影响 |
| 五一/国庆 | 5-7天假期 | 全量影响 |
| 双11/618 | 前后3-5天 | 电商类指标剧烈波动 |
| 开学季 | 8月底-9月初 | 教育/学生类指标波动 |

### 7.2 处理策略

1. **基线期包含节假日** → 从基线中排除节假日当天，或单独标注
2. **观察期包含节假日** → 节假日当天数据不参与 SPC 判断，单独标注
3. **同比对齐遇到节假日** → 确认去年是否也有相同节假日，对齐后再对比
4. **报告中明确标注** → 在图表中用灰色背景标注节假日区间

---

## 八、常见问题 FAQ

**Q: 基线期数据量不够怎么办？**
A: 最少需要 7 个数据点才能计算有意义的 σ。如果基线期不足 7 天，扩大基线窗口（如从上线前 14 天扩展到 21 天），或改用行业基准值。

**Q: 指标是新增的，没有历史数据怎么办？**
A: 无法做前后对比时，改为绝对值监控（如每日 PV/UV 是否达到预期目标值），等积累 7 天数据后再启用 SPC。

**Q: 多个指标同时异动怎么排优先级？**
A: 按严重度排序（P0 > P1 > P2），同等严重度时按业务影响度排序（核心指标 > 辅助指标）。在报告中明确标出"最需要关注的指标"。

**Q: 上线是灰度发布的，怎么监控？**
A: 灰度期间需区分实验组和对照组数据。SQL 中增加 `experiment_group` 过滤条件，分别监控两组数据。全量发布后再合并看整体。

**Q: 环比和同比该看哪个？**
A: 都要看。环比反映短期变化（上线带来的即时影响），同比排除季节性因素（排除年度趋势的干扰）。如果环比和同比方向一致，结论更可靠。
