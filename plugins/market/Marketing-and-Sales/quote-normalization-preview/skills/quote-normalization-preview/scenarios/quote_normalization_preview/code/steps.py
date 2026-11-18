"""
steps.py —— 多格式报价拉平预审 处理步骤

步骤纪律：只往 ctx.outputs 写结果、往 ctx.issues 记问题；
溯源自检：load 步骤声明 trace_check，render 把进产物的关键条目填进 items；
explain：判定依据写进 outputs["explain"]（只写事实与计数，不泄阈值）。

输入契约：source-file=多供应商报价合并文本层（报价行 + 可选口径行混排）；
扫描件/截图行在喂入前由宿主转文本，残余未解析行命中 _SCAN_HINTS 时转人工。
"""

from __future__ import annotations

import time

from scenario_api import Issue, IssueLevel, RunContext, read_file_auto

from .template_reader import try_read_template
from .validator import (
    evaluate,
    evaluate_issues,
    parse_decl_line,
    parse_quote_line,
)


def step_load_inputs(ctx: RunContext) -> None:
    """读输入并归一化为行。

    优先识别标准报价模板 Excel（「报价明细」+「口径声明」表）→ 转键值行；
    否则回退为文本文件逐行读取（兼容旧版键值行文本）。
    """
    src = ctx.inputs["source-file"]
    tmpl = try_read_template(src)
    if tmpl is not None:
        lines = tmpl
        raw = "\n".join(lines)
    else:
        raw = read_file_auto(src)
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    ctx.outputs["raw"] = raw
    ctx.outputs["lines"] = lines
    ctx.outputs["trace_check"] = {"source": raw, "items": []}
    if not lines:
        ctx.issues.append(Issue(IssueLevel.ERROR, "报价文件是空的"))
    return None


def step_parse_lines(ctx: RunContext) -> None:
    """分离口径声明行与报价行；无法解析的行计入待人工。"""
    lines = ctx.outputs.get("lines", [])
    decl: dict = {"rates": {}, "convs": {}, "tax": None}
    quotes: list[dict] = []
    unresolved: list[str] = []
    for idx, line in enumerate(lines):
        d = parse_decl_line(line)
        if d is not None:
            decl["rates"].update(d["rates"])
            decl["convs"].update(d["convs"])
            if d["tax"] is not None:
                decl["tax"] = d["tax"]
            continue
        q = parse_quote_line(line)
        if q:
            q["line_no"] = idx + 1
            q["source"] = line
            quotes.append(q)
        else:
            unresolved.append(line)
    ctx.outputs["decl"] = decl
    ctx.outputs["quotes"] = quotes
    ctx.outputs["unresolved"] = unresolved
    if unresolved:
        ctx.issues.append(
            Issue(IssueLevel.REVIEW,
                  f"{len(unresolved)} 行未能解析（可能为截图/格式不符），转人工核对")
        )
    return None


def step_evaluate(ctx: RunContext) -> None:
    """执行拉平与横向偏离检测，把结论挂到 outputs。"""
    quotes = ctx.outputs.get("quotes", [])
    decl = ctx.outputs.get("decl", {})
    result = evaluate(quotes, decl)
    ctx.outputs["result"] = result
    ctx.outputs["summary"] = result["summary"]
    ctx.outputs["verdict"] = result["verdict"]
    ctx.issues.extend(evaluate_issues(result))

    # 溯源：进产物的关键条目 = 报价/口径行原文（须在 source 里逐字可查）
    ctx.outputs["trace_check"]["items"] = list(ctx.outputs.get("lines", []))
    return None


def step_render_report(ctx: RunContext) -> None:
    """渲染拉平预审报告到 output/ 目录，填入溯源条目与判定依据。"""
    today = time.strftime("%Y-%m-%d")
    result = ctx.outputs.get("result", {})
    summ = ctx.outputs.get("summary", {})
    verdict = ctx.outputs.get("verdict", "REVIEW")
    unresolved = ctx.outputs.get("unresolved", [])

    lines = [
        "# 多格式报价拉平预审报告",
        "",
        f"- 日期：{today}",
        f"- 预审状态：**{verdict}**（仅完成拉平与偏离标记，**不构成选商结论**）",
        f"- 报价行：共 {summ.get('quoted', 0)} 条 | 组 {summ.get('groups', 0)} | "
        f"无偏离 {summ.get('normal', 0)} | 显著偏离 {summ.get('deviation', 0)} | "
        f"不可比 {summ.get('unknown', 0)} | 单家无对照 {summ.get('skipped', 0)}",
        "",
        "## 拉平与偏离结果（按品名分组）",
    ]
    for g in result.get("groups", []):
        title = g["product"] + (f" / {g['model']}" if g["model"] else "")
        lines.append(f"- **{title}**（组状态 {g['status']}，中位数 {g.get('median')}）")
        for it in g["quotes"]:
            lines.append(
                f"  - {it['supplier']}：归一单价 {it['price_norm']} "
                f"（原始 {it['price_raw']}）→ {it['status']}"
                + (f"，偏离 {it['deviation']:+.1%}" if it["deviation"] is not None else "")
            )
            lines.append(f"    - {it['detail']}")

    if unresolved:
        lines += ["", "## 未解析行（转人工）", *[f"- {ln}" for ln in unresolved]]

    out_dir = ctx.runtime.output_dir()
    file_name = f"quote-preview-{today}.md"
    (out_dir / file_name).write_text("\n".join(lines) + "\n", encoding="utf-8")
    ctx.outputs["report_file_name"] = file_name
    ctx.outputs["report_file"] = str(out_dir / file_name)

    ctx.outputs["explain"] = {
        "判定依据": (
            f"报价行 {summ.get('quoted', 0)} 条：无偏离 {summ.get('normal', 0)}，"
            f"显著偏离 {summ.get('deviation', 0)}，不可比 {summ.get('unknown', 0)}"
        ),
        "转人工原因": (
            "存在显著偏离/口径不可比报价" if verdict != "DONE" else "无",
        ),
    }
    return None
