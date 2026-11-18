"""
bid-disqualification-terms —— 废标条款与硬性资格打标（场景包契约）

产品语义（对应研究库 N-18 / D-08，判定族 **T-07**，限缩口径）：
  只做「条款定位 + 要件逐项核对」——把检查清单里的废标/硬性资格条款在招标文件
  全文定位（行号+原文摘录），并对照我方材料清单核对要求材料命中/缺失。
  **不输出"会废标/不会废标/可投标"结论，不生成废标风险摘要**（D-08 提炼生成半边已拆）。

输入契约红线（与 SKILL.md / INPUT_CONTRACT.md 一致）：
  source-file=招标文件文本层；--set checklist-file=条款检查清单；--set
  materials-file=我方材料清单（可选）。只吃文本层；扫描件/图片不得入内。
  本引擎零 LLM 调用：定位与核对全部确定性代码。
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
    step_parse_lists,
    step_render_report,
)
from .steps_presence import (
    step_presence_evaluate,
    step_presence_load_inputs,
    step_presence_parse_required,
    step_presence_render_report,
)

SCENARIO_NAME = "bid-disqualification-terms"
DISPLAY_NAME = "投标应然要求存在性核对（条款/材料 + 完整度）"
VERSION = "0.1.0"


def build_scenario() -> ScenarioDefinition:
    return ScenarioDefinition(
        name=SCENARIO_NAME,
        display_name=DISPLAY_NAME,
        version=VERSION,
        description=(
            "对投标文件中的**应然要求**做确定性存在性核对，两任务共享同一宿主："
            "① check-completeness 对照应然清单核对标书目录中的文件完整度（N-16/N-46）；"
            "② check-terms 把废标/硬性资格条款在招标文件全文定位并逐项核对要求材料"
            "（N-18）。均只给存在性/定位状态，**不出会否废标/能否投标结论**"
        ),
        tasks=(
            TaskDefinition(
                task_id="check-terms",
                label="废标条款与硬性资格打标",
                description=(
                    "条款定位（槽位 6 风险条款定位）+ 要件逐项核对：招标文件全文检索"
                    "检查清单条款，输出 行号+原文摘录 与材料命中/缺失。任何未定位/"
                    "材料缺失/无法判定 -> REVIEW；全部定位且材料齐 -> DONE（仅核对完成，"
                    "不构成投标判断）"
                ),
                input_fields=(
                    InputField(
                        field_id="source-file",
                        label="招标文件文本",
                        kind=InputKind.FILE,
                        help_text=(
                            "PDF(有文本层)/DOCX/TXT 直接读；扫描件务必先转文本层。"
                            "几十页可全文检索"
                        ),
                    ),
                    InputField(
                        field_id="checklist-file",
                        label="条款检查清单",
                        kind=InputKind.FILE,
                        help_text=(
                            "每行 `条款:名称=… 关键词=… 材料=… 类别=废标|硬性资格`。"
                            "关键词逗号分隔，任一命中即定位；多表任务用 "
                            "--set checklist-file=<清单> 传入"
                        ),
                    ),
                    InputField(
                        field_id="materials-file",
                        label="我方材料清单（可选）",
                        kind=InputKind.FILE,
                        help_text=(
                            "每行 `材料:名称=… 关键词=…`。不传则条款材料一律标"
                            "无法判定转人工"
                        ),
                    ),
                ),
                recovery_policy=RecoveryPolicy(fallback_enabled=True),
                steps=(
                    Step(execute=step_load_inputs,
                         policy=StepPolicy(timeout_seconds=60), name="load_inputs"),
                    step_parse_lists,
                    step_evaluate,
                    step_render_report,
                ),
            ),
            TaskDefinition(
                task_id="check-completeness",
                label="封标前完整度与漏项检阅",
                description=(
                    "对照应然清单在标书目录/文件列表中逐项核对投标资料包完整度："
                    "必备项缺失 -> REVIEW；可缺项缺失 -> 提示不阻塞；全部定位 -> "
                    "DONE（仅核对存在性，不核数字一致性/签章位置）"
                ),
                input_fields=(
                    InputField(
                        field_id="source-file",
                        label="标书目录/文件列表",
                        kind=InputKind.FILE,
                        help_text=(
                            "每行一个目录条目或文件名；PDF(有文本层)/DOCX/TXT "
                            "直接读；扫描件务必先转文本层"
                        ),
                    ),
                    InputField(
                        field_id="required-file",
                        label="应然清单",
                        kind=InputKind.FILE,
                        help_text=(
                            "每行 `文件:名称=… 关键词=… 必须=是|否`。关键词逗号"
                            "分隔，任一命中即存在；多表任务用 "
                            "--set required-file=<应然清单> 传入"
                        ),
                    ),
                ),
                recovery_policy=RecoveryPolicy(fallback_enabled=True),
                steps=(
                    Step(execute=step_presence_load_inputs,
                         policy=StepPolicy(timeout_seconds=60), name="load_inputs"),
                    step_presence_parse_required,
                    step_presence_evaluate,
                    step_presence_render_report,
                ),
            ),
        ),
    )
