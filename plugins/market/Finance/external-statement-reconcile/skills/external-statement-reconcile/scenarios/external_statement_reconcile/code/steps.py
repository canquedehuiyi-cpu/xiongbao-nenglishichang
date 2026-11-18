"""
steps.py —— 外部单据对账 处理步骤

步骤纪律：只往 ctx.outputs 写结果、往 ctx.issues 记问题；
溯源自检：load 步骤声明 trace_check，render 把进产物的关键条目填进 items；
explain：判定依据写进 outputs["explain"]（只写事实与计数，不泄阈值）。

输入契约：左表（银行流水）source-file + 右表（订单/应收）right-file（--set 传入），
每行 `侧:键=值`。扫描件/图片行在喂入前由宿主转文本，残余未解析行转人工。
"""

from __future__ import annotations

import time

from scenario_api import Issue, IssueLevel, RunContext, read_file_auto

from .validator import parse_record, reconcile, reconcile_issues, summarize
from .template_reader import try_read


def _read_source(path: str, field_id: str) -> str:
    """模板优先读取：模板 Excel 转键值行；否则回退 read_file_auto。"""
    lines = try_read(path, field_id)
    if lines is not None:
        return "\n".join(lines)
    return read_file_auto(path)


def step_load_tables(ctx: RunContext) -> None:
    """读左右两表并归一化文本；记录溯源原文。"""
    left_raw = _read_source(ctx.inputs["source-file"], "source-file")
    right_raw = _read_source(ctx.inputs["right-file"], "right-file")
    ctx.outputs["left_raw"] = left_raw
    ctx.outputs["right_raw"] = right_raw
    ctx.outputs["trace_check"] = {
        "source": left_raw + right_raw,
        "items": [],
    }
    if not left_raw.strip() or not right_raw.strip():
        ctx.issues.append(Issue(IssueLevel.ERROR, "输入文件存在空表"))
    return None


def step_parse_records(ctx: RunContext) -> None:
    """把左右两侧记录行解析为结构化记录；无法解析的行计入待人工。"""
    left_lines = [ln.strip() for ln in ctx.outputs.get("left_raw", "").splitlines()
                  if ln.strip()]
    right_lines = [ln.strip() for ln in ctx.outputs.get("right_raw", "").splitlines()
                   if ln.strip()]
    left_records: list[dict] = []
    right_records: list[dict] = []
    unresolved: list[str] = []
    for line in left_lines:
        rec = parse_record(line)
        if rec and rec["side"] == "left":
            rec["original"] = line
            left_records.append(rec)
        else:
            unresolved.append(line)
    for line in right_lines:
        rec = parse_record(line)
        if rec and rec["side"] == "right":
            rec["original"] = line
            right_records.append(rec)
        else:
            unresolved.append(line)
    ctx.outputs["left_records"] = left_records
    ctx.outputs["right_records"] = right_records
    ctx.outputs["unresolved"] = unresolved
    if unresolved:
        ctx.issues.append(
            Issue(IssueLevel.REVIEW,
                  f"{len(unresolved)} 行未能解析（可能为扫描件/图片/格式不符），转人工核对")
        )
    return None


def step_reconcile(ctx: RunContext) -> None:
    """执行勾兑判定，并把结论与判定依据挂到 outputs。"""
    left = ctx.outputs.get("left_records", [])
    right = ctx.outputs.get("right_records", [])
    result = reconcile(left, right)
    ctx.outputs["reconcile"] = result
    summ = summarize(result)
    ctx.outputs["summary"] = summ
    ctx.issues.extend(reconcile_issues(result))

    # 溯源：进产物的关键条目 = 参与判定的原始行（原文子串，可逐字回查）
    items = [
        r["original"] for r in ctx.outputs.get("left_records", [])
    ] + [
        r["original"] for r in ctx.outputs.get("right_records", [])
    ]
    ctx.outputs["trace_check"]["items"] = items
    return None


def step_render_report(ctx: RunContext) -> None:
    """渲染对账报告到 output/ 目录，填入溯源条目与判定依据。"""
    today = time.strftime("%Y-%m-%d")
    result = ctx.outputs.get("reconcile", {})
    summ = ctx.outputs.get("summary", {})
    unresolved = ctx.outputs.get("unresolved", [])

    lines = [
        "# 外部单据对账报告",
        "",
        f"- 日期：{today}",
        f"- 匹配：{summ.get('matched_total', 0)} 组"
        f"（1:1 {summ.get('matched_1_1', 0)} / 1:N {summ.get('matched_1_n', 0)}"
        f" / N:1 {summ.get('matched_n_1', 0)}）",
        f"- 红字冲销：{summ.get('writeoff', 0)} 对",
        f"- 未匹配：银行侧 {summ.get('unmatched_left', 0)} 条 / "
        f"订单侧 {summ.get('unmatched_right', 0)} 条",
        f"- 尾差：{summ.get('tail_diff', 0)} 项",
        f"- 跨期提示：{summ.get('cross_period', 0)} 项",
        "",
        "## 匹配关系",
        *[f"- {m['relation']} {m}" for m in result.get("matched", [])],
        "",
        "## 红字冲销",
        *[f"- {w['left_ref']} {w['left_amount']} <-> {w['right_ref']} {w['right_amount']}"
          for w in result.get("writeoff", [])],
        "",
        "## 未匹配（转人工）",
        *[f"- [银行侧] {r['fields']}" for r in result.get("unmatched_left", [])],
        *[f"- [订单侧] {r['fields']}" for r in result.get("unmatched_right", [])],
        "",
        "## 尾差 / 跨期提示",
        *[f"- 尾差 {t['relation']}：{t.get('left_ref') or t.get('right_ref')} 差 {t['diff']} 元"
          for t in result.get("tail_diff", [])],
        *[f"- 跨期 {c['left_ref']} vs {c['right_ref']} 差 {c['days']} 天"
          for c in result.get("cross_period", [])],
    ]
    if unresolved:
        lines += ["", "## 未解析行（转人工）", *[f"- {ln}" for ln in unresolved]]

    out_dir = ctx.runtime.output_dir()
    file_name = f"reconcile-{today}.md"
    (out_dir / file_name).write_text("\n".join(lines) + "\n", encoding="utf-8")
    ctx.outputs["report_file_name"] = file_name
    ctx.outputs["report_file"] = str(out_dir / file_name)

    has_unmatched = summ.get("unmatched_left", 0) or summ.get("unmatched_right", 0)
    ctx.outputs["explain"] = {
        "判定依据": (
            f"共形成 {summ.get('matched_total', 0)} 组匹配（1:1/1:N/N:1），"
            f"红字冲销 {summ.get('writeoff', 0)} 对，未匹配 {summ.get('unmatched_left', 0)}+"
            f"{summ.get('unmatched_right', 0)} 条"
        ),
        "转人工原因": (
            "存在未匹配/尾差/跨期项" if (has_unmatched or summ.get("tail_diff")
                                        or summ.get("cross_period")) else "无",
        ),
    }
    return None