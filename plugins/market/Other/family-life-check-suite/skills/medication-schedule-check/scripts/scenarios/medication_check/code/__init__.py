"""
medication_check —— 家庭用药打卡核对:医嘱计划 × 实际打卡 勾稽 + M 族判据

定位(构思方案 §3-A1 + §4 核心闭环):
    P1 归一摄入(医嘱单/打卡记录粘贴文本,逐行方言解析;坏行 UNCERTAIN 转人工)
    → P2 判据链(M1 漏服 / M2 重复 / M3 间隔不足 / M4 同服禁忌 / M5 疗程断档;
       阈值外置 rules-config,缺省在代码)
    → P3 预审报告(findings + counts + UNCERTAIN 清单 + VERDICT)

输入只需药名+日期+时间(脱敏纪律:不贴病历/身份);医疗类输出为核对提示,不诊疗。
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

SCENARIO_NAME = "medication-check"
DISPLAY_NAME = "家庭用药打卡核对"
VERSION = "0.1.0"


def build_scenario() -> ScenarioDefinition:
    return ScenarioDefinition(
        name=SCENARIO_NAME,
        display_name=DISPLAY_NAME,
        version=VERSION,
        description=(
            "对家庭用药的医嘱计划与实际打卡记录做逐条勾稽:漏服、重复服用、"
            "间隔不足、同服禁忌、疗程断档五族判据,输出带判据编号的问题清单;"
            "解析不了的行 UNCERTAIN 转人工。适合每天替家人(含异地父母)"
            "核对用药执行的人;输入只需药名+时间,先脱敏再贴。"
        ),
        tasks=(
            TaskDefinition(
                task_id="check",
                label="用药核对",
                description="医嘱计划 × 打卡记录勾稽,产出 M 族判据问题清单",
                input_fields=(
                    InputField(
                        field_id="plan",
                        label="医嘱用药单",
                        kind=InputKind.TEXT,
                        help_text=(
                            "医嘱计划粘贴文本。行方言:『药名,日期,时间[,剂量]』"
                            "或『药名 每日3次(08:00/14:00/20:00) 每次1粒 10-28至11-04』"
                            "(脱敏后只贴药名+时间)"
                        ),
                    ),
                    InputField(
                        field_id="log",
                        label="打卡记录",
                        kind=InputKind.TEXT,
                        help_text=(
                            "实际打卡粘贴文本,字段序不拘:『药名 日期 时间 [剂量]』"
                            "(如:阿莫西林 11-01 08:05 1粒)"
                        ),
                    ),
                    InputField(
                        field_id="rules-config",
                        label="阈值配置路径(可选)",
                        kind=InputKind.TEXT,
                        required=False,
                        default="",
                        help_text=(
                            "外置阈值 JSON:grace_minutes/dup_window_minutes/"
                            "min_interval_minutes/forbidden_pairs;缺省用内置默认值"
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
