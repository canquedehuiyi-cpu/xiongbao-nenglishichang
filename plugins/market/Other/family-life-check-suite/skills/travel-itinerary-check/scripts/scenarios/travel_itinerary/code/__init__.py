"""
travel_itinerary —— 旅行行程单核对(构思方案 v4 批产场景)

定位:
    P1 归一摄入(粘贴文本解析,坏行 UNCERTAIN 转人工)
    → P2 判据链(阈值外置 rules-config,缺省在代码)
    → P3 报告(findings + extras + UNCERTAIN 清单 + VERDICT)
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

from .steps import step_p1_parse, step_p2_judge, step_p3_report

SCENARIO_NAME = "travel-itinerary"
DISPLAY_NAME = "旅行行程单核对"
VERSION = "0.1.0"


def build_scenario() -> ScenarioDefinition:
    return ScenarioDefinition(
        name=SCENARIO_NAME,
        display_name=DISPLAY_NAME,
        version=VERSION,
        description="旅行行程单核对:粘贴文本做确定性核对,输出带判据编号的问题清单;解析不了的行 UNCERTAIN 转人工。",
        tasks=(
            TaskDefinition(
                task_id="check",
                label="核对",
                description="旅行行程单核对:归一并跑判据,产出问题清单",
                input_fields=(
                    InputField(
                        field_id="text",
                        label="text",
                        kind=InputKind.TEXT,
                        required=True,
                        help_text="行程要素粘贴文本,一行一段(日期时间+类型+城市[+平台])",
                    ),
                    InputField(
                        field_id="rules-config",
                        label="阈值配置路径(可选)",
                        kind=InputKind.TEXT,
                        required=False,
                        default="",
                        help_text="外置阈值 JSON;缺省用内置默认值",
                    ),
                ),
                steps=(
                    Step(execute=step_p1_parse, policy=StepPolicy(timeout_seconds=120),
                         name="p1_parse"),
                    Step(execute=step_p2_judge, policy=StepPolicy(timeout_seconds=60),
                         name="p2_judge"),
                    step_p3_report,
                ),
            ),
        ),
    )
