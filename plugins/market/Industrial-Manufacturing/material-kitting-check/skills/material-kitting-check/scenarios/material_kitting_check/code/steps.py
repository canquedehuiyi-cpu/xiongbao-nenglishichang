"""
steps.py —— 物料齐套核对 处理步骤

步骤纪律：只往 ctx.outputs 写结果、往 ctx.issues 记问题；
溯源自检：load 步骤声明 trace_check，render 把进产物的关键条目填进 items；
explain：判定依据写进 outputs["explain"]（只写事实与计数，不泄阈值）。

输入契约：source-file=四表（订单×BOM×库存×在途）合并文本层，可混排口径行；
扫描件/截图行在喂入前由宿主转文本，残余未解析行命中 _SCAN_HINTS 时转人工。
"""

from __future__ import annotations

import time

from scenario_api import Issue, IssueLevel, RunContext, read_file_auto

from .validator import (
    evaluate_issues,
    parse_bom_line,
    parse_decl_line,
    parse_order_line,
    parse_stock_line,
    parse_transit_line,
)
from .template_reader import try_read


def _read_source(path: str) -> str:
    """模板优先读取：模板 Excel 转键值行；否则回退 read_file_auto。"""
    lines = try_read(path)
    if lines is not None:
        return "\n".join(lines)
    return read_file_auto(path)


def step_load_inputs(ctx: RunContext) -> None:
    """读四表合并文本文件并归一化；记录溯源原文。"""
    raw = _read_source(ctx.inputs["source-file"])
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    ctx.outputs["raw"] = raw
    ctx.outputs["lines"] = lines
    ctx.outputs["trace_check"] = {"source": raw, "items": []}
    if not lines:
        ctx.issues.append(Issue(IssueLevel.ERROR, "四表文件是空的"))
    return None


def step_parse_lines(ctx: RunContext) -> None:
    """分离口径行与四表数据行；无法解析的行计入待人工。"""
    lines = ctx.outputs.get("lines", [])
    decl: dict = {"unit": None, "batch_mode": None, "safety": 0.0, "convs": {}}
    orders: list[dict] = []
    boms: list[dict] = []
    stocks: list[dict] = []
    transits: list[dict] = []
    unresolved: list[str] = []
    for idx, line in enumerate(lines):
        d = parse_decl_line(line)
        if d is not None:
            for k in ("unit", "batch_mode", "safety"):
                if d[k] is not None:
                    decl[k] = d[k]
            decl["convs"].update(d["convs"])
            continue
        r = None
        for parser in (parse_order_line, parse_bom_line, parse_stock_line,
                       parse_transit_line):
            r = parser(line)
            if r is not None:
                break
        if r is None:
            unresolved.append(line)
            continue
        r["line_no"] = idx + 1
        r["source"] = line
        if parse_order_line(line) is not None:
            orders.append(r)
        elif parse_bom_line(line) is not None:
            boms.append(r)
        elif parse_stock_line(line) is not None:
            stocks.append(r)
        else:
            transits.append(r)
    ctx.outputs["decl"] = decl
    ctx.outputs["orders"] = orders
    ctx.outputs["boms"] = boms
    ctx.outputs["stocks"] = stocks
    ctx.outputs["transits"] = transits
    ctx.outputs["unresolved"] = unresolved
    if unresolved:
        ctx.issues.append(
            Issue(IssueLevel.REVIEW,
                  f"{len(unresolved)} 行未能解析（可能为截图/格式不符），转人工核对")
        )
    return None


def step_evaluate(ctx: RunContext) -> None:
    """执行四表齐套核对，把结论挂到 outputs。"""
    from .validator import check_kitting

    orders = ctx.outputs.get("orders", [])
    boms = ctx.outputs.get("boms", [])
    stocks = ctx.outputs.get("stocks", [])
    transits = ctx.outputs.get("transits", [])
    decl = ctx.outputs.get("decl", {})
    result = check_kitting(orders, boms, stocks, transits, decl)
    ctx.outputs["result"] = result
    ctx.outputs["summary"] = result["summary"]
    ctx.outputs["verdict"] = result["verdict"]
    ctx.issues.extend(evaluate_issues(result))

    # 溯源：进产物的关键条目 = 全部输入行原文（须在 source 里逐字可查）
    ctx.outputs["trace_check"]["items"] = list(ctx.outputs.get("lines", []))
    return None


def step_render_report(ctx: RunContext) -> None:
    """渲染齐套核对报告到 output/ 目录，填入溯源条目与判定依据。"""
    today = time.strftime("%Y-%m-%d")
    result = ctx.outputs.get("result", {})
    summ = ctx.outputs.get("summary", {})
    verdict = ctx.outputs.get("verdict", "REVIEW")
    unresolved = ctx.outputs.get("unresolved", [])

    lines = [
        "# 物料齐套核对报告",
        "",
        f"- 日期：{today}",
        f"- 核对状态：**{verdict}**（仅完成齐套/缺套标记，**不构成补货/下单建议**）",
        f"- 订单：共 {summ.get('orders', 0)} 个 | 子件 {summ.get('components', 0)} | "
        f"齐套 {summ.get('complete', 0)} | 缺套 {summ.get('short', 0)} | "
        f"不可判定 {summ.get('unknown', 0)}",
        "",
        "## 逐订单核对结果",
    ]
    for od in result.get("orders", []):
        title = od["order_id"] + (f"（{od['product']}" + (f" / {od['model']}" if od["model"] else "") + "）" if od["product"] else "")
        lines.append(f"- **{title}**（订单状态 {od['status']}）：{od['detail']}")
        for c in od["components"]:
            gap = f"，缺口 {c['gap']:g}" if c["gap"] is not None else ""
            lines.append(
                f"  - {c['part_name']}（{c['part_code']}）：需要 {c['need']}"
                f"{'（含安全库存）' if c.get('safety') else ''} / 可得 {c['available']}"
                f"{gap} → {c['status']}"
            )
            lines.append(f"    - {c['detail']}")

    if unresolved:
        lines += ["", "## 未解析行（转人工）", *[f"- {ln}" for ln in unresolved]]

    out_dir = ctx.runtime.output_dir()
    file_name = f"kitting-check-{today}.md"
    (out_dir / file_name).write_text("\n".join(lines) + "\n", encoding="utf-8")
    ctx.outputs["report_file_name"] = file_name
    ctx.outputs["report_file"] = str(out_dir / file_name)

    ctx.outputs["explain"] = {
        "判定依据": (
            f"订单 {summ.get('orders', 0)} 个 / 子件 {summ.get('components', 0)} 条："
            f"齐套 {summ.get('complete', 0)}，缺套 {summ.get('short', 0)}，"
            f"不可判定 {summ.get('unknown', 0)}"
        ),
        "转人工原因": (
            "存在缺套/不可判定子件" if verdict != "DONE" else "无",
        ),
    }
    return None
