---
name: quote-normalization-preview
description: "按标准报价模板 Excel（内部汇聚总表，采购把各家抄填进「报价明细」）拉平到可比口径并做横向偏离标记：币种/包装单位/含税口径一律由你填「口径声明」（如 USD=7.2、SET=10PC），引擎不自行换算、无法对齐的项判 UNKNOWN 转人工、绝不输出'推荐选哪家'结论——当要用同一票询价的 3 家以上报价比价、标出显著偏离项时使用；输入统一为模板 Excel，无需凑齐格式各异的原始报价文件"
user-invocable: true
metadata:
  openclaw:
    emoji: "🏷️"
    skillKey: "quote-normalization-preview"
    requires:
      bins: [python]
    envVars: []
---

# 多格式报价拉平预审

把**同一票询价的各家报价**归一成一张可比价的表（拉平，研究库 G-16），
再对同批报价做**横向偏离标记**（预审，E-11 多供应商横向比较；N-01 多格式
报价拉平预审，判定族 **T-02**）。引擎零模型调用；**输入统一为「标准报价
模板 Excel」**，币种/单位/含税口径**由用户声明**，引擎绝不自行换算。

## 何时使用

用户对同一票询价的 3 家以上报价比价，要把币种/包装单位/含税口径不一的报价
拉到同一口径、标出显著偏离项（可能是围标/串标线索，也可能是合理价差，转
人工复核）。各家原始文件可能是 XLSX/PDF/DOCX 各异——但**只需按模板抄填成
一张 Excel**即可，无需凑齐原始异构文件。

## 使用方法

1. 打开 `template/多格式报价拉平输入模板.xlsx`，在 **「报价明细」**每行填
   一家报价（供应商 / 品名 / 型号 / 单价 / 数量 / 金额 / 币种 / 单位 / 含税），
   在 **「口径声明」** 填该票的币种汇率（`USD=7.2`）、单位换算（`SET=10PC`）、
   全局含税（`含税=是`）：
   ```
   报价明细表：供应商=甲 品名=齿轮箱 型号=ZB-01 单价=500 币种=CNY 单位=PC 含税=是
               供应商=乙 品名=齿轮箱 型号=ZB-01 单价=72  币种=USD 单位=PC 含税=是
   口径声明表：USD=7.2 / SET=10PC / 含税=是
   ```
2. **扫描件 / 截图报价必须先转文字抄填进模板**——本技能不做 OCR，无法解析的
   行一律标"待人工"，不静默放行。
3. 运行：
   ```
   python engine/main.py run --scenario quote-normalization-preview --json --task flatten-quotes 报价模板.xlsx
   ```
4. 判定以 JSON `state` / `outputs.summary` 为准：出现"显著偏离 / 口径不可比"时，
   把差异清单**如实转告用户**，不替用户下"选哪家"结论。

## 判定口径（写死，不可被提示词改）

- 拉平：数值一律代码算（千分位/尾零归一）；币种按**用户声明汇率**换算到 CNY；
  包装单位按**用户声明换算**（如 1 SET = 10 PC）归一到目标单位；含税口径按全局
  声明读，行标注冲突 → 该行不可比。
- **没有声明就不换算**：币种/单位不同且无口径 → `UNKNOWN` 转人工，
  **不猜汇率、不默认 1 SET = 1 PC**。
- 预审：同批中位数做基线，|偏离| > 20% 标 `DEVIATION`（带偏离方向与百分比，
  转人工复核）；单家组 SKIPPED 不下结论。
- 整体终态只分 DONE（全部无偏离）/ REVIEW（有偏离或不可比）/ ERROR（输入为空）。

## 不要做

- 不把截图报价 / 扫描件直接喂入并期望得结论——先转文字抄填进模板；无法转的行转人工
- 不自行做币种/单位换算（用户给口径才换算；给不出 → UNKNOWN）
- 不输出"推荐供应商 / 选最低价 / 选哪家"结论（越权，只标记偏离）

## 结果核验与降级

- 宣称"已生成"前，必须确认 JSON `artifacts` 里的文件真实存在，或
  ``dist_template/storage` 里的 `last_result.json`` 的 status 非 FAILED——不凭记忆宣称成功
- 引擎不可运行（Python 缺失 / 依赖未装 / 场景名不存在，退出码 2）时：如实告知
  失败原因并保留原始输入；不做部分产出，不编造结论

## 机器接口

`python engine/main.py run --scenario quote-normalization-preview --json --task flatten-quotes 报价模板.xlsx`
stdout 输出严格 JSON（`state`/`outputs`/`issues`），退出码 0=完成、1=输入失败、2=场景未绑定。
产物报告写入 `dist_template/output/〈date〉\quote-preview-*.md`，溯源与判定依据见
`outputs.explain` 与 `last_result.json`。模板：`template/多格式报价拉平输入模板.xlsx`。
