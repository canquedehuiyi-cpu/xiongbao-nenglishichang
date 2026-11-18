"""
steps.py —— 废标条款与硬性资格打标 处理步骤

步骤纪律：只往 ctx.outputs 写结果、往 ctx.issues 记问题；
溯源自检：load 步骤声明 trace_check，render 把进产物的关键条目填进 items；
explain：判定依据写进 outputs["explain"]（只写事实与计数，不泄阈值）。

输入契约：source-file=招标文件文本层；--set checklist-file=条款检查清单；
--set materials-file=我方材料清单（可选）。扫描件/图片行在喂入前由宿主转文本，
残余未解析行命中 _SCAN_HINTS 时转人工，不静默放行。
"""

from __future__ import annotations

import time

from scenario_api import Issue, IssueLevel, RunContext, read_file_auto

from .validator import (
    evaluate,
    evaluate_issues,
    parse_checklist_line,
    parse_material_line,
)
from .template_reader import try_read


def _read_source(path: str, field_id: str) -> str:
    """模板优先读取：模板 Excel 转键值行；否则回退 read_file_auto。"""
    lines = try_read(path, field_id)
    if lines is not None:
        return "\n".join(lines)
    return read_file_auto(path)


def step_load_inputs(ctx: RunContext) -> None:
    """读招标文件并归一化文本；记录溯源原文。"""
    raw = _read_source(ctx.inputs["source-file"], "source-file")
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    ctx.outputs["raw"] = raw
    ctx.outputs["tender_lines"] = lines
    ctx.outputs["trace_check"] = {"source": raw, "items": []}
    if not lines:
        ctx.issues.append(Issue(IssueLevel.ERROR, "招标文件是空的"))
    return None


def step_parse_lists(ctx: RunContext) -> None:
    """解析条款检查清单与材料清单；无法解析的行计入待人工。"""
    checklist_raw = _read_source(ctx.inputs["checklist-file"], "checklist-file")
    checklist_lines = [ln.strip() for ln in checklist_raw.splitlines() if ln.strip()]
    checklist: list[dict] = []
    cl_unresolved: list[str] = []
    for line in checklist_lines:
        item = parse_checklist_line(line)
        if item:
            checklist.append(item)
        else:
            cl_unresolved.append(line)

    materials: list[dict] = []
    mt_unresolved: list[str] = []
    if ctx.inputs.get("materials-file"):
        mat_raw = _read_source(ctx.inputs["materials-file"], "materials-file")
        mat_lines = [ln.strip() for ln in mat_raw.splitlines() if ln.strip()]
        for line in mat_lines:
            m = parse_material_line(line)
            if m:
                materials.append(m)
            else:
                mt_unresolved.append(line)
    else:
        mat_lines = []

    ctx.outputs["checklist"] = checklist
    ctx.outputs["checklist_lines"] = checklist_lines
    ctx.outputs["materials"] = materials
    ctx.outputs["materials_lines"] = mat_lines
    ctx.outputs["unresolved"] = cl_unresolved + mt_unresolved

    if cl_unresolved:
        ctx.issues.append(
            Issue(IssueLevel.REVIEW,
                  f"{len(cl_unresolved)} 行检查清单未能解析（可能为扫描件/格式不符），转人工核对")
        )
    if mt_unresolved:
        ctx.issues.append(
            Issue(IssueLevel.REVIEW,
                  f"{len(mt_unresolved)} 行材料清单未能解析（可能为扫描件/格式不符），转人工核对")
        )
    return None


def step_evaluate(ctx: RunContext) -> None:
    """执行条款定位 + 要件核对，并把结论挂到 outputs。"""
    tender_lines = ctx.outputs.get("tender_lines", [])
    checklist = ctx.outputs.get("checklist", [])
    materials = ctx.outputs.get("materials", [])
    result = evaluate(tender_lines, checklist, materials)
    ctx.outputs["result"] = result
    ctx.outputs["summary"] = result["summary"]
    ctx.outputs["verdict"] = result["verdict"]
    ctx.issues.extend(evaluate_issues(result))

    # 溯源：进产物的关键条目 = 招标文件命中行原文（须在 source 里逐字可查）
    items = []
    for t in result["terms"]:
        for h in t["hits"]:
            items.append(h["excerpt"])
    ctx.outputs["trace_check"]["items"] = items
    return None


def step_render_report(ctx: RunContext) -> None:
    """渲染打标报告到 output/ 目录，填入溯源条目与判定依据。"""
    today = time.strftime("%Y-%m-%d")
    result = ctx.outputs.get("result", {})
    summ = ctx.outputs.get("summary", {})
    verdict = ctx.outputs.get("verdict", "REVIEW")
    unresolved = ctx.outputs.get("unresolved", [])

    lines = [
        "# 废标条款与硬性资格打标报告",
        "",
        f"- 日期：{today}",
        f"- 核对状态：**{verdict}**（仅表示核对完成，**不构成可投标判断**）",
        f"- 条款：共 {summ.get('total', 0)} 条 | 定位并材料齐 {summ.get('located', 0)} | "
        f"材料缺 {summ.get('missing', 0)} | 未定位 {summ.get('not_found', 0)} | "
        f"无法判定 {summ.get('unknown', 0)}",
        "",
        "## 条款定位与要件核对",
    ]
    for t in result.get("terms", []):
        st = t["status"]
        lines.append(f"- **{t['name']}**（{t['category']}）→ {st}")
        if t["hits"]:
            for h in t["hits"]:
                lines.append(f"  - 第 {h['line_no']} 行：{h['excerpt']}")
        mc = t.get("material_check", {})
        if mc.get("required"):
            lines.append(f"  - 要求材料：{'、'.join(mc['required'])}")
            if mc.get("matched"):
                lines.append(f"  - 已命中：{'、'.join(mc['matched'])}")
            if mc.get("missing"):
                lines.append(f"  - 缺失：{'、'.join(mc['missing'])}")
        elif mc.get("unknown"):
            lines.append("  - 未提供材料清单，无法核对要求材料")

    if unresolved:
        lines += ["", "## 未解析行（转人工）", *[f"- {ln}" for ln in unresolved]]

    out_dir = ctx.runtime.output_dir()
    file_name = f"bid-terms-{today}.md"
    (out_dir / file_name).write_text("\n".join(lines) + "\n", encoding="utf-8")
    ctx.outputs["report_file_name"] = file_name
    ctx.outputs["report_file"] = str(out_dir / file_name)

    ctx.outputs["explain"] = {
        "判定依据": (
            f"条款 {summ.get('total', 0)} 条：定位 {summ.get('located', 0)}+"
            f"{summ.get('missing', 0)}+{summ.get('unknown', 0)}，"
            f"未定位 {summ.get('not_found', 0)} 条"
        ),
        "转人工原因": (
            "存在未定位/材料缺失/无法判定条款" if verdict != "DONE" else "无",
        ),
    }
    return None
