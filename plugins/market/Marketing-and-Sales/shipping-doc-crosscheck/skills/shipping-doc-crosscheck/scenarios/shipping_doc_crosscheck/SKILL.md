---
name: shipping-doc-crosscheck
description: "把多份单证（PO/PI/INV/PL/BL/SL）的同一字段做确定性交叉核对：数值一律代码算、单位口径不可比（CTN vs PC）必须输出 UNKNOWN 转人工、每条不一致结论必带定位（单证+行号+原文摘录），绝不默认 1 CTN=1 PC——当要对形式发票与订单、发票与装箱单、提单草单与出货清单的数字和字段对不对得上时使用"
user-invocable: true
metadata:
  openclaw:
    emoji: "📑"
    skillKey: "shipping-doc-crosscheck"
    requires:
      bins: [python]
    envVars: []
---

# 单证交叉核对

把**多份单证**（PO / PI / INV / PL / BL / SL）同场逐字段做**确定性交叉核对**
（研究库 N-06 / N-07 / N-08，判定族 **T-01a 跨文档相符核对子族**）。引擎零
模型调用；宿主只负责整理文本层输入与转述结论，**不替引擎编造对应关系**。

## 何时使用

用户要确认几份单证之间"同一件事"的数字与字段对不对得上：形式发票 vs 客户订单
（型号/单价/数量/条款）、发票 vs 装箱单（箱数/数量/净毛重/金额/唛头）、提单
草单 vs 出货清单（件数/毛重/体积/柜号/港口/收发通）。

## 使用方法

1. 把多份单证合并为一个**文本层文件**（TXT/MD 最干净；PDF 须有文本层，DOCX
   走惰性导入），每行一条单证行：
   ```
   单证:类型=PO 品名=齿轮箱 数量=100 单价=500.00 币种=CNY 毛重=1500KG
   单证:类型=PI 品名=齿轮箱 数量=100.0 单价=500 币种=CNY 毛重=1500 千克
   ```
2. **扫描件 / 图片 / 截图必须先转文本层再喂入**——本技能不做 OCR，无法解析的
   行一律标"待人工"，不静默放行。
3. 运行：
   ```
   python engine/main.py run --scenario shipping-doc-crosscheck --json --task crosscheck-docs 单证合并.txt
   ```
4. 判定以 JSON `state` / `outputs.summary` 为准：出现"不一致 / 口径不可比"时，
   把差异清单**如实转告用户**，不替用户下"没问题"结论。

## 判定口径（写死，不可被提示词改）

- 数值一律**代码算**：千分位/尾零/全半角先归一化再比（100 = 100.0 = 100.00）。
- 单位同度量别名归一：1500KG = 1500 千克；**不同度量不换算**（CTN vs PC、
  KG vs LB 无换算依据）→ `UNKNOWN` 转人工，**不得默认 1 CTN = 1 PC**。
- 每条不一致 / 不可比结论**必带定位**：单证类型 + 行号 + 原文摘录（业务可复核）。
- 只出现在 1 份单证里的字段不参与交叉核对（无对照，不猜）。
- 整体终态只分 DONE（全部一致）/ REVIEW（有不一致或不可比）/ ERROR（输入为空）。

## 不要做

- 不把扫描件 / 截图直接喂入并期望得结论——真实可用输入面只在文本层
- 不编造单位换算（1 CTN = 1 PC 这类假设**一票否决**）
- 不替用户下"可通关 / 可放行 / 可结汇"结论：只输出逐字段一致/不一致/不可比事实
- 不做单文档内部自洽（合计=分项和、箱号连续）——那是脚本/另一子族（T-01b）

## 结果核验与降级

- 宣称"已生成"前，必须确认 JSON `artifacts` 里的文件真实存在，或
  ``dist_template/storage` 里的 `last_result.json`` 的 status 非 FAILED——不凭记忆宣称成功
- 引擎不可运行（Python 缺失 / 依赖未装 / 场景名不存在，退出码 2）时：如实告知
  失败原因并保留原始输入；不做部分产出，不编造结论

## 机器接口

`python engine/main.py run --scenario shipping-doc-crosscheck --json --task crosscheck-docs 单证合并.txt`
stdout 输出严格 JSON（`state`/`outputs`/`issues`），退出码 0=完成、1=输入失败、2=场景未绑定。
产物报告写入 `dist_template/output/〈date〉\doc-crosscheck-*.md`，溯源与判定依据见
`outputs.explain` 与 `last_result.json`。
