"""
external-statement-reconcile —— 外部单据对账（场景包契约）

产品语义（对应研究库 N-24 银行流水勾兑 / N-13 客户账单核对，判定族 **T-11 外部线**）：
  把「我方银行流水」与「对方订单/应收」做确定性勾兑：识别 1:1 / 一对多 / 多对一、
  尾差、红字冲销，输出匹配关系与未匹配清单。
  **绝不编造勾兑关系把表做平**（FM-01 一票否决）：无法归入任何匹配的记录 → 未匹配转人工。

输入契约红线（与 SKILL.md / INPUT_CONTRACT.md 一致）：
  左表 source-file（银行流水）+ 右表 right-file（--set 传入，订单/应收）；
  只吃文本层（CSV/TXT 最干净，XLSX 依赖惰性导入）；扫描件/图片不得入内。
  本引擎零 LLM 调用：勾兑、尾差、冲销、跨期提示全部确定性代码。
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
    step_load_tables,
    step_parse_records,
    step_reconcile,
    step_render_report,
)

SCENARIO_NAME = "external-statement-reconcile"
DISPLAY_NAME = "外部单据对账"
VERSION = "0.1.0"


def build_scenario() -> ScenarioDefinition:
    return ScenarioDefinition(
        name=SCENARIO_NAME,
        display_name=DISPLAY_NAME,
        version=VERSION,
        description=(
            "把银行流水与订单/应收做确定性勾兑：识别 1:1 / 一对多 / 多对一匹配、"
            "尾差、红字冲销与跨期提示，输出未匹配清单转人工——当要对银行回款与"
            "订单/发票逐笔对上、定位差异时使用"
        ),
        tasks=(
            TaskDefinition(
                task_id="reconcile-sides",
                label="外部单据勾兑",
                description=(
                    "跨文档相符核对（槽位 2）+ 差异定性（槽位 5）：左表=银行流水，"
                    "右表=订单/应收；输出匹配关系与未匹配清单。未匹配/尾差/跨期一律 REVIEW"
                ),
                input_fields=(
                    InputField(
                        field_id="source-file",
                        label="左表（银行流水）文本",
                        kind=InputKind.FILE,
                        help_text=(
                            "CSV/TXT/MD 直接读；每行 `流水:键=值`，键用 日期/客户/金额/"
                            "单号/类型/摘要。扫描件务必先转文本层"
                        ),
                    ),
                    InputField(
                        field_id="right-file",
                        label="右表（订单/应收）文本",
                        kind=InputKind.FILE,
                        help_text=(
                            "每行 `订单:键=值`（或 应收/发票/账单），键同上。"
                            "多表任务用 --set right-file=<右表> 传入"
                        ),
                    ),
                ),
                recovery_policy=RecoveryPolicy(fallback_enabled=True),
                steps=(
                    Step(execute=step_load_tables,
                         policy=StepPolicy(timeout_seconds=60), name="load_tables"),
                    step_parse_records,
                    step_reconcile,
                    step_render_report,
                ),
            ),
        ),
    )