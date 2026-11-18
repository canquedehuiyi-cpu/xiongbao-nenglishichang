"""steps.py —— 简历制作的适配层（验据逻辑在 _core.py，阈值在其顶部常量）

混合架构的引擎侧：宿主 LLM 起草草稿（SKILL.md 指令保证结构约定），
本引擎逐条验据——锚点（日期/数字）全中且实义覆盖率达标才进终稿，
无据条目 FLAG 打回（不删，列给用户补素材后重跑）。

产物：终稿 Markdown（仅过验条目）+ 报告，各落独立时间戳子目录。
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import yaml
from scenario_api import Issue, IssueLevel, RunContext, read_text_auto

from . import _core


def _rules(ctx: RunContext) -> dict[str, Any]:
    doc = yaml.safe_load(ctx.runtime.read_template("rules.yaml")) or {}
    return {
        "title": str(doc.get("title", "简历制作报告")),
        "verify_sections": [str(x) for x in doc.get("verify_sections") or []],
        "degree": [str(x) for x in doc.get("jd_degree_words") or []],
        "cert": [str(x) for x in doc.get("jd_cert_words") or []],
        "tool": [str(x) for x in doc.get("jd_tool_words") or []],
        "footer": str(doc.get("footer", "")).strip(),
    }


def step_parse_validate(ctx: RunContext) -> None:
    """读三个输入：草稿/素材/JD；任一缺失或为空记 ERROR。"""
    draft_path = str(ctx.inputs.get("draft-file", "") or "")
    material_path = str(ctx.inputs.get("material-file", "") or "")
    jd_text = str(ctx.inputs.get("jd-text", "") or "")
    if not draft_path or not material_path or not jd_text.strip():
        ctx.issues.append(
            Issue(IssueLevel.ERROR, "输入不全：需要草稿文件(draft-file)、素材文件(material-file)、JD 文本(jd-text)三者齐备")
        )
        return
    draft_lines = read_text_auto(Path(draft_path)).splitlines()
    material = _core.normalize_for_match(read_text_auto(Path(material_path)))
    if not any(ln.strip() for ln in draft_lines):
        ctx.issues.append(Issue(IssueLevel.ERROR, "草稿是空的：没有可验据的内容"))
        return
    if not material:
        ctx.issues.append(Issue(IssueLevel.ERROR, "素材是空的：没有验据基准"))
        return
    ctx.outputs["draft_lines"] = draft_lines
    ctx.outputs["material_norm"] = material
    ctx.outputs["jd_text"] = jd_text


def step_judge(ctx: RunContext) -> None:
    """逐条验据 → 终稿(仅过验) → JD 覆盖 → 时间线。"""
    r = _rules(ctx)
    draft_lines: list[str] = ctx.outputs.get("draft_lines", [])
    material: str = ctx.outputs.get("material_norm", "")
    jd_text: str = ctx.outputs.get("jd_text", "")

    entries = _core.parse_draft(draft_lines, r["verify_sections"])
    if not entries:
        ctx.outputs["verdict"] = "UNKNOWN"
        ctx.issues.append(
            Issue(
                IssueLevel.REVIEW,
                f"草稿里认不出任何待验节（{'/'.join(r['verify_sections'])}）——结构不符约定，"
                "判不了，不硬判；请按 SKILL.md 的草稿结构重排后重跑",
            )
        )
        return

    results = []
    for e in entries:
        v = _core.verify_line(e["text"], material)
        results.append({**e, **v, "advice": _flag_advice(e["text"], v, material)})
    flagged = [x for x in results if x["status"] == "FLAG"]
    passed = [x for x in results if x["status"] == "PASS"]
    ctx.outputs["results"] = results
    ctx.outputs["flagged"] = flagged

    final_lines = [
        ln for no, ln in enumerate(draft_lines, start=1)
        if no not in {x["line_no"] for x in flagged}
    ]
    ctx.outputs["final_lines"] = final_lines
    final_norm = _core.normalize_for_match("\n".join(final_lines))

    timeline = _core.check_timeline(_core.parse_timeline(passed))
    ctx.outputs["timeline_issues"] = timeline

    reqs = _core.extract_jd_requirements(jd_text, r["degree"], r["cert"], r["tool"])
    coverage = []
    for q in reqs:
        hit = q["word"] in final_norm or (
            q["kind"] == "年限" and any(v in final_norm for v in _year_variants(q["word"]))
        )
        coverage.append({**q, "status": "有" if hit else "未提及"})
    ctx.outputs["jd_coverage"] = coverage

    flagged_n = len(flagged)
    ctx.outputs["summary"] = {
        "entries": len(results),
        "verified": len(passed),
        "flagged": flagged_n,
        "jd_requirements": len(coverage),
        "jd_missing": sum(1 for c in coverage if c["status"] == "未提及"),
        "timeline_issues": len(timeline),
    }
    if flagged_n:
        ctx.issues.append(
            Issue(
                IssueLevel.REVIEW,
                f"{flagged_n} 条经历/技能在素材里找不到依据，已打回不进终稿（逐条见报告）——"
                "不是写得不好，是无据；补进素材后重跑即可进终稿",
            )
        )
    if timeline:
        ctx.issues.append(
            Issue(IssueLevel.WARN, f"时间线 {len(timeline)} 处断档/重叠（阈值 { _core.GAP_MONTHS} 个月）——逐条见报告，请本人能说清")
        )
    ctx.outputs["verdict"] = "WARNING" if (flagged_n or timeline) else "PASS"


def _flag_advice(text: str, verdict: dict, material_norm: str) -> str:
    """打回条目的处置建议(0.3.0)——只按可数事实分流,不评好坏。

    - 缺日期/数字锚点 → 核对写法或补真实数据;
    - 覆盖率 ≥ 0.5 的混合行(真假掺杂) → 拆行:有据部分先留,无据部分补素材;
    - 其余 → 素材无此条依据,补素材重跑或从草稿删除。
    """
    if verdict["missing_anchors"]:
        return "日期/数字在素材里找不到——核对写法（五十万↔50万 已自动归一），属实则补素材后重跑"
    if verdict["coverage"] >= 0.5:
        return "混合行：有据部分可先拆行保留，无据部分补进素材后再加回"
    return "素材里没有这条经历的依据——补素材后重跑，或从草稿删掉"


def _year_variants(word: str) -> list[str]:
    """「5年」的等值写法:5年/五年/5 年(规范化后空格已去)。"""
    n = word.replace("年", "")
    cn = {"0": "零", "1": "一", "2": "二", "3": "三", "4": "四", "5": "五", "6": "六", "7": "七", "8": "八", "9": "九"}
    return [word, f"{n} 年", "".join(cn.get(c, c) for c in n) + "年"]


def step_render(ctx: RunContext) -> None:
    """终稿 + 报告落独立时间戳子目录。"""
    rt = ctx.runtime
    r = _rules(ctx)
    s = ctx.outputs.get("summary", {})
    ts = time.strftime("%Y%m%d-%H%M%S")
    run_dir = rt.output_dir() / ts
    n = 1
    while run_dir.exists():
        run_dir = rt.output_dir() / f"{ts}-{n}"
        n += 1
    run_dir.mkdir(parents=True, exist_ok=True)

    final = run_dir / "resume_final.md"
    final.write_text("\n".join(ctx.outputs.get("final_lines", [])), encoding="utf-8")
    ctx.outputs["resume_file"] = str(final)

    # DOCX 终稿（0.3.0）：# 标题 → Heading，- 行 → 项目符号，其余普通段落
    import docx as _docx

    doc = _docx.Document()
    for raw in ctx.outputs.get("final_lines", []):
        ln = raw.rstrip()
        if not ln.strip():
            continue
        if ln.startswith("#"):
            level = min(len(ln) - len(ln.lstrip("#")), 4)
            doc.add_heading(ln.lstrip("#").strip(), level=level)
        elif ln.lstrip().startswith(("- ", "* ")):
            doc.add_paragraph(ln.lstrip()[2:].strip(), style="List Bullet")
        else:
            doc.add_paragraph(ln.strip())
    docx_path = run_dir / "resume_final.docx"
    doc.save(str(docx_path))
    ctx.outputs["resume_docx"] = str(docx_path)

    lines = [
        f"# {r['title']}",
        "",
        f"生成时间：{time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 总判定",
        "",
        f"- **{ctx.outputs.get('verdict', 'UNKNOWN')}** —— 条目 {s.get('entries', 0)}："
        f"过验 {s.get('verified', 0)}、打回 {s.get('flagged', 0)}；"
        f"JD 硬性要求 {s.get('jd_requirements', 0)} 条（未提及 {s.get('jd_missing', 0)}）；"
        f"时间线问题 {s.get('timeline_issues', 0)} 处",
        f"- 终稿：`resume_final.md`（仅含过验条目——素材里没有的，它不写）",
        "",
    ]
    flagged = ctx.outputs.get("flagged") or []
    if flagged:
        lines += ["## 打回清单（无据，未进终稿）", "", "| 行号 | 节 | 缺的锚点 | 缺的实义词 | 建议 | 原文 |", "|---|---|---|---|---|---|"]
        for f in flagged:
            lines.append(
                f"| {f['line_no']} | {f['section']} | {'、'.join(f['missing_anchors']) or '—'} | "
                f"{'、'.join(f['missing_tokens'][:5]) or '—'} | {f['advice']} | {f['text'][:40]} |"
            )
        lines += ["", "补素材后重跑即可——引擎不替你编。", ""]
    coverage = ctx.outputs.get("jd_coverage") or []
    if coverage:
        lines += ["## JD 覆盖表", "", "| 要求 | 类型 | 状态 |", "|---|---|---|"]
        for c in coverage:
            lines.append(f"| {c['word']} | {c['kind']} | {c['status']} |")
        lines += ["", "「未提及」= 终稿里没找到——不是判你不满足，请自查素材是否漏写。", ""]
    tl = ctx.outputs.get("timeline_issues") or []
    if tl:
        lines += ["## 时间线体检", ""]
        lines += [f"- {t['type']}：{t['detail']}（草稿行 {t['lines']}）" for t in tl]
        lines.append("")
    lines += [
        "## 口径（如实）",
        "",
        f"- 过验标准：日期/数字锚点全部在素材出现（含写法换算）且实义词覆盖率 ≥ {_core.TOKEN_COVERAGE:.0%}",
        "- 中文数字自动归一（五十万↔50万、四成↔40%、百分之三十↔30%），写法差异不误打回",
        "- 「基本信息」「自我评价」节不核（非事实主张节）；验据节清单在 rules.yaml 可改",
    ]
    if r["footer"]:
        lines += ["", "---", "", r["footer"]]
    out = run_dir / "resume_build_report.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    ctx.outputs["report_file"] = str(out)
