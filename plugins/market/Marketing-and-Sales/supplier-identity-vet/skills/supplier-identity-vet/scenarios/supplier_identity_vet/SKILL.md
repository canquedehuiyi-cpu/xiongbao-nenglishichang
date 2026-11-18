---
name: supplier-identity-vet
description: "把台账侧与证照侧的供应商主体字段（名称/法定代表人/开户行/统一社会信用代码）做归一化一致性核验，输出 PASS/CONFLICT/UNKNOWN，无法解析（扫描件/缺侧）一律转人工——当要核验供应商是否同一主体、证件与台账是否相符时使用"
user-invocable: true
metadata:
  openclaw:
    emoji: "🪪"
    skillKey: "supplier-identity-vet"
    requires:
      bins: [python]
    envVars: []
    # 本技能不联网、仅依赖 python 解释器：判定、归一、溯源、结论全在本地确定性引擎里。
---

# 供应商主体一致性核验

单项确定性任务：把两侧实体字段做**归一化跨文档相符核对**（研究库 N-05 / 判定族 T-01），
输出 `PASS / CONFLICT / UNKNOWN`。引擎零模型调用；宿主只负责把原始材料整理成文本层
输入并转述结论，**不替引擎下判定**。

## 何时使用

用户要确认「我方台账里的供应商」与「对方提供的证照 / 登记信息」是否是**同一主体**，
或核验名称 / 法定代表人 / 开户行 / 统一社会信用代码是否彼此相符。典型：供应商准入、
签约前核验、对公付款前确认收款主体与台账一致，防"付款付错主体 / 挂靠冒名主体"。

## 使用方法

1. 把两侧信息整理成**文本层文件**（UTF-8 TXT / 文本 PDF / DOCX / XLSX / CSV）：
   每行一条 `侧:键=值`。侧用 `台账`/`我方`/`a` 或 `证照`/`对方`/`b`；
   键用 名称 / 法定代表人 / 开户行 / 统一社会信用代码（含别名，见 `INPUT_CONTRACT.md`）。
2. **扫描件 / 图片 / 截图必须先转文本层再喂入**——本技能不做 OCR，无法解析的行
   一律标为"待人工"（UNKNOWN），不静默放行。
3. 运行：
   ```
   python engine/main.py run --scenario supplier-identity-vet --json --task verify-supplier 台账证照.txt
   ```
4. 判定以 JSON `state` / `artifacts` 为准：`PASS` 一致即放行；`CONFLICT` / `UNKNOWN`
   或出现"待人工复核项"时，把差异与未解析行**如实转告用户**，不替用户下"同一主体"结论。

## 不要做

- 不把扫描件 / 截图直接喂入并期望得结论——真实可用输入面只在文本层
- 一侧缺字段、或字段无法解析时，不给 PASS / CONFLICT——只会 UNKNOWN 转人工
- 不替引擎下判定：结论一律以 `dist_template/output/*.md` 报告与 JSON `state` 为准

## 结果核验与降级

- 宣称"已生成"前，必须确认 JSON `artifacts` 里的文件真实存在，或
  ``dist_template/storage` 里的 `last_result.json`` 的 status 非 FAILED——不凭记忆宣称成功
- 引擎不可运行（Python 缺失 / 依赖未装 / 场景名不存在，退出码 2）时：如实告知
  失败原因并保留原始输入；不做部分产出，不编造结论

## 机器接口

`python engine/main.py run --scenario supplier-identity-vet --json --task verify-supplier <文件>`
stdout 输出严格 JSON（`state`/`artifacts`/`issues`），退出码 0=完成、1=输入失败、2=场景未绑定。
产物报告写入 `dist_template/output/〈date〉\.md`，溯源与判定依据见 `outputs.explain` 与 `last_result.json`。