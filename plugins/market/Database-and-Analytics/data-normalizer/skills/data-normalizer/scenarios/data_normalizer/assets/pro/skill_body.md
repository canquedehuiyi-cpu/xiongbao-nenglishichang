# 数据标准化

## 何时使用

当用户拿来的原始数据文件（各企业格式各异的 Excel/CSV/文本/PDF）需要先标准化成
目标审计场景的标准键值行、再喂给判定场景（供应商核验 / 单证交叉核对 / 物料齐套 /
外部对账 / 偏离核对 / 投标要件核对）时使用——判定场景无法直接吃原始格式，
不先标准化，后续判定进行不下去。

## 使用方法

1. 确认输入是文本层数据文件：Excel/CSV 表格优先（自动按列名别名识别）；
   扫描件 / 截图先转文本层，本技能不做 OCR
2. 调用：`python engine/main.py run --scenario data_normalizer --json --task normalize-input --set scenario=supplier_identity_vet 企业导出.csv`
3. 结果摘要输出到控制台并写入 ``dist_template/storage` 里的 `last_result.json``，
   产物三件套在 `dist_template/output/` 目录
4. 输出标注"待处理项"（REVIEW）时提示用户人工复核，不要替用户直接下结论

## 不要做的事

- 不要把扫描件 / 截图直接喂入——命中扫描件占位的单元格整行拒出、转人工清单
- 不要绕过确定性引擎自由发挥——列名识别、值清洗、模板回填全在本地引擎里
