# SOP-11：跨境税费与合规核算全流程 v1.0.7

<!--
  sopMeta = {
    sopVersion: "1.0.7",
    owner: "算账(利润分析师) + 合规(合规官) 共管",
    ownerContact: "expert-panel#profit-analyst + expert-panel#compliance-checker",
    scope: "涉及跨境销售的定价/利润测算/上架前必须执行; 税费口径以目标国官方为准。",
    lastUpdated: "2026-09-02",
    lastVerified: "2026-09-02",
    verifyCycleDays: 90,
    nextVerifyAt: "2026-12-01"
  }
-->

## 一、触发条件（命中任意即执行）

1. 定价或利润测算涉及跨境（非本国销售）→ 先过本 SOP
2. 首次进入新目标国 / 首次发往欧盟 / 美国新增州
3. 定价含税口径不清晰、买家承担关税 / 卖家承担关税需明确
4. 平台要求提供 VAT / EORI / 销售税号 / 税务代理证明
5. 季度复盘时核对税率是否过期（见 SOP-04 合规巡检）

## 二、税费核算 3 步

### Step 1 — 识别目标国税费类型
- 欧盟/英国：增值税 VAT（标准档见 cross-border-guide.md，每季度核实）
- 美国：州销售税（us-sales-tax.md，每季度核实）+ 无联邦 VAT
- 其他市场：GST / 消费税 / 进口关税（以目标国官方为准）

### Step 2 — 试算税费与到岸成本
```bash
python3 references/scripts/tax_calculator.py --country DE --price 100 --shipping 15 --json
python3 references/scripts/tax_calculator.py --country US --state CA --price 100 --shipping 10 --json
python3 references/scripts/tax_calculator.py --country US --state NY --price 700 --duty-rate 5 --json
```
- 输出含：税费类型 / 税率 / 税费金额 / 关税 / 到岸总成本
- 美国各州费率需结合收货地地方税实时复核；关税以 HS 编码与海关审定为准
- 把「到岸总成本」回填进 profit_calculator 作为成本口径再算利润

### Step 3 — 税务主体与申报义务
- 欧盟：注册 VAT 号 + EORI（清关用），货值超阈值需本地 VAT 申报
- 美国：需确定 nexus（仓储州/销售州），配置 Sales Tax Permit 与平台代收
- 平台代收税费 ≠ 卖家申报义务豁免，需按申报周期自行申报
- 结论：是否由平台代收 / 卖家自报 / 需税务代理，需在报价中写明

## 三、计价口径（避免含税/不含税混乱）

| 场景 | 建议口径 |
|------|----------|
| 平台前台价 | 明确含税(欧盟显示含 VAT) 或 不含税(美区税前价) |
| 利润测算 | 统一用"扣除税费后的净收入"作为收入端 |
| 买家承担关税 | 前台价不含关税, 页面说明关税由买家承担(平台机制内) |
| 卖家承担关税 | 把关税计入成本, 重新算利润是否达标 |

## 四、验证与回填
- 税率引用必须带「核实日期 + 来源」；超过核实周期标"需验证"
- 税费结果回填利润计算 → 利润 < 目标 → 回到 SOP-03 调价
- 季度复盘：跑一次本 SOP 全流程作为税费门禁

## 否决路径
算账 / 合规任一否决：税率未核实 / 关税口径不清 / 申报义务不明 → 禁止上架与定价发布。
