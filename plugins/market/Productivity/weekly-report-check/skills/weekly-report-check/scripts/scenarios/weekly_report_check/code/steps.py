"""steps.py —— 周报体检的适配层（判定逻辑在 _core.py，节识别逻辑在其顶部常量）

**这一层不做判定。** 步骤只干三件事：
1. 从 ctx.inputs 拿周报文本（report-text，MULTILINE 粘贴）；
2. 调 _core 纯函数 + rules.yaml 数据面（节名/期限词/交付物词，用户可改）；
3. 把事实翻译成 ctx.outputs / ctx.issues，报告落 runtime.output_dir() 的
   独立时间戳子目录（互不覆盖）。
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import yaml
from scenario_api import Issue, IssueLevel, RunContext

from . import _core

_REPORT_NAME = "weekly_report_check_report.md"
_LAST_TODOS = "last_todos.json"


def _load_rules(ctx: RunContext) -> dict[str, Any]:
    doc = yaml.safe_load(ctx.runtime.read_template("rules.yaml")) or {}
    return {
        "title": str(doc.get("title", "周报体检报告")),
        "todo_sections": [str(x) for x in doc.get("todo_sections") or []],
        "progress_sections": [str(x) for x in doc.get("progress_sections") or []],
        "deadline_words": [str(x) for x in doc.get("deadline_words") or []],
        "deliverable_words": [str(x) for x in doc.get("deliverable_words") or []],
        "footer": str(doc.get("footer", "")).strip(),
    }


def step_parse_validate(ctx: RunContext) -> None:
    """归一 + 校验：周报文本 → 行列表；空输入记 ERROR。"""
    raw = str(ctx.inputs.get("report-text", "") or "")
    lines = raw.splitlines()
    nonempty = [ln for ln in lines if ln.strip()]
    ctx.outputs["lines"] = lines
    ctx.outputs["explain"] = {"source_chars": len(raw), "total_lines": len(lines), "nonempty_lines": len(nonempty)}
    if not nonempty:
        ctx.issues.append(Issue(IssueLevel.ERROR, "输入是空的：没有可体检的周报内容"))


def step_judge(ctx: RunContext) -> None:
    """节识别 → 待办逐行体检 + 进展逐句体检 + 上周待办呼应 → 汇总。"""
    lines: list[str] = ctx.outputs.get("lines", [])
    r = _load_rules(ctx)
    sections = _core.split_sections(lines, r["todo_sections"], r["progress_sections"])
    sections_found = bool(sections["todo"] or sections["progress"])

    findings: list[dict[str, Any]] = []
    todo_missing = 0
    for no, line in sections["todo"]:
        for item in _core.check_todo_line(line, r["deadline_words"]):
            todo_missing += 1
            findings.append(
                {
                    "line_no": no,
                    "section": "待办",
                    "type": "MISSING" if item == "负责人" else "WARNING",
                    "missing": item,
                    "excerpt": line[:60],
                }
            )
    empty_progress = 0
    for no, line in sections["progress"]:
        for sent in _core.split_sentences(line):
            if _core.is_empty_progress(sent, r["deliverable_words"]):
                empty_progress += 1
                findings.append(
                    {
                        "line_no": no,
                        "section": "进展",
                        "type": "WARNING",
                        "missing": "空转句（无数字且无交付物）",
                        "excerpt": sent[:60],
                    }
                )

    # ── 跨期对比（0.3.0）：上周待办本周是否提及；本次待办自动存档供下周用 ──
    store = ctx.runtime.data_dir() / _LAST_TODOS
    last_text = str(ctx.inputs.get("last-report-text", "") or "")
    if last_text.strip():
        last_sections = _core.split_sections(last_text.splitlines(), r["todo_sections"], r["progress_sections"])
        last_todos = [ln.lstrip("-*·• ").strip() for _, ln in last_sections["todo"]]
    elif store.exists():
        last_todos = [str(x) for x in json.loads(store.read_text(encoding="utf-8"))]
    else:
        last_todos = []
    current_norm = _core.normalize_text_for_match("\n".join(lines))
    unfollowed = 0
    followed = 0
    for todo in last_todos:
        if _core.is_followed(todo, current_norm):
            followed += 1
        else:
            unfollowed += 1
            findings.append(
                {
                    "line_no": 0,
                    "section": "上周待办",
                    "type": "WARNING",
                    "missing": "上周待办未呼应",
                    "excerpt": todo[:60],
                }
            )
    if sections_found:
        store.write_text(
            json.dumps([ln.lstrip("-*·• ").strip() for _, ln in sections["todo"]], ensure_ascii=False),
            encoding="utf-8",
        )

    verdict = _core.aggregate(todo_missing, empty_progress, sections_found, unfollowed)
    ctx.outputs["verdict"] = verdict
    ctx.outputs["findings"] = findings
    ctx.outputs["summary"] = {
        "todo_lines": len(sections["todo"]),
        "progress_lines": len(sections["progress"]),
        "todo_missing": todo_missing,
        "empty_progress": empty_progress,
        "last_todos": len(last_todos),
        "followed": followed,
        "unfollowed": unfollowed,
        "sections_found": sections_found,
    }
    if not sections_found:
        ctx.issues.append(
            Issue(
                IssueLevel.REVIEW,
                "没认出任何已知节名（本周工作/进展/下周计划/待办等）——格式不认识，判不了，不硬判；"
                "若贵司节名不同，在技能模板 rules.yaml 的清单里加上即可",
            )
        )
    else:
        if unfollowed:
            ctx.issues.append(
                Issue(IssueLevel.WARN, f"上周待办 {unfollowed} 条本周只字不提（只判提没提，不判做完没做）——逐条见报告")
            )
        if verdict == "WARNING":
            ctx.issues.append(
                Issue(IssueLevel.WARN, f"体检发现 {len(findings)} 处：待办缺项 {todo_missing}、空转句 {empty_progress}、上周未呼应 {unfollowed}（逐条见报告）")
            )


def step_render(ctx: RunContext) -> None:
    """报告落独立时间戳子目录：发现清单 / 计数 / 覆盖边界。"""
    rt = ctx.runtime
    r = _load_rules(ctx)
    s = ctx.outputs.get("summary", {})
    lines = [f"# {r['title']}", "", f"生成时间：{time.strftime('%Y-%m-%d %H:%M:%S')}", ""]

    lines += ["## 总判定", "", f"- **{ctx.outputs.get('verdict', 'UNKNOWN')}**"
              f" —— 待办 {s.get('todo_lines', 0)} 行（缺项 {s.get('todo_missing', 0)}）、"
              f"进展 {s.get('progress_lines', 0)} 行（空转句 {s.get('empty_progress', 0)}）",
              f"- 上周待办呼应：{s.get('last_todos', 0)} 条中提及 {s.get('followed', 0)}、"
              f"只字未提 {s.get('unfollowed', 0)}（本次待办已存档，下周自动对比）", ""]

    findings = ctx.outputs.get("findings") or []
    if findings:
        lines += ["## 逐条发现（带定位）", "", "| 行号 | 节 | 状态 | 缺什么 | 原文摘录 |", "|---|---|---|---|---|"]
        for f in findings:
            lines.append(f"| {f['line_no']} | {f['section']} | {f['type']} | {f['missing']} | {f['excerpt']} |")
        lines.append("")
    lines += [
        "## 覆盖边界（如实）",
        "",
        "- 负责人判定 = 行内含 @ 或「负责」字样；期限判定 = 期限词或日期式——启发式口径，漏报时报表不会替你补",
        "- 词表外的句子不判；贵司节名/说法不同时改 rules.yaml 即可，不需要改代码",
        "- 本件不改写周报、不评文风——只点可数事实",
    ]

    ts = time.strftime("%Y%m%d-%H%M%S")
    run_dir = rt.output_dir() / ts
    n = 1
    while run_dir.exists():
        run_dir = rt.output_dir() / f"{ts}-{n}"
        n += 1
    run_dir.mkdir(parents=True, exist_ok=True)
    if r["footer"]:
        lines += ["", "---", "", r["footer"]]
    out = run_dir / _REPORT_NAME
    out.write_text("\n".join(lines), encoding="utf-8")
    ctx.outputs["report_file"] = str(out)
