"""
steps.py —— 偏离表与正文矛盾核对 处理步骤

步骤纪律：只往 ctx.outputs 写结果、往 ctx.issues 记问题；
溯源自检：load 步骤声明 trace_check，render 把进产物的关键条目填进 items；
explain：判定依据写进 outputs["explain"]（只写事实与计数，不泄阈值）。

输入契约：source-file=方案正文（文本层）；--set deviation-file=偏离表。
扫描件/图片行在喂入前由宿主转文本，残余未解析行命中 _SCAN_HINTS 时转人工。
"""

from __future__ import annotations

import time

from scenario_api import Issue, IssueLevel, RunContext, read_file_auto

from .validator import (
    evaluate,
    evaluate_issues,
    parse_deviation_line,
)
from .template_reader import try_read


def _read_source(path: str, field_id: str) -> str:
    """模板优先读取：模板 Excel 转键值行；否则回退 read_file_auto。"""
    lines = try_read(path, field_id)
    if lines is not None:
        return "\n".join(lines)
    return read_file_auto(path)


def step_load_inputs(ctx: RunContext) -> None:
    """读方案正文并归一化文本；记录溯源原文。"""
    raw = _read_source(ctx.inputs["source-file"], "source-file")
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    ctx.outputs["raw"] = raw
    ctx.outputs["doc_lines"] = lines
    ctx.outputs["trace_check"] = {"source": raw, "items": []}
    if not lines:
        ctx.issues.append(Issue(IssueLevel.ERROR, "方案正文是空的"))
    return None


def step_parse_deviation(ctx: RunContext) -> None:
    """解析偏离表；无法解析的行计入待人工。"""
    dev_raw = _read_source(ctx.inputs["deviation-file"], "deviation-file")
    dev_lines = [ln.strip() for ln in dev_raw.splitlines() if ln.strip()]
    deviations: list[dict] = []
    unresolved: list[str] = []
    for line in dev_lines:
        item = parse_deviation_line(line)
        if item:
            deviations.append(item)
        else:
            unresolved.append(line)
    ctx.outputs["deviations"] = deviations
    ctx.outputs["deviation_lines"] = dev_lines
    ctx.outputs["unresolved"] = unresolved
    if unresolved:
        ctx.issues.append(
            Issue(IssueLevel.REVIEW,
                  f"{len(unresolved)} 行偏离表未能解析（可能为扫描件/格式不符），转人工核对")
        )
    return None


def step_evaluate(ctx: RunContext) -> None:
    """执行逐行定位 + 矛盾检测，把结论挂到 outputs。"""
    doc_lines = ctx.outputs.get("doc_lines", [])
    deviations = ctx.outputs.get("deviations", [])
    result = evaluate(doc_lines, deviations)
    ctx.outputs["result"] = result
    ctx.outputs["summary"] = result["summary"]
    ctx.outputs["verdict"] = result["verdict"]
    ctx.issues.extend(evaluate_issues(result))

    # 溯源：进产物的关键条目 = 正文命中行原文（须在 source 里逐字可查）
    items = []
    for r in result["rows"]:
        for h in r["hits"]:
            items.append(h["excerpt"])
    ctx.outputs["trace_check"]["items"] = items
    return None


def step_render_report(ctx: RunContext) -> None:
    """渲染核对报告到 output/ 目录，填入溯源条目与判定依据。"""
    today = time.strftime("%Y-%m-%d")
    result = ctx.outputs.get("result", {})
    summ = ctx.outputs.get("summary", {})
    verdict = ctx.outputs.get("verdict", "REVIEW")
    unresolved = ctx.outputs.get("unresolved", [])

    lines = [
        "# 偏离表与正文矛盾核对报告",
        "",
        f"- 日期：{today}",
        f"- 核对状态：**{verdict}**（仅表示未发现矛盾，**不构成达标/可投标判断**）",
        f"- 偏离表：共 {summ.get('total', 0)} 行 | 未见矛盾 {summ.get('located', 0)} | "
        f"发现矛盾 {summ.get('conflict', 0)} | 未定位 {summ.get('not_found', 0)} | "
        f"无法判定 {summ.get('unknown', 0)}",
        "",
        "## 逐行核对结果",
    ]
    for r in result.get("rows", []):
        st = r["status"]
        lines.append(f"- **{r['item']}**（声明：{r['decl']}）→ {st}")
        if r["hits"]:
            for h in r["hits"]:
                lines.append(f"  - 第 {h['line_no']} 行：{h['excerpt']}")
        sig = r.get("signals", {})
        if sig.get("neg"):
            lines.append(f"  - 检测到否定/回避信号：{'、'.join(sig['neg'])}")
        if sig.get("pos"):
            lines.append(f"  - 检测到完全满足信号：{'、'.join(sig['pos'])}")
        if r.get("basis"):
            lines.append(f"  - 偏离表依据：{r['basis']}")

    if unresolved:
        lines += ["", "## 未解析行（转人工）", *[f"- {ln}" for ln in unresolved]]

    out_dir = ctx.runtime.output_dir()
    file_name = f"deviation-crosscheck-{today}.md"
    (out_dir / file_name).write_text("\n".join(lines) + "\n", encoding="utf-8")
    ctx.outputs["report_file_name"] = file_name
    ctx.outputs["report_file"] = str(out_dir / file_name)

    ctx.outputs["explain"] = {
        "判定依据": (
            f"偏离表 {summ.get('total', 0)} 行：未见矛盾 {summ.get('located', 0)}，"
            f"矛盾 {summ.get('conflict', 0)}，未定位 {summ.get('not_found', 0)}，"
            f"无法判定 {summ.get('unknown', 0)}"
        ),
        "转人工原因": (
            "存在矛盾/未定位/无法判定行" if verdict != "DONE" else "无",
        ),
    }
    return None
