"""
pre-send-check —— 公众号发文前错字核对·场景包

贴入公众号推文全文,点"发表"之前核对:错别字、异形词、标点、数字用法、
广告法极限词。硬错条条带依据(规范库条目 ID + 国标/法规条款),软建议档
(语病/冗余/搭配)由 Host 段生成,不进引擎判定。
个人词典本地存储(~/.gzh-typo-check/dictionary.txt):修正一次,永不再报。

导入规则:
- 引擎契约:from scenario_api import ...(扁平,靠 engine 的 sys.path)
- 判定能力:本包 code/ 内(specs.py 封闭规范库 + checker.py 纯函数判定器)
- 包内模块:相对导入
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

from .steps import (
    step_dict_exec,
    step_dict_parse,
    step_judge,
    step_parse_validate,
    step_render,
)

SCENARIO_NAME = "pre-send-check"
DISPLAY_NAME = "发文前核对"
VERSION = "0.4.0"


def build_scenario() -> ScenarioDefinition:
    return ScenarioDefinition(
        name=SCENARIO_NAME,
        display_name=DISPLAY_NAME,
        version=VERSION,
        description=(
            "公众号推文点'发表'之前的全文核对:判错别字、异形词、标点、数字用法、"
            "广告法极限词五类硬错,每条命中带规范库条目 ID 与国标/法规依据;"
            "个人词典本地存储,命中词加入后不再报。输入推文全文或管理词典时触发。"
        ),
        tasks=(
            TaskDefinition(
                task_id="check",
                label="发文前核对",
                description=(
                    "这次判定回答:这篇推文点'发表'前,有哪些条条有依据的硬错?"
                    "verdict = HARD_FOUND(附命中清单)/ CLEAN(附未覆盖声明);"
                    "本地词典与参数白名单自动合并生效"
                ),
                input_fields=(
                    InputField(
                        field_id="text",
                        label="推文全文",
                        kind=InputKind.TEXT,
                        help_text="粘贴推文全文,任何编辑器写的都行",
                    ),
                    InputField(
                        field_id="whitelist",
                        label="临时白名单(可选)",
                        kind=InputKind.TEXT,
                        required=False,
                        default="",
                        help_text="逗号分隔,本次不报;要永久不报请用 dict 任务加词典",
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
            TaskDefinition(
                task_id="dict",
                label="个人词典",
                description=(
                    "管理本地个人词典(品牌名/产品名/自造梗):add 加入后 check 永不再报,"
                    "list 列出当前词典,remove 恢复报告。词典文件在"
                    " ~/.gzh-typo-check/dictionary.txt,一行一词,可用记事本直接编辑"
                ),
                input_fields=(
                    InputField(
                        field_id="action",
                        label="操作",
                        kind=InputKind.CHOICE,
                        choices=("add", "list", "remove"),
                        help_text="add=加入词条;list=列出词典;remove=删除词条",
                    ),
                    InputField(
                        field_id="words",
                        label="词条(逗号分隔)",
                        kind=InputKind.TEXT,
                        required=False,
                        default="",
                        help_text="add/remove 时填;list 留空",
                    ),
                ),
                steps=(
                    Step(execute=step_dict_parse,
                         policy=StepPolicy(timeout_seconds=60),
                         name="dict_parse"),
                    Step(execute=step_dict_exec,
                         policy=StepPolicy(timeout_seconds=60),
                         name="dict_exec"),
                    step_render,
                ),
            ),
        ),
    )
