"""
shipping-doc-crosscheck —— 单证交叉核对（场景包契约）

产品语义（对应研究库 N-06 / N-07 / N-08，判定族 **T-01a 跨文档相符核对子族**，
限缩口径 S2.2 / 输入整治计划 §4.3）：
  多份单证（PO/PI/INV/PL/BL/SL）同场，逐字段比对。数值一律代码算；口径不可比
  （CTN vs PC 无换算依据）→ UNKNOWN 转人工，**不得默认 1 CTN = 1 PC**。
  T-01b（单文档内部自洽）不在本包。

输入契约红线（与 SKILL.md / INPUT_CONTRACT.md 一致）：
  source-file=多单证合并文本层（每行一条单证行 `单证:类型=PO 品名=… …`）。
  只吃文本层；扫描件/图片不得入内。本引擎零 LLM 调用。
"""

from __future__ import annotations

from scenario_api import (
    InputField,
    InputKind,
    RecoveryPolicy,
    ScenarioDefinition,
    Step,
    StepPolicy,
    TaskDefinition,
)

from .steps import (
    step_evaluate,
    step_load_inputs,
    step_parse_docs,
    step_render_report,
)

SCENARIO_NAME = "shipping-doc-crosscheck"
DISPLAY_NAME = "单证交叉核对"
VERSION = "0.1.0"


def build_scenario() -> ScenarioDefinition:
    return ScenarioDefinition(
        name=SCENARIO_NAME,
        display_name=DISPLAY_NAME,
        version=VERSION,
        description=(
            "多份单证（PO/PI/INV/PL/BL/SL）同场逐字段交叉核对——当要确认形式发票"
            "与订单、发票与装箱单、提单草单与出货清单的数字与字段对不对得上时使用；"
            "数值代码算、口径不可比必停、每条结论带定位"
        ),
        tasks=(
            TaskDefinition(
                task_id="crosscheck-docs",
                label="单证交叉核对",
                description=(
                    "把多单证合并文本层逐条解析（类型前缀 PO/PI/INV/PL/BL/SL），"
                    "对出现在 ≥2 份单证中的字段做跨单证比对：全部一致 -> DONE；"
                    "任何不一致/口径不可比 -> REVIEW（必带定位：行号+原文摘录）"
                ),
                input_fields=(
                    InputField(
                        field_id="source-file",
                        label="多单证合并文本",
                        kind=InputKind.FILE,
                        help_text=(
                            "每行一条单证行：`单证:类型=PO 品名=… 数量=… 单价=… "
                            "金额=… 币种=… 毛重=…`；PDF(有文本层)/DOCX/TXT "
                            "直接读；扫描件务必先转文本层"
                        ),
                    ),
                ),
                recovery_policy=RecoveryPolicy(fallback_enabled=True),
                steps=(
                    Step(execute=step_load_inputs,
                         policy=StepPolicy(timeout_seconds=60), name="load_inputs"),
                    step_parse_docs,
                    step_evaluate,
                    step_render_report,
                ),
            ),
        ),
    )
