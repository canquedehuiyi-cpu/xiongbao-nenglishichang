"""
prompt-skill —— Prompt 修复与 Skill 质检产线（场景包契约）

产品语义（对应用户十三项产品能力，编号与 SKILL.md 的 SOP 表一致）：
1a. fix-prompt    修复已有 Prompt：诊断 -> output/diagnosis-*.md 修复清单（宿主照单改写）
1b. (人工)        宿主按清单改写并逐轮重送
2.  draft-prompt  按描述新建 Prompt：标准骨架 + 槽位清单（明文模板装配，非模型生成）
3.  score-prompt  Prompt 质量认证（体系A 定死评分）：达标可用；版本链随候选 ID 连续
3a. prompt-version 版本链人工干预：查询 / 指定 active 指针 / 踢出回滚候选集（D-017）
3b. delta-report  两版修复对比：总分·双轨·8 维升降 + 缺口按维度增减 + 字符量 Δ（纯只读）
4.  build-skill   封装为 Skill：output/skills/<name>/ 落 AWP 目录（SKILL.md+权限+种子用例）
5a. plan-responses 响应回填作业单与体检（宿主执行被测技能后的管道支持；**绝不生成/评判响应**）
6.  score-skill   Skill 质量认证（体系B 定死评分）：结构断言 + 矩阵响应断言（确定性，严禁自评）
7.  ship-skill    交付：包指纹一致 + 回归重放通过才交付 AWP 目录 + manifest
8a. harvest-case / import-cases  Gold Case 沉淀：单条（飞轮）与批量（共用同一套审批规则）
9.  benchmark     Gold Set 指标引擎：Gate 判定 + FAR/CAR（≥30 例可回测才产结论，反空转）
10. sag-fetch     LIVE 材料承接：溯源→落盘→注入（append-only；缺溯源 FAILED 硬拒）

引擎零 LLM 调用：所有「改写、补槽、执行被测 Skill、回填响应」由宿主 Agent（WorkBuddy/Trae）
按 SKILL.md 的 SOP 完成；本包只做确定性判定与装配——这正是「严禁模型自评」的架构等价物。
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
    step_assemble_awp,
    step_assemble_draft,
    step_assert_matrix,
    step_assert_matrix_degraded,
    step_benchmark,
    step_certify_prompt,
    step_certify_skill,
    step_delta_compare,
    step_finalize_delivery,
    step_harvest_case,
    step_import_cases,
    step_lint_fix,
    step_load_brief,
    step_load_prompt,
    step_load_skill,
    step_plan_responses,
    step_precheck_build,
    step_render_benchmark_report,
    step_render_build_report,
    step_render_delta_report,
    step_render_draft_report,
    step_render_fix_report,
    step_render_harvest_report,
    step_render_import_report,
    step_render_prompt_cert,
    step_render_response_plan,
    step_render_sag_report,
    step_render_ship_report,
    step_render_skill_cert,
    step_render_version_report,
    step_replay_regression,
    step_sag_fetch,
    step_verify_ship_gate,
    step_version_control,
)

SCENARIO_NAME = "prompt-skill"
DISPLAY_NAME = "Prompt 修复与 Skill 质检产线"
VERSION = "0.2.0"

_PROMPT_SOURCE = InputField(
    field_id="source-file",
    label="Prompt 文件",
    kind=InputKind.FILE,
    help_text="txt/md 直接读；旧版 .xls 请先另存为 .xlsx",
)

_LOAD_POLICY = StepPolicy(timeout_seconds=60)


def build_scenario() -> ScenarioDefinition:
    return ScenarioDefinition(
        name=SCENARIO_NAME,
        display_name=DISPLAY_NAME,
        version=VERSION,
        description=(
            "把粗糙 Prompt 诊断修复或按描述新建，认证质量达标后封装为标准 Skill 包"
            "（AWP 目录），再做矩阵测试认证、指纹闸门打包交付——"
            "当用户要「整理/评估/产品化一个提示词或技能」时使用"
        ),
        tasks=(
            TaskDefinition(
                task_id="fix-prompt",
                label="诊断修复清单",
                description="对已有 Prompt 跑体系A 8 维检查，产出逐条修复清单（本任务只诊断，不认证）",
                input_fields=(_PROMPT_SOURCE,),
                steps=(
                    Step(execute=step_load_prompt, policy=_LOAD_POLICY, name="load_prompt"),
                    Step(execute=step_lint_fix, name="lint_fix"),
                    Step(execute=step_render_fix_report, name="render_fix_report"),
                ),
            ),
            TaskDefinition(
                task_id="draft-prompt",
                label="新建标准骨架",
                description="按任务描述装配标准 Prompt 骨架（四层上下文模板），列【待填】槽位清单",
                input_fields=(
                    InputField(field_id="task-brief", label="任务描述（一句话）",
                               kind=InputKind.TEXT,
                               help_text="这个 Prompt 要解决什么问题、面向谁；细节写到附加要求"),
                    InputField(field_id="extra-requirements", label="附加要求（可留空）",
                               kind=InputKind.MULTILINE, required=False),
                ),
                steps=(
                    Step(execute=step_load_brief, name="load_brief"),
                    Step(execute=step_assemble_draft, name="assemble_draft"),
                    Step(execute=step_render_draft_report, name="render_draft_report"),
                ),
            ),
            TaskDefinition(
                task_id="score-prompt",
                label="Prompt 质量认证",
                description="体系A 认证：总分≥80 + Risk≥28 + Gate M 材料契约 + Gate S 实质内容（有效行≥10，防堆砌空壳），且未降级才放行；同一文本第二次仍不达标会被闸门转人工",
                input_fields=(
                    _PROMPT_SOURCE,
                    InputField(field_id="candidate", label="候选 ID（可留空）",
                               kind=InputKind.TEXT, required=False,
                               help_text="同一候选跨轮修复/重做时填同一个 ID；留空则以本次文本指纹建档"),
                    InputField(field_id="route", label="路线",
                               kind=InputKind.CHOICE, required=False, choices=("A", "B"),
                               help_text="A=从 0 新建（重做上限 2 轮）；B=已有 Prompt 修改（修复上限 3 轮）；留空默认 B"),
                    InputField(field_id="degraded", label="降级产物",
                               kind=InputKind.CHOICE, required=False, choices=("false", "true"),
                               help_text="true=宿主确认无材料依据仍产出：分数再高也只给 REVIEW，不放行"),
                    InputField(field_id="change-reason", label="修改说明（可留空）",
                               kind=InputKind.TEXT, required=False,
                               help_text="记入版本快照，如「补拒答声明」「补材料契约」"),
                ),
                steps=(
                    Step(execute=step_load_prompt, policy=_LOAD_POLICY, name="load_prompt"),
                    Step(execute=step_certify_prompt, name="certify_prompt"),
                    Step(execute=step_render_prompt_cert, name="render_prompt_cert"),
                ),
            ),
            TaskDefinition(
                task_id="prompt-version",
                label="版本链查询与指针干预",
                description="按候选 ID 查版本链（append-only 快照：总分/双轨/8维/降级/时间/说明）；"
                            "--set to=vN 人工指定 active 指针，--set exclude=vN 把走错的版本踢出"
                            "回滚候选集（若它正占着 active 则立即重算到次高非排除版）；"
                            "两者都不给即纯只读查询。不重评分、不新增快照",
                input_fields=(
                    InputField(field_id="candidate", label="候选 ID",
                               kind=InputKind.TEXT,
                               help_text="score-prompt 首次送检报告里的 candidate_id"),
                    InputField(field_id="to", label="指定 active 指针版本（可留空）",
                               kind=InputKind.TEXT, required=False,
                               help_text="如 v2；不得指向已 exclude 的版本"),
                    InputField(field_id="exclude", label="标记不可回滚的版本（可留空）",
                               kind=InputKind.TEXT, required=False,
                               help_text="如 v1；目标写错而非写得不好时，把它踢出回滚候选集，"
                                       "再用 score-prompt --set route=A 从 0 重做"),
                ),
                steps=(
                    Step(execute=step_version_control, name="version_control"),
                    Step(execute=step_render_version_report, name="render_version_report"),
                ),
            ),
            TaskDefinition(
                task_id="delta-report",
                label="修复对比（两版升降）",
                description="Repair Improvement Delta：两版总分/双轨/8 维升降 + 缺口按维度增减 + "
                            "字符量 Δ；缺省对比 次新→最新，--set from=vX --set to=vY 可任意对比。"
                            "纯只读。分数取归档快照（当时认证事实），缺口与字符量按归档正文以当前"
                            "评分器重算；重算总分与归档不一致会 WARN 报评分器漂移",
                input_fields=(
                    InputField(field_id="candidate", label="候选 ID",
                               kind=InputKind.TEXT,
                               help_text="score-prompt 首次送检报告里的 candidate_id"),
                    InputField(field_id="from", label="基准版（可留空）",
                               kind=InputKind.TEXT, required=False,
                               help_text="如 v0；留空取次新版"),
                    InputField(field_id="to", label="对比版（可留空）",
                               kind=InputKind.TEXT, required=False,
                               help_text="如 v2；留空取最新版"),
                ),
                steps=(
                    Step(execute=step_delta_compare, name="delta_compare"),
                    Step(execute=step_render_delta_report, name="render_delta_report"),
                ),
            ),
            TaskDefinition(
                task_id="build-skill",
                label="封装为 Skill 包",
                description="把（应已认证的）Prompt 装配为 output/skills/<name>/ AWP 目录：SKILL.md + 权限声明 + 种子测试用例",
                input_fields=(
                    _PROMPT_SOURCE,
                    InputField(field_id="skill-name", label="技能名（kebab-case）",
                               kind=InputKind.TEXT,
                               help_text="如 meeting-cleaner；目录名与指纹都以此为准"),
                    InputField(field_id="one-liner", label="一句话描述（可留空）",
                               kind=InputKind.TEXT, required=False,
                               help_text="留空则从 Prompt 首行推导"),
                    InputField(field_id="net-policy", label="权限档位",
                               kind=InputKind.CHOICE,
                               choices=("无网络·只读工作区", "无网络·读写工作区", "允许联网"),
                               help_text="写入封装包的 PERMISSIONS.txt，联网档会强制人审"),
                ),
                steps=(
                    Step(execute=step_load_prompt, policy=_LOAD_POLICY, name="load_prompt"),
                    Step(execute=step_precheck_build, name="precheck_build"),
                    Step(execute=step_assemble_awp, name="assemble_awp"),
                    Step(execute=step_render_build_report, name="render_build_report"),
                ),
            ),
            TaskDefinition(
                task_id="plan-responses",
                label="响应回填作业单与体检",
                description="SOP 第 5 步（人工执行被测技能并回填响应）的管道支持：产出逐条作业单"
                            "（case_id / 类别 / 风险级 / 断言 / 期望结论 / input 原文 / 目标文件名），"
                            "并体检已回填的结果——待回填、空文件、孤儿文件名（对不上任何 case_id）、"
                            "非 .txt、用例 JSON 损坏。引擎**不生成也不评判任何响应内容**"
                            "（B6 严禁模型自评）；回填齐备后 score-skill 才不会降级为结构自检",
                input_fields=(
                    InputField(field_id="skill-file", label="技能包的 SKILL.md",
                               kind=InputKind.FILE,
                               help_text="选 build-skill 生成的 output/skills/<name>/SKILL.md"),
                ),
                steps=(
                    Step(execute=step_load_skill, policy=_LOAD_POLICY, name="load_skill"),
                    Step(execute=step_plan_responses, name="plan_responses"),
                    Step(execute=step_render_response_plan, name="render_response_plan"),
                ),
            ),
            TaskDefinition(
                task_id="score-skill",
                label="Skill 质量认证",
                description="体系B 认证：结构断言 + 种子用例响应矩阵；响应目录缺失自动降级为结构自检（不算可用）",
                input_fields=(
                    InputField(field_id="skill-file", label="技能包的 SKILL.md",
                               kind=InputKind.FILE,
                               help_text="选 build-skill 生成的 output/skills/<name>/SKILL.md"),
                ),
                recovery_policy=RecoveryPolicy(fallback_enabled=True),
                steps=(
                    Step(execute=step_load_skill, policy=_LOAD_POLICY, name="load_skill"),
                    Step(execute=step_assert_matrix,
                         fallback=step_assert_matrix_degraded,
                         name="assert_matrix"),
                    Step(execute=step_certify_skill, name="certify_skill"),
                    Step(execute=step_render_skill_cert, name="render_skill_cert"),
                ),
            ),
            TaskDefinition(
                task_id="ship-skill",
                label="打包交付",
                description="交付闸门：包指纹与认证记录一致才交付 AWP 目录 + SHA-256 manifest（不打包 zip），否则拒绝；同名历史版本的通过用例会做回归重放，PASS→非PASS 同样拒发",
                input_fields=(
                    InputField(field_id="skill-file", label="技能包的 SKILL.md",
                               kind=InputKind.FILE,
                               help_text="同上；未认证或认证后改动过会被拒绝"),
                ),
                steps=(
                    Step(execute=step_load_skill, policy=_LOAD_POLICY, name="load_skill"),
                    Step(execute=step_verify_ship_gate, name="verify_ship_gate"),
                    Step(execute=step_replay_regression, name="replay_regression"),
                    Step(execute=step_finalize_delivery, name="finalize_delivery"),
                    Step(execute=step_render_ship_report, name="render_ship_report"),
                ),
            ),
            TaskDefinition(
                task_id="harvest-case",
                label="飞轮沉淀案例",
                description="把真实 REVIEW/失败案例沉淀为 Gold Case（origin=human_feedback，gold_NNN 递增）；"
                            "审批规则：实质断言必填、input 去重、P0 类必须显式 verdict；沉淀后认证作废须重跑 score-skill",
                input_fields=(
                    InputField(field_id="skill-file", label="技能包的 SKILL.md",
                               kind=InputKind.FILE,
                               help_text="案例沉淀进该包的 testcases/"),
                    InputField(field_id="case-input", label="当时的真实输入",
                               kind=InputKind.MULTILINE,
                               help_text="引发 REVIEW/失败的那次输入原文"),
                    InputField(field_id="category", label="案例类别",
                               kind=InputKind.CHOICE,
                               choices=("happy", "edge", "adversarial", "refusal", "conflict")),
                    InputField(field_id="asserts", label="断言（多条用 || 分隔）",
                               kind=InputKind.TEXT,
                               help_text="至少一条实质断言：contains: / not-contains: / regex:——纯 nonempty 会被审批规则拒绝"),
                    InputField(field_id="verdict", label="期望结论（P0 类必填）",
                               kind=InputKind.CHOICE, required=False,
                               choices=("PASS", "REVIEW", "FAIL", "REJECT"),
                               help_text="adversarial/refusal/conflict 类必须显式给出"),
                    InputField(field_id="error-type", label="错误类型（可留空）",
                               kind=InputKind.TEXT, required=False,
                               help_text="如 编造事实 / 格式跑偏 / 拒答失效，记入飞轮日志"),
                    InputField(field_id="actual", label="当时的实际输出（可留空）",
                               kind=InputKind.MULTILINE, required=False),
                    InputField(field_id="risk-level", label="风险级（可留空）",
                               kind=InputKind.CHOICE, required=False,
                               choices=("P0", "P1", "P2"),
                               help_text="缺省：P0 类→P0，其余→P1"),
                    InputField(field_id="note", label="备注（可留空）",
                               kind=InputKind.TEXT, required=False),
                ),
                steps=(
                    Step(execute=step_load_skill, policy=_LOAD_POLICY, name="load_skill"),
                    Step(execute=step_harvest_case, name="harvest_case"),
                    Step(execute=step_render_harvest_report, name="render_harvest_report"),
                ),
            ),
            TaskDefinition(
                task_id="import-cases",
                label="Gold Case 批量导入",
                description="一次导入一组真实案例（cases-file 为 JSON 数组），逐条走与 harvest-case "
                            "**完全相同**的审批规则（实质断言必填、input 去重、P0 类必须显式 verdict）"
                            "——批量不比单条宽松。被拒案例逐条给理由、不写入；0 例通过才算失败。"
                            "存在意义是让 benchmark 的 Gold Set ≥30 门槛**可达**（build-skill 只产 5 个种子、"
                            "harvest-case 每次 1 个，靠单条沉淀要跑约 25 次）；门槛本身是 A.7 反空转的"
                            "刻意设计，不予调低。导入即改包指纹，认证作废须重跑 score-skill",
                input_fields=(
                    InputField(field_id="skill-file", label="技能包的 SKILL.md",
                               kind=InputKind.FILE,
                               help_text="案例导入该包的 testcases/"),
                    InputField(field_id="cases-file", label="案例清单 JSON",
                               kind=InputKind.FILE,
                               help_text="顶层为数组，每元素一个案例：必填 input / category / asserts；"
                                       "P0 类须给 expected.verdict；可选 risk_level / origin / label / "
                                       "note / error_type / case_id（缺省自动 gold_NNN 递增）"),
                ),
                steps=(
                    Step(execute=step_load_skill, policy=_LOAD_POLICY, name="load_skill"),
                    Step(execute=step_import_cases, name="import_cases"),
                    Step(execute=step_render_import_report, name="render_import_report"),
                ),
            ),
            TaskDefinition(
                task_id="benchmark",
                label="Gold Set 指标引擎",
                description="对已 build 的技能包 Gold Case 做确定性基准统计：五类覆盖度 / 实质性 / 可回测性，产出回连 Gate 的达标判定（AP-11）；>30 例才产结论，FAR/CAR 标注为需响应后启用",
                input_fields=(
                    InputField(field_id="skill-file", label="技能包的 SKILL.md",
                               kind=InputKind.FILE,
                               help_text="选 build-skill 生成（并已回填响应）的 output/skills/<name>/SKILL.md"),
                ),
                steps=(
                    Step(execute=step_load_skill, policy=_LOAD_POLICY, name="load_skill"),
                    Step(execute=step_benchmark, name="benchmark"),
                    Step(execute=step_render_benchmark_report, name="render_benchmark_report"),
                ),
            ),
            TaskDefinition(
                task_id="sag-fetch",
                label="SAG 材料承接（LIVE 补给线）",
                description="对材料契约 §11 = LIVE 的技能包承接「溯源→落盘→注入」：宿主先获取材料，引擎校验溯源元数据（来源/日期/摘录/正文）齐备后落盘 materials/<topic>/<asof>.md；缺溯源按 MISSING_MATERIAL 压级禁止注入",
                input_fields=(
                    InputField(field_id="skill-file", label="技能包的 SKILL.md",
                               kind=InputKind.FILE,
                               help_text="材料契约 §11 标注 LIVE（如竞品/行业/实时法规类）的技能包"),
                    InputField(field_id="source", label="材料来源",
                               kind=InputKind.TEXT, required=False,
                               help_text="宿主已获取的来源，如 WebSearch/iFinD/报告名/URL（仅 LIVE 时必填）"),
                    InputField(field_id="asof", label="as-of 日期",
                               kind=InputKind.TEXT, required=False,
                               help_text="材料有效日期 YYYY-MM-DD（仅 LIVE 时必填；重用时按此校验新鲜度）"),
                    InputField(field_id="title", label="材料标题/主题",
                               kind=InputKind.TEXT, required=False,
                               help_text="用于落盘目录与注入引用（仅 LIVE 时必填；topic 留空时由此推导）"),
                    InputField(field_id="excerpt", label="原文摘录",
                               kind=InputKind.MULTILINE, required=False,
                               help_text="溯源锚定的原文片段，缺此项禁止注入（仅 LIVE 时必填）"),
                    InputField(field_id="body", label="材料正文",
                               kind=InputKind.MULTILINE, required=False,
                               help_text="本次注入 prompt / 执行时消费的正文（仅 LIVE 时必填）"),
                    InputField(field_id="topic", label="落盘子目录（可留空）",
                               kind=InputKind.TEXT, required=False,
                               help_text="留空从 title 推导；建议传主题词以聚合同源材料"),
                    InputField(field_id="note", label="备注（可留空）",
                               kind=InputKind.TEXT, required=False),
                ),
                steps=(
                    Step(execute=step_load_skill, policy=_LOAD_POLICY, name="load_skill"),
                    Step(execute=step_sag_fetch, name="sag_fetch"),
                    Step(execute=step_render_sag_report, name="render_sag_report"),
                ),
            ),
        ),
        trial_limit=15,  # 产线任务链路长（诊断+认证+封装+认证+交付 ≈5 步起），比默认 10 次宽一点
    )
