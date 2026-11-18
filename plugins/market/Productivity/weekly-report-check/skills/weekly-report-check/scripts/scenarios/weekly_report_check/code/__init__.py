"""
weekly-report-check —— 周报体检（场景包，判定逻辑在 _core.py）

免费获客件之一：只点可数事实（待办无主无期、进展句空转），不改写不评文风；
节名/词表是 rules.yaml 数据面（用户可改），节识别逻辑与阈值在 _core.py 顶部常量。

导入规则：
- 引擎契约：from scenario_api import ...（扁平，靠 engine 的 sys.path）
- 包内模块：from .steps import ... / from . import _core（相对导入）
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

from .steps import step_judge, step_parse_validate, step_render

SCENARIO_NAME = "weekly-report-check"
DISPLAY_NAME = "周报体检"
VERSION = "0.3.0"  # 0.3.0: 跨期对比——上周待办本周呼应核对(状态自动存档,可显式传上周文本)


def build_scenario() -> ScenarioDefinition:
    return ScenarioDefinition(
        name=SCENARIO_NAME,
        display_name=DISPLAY_NAME,
        version=VERSION,
        description=(
            "把写好的周报粘贴进来：挑出无负责人、无期限的待办和没有任何数字、"
            "没有交付物的空转进展句，逐条带行号定位；不改一个字，只点名。"
            "每周提交周报前使用。"
        ),
        tasks=(
            TaskDefinition(
                task_id="check",
                label="体检周报",
                description="逐条挑出待办缺项与进展空转句，带定位输出",
                input_fields=(
                    InputField(
                        field_id="report-text",
                        label="周报全文",
                        kind=InputKind.MULTILINE,
                        help_text="直接粘贴周报全文；节名（本周工作/下周计划等）"
                        "对不上时在技能模板 rules.yaml 里加词即可",
                    ),
                    InputField(
                        field_id="last-report-text",
                        label="上周周报（可选）",
                        kind=InputKind.MULTILINE,
                        required=False,
                        help_text="不填则自动用上次运行存档的待办做呼应对比；首次使用可粘贴上周周报",
                    ),
                ),
                steps=(
                    # 输入面先行：归一 + 校验，业务步骤只消费 parsed 产物
                    Step(execute=step_parse_validate,
                         policy=StepPolicy(timeout_seconds=120),
                         name="parse_validate"),
                    Step(execute=step_judge,
                         policy=StepPolicy(timeout_seconds=120),
                         name="judge"),
                    step_render,
                ),
            ),
        ),
    )
