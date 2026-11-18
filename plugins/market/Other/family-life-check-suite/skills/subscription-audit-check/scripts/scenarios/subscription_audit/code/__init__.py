"""
subscription_audit —— 会员订阅体检:多渠道扣费流水聚合 + S 族判据

定位(构思方案 §3-A2 + §4 核心闭环):
    P1 归一摄入(扣费流水粘贴文本,日期/服务名/金额/渠道,坏行 UNCERTAIN 转人工)
    → P2 判据链(S1 续费形态全景 / S2 同月重复 / S3 涨价 / S4 连续扣费提醒 / S5 大额;
       阈值外置 rules-config,缺省在代码)
    → P3 报告(findings + 月度聚合 + UNCERTAIN 清单 + VERDICT)

输入粘贴前先脱敏(隐去卡号/姓名/尾号);判定全程确定性,零 LLM 调用。
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

SCENARIO_NAME = "subscription-audit"
DISPLAY_NAME = "会员订阅体检"
VERSION = "0.1.0"


def build_scenario() -> ScenarioDefinition:
    return ScenarioDefinition(
        name=SCENARIO_NAME,
        display_name=DISPLAY_NAME,
        version=VERSION,
        description=(
            "合并核对多支付渠道的会员自动续费扣费流水:同一家会员重复扣、涨价、"
            "连续扣费的僵尸订阅、大额扣费四族判据,输出带判据编号的问题清单与"
            "续费全景;解析不了的行 UNCERTAIN 转人工。粘贴扣费流水即可,"
            "先隐去卡号姓名。"
        ),
        tasks=(
            TaskDefinition(
                task_id="check",
                label="订阅体检",
                description="扣费流水聚合与 S 族判据核对,产出问题清单",
                input_fields=(
                    InputField(
                        field_id="text",
                        label="扣费流水",
                        kind=InputKind.TEXT,
                        help_text=(
                            "多渠道扣费流水粘贴文本,一行一笔,字段序不拘:"
                            "『日期 服务名 金额 [渠道]』"
                            "(如:2026-10-12 腾讯视频连续包月 ¥25 微信;先脱敏再贴)"
                        ),
                    ),
                    InputField(
                        field_id="rules-config",
                        label="阈值配置路径(可选)",
                        kind=InputKind.TEXT,
                        required=False,
                        default="",
                        help_text=(
                            "外置阈值 JSON:price_tolerance/zombie_months/big_amount;"
                            "缺省用内置默认值"
                        ),
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
