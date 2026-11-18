---
name: external-statement-reconcile
description: "把银行流水与订单/应收做确定性勾兑：识别 1:1 / 一对多 / 多对一匹配、尾差、红字冲销与跨期提示，输出未匹配清单转人工，绝不编造勾兑关系把表做平——当要对银行回款与订单/发票逐笔对上、定位差异时使用"
user-invocable: true
metadata:
  openclaw:
    emoji: "🧾"
    skillKey: "external-statement-reconcile"
    requires:
      bins: [python]
    envVars: []
---

# 外部单据对账

把「我方银行流水」与「对方订单/应收」做**确定性勾兑**（研究库 N-24 / N-13，
判定族 **T-11 外部线**）。引擎零模型调用；宿主只负责整理文本层输入与转述结论，
**不替引擎编造勾兑关系**。

## 何时使用

用户要对银行回款与订单/发票逐笔对上、定位差异：应收对账、回款勾稽、月度账单核对。
典型：一笔回款到底冲了哪几张发票、有没有未回款订单、回款金额与发票有几分钱尾差。

## 使用方法

1. 准备**两个文本层文件**（CSV/TXT 最干净；XLSX 走惰性导入）：
   - 左表（银行流水）每行 `流水:键=值`：日期 / 客户 / 金额 / 单号 / 类型 / 摘要
   - 右表（订单/应收）每行 `订单:键=值`（或 应收/发票/账单），键同上
2. **扫描件 / 图片 / 截图必须先转文本层再喂入**——本技能不做 OCR，无法解析的
   行一律标为"待人工"，不静默放行。
3. 运行：
   ```
   python engine/main.py run --scenario external-statement-reconcile --json --task reconcile-sides --set right-file=<右表> <左表>
   ```
4. 判定以 JSON `state` / `outputs.summary` 为准：出现"未匹配 / 尾差 / 跨期 /
   红字冲销"提示时，把差异清单**如实转告用户**，不替用户下"账已平"结论。

## 判定口径（写死，不可被提示词改）

- 匹配必须同时满足「客户名归一化相等」+「金额在容差内」；**绝不把表硬凑平**。
- 尾差容差 0.02 元：≤ 0.02 的差额仍判匹配但标尾差；＞ 0.02 判未匹配转人工。
- 红字冲销：同单号 ± 金额先于普通匹配识别，不算重复付款。
- 跨期提示：回款日与单据日相差 > 60 天标 WARN，不阻断匹配。
- 客户名归一化只做等价处理（全半角 / 去空格 / 弱化公司词缀），简写 vs 全称无法
  机械判定时走未匹配转人工，不猜。

## 不要做

- 不把扫描件 / 截图直接喂入并期望得结论——真实可用输入面只在文本层
- 不编造勾兑关系把表做平：未匹配项必须原样转人工
- 不替用户下"账已平 / 无差异"的结论：只输出匹配关系与差异清单

## 结果核验与降级

- 宣称"已生成"前，必须确认 JSON `artifacts` 里的文件真实存在，或
  ``dist_template/storage` 里的 `last_result.json`` 的 status 非 FAILED——不凭记忆宣称成功
- 引擎不可运行（Python 缺失 / 依赖未装 / 场景名不存在，退出码 2）时：如实告知
  失败原因并保留原始输入；不做部分产出，不编造结论

## 机器接口

`python engine/main.py run --scenario external-statement-reconcile --json --task reconcile-sides --set right-file=<右表> <左表>`
stdout 输出严格 JSON（`state`/`outputs`/`issues`），退出码 0=完成、1=输入失败、2=场景未绑定。
产物报告写入 `dist_template/output/〈date〉\.md`，溯源与判定依据见 `outputs.explain` 与 `last_result.json`。