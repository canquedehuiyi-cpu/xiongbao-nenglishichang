---
name: data-normalizer
description: "把用户真实数据文件（各企业格式各异的 Excel/CSV/文本/PDF）按目标审计场景自动标准化为统一格式：列名别名识别、值清洗、扫描件占位拒识，产出标准键值行 txt + 回填模板 xlsx + 清洗报告——判定场景的第一步/第二步必须先跑它，后续判定才能喂标准格式输入——当用户拿来的原始数据文件格式各异、需要先标准化成标准键值行再进判定场景时使用"
user-invocable: true
metadata:
  openclaw:
    emoji: "🧹"
    skillKey: "data-normalizer"
    requires:
      bins: [python]
    envVars: []
    # 本技能不联网、零模型调用：标准化规则全在本地确定性引擎里，只做文本层转换。
---

# 数据标准化（固定前置功能）

80-20 通用化的关键前置步骤：每个厂家/公司的真实数据格式都不一样（列名、版式、
单位写法各异），判定场景无法直接吃原始文件。本技能把「用户真实数据」自动标准化成
**目标场景的标准键值行与回填模板**——这是判定场景的第一步或第二步，不跑它后续
判定都进行不下去。

引擎零模型调用、确定性规则、不臆造值；宿主只负责喂原始文件并转述清洗报告，
**不替引擎造数据**。

## 何时使用

用户拿来的原始材料是**自家/对方企业的导出文件**（Excel/CSV 表格，或文本/PDF/
Word），而后续要用某个审计场景（供应商核验 / 单证交叉核对 / 物料齐套核对 /
外部对账 / 偏离核对 / 投标要件核对）做判定时——先跑本技能把数据标准化。

## 使用方法

1. 准备**用户真实数据文件**：Excel/CSV 表格优先（自动按列名别名识别）；
   文本/PDF/Word 按文本行原样输出。**扫描件 / 截图必须先转文本层**，本技能
   不做 OCR，命中扫描件占位的单元格整行拒出、转人工清单。
2. 指定目标场景键集，运行：
   ```
   python engine/main.py run --scenario data-normalizer --json --task normalize-input ^
     --set scenario=supplier_identity_vet 企业导出.csv
   ```
   `scenario` 可选：supplier_identity_vet / shipping_doc_crosscheck /
   material_kitting_check / external_statement_reconcile / bid_deviation_crosscheck /
   bid_disqualification_terms（产物喂给哪个判定场景就选哪个）。
3. 产物三件套落在 `dist_template/output/〈date〉\`：
   - `〈snake〉-normalized.txt`：标准键值行（可直接喂目标场景判定）
   - `〈snake〉-normalized.xlsx`：回填模板（表名/表头与场景模板一致，可回喂判定）
   - `normalize-report-〈date〉.md`：清洗报告（列映射 / 未识别列 / 转人工清单）
4. 输出 `state=REVIEW`（有未识别列或扫描件占位）时，把清洗报告里的**转人工清单
   如实转告用户**，请其按回填模板补齐后再进判定，不要静默继续。

## 不要做

- 不把扫描件 / 截图直接喂入并期望得到标准化产物——真实可用输入面只在文本层
- 不臆造值：列名对不上、单元格是图片占位时如实转人工，绝不猜测填数
- 不做数值换算 / 口径假设（如币种折算、税率推算）——只做格式层清洗
- 不替用户选目标场景：`scenario` 必须由用户按下一步判定意图指定

## 结果核验与降级

- 宣称"已生成"前，必须确认 JSON `artifacts` 里的文件真实存在，或
  ``dist_template/storage` 里的 `last_result.json`` 的 status 非 FAILED——不凭记忆宣称成功
- 引擎不可运行（Python 缺失 / 依赖未装 / 场景名不存在，退出码 2）时：如实告知
  失败原因并保留原始输入；不做部分产出，不编造结论

## 机器接口

`python engine/main.py run --scenario data-normalizer --json --task normalize-input
--set scenario=〈snake〉 <文件>`
stdout 输出严格 JSON（`state`/`artifacts`/`issues`），退出码 0=完成、1=输入失败、
2=场景未绑定。产物报告写入 `dist_template/output/〈date〉\`，清洗依据见 `outputs.explain` 与
`last_result.json`。
