# 埋点质量 Checklist

## 完整性检查（20 项）

### 事件定义

| # | 检查项 | 通过标准 | 常见问题 |
|---|--------|---------|---------|
| 1 | 曝光/点击成对 | 每个 2101 都有对应 2201 | 只埋了点击没埋曝光 |
| 2 | event_id 规范 | 只用 2101/2201 | 自定义 event_id 导致跨表不兼容 |
| 3 | arg1 命名规范 | page_module_element_action | 命名随意，后续无法识别 |
| 4 | arg1 唯一性 | 全局不重复 | 不同功能复用了同一 arg1 |
| 5 | 页面过滤条件 | lower(page)='page_xxx' | 漏了页面过滤，其他页面事件混入 |
| 6 | 环境过滤 | environment_code='online' | 测试数据污染分析结果 |

### args 参数

| # | 检查项 | 通过标准 | 常见问题 |
|---|--------|---------|---------|
| 7 | 格式正确 | & 分隔 key=value | 用 JSON 或 , 分隔 |
| 8 | key 命名 | snake_case | camelCase 或中文 |
| 9 | 同 arg1 区分 | 通过 args 参数区分不同场景 | 多场景复用 arg1 无法区分 |
| 10 | 参数必要性 | 只放分析需要的维度 | 过度参数化，存储浪费 |

### 口径定义

| # | 检查项 | 通过标准 | 常见问题 |
|---|--------|---------|---------|
| 11 | 率值指标定义 | 分子分母都写明 | 只写了"点击率"没写怎么算 |
| 12 | UV 去重维度 | 标注 visitor_id/utdid/user_id | 不同指标用了不同去重维度 |
| 13 | 时间窗口 | 标注日/周/月 | 日报和周报口径混用 |
| 14 | 转化率分母 | 用曝光 UV 而非 PV | PV 做分母会虚高转化率 |

### 路径覆盖

| # | 检查项 | 通过标准 | 常见问题 |
|---|--------|---------|---------|
| 15 | 入口覆盖 | 所有入口有曝光+点击 | 遗漏次要入口 |
| 16 | 关键决策点 | 每个分支有埋点 | 用户跳过的路径没追踪 |
| 17 | 结果页覆盖 | 成功/失败/超时都有 | 只埋了成功路径 |
| 18 | 退出追踪 | 用户关闭/返回有埋点 | 不知道用户在哪流失 |

### 数据验证

| # | 检查项 | 通过标准 | 常见问题 |
|---|--------|---------|---------|
| 19 | 验证 SQL | 提供了可执行的验证查询 | 没有验证 SQL，上线后无法确认 |
| 20 | 数据量预估 | 预估了日均 PV/UV 量级 | 量级过小可能导致采样误差 |

## 常见埋点设计错误

### 错误 1：只埋点击不埋曝光

**问题**：没有曝光数据，无法计算点击率，只能看到绝对点击数。

**修复**：每个点击事件必须有对应曝光事件，即使曝光量很大。

### 错误 2：args 用 JSON 格式

**问题**：ODPS 的 KEYVALUE 函数只能解析 `&` 分隔格式，JSON 需要用 get_json_object，更复杂且易出错。

**修复**：统一用 `key1=value1&key2=value2` 格式。

### 错误 3：arg1 复用不区分

**问题**：两个不同场景的点击用了同一个 arg1，分析时无法区分。

**修复**：在 args 中添加区分参数（如 `source=scene_a` vs `source=scene_b`），或直接用不同 arg1。

### 错误 4：缺少环境过滤

**问题**：测试环境和预发环境的数据混入线上分析。

**修复**：所有查询 SQL 都加 `WHERE environment_code='online'`。

### 错误 5：过度埋点

**问题**：把页面上每个元素都埋了事件，导致数据量爆炸但实际分析只用 20%。

**修复**：只埋与分析目标直接相关的事件。遵循"如果你说不出这个事件用来回答什么业务问题，就不要埋"原则。

## arg1 命名模式库

| 场景 | 曝光 arg1 | 点击 arg1 | 说明 |
|------|----------|----------|------|
| 入口按钮 | {module}_entry_show | {module}_entry_click | 主入口 |
| 页面加载 | {page}_page_show | — | 页面级曝光 |
| 功能操作 | — | {module}_{action}_click | 具体操作 |
| 结果展示 | {module}_result_show | — | 结果页曝光 |
| 结果操作 | — | {module}_result_{action} | 复制/分享/重试 |
| 推荐项 | {module}_sug_show | {module}_sug_click | 推荐/sug |
| PAA推荐 | {module}_paa_show | {module}_paa_click | People Also Ask |

## 数据验证 SQL 模板

### 基础验证：检查事件是否正常上报

```sql
-- 检查指定页面的所有事件
SELECT arg1, event_id, COUNT(1) AS pv, COUNT(DISTINCT visitor_id) AS uv
FROM {table}
WHERE day = '{date}'
  AND environment_code = 'online'
  AND lower(page) = '{page_name}'
GROUP BY arg1, event_id
ORDER BY pv DESC;
```

### 漏斗验证：检查转化链路是否完整

```sql
SELECT
  CASE
    WHEN arg1 = '{show}' AND event_id = '2201' THEN '1_曝光'
    WHEN arg1 = '{click}' AND event_id = '2101' THEN '2_点击'
    WHEN arg1 = '{action}' AND event_id = '2101' THEN '3_操作'
    WHEN arg1 = '{result}' AND event_id = '2201' THEN '4_结果'
  END AS stage,
  COUNT(1) AS pv,
  COUNT(DISTINCT visitor_id) AS uv
FROM {table}
WHERE day = '{date}'
  AND environment_code = 'online'
GROUP BY stage
HAVING stage IS NOT NULL
ORDER BY stage;
```

### args 验证：检查参数是否正确上报

```sql
SELECT
  KEYVALUE(args, '&', '=', '{key}') AS param_value,
  COUNT(1) AS cnt
FROM {table}
WHERE day = '{date}'
  AND environment_code = 'online'
  AND arg1 = '{event}'
GROUP BY param_value
ORDER BY cnt DESC
LIMIT 20;
```
