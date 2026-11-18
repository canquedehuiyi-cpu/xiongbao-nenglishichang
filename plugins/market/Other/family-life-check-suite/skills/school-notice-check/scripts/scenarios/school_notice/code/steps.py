"""
steps.py —— 家长群通知要求核对适配层:解析归一(P1) → 判据(P2) → 报告(P3)

本层不做判定:判定纯函数在 checker.py;阈值装载与引擎语言翻译在这里。
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

_CONFIG_KEYS = set(Thresholds.__dataclass_fields__)


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
    for key, val in data.items():
        if key in _CONFIG_KEYS and isinstance(val, (int, float)) \
                and not isinstance(val, bool):
            th = replace(th, **{key: val})
    return th, notes


def step_p1_parse(ctx: RunContext) -> None:
    """P1 归一:粘贴文本 → 结构化事实;坏行 UNCERTAIN。"""
    text = str(ctx.inputs.get("text", "") or "")
    config_path = str(ctx.inputs.get("rules-config", "") or "")
    parsed = checker.parse_all(text=text)
    th, notes = _load_thresholds(config_path)
    ctx.outputs["explain"] = {
        "lines_in": len(text.splitlines()),
        "parsed": parsed.counts(),
        "uncertain_lines": len(parsed.uncertain),
        "thresholds": th.__dict__,
        "config_notes": notes,
    }
    ctx.outputs["_state"] = {
        "parsed": parsed.to_state(),
        "uncertain": [list(u) for u in parsed.uncertain],
    }
    if parsed.empty():
        ctx.issues.append(Issue(IssueLevel.WARN,
                                "没有解析出可核对条目:若确有要求请检查行格式或补充粘贴"))
    for note in notes:
        ctx.issues.append(Issue(IssueLevel.WARN, note))


def step_p2_judge(ctx: RunContext) -> None:
    """P2 判定:纯函数链(checker.run_all_checks)。"""
    state = ctx.outputs.get("_state", {})
    parsed = checker.from_state(state.get("parsed", {}))
    th = Thresholds(**ctx.outputs["explain"]["thresholds"])
    findings, extras = checker.run_all_checks(parsed, th)
    ctx.outputs["findings"] = [
        {"rule": f.rule, "severity": f.severity, "target": f.target,
         "when": f.when, "detail": f.detail}
        for f in findings
    ]
    ctx.outputs["extras"] = extras
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
    blocking = any(f["severity"] != "info" for f in findings)
    verdict = compute_verdict(counts, degraded=bool(uncertain_count) and not blocking)
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
        f"可核对条目 {sum(ctx.outputs['explain'].get('parsed', {}).values())} / "
        f"命中 {len(findings)} 条 / 转人工 {len(uncertain)} 行 → {verdict}")
