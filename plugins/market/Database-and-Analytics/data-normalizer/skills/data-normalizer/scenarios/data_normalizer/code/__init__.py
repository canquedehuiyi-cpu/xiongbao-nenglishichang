"""
data-normalizer —— 数据标准化（固定前置功能，场景包契约）

产品语义（80-20 通用化的关键前置步骤）：
  各企业/公司的真实数据格式各异（列名、版式、单位写法都不同），判定场景
  无法直接吃原始文件。本功能把「用户真实数据」标准化成目标场景的标准键值行
  与回填模板——列名别名自动识别（中文为主、英文为辅）、值清洗（全半角/
  首尾空白/千分位保留）、扫描件占位拒识转人工。零 LLM、确定性规则，不臆造值。

输入契约红线（与 SKILL.md / INPUT_CONTRACT.md 一致）：
  source-file=用户真实数据文件（Excel/CSV 表格优先，文本/PDF/Word 走文本层）；
  --set scenario=<snake> 指定目标场景键集（CHOICE：6 个审计场景）。
  只吃文本层；扫描件占位不得入内；不换算/不假设口径；列名对不上如实转人工。

产物（三件套，落在 output/ 目录）：
  <snake>-normalized.txt   标准键值行（可直接喂目标场景判定）
  <snake>-normalized.xlsx  回填模板（表名/表头与场景模板一致，可回喂）
  normalize-report-<date>.md  清洗报告（列映射/未识别列/转人工清单）
"""

from __future__ import annotations

from scenario_api import (
    InputField,
    InputKind,
    ScenarioDefinition,
    Step,
    StepPolicy,
    TaskDefinition,
)

from .steps import step_load_inputs, step_normalize, step_render_report

SCENARIO_NAME = "data-normalizer"
DISPLAY_NAME = "数据标准化"
VERSION = "0.1.0"

SCENARIO_CHOICES = (
    "supplier_identity_vet",
    "shipping_doc_crosscheck",
    "material_kitting_check",
    "external_statement_reconcile",
    "bid_deviation_crosscheck",
    "bid_disqualification_terms",
)


def build_scenario() -> ScenarioDefinition:
    return ScenarioDefinition(
        name=SCENARIO_NAME,
        display_name=DISPLAY_NAME,
        version=VERSION,
        description=(
            "把用户真实数据（各企业格式各异的 Excel/CSV/文本/PDF）按目标场景"
            "自动标准化：列名别名识别、值清洗、扫描件拒识，产出标准键值行 txt + "
            "回填模板 xlsx + 清洗报告——判定场景的第一步/第二步必须先跑它，"
            "后续判定才能喂标准格式输入"
        ),
        tasks=(
            TaskDefinition(
                task_id="normalize-input",
                label="数据标准化",
                description=(
                    "把用户真实数据文件转成目标场景的标准键值行与回填模板："
                    "表格按列名别名自动识别并清洗，文本按行原样输出；"
                    "扫描件占位/未识别列如实转人工，不臆造值"
                ),
                input_fields=(
                    InputField(
                        field_id="scenario",
                        label="目标场景",
                        kind=InputKind.CHOICE,
                        choices=SCENARIO_CHOICES,
                        help_text=(
                            "标准化产物喂给哪个判定场景："
                            "supplier_identity_vet=供应商核验 / shipping_doc_crosscheck=单证交叉核对 / "
                            "material_kitting_check=物料齐套核对 / external_statement_reconcile=外部对账 / "
                            "bid_deviation_crosscheck=偏离核对 / bid_disqualification_terms=投标要件核对"
                        ),
                    ),
                    InputField(
                        field_id="source-file",
                        label="用户真实数据文件",
                        kind=InputKind.FILE,
                        help_text=(
                            "企业原始导出文件：Excel/CSV 表格优先（自动识别列名）；"
                            "文本/PDF/Word 按文本行原样输出。扫描件/截图务必先转文本层"
                        ),
                    ),
                ),
                steps=(
                    Step(execute=step_load_inputs,
                         policy=StepPolicy(timeout_seconds=60), name="load_inputs"),
                    step_normalize,
                    step_render_report,
                ),
            ),
        ),
    )
