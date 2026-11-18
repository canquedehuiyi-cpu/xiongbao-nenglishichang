"""
supplier-identity-vet —— 供应商主体一致性核验（场景包契约）

产品语义（对应研究库 N-05 / B-30，判定族 T-01「跨文档相符核对」）：
  判定的唯一动作 = 把台账侧与证照侧的实体字段（名称 / 法定代表人 / 开户行 /
  统一社会信用代码）做归一化一致性比对，输出 PASS / CONFLICT / UNKNOWN。

输入契约红线（与 SKILL.md / INPUT_CONTRACT.md 一致）：
  只吃文本层；扫描件/图片/截图必须在喂入前由宿主转文本层，残余未解析行
  一律 UNKNOWN 转人工。本引擎不做 OCR（GATE 1c 硬性否决）。

引擎零 LLM 调用：比对、归一、溯源、结论全部是确定性代码；
宿主只负责把原始材料整理成文本层输入并转述结论，不替引擎下判定。
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
    step_cross_check,
    step_load_entries,
    step_partition_entities,
    step_render_report,
)

SCENARIO_NAME = "supplier-identity-vet"
DISPLAY_NAME = "供应商主体一致性核验"
VERSION = "0.1.0"


def build_scenario() -> ScenarioDefinition:
    return ScenarioDefinition(
        name=SCENARIO_NAME,
        display_name=DISPLAY_NAME,
        version=VERSION,
        description=(
            "把台账侧与证照侧的供应商主体实体字段（名称/法定代表人/开户行/统一"
            "社会信用代码）做归一化一致性核验，输出 PASS/CONFLICT/UNKNOWN——"
            "当要核验供应商是不是同一主体、证件与台账是否相符时使用"
        ),
        tasks=(
            TaskDefinition(
                task_id="verify-supplier",
                label="供应商主体一致性核验",
                description=(
                    "跨文档相符核对：两侧实体字段归一化比对，输出 PASS/CONFLICT/UNKNOWN；"
                    "两侧缺一侧、字段无法解析（扫描件/图片残留）一律 REVIEW 转人工，不静默放行"
                ),
                input_fields=(
                    InputField(
                        field_id="source-file",
                        label="两侧文本（一行一条 `侧:键=值`）",
                        kind=InputKind.FILE,
                        help_text=(
                            "TXT/MD 直接读；每行形如 `台账:名称=深圳市蓝天科技有限公司`，"
                            "侧用 `台账/我方/a` 或 `证照/对方/b`，键用 名称/法定代表人/"
                            "开户行/统一社会信用代码 及别名。扫描件务必先转文本层"
                        ),
                    ),
                ),
                recovery_policy=RecoveryPolicy(fallback_enabled=True),
                steps=(
                    Step(execute=step_load_entries, policy=StepPolicy(timeout_seconds=60),
                         name="load_entries"),
                    Step(execute=step_partition_entities, name="partition_entities"),
                    Step(execute=step_cross_check, name="cross_check"),
                    Step(execute=step_render_report, name="render_report"),
                ),
            ),
        ),
    )