"""
steps_presence.py —— 投标资料完整度（check-completeness 任务）处理步骤

与主任务 check-terms 同处一个场景宿主，步骤纪律一致：只往 ctx.outputs 写结果、
往 ctx.issues 记问题；溯源自检 load 声明 trace_check，render 把进产物的关键条目
填进 items；explain 只写事实与计数。

输入契约：source-file=标书目录/文件列表（文本层）；--set required-file=应然清单。
扫描件/图片行在喂入前由宿主转文本，残余未解析行命中 _SCAN_HINTS 时转人工。
"""

from __future__ import annotations

import time

from scenario_api import Issue, IssueLevel, RunContext, read_file_auto

from .validator_presence import (
    MISSING as P_MISSING,
    UNKNOWN as P_UNKNOWN,
    evaluate as evaluate_presence,
    evaluate_issues as presence_issues,
    parse_required_line,
)
from .template_reader import try_read


def _read_source(path: str, field_id: str) -> str:
    """模板优先读取：模板 Excel 转键值行；否则回退 read_file_auto。"""
    lines = try_read(path, field_id)
    if lines is not None:
        return "\n".join(lines)
    return read_file_auto(path)


def step_presence_load_inputs(ctx: RunContext) -> None:
    """读标书目录/文件列表并归一化文本；记录溯源原文。"""
    raw = _read_source(ctx.inputs["source-file"], "source-file")
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    ctx.outputs["raw"] = raw
    ctx.outputs["toc_lines"] = lines
    ctx.outputs["trace_check"] = {"source": raw, "items": []}
    if not lines:
        ctx.issues.append(Issue(IssueLevel.ERROR, "标书目录/文件列表是空的"))
    return None


def step_presence_parse_required(ctx: RunContext) -> None:
    """解析应然清单；无法解析的行计入待人工。"""
    req_raw = _read_source(ctx.inputs["required-file"], "required-file")
    req_lines = [ln.strip() for ln in req_raw.splitlines() if ln.strip()]
    required_list: list[dict] = []
    unresolved: list[str] = []
    for line in req_lines:
        item = parse_required_line(line)
        if item:
            required_list.append(item)
        else:
            unresolved.append(line)
    ctx.outputs["required_list"] = required_list
    ctx.outputs["required_lines"] = req_lines
    ctx.outputs["unresolved"] = unresolved
    if unresolved:
        ctx.issues.append(
            Issue(IssueLevel.REVIEW,
                  f"{len(unresolved)} 行应然清单未能解析（可能为扫描件/格式不符），转人工核对")
        )
    return None


def step_presence_evaluate(ctx: RunContext) -> None:
    """执行逐项存在性核对，把结论挂到 outputs。"""
    toc_lines = ctx.outputs.get("toc_lines", [])
    required_list = ctx.outputs.get("required_list", [])
    result = evaluate_presence(toc_lines, required_list)
    ctx.outputs["result"] = result
    ctx.outputs["summary"] = result["summary"]
    ctx.outputs["verdict"] = result["verdict"]
    ctx.issues.extend(presence_issues(result))

    # 溯源：进产物的关键条目 = 标书目录命中行原文（须在 source 里逐字可查）
    items = []
    for it in result["items"]:
        for h in it["hits"]:
            items.append(h["excerpt"])
    ctx.outputs["trace_check"]["items"] = items
    return None


def step_presence_render_report(ctx: RunContext) -> None:
    """渲染完整度核对报告到 output/ 目录，填入溯源条目与判定依据。"""
    today = time.strftime("%Y-%m-%d")
    result = ctx.outputs.get("result", {})
    summ = ctx.outputs.get("summary", {})
    verdict = ctx.outputs.get("verdict", "REVIEW")
    unresolved = ctx.outputs.get("unresolved", [])

    lines = [
        "# 封标前完整度与漏项检阅报告",
        "",
        f"- 日期：{today}",
        f"- 核对状态：**{verdict}**（仅核对存在性，不核数字一致性/签章位置）",
        f"- 应然项：共 {summ.get('total', 0)} 项 | 已定位 {summ.get('present', 0)} | "
        f"必备缺失 {summ.get('missing', 0)} | 可缺 {summ.get('optional_missing', 0)} | "
        f"无法判定 {summ.get('unknown', 0)}",
        "",
        "## 逐项核对结果",
    ]
    for it in result.get("items", []):
        st = it["status"]
        tag = "必备" if it["required"] else "可缺"
        lines.append(f"- **{it['name']}**（{tag}）→ {st}")
        if it["hits"]:
            for h in it["hits"]:
                lines.append(f"  - 第 {h['line_no']} 行：{h['excerpt']}")
        if st in (P_MISSING, P_UNKNOWN):
            lines.append("  - 待人工确认（漏装/改名/解析失败）")

    if unresolved:
        lines += ["", "## 未解析行（转人工）", *[f"- {ln}" for ln in unresolved]]

    out_dir = ctx.runtime.output_dir()
    file_name = f"bid-completeness-{today}.md"
    (out_dir / file_name).write_text("\n".join(lines) + "\n", encoding="utf-8")
    ctx.outputs["report_file_name"] = file_name
    ctx.outputs["report_file"] = str(out_dir / file_name)

    ctx.outputs["explain"] = {
        "判定依据": (
            f"应然项 {summ.get('total', 0)} 项：已定位 {summ.get('present', 0)}，"
            f"必备缺失 {summ.get('missing', 0)}，可缺 {summ.get('optional_missing', 0)}，"
            f"无法判定 {summ.get('unknown', 0)}"
        ),
        "转人工原因": (
            "存在必备项缺失/无法判定项" if verdict != "DONE" else "无",
        ),
    }
    return None