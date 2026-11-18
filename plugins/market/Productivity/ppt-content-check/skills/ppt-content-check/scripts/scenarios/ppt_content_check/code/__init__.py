"""
ppt-content-check —— PPT 内容核对（场景包，判定逻辑在 _core.py）

免费获客件之二：数字断言逐个回源表对账（含 %↔小数/万·亿换算），
有出处带单元格定位，无出处点名不说是错；不改 PPT、不猜单元格对应关系。

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

SCENARIO_NAME = "ppt-content-check"
DISPLAY_NAME = "PPT 内容核对"
VERSION = "0.3.0"  # 0.3.0: .pptx 直读(zipfile+ElementTree 零新依赖,逐页文本+页码定位)


def build_scenario() -> ScenarioDefinition:
    return ScenarioDefinition(
        name=SCENARIO_NAME,
        display_name=DISPLAY_NAME,
        version=VERSION,
        description=(
            "汇报前把 PPT 大纲文本和源数据表放一起：逐数字对账，"
            "每个数字要么在源表找到出处（带单元格定位），要么点名「无出处」。"
            "不改 PPT、不猜对应关系。演示/汇报材料提交前使用。"
        ),
        tasks=(
            TaskDefinition(
                task_id="check",
                label="核对 PPT 数字",
                description="PPT 大纲文本的数字断言逐个回源表对账",
                input_fields=(
                    InputField(
                        field_id="pptx-file",
                        label="PPT 文件（.pptx，可选）",
                        kind=InputKind.FILE,
                        required=False,
                        help_text="直接给 .pptx 文件（推荐）；与下方粘贴文本二选一",
                    ),
                    InputField(
                        field_id="ppt-text",
                        label="PPT 大纲文本（可选）",
                        kind=InputKind.MULTILINE,
                        required=False,
                        help_text="没有文件时粘贴每页文字；与 .pptx 二选一",
                    ),
                    InputField(
                        field_id="source-file",
                        label="源数据表 CSV",
                        kind=InputKind.FILE,
                        help_text="数字的出处表（.csv，首行可为列名）",
                    ),
                ),
                steps=(
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
