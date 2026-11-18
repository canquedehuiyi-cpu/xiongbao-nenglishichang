"""
material-kitting-check —— 物料齐套核对（场景包契约）

产品语义（对应研究库 N-15 / B-43，判定族 **T-01 跨文档字段/数值核对，
B-43 内部系统导出件线**，限缩口径 输入整治计划 §4.2 / 节点池 §2 T-01）：
  单次运行读用户导出的四张表（订单 × BOM 明细 × 库存 × 在途）合并文本层 →
  按生产订单展开 BOM → 比对库存+在途 → 标记齐套/缺套及缺口数量。物料编码
  为跨表主键；单位/批次口径**由用户声明**，引擎绝不自行换算单位、绝不跨批
  自动合并；不接 ERP/MES 实时 API；不输出补货/下单建议。

输入契约红线（与 SKILL.md / INPUT_CONTRACT.md 一致）：
  source-file=四表合并文本层。订单行 `订单:订单号=… 成品=… 型号=… 数量=…`，
  BOM 行 `BOM:成品=… 子件=… 编码=… 用量=… 单位=…`，库存行
  `库存:编码=… 名称=… 数量=… 单位=… 批次=…`，在途行
  `在途:编码=… 数量=… 交期=…`；可混排口径行 `口径:单位=PC` /
  `口径:批次=合并` / `口径:安全库存=5` / `口径:换算:KG=1000PC`。
  只吃文本层；扫描件/截图不得入内。本引擎零 LLM 调用。
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

SCENARIO_NAME = "material-kitting-check"
DISPLAY_NAME = "物料齐套核对"
VERSION = "0.1.0"


def build_scenario() -> ScenarioDefinition:
    return ScenarioDefinition(
        name=SCENARIO_NAME,
        display_name=DISPLAY_NAME,
        version=VERSION,
        description=(
            "按生产订单展开 BOM，比对库存+在途，标记齐套/缺套及缺口数量——"
            "当要用订单/BOM/库存/在途四张导出表核对物料是否齐套时使用；"
            "单位/批次口径由用户声明，引擎不自行换算、不跨批自动合并，"
            "不输出补货/下单建议"
        ),
        tasks=(
            TaskDefinition(
                task_id="check-kitting",
                label="物料齐套核对",
                description=(
                    "把订单/BOM/库存/在途四表合并文本层逐条解析（数据行+可选"
                    "口径行），按生产订单展开 BOM 比对可得量：全部齐套 -> DONE；"
                    "任何缺套/不可判定 -> REVIEW（必带定位：子件编码+缺口数量）"
                ),
                input_fields=(
                    InputField(
                        field_id="source-file",
                        label="四表合并文本（订单×BOM×库存×在途）",
                        kind=InputKind.FILE,
                        help_text=(
                            "每行一条数据：`订单:订单号=… 成品=… 型号=… 数量=…`；"
                            "`BOM:成品=… 子件=… 编码=… 用量=… 单位=…`；"
                            "`库存:编码=… 名称=… 数量=… 单位=… 批次=…`；"
                            "`在途:编码=… 数量=… 交期=…`；可混排口径行："
                            "`口径:单位=PC`/`口径:批次=合并`/`口径:安全库存=5`/"
                            "`口径:换算:KG=1000PC`；PDF(有文本层)/DOCX/TXT 直接读；"
                            "扫描件务必先转文本层"
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
