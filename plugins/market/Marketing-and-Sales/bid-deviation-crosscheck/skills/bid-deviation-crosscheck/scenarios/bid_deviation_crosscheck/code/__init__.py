"""
bid-deviation-crosscheck —— 偏离表与正文矛盾核对（场景包契约）

产品语义（对应研究库 N-17 / D-07，判定族 **T-07** 槽位 2 相符核对变体，限缩口径）：
  只做「核验用户**既有偏离表** vs 方案正文」——逐行定位 + 矛盾信号检测。
  **不生成偏离表/响应矩阵（G-01 出局），不做"建议怎么改"**。
  README §三 第 3 行：表称满足、正文不满足＝评标当场翻车——引擎负责把翻车点抓出来。

输入契约红线（与 SKILL.md / INPUT_CONTRACT.md 一致）：
  source-file=方案正文（文本层）；--set deviation-file=偏离表。
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
    step_parse_deviation,
    step_render_report,
)

SCENARIO_NAME = "bid-deviation-crosscheck"
DISPLAY_NAME = "偏离表与正文矛盾核对"
VERSION = "0.1.0"


def build_scenario() -> ScenarioDefinition:
    return ScenarioDefinition(
        name=SCENARIO_NAME,
        display_name=DISPLAY_NAME,
        version=VERSION,
        description=(
            "核验用户既有偏离表 vs 方案正文：偏离表每行声明（满足/偏离）用关键词在"
            "方案正文定位，检测相反信号（表称满足但正文否定回避/表称偏离但正文声称"
            "全满足）——当要确认偏离表与实际方案是否矛盾时使用；不生成偏离表，"
            "不下是否达标的结论"
        ),
        tasks=(
            TaskDefinition(
                task_id="crosscheck-deviation",
                label="偏离表与正文矛盾核对",
                description=(
                    "逐行定位偏离表声明到方案正文（行号+原文摘录），检测矛盾信号；"
                    "任何矛盾/未定位/无法判定 -> REVIEW；全部未见矛盾 -> DONE"
                    "（仅核对完成，不构成达标/可投标判断）"
                ),
                input_fields=(
                    InputField(
                        field_id="source-file",
                        label="方案正文",
                        kind=InputKind.FILE,
                        help_text=(
                            "PDF(有文本层)/DOCX/TXT 直接读；扫描件务必先转文本层"
                        ),
                    ),
                    InputField(
                        field_id="deviation-file",
                        label="偏离表",
                        kind=InputKind.FILE,
                        help_text=(
                            "每行 `偏离:条目=… 声明=满足|偏离 关键词=… 依据=…`。"
                            "关键词逗号分隔，任一命中即定位；多表任务用 "
                            "--set deviation-file=<偏离表> 传入"
                        ),
                    ),
                ),
                recovery_policy=RecoveryPolicy(fallback_enabled=True),
                steps=(
                    Step(execute=step_load_inputs,
                         policy=StepPolicy(timeout_seconds=60), name="load_inputs"),
                    step_parse_deviation,
                    step_evaluate,
                    step_render_report,
                ),
            ),
        ),
    )
