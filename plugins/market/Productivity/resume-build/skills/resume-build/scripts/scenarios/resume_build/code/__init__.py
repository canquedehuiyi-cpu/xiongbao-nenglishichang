"""
resume-build —— 简历制作（场景包，验据逻辑在 _core.py）

免费获客件之三（生成+判定混合，所有者 2026-10-13 裁定的生成类例外）：
宿主 LLM 按 SKILL.md 指令起草草稿，引擎逐条验据——素材里没有的经历不编，
无据条目打回不进终稿；附 JD 覆盖表与时间线体检。
判定权在代码：生成归宿主，「做到什么程度才算完成」归本引擎。

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

SCENARIO_NAME = "resume-build"
DISPLAY_NAME = "简历制作"
VERSION = "0.3.0"  # 0.3.0: 打回分拆建议 + DOCX 终稿(python-docx) + 素材问答引导


def build_scenario() -> ScenarioDefinition:
    return ScenarioDefinition(
        name=SCENARIO_NAME,
        display_name=DISPLAY_NAME,
        version=VERSION,
        description=(
            "求职者给 JD 与个人素材，宿主起草简历、引擎逐条验据：素材里没有的"
            "经历、数字、日期不进终稿；附 JD 覆盖表（未提及点名）与时间线体检"
            "（断档/重叠）。投递前使用。"
        ),
        tasks=(
            TaskDefinition(
                task_id="verify",
                label="验据出终稿",
                description="对宿主起草的简历草稿逐条验据，过验条目进终稿，无据打回",
                input_fields=(
                    InputField(
                        field_id="draft-file",
                        label="简历草稿",
                        kind=InputKind.FILE,
                        help_text="按 SKILL.md 结构约定起草的 Markdown 草稿"
                        "（教育/工作/项目/实习/技能为待验节）",
                    ),
                    InputField(
                        field_id="material-file",
                        label="个人素材",
                        kind=InputKind.FILE,
                        help_text="教育/经历/技能的自由文本素材——验据基准，"
                        "草稿里每条经历都要能在里面找到依据",
                    ),
                    InputField(
                        field_id="jd-text",
                        label="目标岗位 JD",
                        kind=InputKind.MULTILINE,
                        help_text="粘贴 JD 全文，硬性要求（学历/年限/证书/工具）逐条对照终稿",
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
