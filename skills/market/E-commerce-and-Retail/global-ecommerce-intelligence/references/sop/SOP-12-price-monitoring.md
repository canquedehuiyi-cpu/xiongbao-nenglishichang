# SOP-12：竞品价格监控与调价决策全流程 v1.0.7

<!--
  sopMeta = {
    sopVersion: "1.0.7",
    owner: "监价(价格监控员)",
    ownerContact: "expert-panel#price-monitor",
    scope: "竞品价格/BSR/评价变动监控与调价触发; 调价≥10%必须专家团合议。",
    lastUpdated: "2026-09-02",
    lastVerified: "2026-09-02",
    verifyCycleDays: 60,
    nextVerifyAt: "2026-11-01"
  }
-->

## 一、触发条件（命中任意即执行）

1. 有明确竞品（同品类 TOP 卖家）需要盯价
2. 竞品降价 / 促销导致我方转化或 Buy Box 受影响
3. 需决定"跟不跟价"（先看 SOP-07 四档策略，不直接硬跟）
4. 调价前需要价格弹性与利润复核（SOP-03 + price-elasticity）

## 二、价格快照记录（每日/按需）

```bash
# 记录本次观测价（存储于系统临时目录, 不与包冲突）
node references/scripts/price-monitor.mjs --product B0XXXXXX --price 29.99 --json
# 异动阈值默认5%, 可自定义
node references/scripts/price-monitor.mjs --product B0XXXXXX --price 25.50 --threshold 5 --json
# 查看已跟踪商品
node references/scripts/price-monitor.mjs --list --json
```
- 输出含：上次价 / 变化幅度 / 是否触发异动（alert）
- 首次快照无对比基线，记第二次起才有变化率

## 三、异动处理流程

1. **触发 alert** → 判断异动类型：清仓降价 / 新品定价 / 促销限时 / 提价试探
2. **不直接硬跟** → 按 SOP-07 四档策略判断：
   - ≤5% 短期 → 观察 7 天，先不动
   - 5-15% 持续 → 软性应对（Coupon/捆绑/PPC 加投）优先
   - ≥15% 持续 → 才考虑硬降价，先过 SOP-03 + 弹性计算
   - 亏本甩卖 → 绝对不跟，转差异化
3. **调价 ≥10%** → 必须专家团合议（算账+监价+跨境 3 人交叉）
4. **调价后验证**：2 周内转化/BSR/收入是否达标，未达标回到本流程

## 四、周报输出（每周一）
- TOP5 竞品价格对比（我方 vs 竞品）
- 本周异动记录：谁降了 / 谁提价 / 谁上新
- 我方关键指标 vs 上周：转化 / BSR / 评分 / ACOS
- 下周 ≤3 条 P0 行动

## 否决路径
监价否决：数据无来源 / 阈值未设 / 未过价格弹性 → 禁止据此直接调价。
