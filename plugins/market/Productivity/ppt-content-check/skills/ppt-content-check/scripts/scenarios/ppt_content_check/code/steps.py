"""steps.py —— PPT 内容核对的适配层（判定逻辑在 _core.py）

**这一层不做判定。** 拿 PPT 大纲文本（ppt-text）与源数据表（source-file CSV），
调 _core 纯函数对账，报告落 output_dir() 独立时间戳子目录。
"""

from __future__ import annotations

import csv
import time
from pathlib import Path
from typing import Any

import yaml
from scenario_api import Issue, IssueLevel, RunContext, read_text_auto

from . import _core

_REPORT_NAME = "ppt_content_check_report.md"


def _rules(ctx: RunContext) -> dict[str, Any]:
    doc = yaml.safe_load(ctx.runtime.read_template("rules.yaml")) or {}
    return {
        "title": str(doc.get("title", "PPT 内容核对报告")),
        "footer": str(doc.get("footer", "")).strip(),
    }


def step_parse_validate(ctx: RunContext) -> None:
    """归一 + 校验：PPT 来源（.pptx 直读或粘贴文本，二选一）→ 行；源表 → 二维表。"""
    ppt_text = str(ctx.inputs.get("ppt-text", "") or "")
    pptx_path = str(ctx.inputs.get("pptx-file", "") or "")
    src_path = str(ctx.inputs.get("source-file", "") or "")
    pages: list[int] = []
    if pptx_path and ppt_text:
        ctx.issues.append(Issue(IssueLevel.ERROR, "pptx-file 与 ppt-text 只能二选一——请只给一个来源"))
        return
    if pptx_path:
        try:
            lines, pages = _core.extract_pptx_text(pptx_path)
        except ValueError as exc:
            ctx.issues.append(Issue(IssueLevel.ERROR, str(exc)))
            return
        source_kind = Path(pptx_path).name
    else:
        lines = [ln for ln in ppt_text.splitlines() if ln.strip()]
        if not lines:
            ctx.issues.append(Issue(IssueLevel.ERROR, "PPT 大纲文本是空的：没有可核对的数字"))
            return
        source_kind = "paste"
    if not src_path:
        ctx.issues.append(Issue(IssueLevel.ERROR, "缺少源数据表（source-file）"))
        return
    text = read_text_auto(Path(src_path))
    rows = list(csv.reader(text.splitlines()))
    rows = [r for r in rows if any(str(c).strip() for c in r)]
    if not rows:
        ctx.issues.append(Issue(IssueLevel.ERROR, "源数据表是空的：没有可对的数"))
        return
    header = None
    first = rows[0]
    if any(not _core._NUM.search(str(c)) for c in first):
        header = [str(c).strip() for c in first]
        rows = rows[1:]
        if not rows:
            ctx.issues.append(Issue(IssueLevel.ERROR, "源数据表只有表头没有数据行：没有可对的数"))
            return
    ctx.outputs["ppt_lines"] = lines
    ctx.outputs["ppt_pages"] = pages
    ctx.outputs["source_rows"] = rows
    ctx.outputs["source_header"] = header
    ctx.outputs["explain"] = {
        "ppt_lines": len(lines),
        "source_rows": len(rows),
        "source_file": Path(src_path).name,
        "ppt_source": source_kind,
    }


def step_judge(ctx: RunContext) -> None:
    """抽断言 → 建索引(带标签) → 逐个对账(标签感知)。"""
    lines: list[str] = ctx.outputs.get("ppt_lines", [])
    pages: list[int] = ctx.outputs.get("ppt_pages", [])
    assertions = _core.extract_assertions(lines, pages or None)
    index, has_labels = _core.build_source_index(
        ctx.outputs.get("source_rows", []), ctx.outputs.get("source_header")
    )
    results = [_core.match(a, index, has_labels) for a in assertions]
    ctx.outputs["verdict"] = _core.aggregate(results)
    ctx.outputs["results"] = results
    ctx.outputs["summary"] = {
        "assertions": len(results),
        "with_source": sum(1 for r in results if r["status"] == "PASS"),
        "no_source": sum(1 for r in results if "未找到" in r.get("note", "")),
        "wrong_metric": sum(1 for r in results if "指标对不上" in r.get("note", "")),
        "source_labeled": has_labels,
    }
    if not assertions:
        ctx.issues.append(Issue(IssueLevel.WARN, "PPT 文本里没有抽到任何数字断言（排版数字已排除）——无可核对项"))
        return
    s = ctx.outputs["summary"]
    if s["wrong_metric"]:
        ctx.issues.append(
            Issue(IssueLevel.WARN, f"{s['wrong_metric']} 个数字在源表存在但指标对不上（可能抄错行）——逐条见报告")
        )
    if s["no_source"]:
        ctx.issues.append(
            Issue(IssueLevel.WARN, f"{s['no_source']} 个数字在源表全表找不到（含换算）——逐条见报告，请人工核对")
        )


def step_render(ctx: RunContext) -> None:
    """报告落独立时间戳子目录：逐数字对账表 / 计数 / 口径说明。"""
    rt = ctx.runtime
    r = _rules(ctx)
    s = ctx.outputs.get("summary", {})
    lines = [
        f"# {r['title']}",
        "",
        f"生成时间：{time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 总判定",
        "",
        f"- **{ctx.outputs.get('verdict', 'UNKNOWN')}** —— 数字断言 {s.get('assertions', 0)} 个："
        f"有出处 {s.get('with_source', 0)}、无出处 {s.get('no_source', 0)}、"
        f"错位(数值存在但指标对不上) {s.get('wrong_metric', 0)}",
        "",
    ]
    results = ctx.outputs.get("results") or []
    if results:
        has_pages = any("page" in x for x in results)
        loc_head = "页/行" if has_pages else "行号"
        lines += ["## 逐数字对账", "", f"| {loc_head} | 数字 | 状态 | 出处/说明 | 原文摘录 |", "|---|---|---|---|---|"]
        for x in results:
            loc = f"P{x['page']}·{x['line_no']}" if "page" in x else str(x["line_no"])
            ref = "；".join(x["refs"]) if x["refs"] else x.get("note", "")
            lines.append(f"| {loc} | {x['raw']} | {x['status']} | {ref} | {x['excerpt']} |")
        lines.append("")
    lines += [
        "## 口径说明（如实）",
        "",
        "- 数值等值含换算：百分数↔小数（3.25% = 0.0325）、千分位、万/百万/千万/亿量级",
        "- 指标对齐：断言所在句的指标词与出处行列标签做二字组/拉丁词交集（"
        + ("本表有标签，已启用" if s.get("source_labeled") else "本表无文字标签，退回存在性核对") + "）",
        "- 已排除的排版数字：列表序号、页码（第X页/PX）、完整日期、字母紧贴的编号（v0.3/Q3；"
        "指标缩写紧贴数字如「GMV68万」也会被排除——数字与缩写间加空格即可纳入核对）",
        "- 「无出处」= 源表全表找不到；「错位」= 数值在别的指标下——都不等于确认错误，请人工核对",
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
