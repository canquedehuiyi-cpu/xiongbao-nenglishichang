"""
steps.py —— 数据标准化 处理步骤

步骤纪律：只往 ctx.outputs 写结果、往 ctx.issues 记问题；
溯源自检：load 步骤声明 trace_check，render 把进产物的关键条目填进 items
（标准化产物是转换行，溯源条目取输入原文行，保证逐字可查）；
explain：把清洗依据写进 outputs["explain"]（只写识别事实与计数）。

输入契约：source-file=用户真实数据文件（Excel/CSV 表格优先；文本/PDF/Word
走文本层）；--set scenario=<snake> 指定目标场景键集。零 LLM、只吃文本层；
扫描件占位单元格拒绝转人工，不输出伪数据。
"""

from __future__ import annotations

import csv
import time
from pathlib import Path

from scenario_api import (
    Issue,
    IssueLevel,
    RunContext,
    file_kind,
    read_excel_rows,
    read_file_auto,
    write_excel_rows,
)

from .validator import SCENES, backfill_sheets, normalize_table, normalize_text


def _read_csv_rows(path: Path) -> list[list[str]]:
    """CSV 读为单元格二维表（utf-8-sig 优先，GBK 兜底，与 read_text_auto 一致）。"""
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "gbk"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = raw.decode("utf-8", errors="replace")
    return [row for row in csv.reader(text.splitlines())]


def step_load_inputs(ctx: RunContext) -> None:
    """读真实数据文件并判定输入类型（表格 / 文本层）；记录溯源原文。"""
    path = Path(ctx.inputs["source-file"])
    ctx.outputs["scenario"] = ctx.inputs.get("scenario", "")
    raw = read_file_auto(str(path))
    ctx.outputs["raw"] = raw
    ctx.outputs["trace_check"] = {"source": raw, "items": []}
    kind = file_kind(path)
    if kind == "excel":
        ctx.outputs["table_kind"] = "excel"
        ctx.outputs["table_rows"] = list(read_excel_rows(str(path)))
    elif path.suffix.lower() == ".csv":
        ctx.outputs["table_kind"] = "csv"
        ctx.outputs["table_rows"] = _read_csv_rows(path)
    else:
        ctx.outputs["table_kind"] = "text"
        ctx.outputs["text_lines"] = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    if not raw.strip():
        ctx.issues.append(Issue(IssueLevel.ERROR, "输入文件是空的"))
    return None


def step_normalize(ctx: RunContext) -> None:
    """按目标场景键集执行标准化：表格走列名识别，文本走原样清洗。"""
    snake = ctx.outputs.get("scenario", "")
    spec = SCENES.get(snake)
    if spec is None:
        ctx.issues.append(Issue(
            IssueLevel.ERROR,
            f"未知目标场景：{snake!r}（可选：{' / '.join(sorted(SCENES))}）",
        ))
        return None
    ctx.outputs["scene_name"] = spec.display
    if ctx.outputs.get("table_kind") == "text":
        result = normalize_text(ctx.outputs.get("text_lines", []), spec)
    else:
        result = normalize_table(ctx.outputs.get("table_rows", []), spec)
    # spec 对象仅 render 阶段内部使用，不落入 outputs（保持 JSON 可序列化）
    ctx.outputs["result"] = {k: v for k, v in result.items() if k not in ("tables", "scene")}
    ctx.outputs["lines"] = result["lines"]
    ctx.outputs["report"] = result["report"]
    report = result["report"]
    if report.get("转人工"):
        ctx.issues.append(Issue(
            IssueLevel.REVIEW,
            f"{len(report['转人工'])} 个单元格/行命中扫描件占位，已转人工清单",
        ))
    if report.get("未识别列") and report["未识别列"][0] != "（无，列名全部识别）":
        ctx.issues.append(Issue(
            IssueLevel.REVIEW,
            f"{len(report['未识别列'])} 列未识别：{'、'.join(report['未识别列'][:5])}",
        ))
    # 错误类问题（表头无法识别等）不在此登记：ERROR 会令引擎跳过后续
    # render 步骤，导致产物/verdict 缺失；统一由 render 步骤在产出报告后登记。
    return None


def step_render_report(ctx: RunContext) -> None:
    """写产物：标准键值行 txt + 回填模板 xlsx + 清洗报告 md；填溯源与依据。"""
    today = time.strftime("%Y-%m-%d")
    snake = ctx.outputs.get("scenario", "")
    result = ctx.outputs.get("result", {})
    spec = SCENES.get(snake)
    render_result = dict(result)  # 副本：tables/scene 仅渲染用，不回写 outputs
    if spec is not None:
        render_result["tables"] = spec.tables
        render_result["scene"] = spec
    lines = render_result.get("lines", [])
    report = render_result.get("report", {})
    scene_display = ctx.outputs.get("scene_name", snake)
    out_dir = ctx.runtime.output_dir()

    txt_name = f"{snake or 'data'}-normalized.txt"
    xlsx_name = f"{snake or 'data'}-normalized.xlsx"
    md_name = f"normalize-report-{today}.md"

    (out_dir / txt_name).write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    if snake:
        sheets = backfill_sheets(render_result)
        write_excel_rows(str(out_dir / xlsx_name), sheets)

    report_lines = _render_md(snake, scene_display, render_result)
    (out_dir / md_name).write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    ctx.outputs["txt_file"] = str(out_dir / txt_name)
    ctx.outputs["xlsx_file"] = str(out_dir / xlsx_name) if snake else None
    ctx.outputs["report_file"] = str(out_dir / md_name)

    verdict = "DONE"
    if report.get("转人工") or (report.get("未识别列") and report["未识别列"][0] != "（无，列名全部识别）"):
        verdict = "REVIEW"
    if report.get("错误"):
        verdict = "FAILED"
    ctx.outputs["verdict"] = verdict

    if report.get("错误"):
        ctx.issues.append(Issue(IssueLevel.ERROR, report["错误"][0]))

    # 溯源：进产物的关键条目 = 输入原文行（标准化产物由原文行转换而来，逐字可查）
    ctx.outputs["trace_check"]["items"] = [
        ln for ln in ctx.outputs.get("raw", "").splitlines() if ln.strip()
    ]
    ctx.outputs["explain"] = {
        "目标场景": scene_display,
        "输入类型": ctx.outputs.get("table_kind", ""),
        "标准化行数": len(lines),
        "识别表": _table_label(render_result),
        "列映射": {k: v for k, v in result.get("col_map", {}).items()},
        "未识别列": report.get("未识别列", []),
        "转人工": report.get("转人工", []),
    }
    return None


def _table_label(result: dict) -> str:
    ti = result.get("table_index")
    if ti is None:
        return "（原文表/未识别）"
    return result["tables"][ti].name


def _render_md(snake: str, scene_display: str, result: dict) -> list[str]:
    report = result.get("report", {})
    lines = [
        "# 数据标准化报告",
        "",
        f"- 日期：{time.strftime('%Y-%m-%d')}",
        f"- 目标场景：{scene_display}（{snake or '未指定'}）",
        f"- 输入类型：{result.get('table_kind', '')}",
        f"- 识别表：{_table_label(result)}",
        f"- 标准化行数：{len(result.get('lines', []))}",
        "",
        "## 列映射（输入列 -> 标准键）",
    ]
    col_map = result.get("col_map", {})
    if col_map:
        for std, src in col_map.items():
            lines.append(f"- {src} -> {std}")
    else:
        lines.append("- （未识别或原文表）")
    lines += ["", "## 清洗报告"]
    for section, entries in report.items():
        lines.append(f"- **{section}**：{len(entries)} 项")
        for e in entries:
            lines.append(f"  - {e}")
    lines += ["", "## 产物"]
    stem = snake or "data"
    lines.append(f"- `{stem}-normalized.txt`：标准键值行（可直接喂目标场景判定）")
    lines.append(f"- `{stem}-normalized.xlsx`：回填模板（表名/表头与场景模板一致）")
    return lines
