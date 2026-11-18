"""
steps.py —— 单证交叉核对 处理步骤

步骤纪律：只往 ctx.outputs 写结果、往 ctx.issues 记问题；
溯源自检：load 步骤声明 trace_check，render 把进产物的关键条目填进 items；
explain：判定依据写进 outputs["explain"]（只写事实与计数，不泄阈值）。

输入契约：source-file=多单证合并文本层（每行一条单证行）；扫描件/图片行在喂入
前由宿主转文本，残余未解析行命中 _SCAN_HINTS 时转人工。
"""

from __future__ import annotations

import time

from scenario_api import Issue, IssueLevel, RunContext, read_file_auto

from .validator import (
    evaluate,
    evaluate_issues,
    parse_doc_line,
)
from .template_reader import try_read


def _read_source(path: str) -> str:
    """模板优先读取：模板 Excel 转键值行；否则回退 read_file_auto。"""
    lines = try_read(path)
    if lines is not None:
        return "\n".join(lines)
    return read_file_auto(path)


def step_load_inputs(ctx: RunContext) -> None:
    """读多单证文件并归一化文本；记录溯源原文。"""
    raw = _read_source(ctx.inputs["source-file"])
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    ctx.outputs["raw"] = raw
    ctx.outputs["doc_lines"] = lines
    ctx.outputs["trace_check"] = {"source": raw, "items": []}
    if not lines:
        ctx.issues.append(Issue(IssueLevel.ERROR, "单证文件是空的"))
    return None


def step_parse_docs(ctx: RunContext) -> None:
    """解析单证行；无法解析的行计入待人工。给每条单证附行号与原文（定位用）。"""
    doc_lines = ctx.outputs.get("doc_lines", [])
    docs: list[dict] = []
    unresolved: list[str] = []
    for idx, line in enumerate(doc_lines):
        doc = parse_doc_line(line)
        if doc:
            doc["line_no"] = idx + 1
            doc["source"] = line
            docs.append(doc)
        else:
            unresolved.append(line)
    ctx.outputs["docs"] = docs
    ctx.outputs["unresolved"] = unresolved
    if unresolved:
        ctx.issues.append(
            Issue(IssueLevel.REVIEW,
                  f"{len(unresolved)} 行单证未能解析（可能为扫描件/格式不符），转人工核对")
        )
    return None


def step_evaluate(ctx: RunContext) -> None:
    """执行跨单证逐字段比对，把结论挂到 outputs。"""
    docs = ctx.outputs.get("docs", [])
    result = evaluate(docs)
    ctx.outputs["result"] = result
    ctx.outputs["summary"] = result["summary"]
    ctx.outputs["verdict"] = result["verdict"]
    ctx.issues.extend(evaluate_issues(result))

    # 溯源：进产物的关键条目 = 单证行原文（须在 source 里逐字可查）
    ctx.outputs["trace_check"]["items"] = list(ctx.outputs.get("doc_lines", []))
    return None


def step_render_report(ctx: RunContext) -> None:
    """渲染交叉核对报告到 output/ 目录，填入溯源条目与判定依据。"""
    today = time.strftime("%Y-%m-%d")
    result = ctx.outputs.get("result", {})
    summ = ctx.outputs.get("summary", {})
    verdict = ctx.outputs.get("verdict", "REVIEW")
    unresolved = ctx.outputs.get("unresolved", [])

    lines = [
        "# 单证交叉核对报告",
        "",
        f"- 日期：{today}",
        f"- 核对状态：**{verdict}**（仅表示跨单证一致，**不构成通关/放行结论**）",
        f"- 跨单证字段：共 {summ.get('total', 0)} 个 | 一致 {summ.get('match', 0)} | "
        f"不一致 {summ.get('conflict', 0)} | 口径不可比/无法判定 {summ.get('unknown', 0)}",
        "",
        "## 逐字段核对结果",
    ]
    for f in result.get("fields", []):
        lines.append(f"- **{f['fid']}**（{'/'.join(f['present_in'])}）→ {f['status']}")
        lines.append(f"  - {f['detail']}")
        lines.append(f"  - 原始值：{' | '.join(str(v) for v in f['values'])}")
        locs = "；".join(
            f"{loc['doc_type']}" + (f" 第{loc['line_no']}行" if loc.get("line_no") else "")
            for loc in f.get("locations", [])
        )
        lines.append(f"  - 定位：{locs}")

    if unresolved:
        lines += ["", "## 未解析行（转人工）", *[f"- {ln}" for ln in unresolved]]

    out_dir = ctx.runtime.output_dir()
    file_name = f"doc-crosscheck-{today}.md"
    (out_dir / file_name).write_text("\n".join(lines) + "\n", encoding="utf-8")
    ctx.outputs["report_file_name"] = file_name
    ctx.outputs["report_file"] = str(out_dir / file_name)

    ctx.outputs["explain"] = {
        "判定依据": (
            f"跨单证字段 {summ.get('total', 0)} 个：一致 {summ.get('match', 0)}，"
            f"不一致 {summ.get('conflict', 0)}，不可比 {summ.get('unknown', 0)}"
        ),
        "转人工原因": (
            "存在跨单证不一致/口径不可比字段" if verdict != "DONE" else "无",
        ),
    }
    return None
