"""
steps.py —— 会员订阅体检适配层:解析归一(P1) → S 族判据(P2) → 报告(P3)

本层不做判定:判定纯函数在 checker.py;阈值装载与引擎语言翻译在这里。
源输入(粘贴流水)零写入;阈值外置(rules-config JSON),缺省用代码内默认值。
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from scenario_api import Issue, IssueLevel, RunContext

from detection.verdict import compute_verdict, verdict_action, verdict_badge

from . import checker
from .checker import Thresholds

_CONFIG_KEYS = {"price_tolerance", "zombie_months", "big_amount"}


def _load_thresholds(config_path: str) -> tuple[Thresholds, list[str]]:
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
    if isinstance(data.get("price_tolerance"), (int, float)):
        th = replace(th, price_tolerance=float(data["price_tolerance"]))
    if isinstance(data.get("zombie_months"), int) and data["zombie_months"] >= 2:
        th = replace(th, zombie_months=data["zombie_months"])
    if isinstance(data.get("big_amount"), (int, float)):
        th = replace(th, big_amount=float(data["big_amount"]))
    return th, notes


def step_p1_parse(ctx: RunContext) -> None:
    """P1 归一:流水粘贴文本 → 扣费列表;坏行 UNCERTAIN。"""
    raw = str(ctx.inputs.get("text", "") or "")
    config_path = str(ctx.inputs.get("rules-config", "") or "")
    parsed = checker.parse_all(raw)
    th, notes = _load_thresholds(config_path)
    ctx.outputs["explain"] = {
        "lines_in": len(raw.splitlines()),
        "charges": len(parsed.charges),
        "services": len({c.service for c in parsed.charges}),
        "uncertain_lines": len(parsed.uncertain),
        "total_amount": round(sum(c.amount for c in parsed.charges), 2),
        "thresholds": {
            "price_tolerance": th.price_tolerance,
            "zombie_months": th.zombie_months,
            "big_amount": th.big_amount,
        },
        "config_notes": notes,
    }
    ctx.outputs["_state"] = {
        "charges": [c.__dict__ for c in parsed.charges],
        "uncertain": [list(u) for u in parsed.uncertain],
    }
    if not parsed.charges:
        ctx.issues.append(Issue(IssueLevel.ERROR,
                                "没有解析出任何一笔扣费:请按『日期 服务名 金额 [渠道]』一行一笔粘贴"))
    for note in notes:
        ctx.issues.append(Issue(IssueLevel.WARN, note))


def step_p2_judge(ctx: RunContext) -> None:
    """P2 判定:S1~S5 纯函数链。"""
    state = ctx.outputs.get("_state", {})
    parsed = checker.ParsedInput(
        charges=[checker.Charge(**c) for c in state.get("charges", [])],
        uncertain=[tuple(u) for u in state.get("uncertain", [])],
    )
    th_data = ctx.outputs["explain"]["thresholds"]
    th = Thresholds(**th_data)
    findings, monthly = checker.run_all_checks(parsed, th)
    ctx.outputs["findings"] = [
        {"rule": f.rule, "severity": f.severity, "service": f.service,
         "month": f.month, "detail": f.detail}
        for f in findings
    ]
    ctx.outputs["monthly_totals"] = {k: round(v, 2) for k, v in sorted(monthly.items())}
    counts: dict[str, int] = {}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1
    ctx.outputs["counts_by_severity"] = counts
    ctx.outputs["_uncertain_count"] = len(parsed.uncertain)


def step_p3_report(ctx: RunContext) -> None:
    """P3 报告:VERDICT 计算 + UNCERTAIN 转人工清单。"""
    findings = ctx.outputs.get("findings", [])
    counts = ctx.outputs.get("counts_by_severity", {})
    uncertain_count = int(ctx.outputs.pop("_uncertain_count", 0) or 0)
    state = ctx.outputs.pop("_state", None)
    uncertain = [list(u) for u in (state or {}).get("uncertain", [])] if state else []
    verdict = compute_verdict(counts, degraded=bool(uncertain_count) and not findings)
    ctx.outputs["verdict"] = verdict
    ctx.outputs["verdict_action"] = verdict_action(verdict)
    ctx.outputs["verdict_badge"] = verdict_badge(verdict)
    ctx.outputs["uncertain"] = [
        {"line_no": no, "text": txt} for no, txt in uncertain
    ]
    if uncertain:
        ctx.issues.append(Issue(
            IssueLevel.WARN,
            f"{len(uncertain)} 行未能解析(UNCERTAIN 转人工):请人工核对这部分"))
    ctx.outputs["summary"] = (
        f"扣费 {ctx.outputs['explain'].get('charges', 0)} 笔 / "
        f"服务 {ctx.outputs['explain'].get('services', 0)} 个 / "
        f"合计 {ctx.outputs['explain'].get('total_amount', 0)} 元 / "
        f"命中 {len(findings)} 条 / 转人工 {len(uncertain)} 行 → {verdict}")
