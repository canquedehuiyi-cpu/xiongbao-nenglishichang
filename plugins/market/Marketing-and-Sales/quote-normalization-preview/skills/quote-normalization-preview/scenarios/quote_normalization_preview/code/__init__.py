"""
quote-normalization-preview —— 多格式报价拉平预审（场景包契约）

产品语义（对应研究库 N-01 / E-11 / G-16，判定族 **T-02 多来源报价拉平**，
限缩口径 输入整治计划 §4.1 / 节点池 §2）：
  多家供应商格式各异的报价单 → 归一成可比单价（拉平，G-16）→ 同批横向偏离
  标记（预审，E-11，基线 = 同批中位数）。数值一律代码算；币种/单位/含税口径
  **由用户声明**，引擎不自行换算；截图件判 UNKNOWN 转人工；不输出选商结论。

输入契约红线（与 SKILL.md / INPUT_CONTRACT.md 一致）：
  source-file=多供应商报价合并文本层。报价行 `报价:供应商=… 品名=… 型号=…
  单价=… 数量=… 币种=…`，可混排口径行 `口径:USD=7.2` / `口径:SET=10PC` /
  `口径:含税=是`。只吃文本层；扫描件/截图不得入内。本引擎零 LLM 调用。
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
    step_parse_lines,
    step_render_report,
)

SCENARIO_NAME = "quote-normalization-preview"
DISPLAY_NAME = "多格式报价拉平预审"
VERSION = "0.1.0"


def build_scenario() -> ScenarioDefinition:
    return ScenarioDefinition(
        name=SCENARIO_NAME,
        display_name=DISPLAY_NAME,
        version=VERSION,
        description=(
            "多家供应商格式各异的报价单归一成可比单价（拉平），并对同批报价做"
            "横向偏离标记（预审）——当要把 3~5 家文本层报价拉到同一口径比较、"
            "标出显著偏离项时使用；币种/单位/含税口径由用户声明，引擎不自行换算，"
            "不输出选商结论"
        ),
        tasks=(
            TaskDefinition(
                task_id="flatten-quotes",
                label="多格式报价拉平预审",
                description=(
                    "把多供应商报价合并文本层逐条解析（报价行+可选口径行），"
                    "按品名/型号分组归一可比单价：组内全部无偏离 -> DONE；"
                    "任何显著偏离/口径不可比 -> REVIEW（必带定位：行号+原文摘录）"
                ),
                input_fields=(
                    InputField(
                        field_id="source-file",
                        label="多供应商报价合并文本",
                        kind=InputKind.FILE,
                        help_text=(
                            "**标准报价模板 Excel（推荐）**：`template/多格式报价拉平输入模板.xlsx`，"
                            "「报价明细」每行一家报价（供应商/品名/型号/单价/数量/金额/币种/单位/含税），"
                            "「口径声明」填汇率 / 单位换算 / 全局含税。"
                            "也兼容键值行文本：`报价:供应商=… 品名=… 单价=… 币种=… 单位=…`，"
                            "可混排口径行 `口径:USD=7.2`/`口径:SET=10PC`/`口径:含税=是`；"
                            "截图报价务必先转文本层/抄填进模板"
                        ),
                    ),
                ),
                recovery_policy=RecoveryPolicy(fallback_enabled=True),
                steps=(
                    Step(execute=step_load_inputs,
                         policy=StepPolicy(timeout_seconds=60), name="load_inputs"),
                    step_parse_lines,
                    step_evaluate,
                    step_render_report,
                ),
            ),
        ),
    )
