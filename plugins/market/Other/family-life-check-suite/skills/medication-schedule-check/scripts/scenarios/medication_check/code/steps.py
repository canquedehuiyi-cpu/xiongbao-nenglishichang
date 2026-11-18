"""
steps.py —— 用药打卡核对适配层:解析归一(P1) → M 族判据(P2) → 预审报告(P3)

本层不做判定:判定纯函数在 checker.py;IO/阈值装载/引擎语言翻译在这里。
源输入(粘贴文本)零写入;阈值外置(rules-config JSON),缺省用代码内默认值。
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from scenario_api import Issue, IssueLevel, RunContext

from detection.verdict import compute_verdict, verdict_action, verdict_badge

from . import checker
from .checker import Thresholds

# rules-config 允许的键(外置覆盖面;出现未知键只提醒不阻断)
_CONFIG_KEYS = {
    "grace_minutes", "dup_window_minutes", "min_interval_minutes",
    "forbidden_pairs",
}


def _load_thresholds(ctx: RunContext, config_path: str) -> tuple[Thresholds, list[str]]:
    """阈值装载:缺省在代码;外置 JSON 只覆盖显式给出的键;坏配置 fail-safe 回默认。"""
    notes: list[str] = []
    th = Thresholds()
    if not config_path:
        return th, notes
    path = Path(config_path)
    if not path.is_file():
        notes.append(f"rules-config 不存在({config_path}),用默认阈值")
        return th, notes
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        notes.append(f"rules-config 解析失败({exc}),用默认阈值")
        return th, notes
    if not isinstance(data, dict):
        notes.append("rules-config 顶层必须是对象,用默认阈值")
        return th, notes
    unknown = sorted(set(data) - _CONFIG_KEYS)
    if unknown:
        notes.append("rules-config 未认识的键(忽略):" + ",".join(unknown))
    if isinstance(data.get("grace_minutes"), int):
        th = replace(th, grace_minutes=data["grace_minutes"])
    if isinstance(data.get("dup_window_minutes"), int):
        th = replace(th, dup_window_minutes=data["dup_window_minutes"])
    if isinstance(data.get("min_interval_minutes"), int):
        th = replace(th, min_interval_minutes=data["min_interval_minutes"])
    pairs = data.get("forbidden_pairs")
    if isinstance(pairs, list) and pairs and all(
            isinstance(p, (list, tuple)) and len(p) == 2
            and all(isinstance(x, str) and x for x in p) for p in pairs):
        th = replace(th, forbidden_pairs=tuple((str(a), str(b)) for a, b in pairs))
    elif pairs is not None:
        notes.append("forbidden_pairs 格式应为 [[药A,药B],...],忽略该键")
    return th, notes


def step_p1_parse(ctx: RunContext) -> None:
    """P1 归一:两段粘贴文本 → 计划面/打卡面/未解析行;阈值装载。"""
    plan_text = str(ctx.inputs.get("plan", "") or "")
    log_text = str(ctx.inputs.get("log", "") or "")
    config_path = str(ctx.inputs.get("rules-config", "") or "")
    parsed = checker.parse_all(plan_text, log_text)
    th, notes = _load_thresholds(ctx, config_path)
    ctx.outputs["explain"] = {
        "plan_lines_in": len(checker._nonempty(plan_text)),
        "log_lines_in": len(checker._nonempty(log_text)),
        "plan_doses": len(parsed.plan_doses),
        "drug_plans": len(parsed.drug_plans),
        "log_takes": len(parsed.log_takes),
        "uncertain_lines": len(parsed.uncertain),
        "reference_year": parsed.reference_year,
        "thresholds": {
            "grace_minutes": th.grace_minutes,
            "dup_window_minutes": th.dup_window_minutes,
            "min_interval_minutes": th.min_interval_minutes,
            "forbidden_pairs": [list(p) for p in th.forbidden_pairs],
        },
        "config_notes": notes,
    }
    ctx.outputs["_parsed_state"] = {
        "plan_doses": [pd.__dict__ for pd in parsed.plan_doses],
        "drug_plans": [dp.__dict__ for dp in parsed.drug_plans],
        "log_takes": [tk.__dict__ for tk in parsed.log_takes],
        "uncertain": [list(u) for u in parsed.uncertain],
    }
    if not plan_text.strip():
        ctx.issues.append(Issue(IssueLevel.ERROR, "医嘱计划(plan)为空:没有可核对的基准,转人工"))
    if not log_text.strip():
        ctx.issues.append(Issue(IssueLevel.ERROR, "打卡记录(log)为空:没有可核对的执行,转人工"))
    for note in notes:
        ctx.issues.append(Issue(IssueLevel.WARN, note))


def step_p2_judge(ctx: RunContext) -> None:
    """P2 判定:M1~M5 纯函数链,事实翻译成 findings 列表。"""
    state = ctx.outputs.get("_parsed_state", {})
    parsed = checker.ParsedInput(
        plan_doses=[checker.PlanDose(**d) for d in state.get("plan_doses", [])],
        drug_plans=[checker.DrugPlan(**d) for d in state.get("drug_plans", [])],
        log_takes=[checker.LogTake(**d) for d in state.get("log_takes", [])],
        uncertain=[tuple(u) for u in state.get("uncertain", [])],
    )
    th_data = ctx.outputs["explain"]["thresholds"]
    th = Thresholds(
        grace_minutes=th_data["grace_minutes"],
        dup_window_minutes=th_data["dup_window_minutes"],
        min_interval_minutes=th_data["min_interval_minutes"],
        forbidden_pairs=tuple(tuple(p) for p in th_data["forbidden_pairs"]),
    )
    findings, plan_doses = checker.run_all_checks(parsed, th)
    ctx.outputs["findings"] = [
        {"rule": f.rule, "severity": f.severity, "drug": f.drug,
         "date": f.date, "detail": f.detail}
        for f in findings
    ]
    ctx.outputs["explain"]["plan_doses_total"] = len(plan_doses)
    counts: dict[str, int] = {}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1
    ctx.outputs["counts_by_severity"] = counts
    ctx.outputs["_uncertain_count"] = len(parsed.uncertain)


def step_p3_report(ctx: RunContext) -> None:
    """P3 报告:VERDICT 计算(判定权归代码)+ UNCERTAIN 转人工清单。"""
    findings = ctx.outputs.get("findings", [])
    counts = ctx.outputs.get("counts_by_severity", {})
    uncertain_count = int(ctx.outputs.pop("_uncertain_count", 0) or 0)
    state = ctx.outputs.pop("_parsed_state", None)
    uncertain = [list(u) for u in (state or {}).get("uncertain", [])] if state else []
    # findings 优先呈现为 REVIEW(人工复核);仅当零 findings 而存在未解析行时,
    # "部分输入没核对到"才构成 DEGRADED(知情放行)——降级不掩盖问题,问题也不顶掉降级
    verdict = compute_verdict(counts, degraded=bool(uncertain_count) and not findings)
    ctx.outputs["verdict"] = verdict
    ctx.outputs["verdict_action"] = verdict_action(verdict)
    ctx.outputs["verdict_badge"] = verdict_badge(verdict)
    ctx.outputs["uncertain"] = [
        {"section": sec, "line_no": no, "text": txt} for sec, no, txt in uncertain
    ]
    if uncertain:
        ctx.issues.append(Issue(
            IssueLevel.WARN,
            f"{len(uncertain)} 行未能解析(UNCERTAIN 转人工):核对这部分请人工处理"))
    # 展示层文案不放判定阈值(模板纪律);结论只陈述事实与计数
    ctx.outputs["summary"] = (
        f"计划 {ctx.outputs['explain'].get('plan_doses_total', 0)} 次 / "
        f"打卡 {ctx.outputs['explain'].get('log_takes', 0)} 次 / "
        f"命中 {len(findings)} 条(M1漏服/M2重复/M3间隔/M4禁忌/M5断档) / "
        f"转人工 {len(uncertain)} 行 → {verdict}")
