# -*- coding: utf-8 -*-
"""
distill_skeleton.py —— 单一大纲源渲染器（纯标准库·零第三方依赖）

保证「多格式同源」：蒸馏完成只产一份 canonical outline（内容模型），
六个格式生成器从【同一个 outline 对象】经确定性适配器渲染，
Agent 不得为每个格式单独重撰 outline —— 从结构上消灭 TXT 跑偏这类漂移。

canonical 内容模型（蒸馏产出统一结构）:
{
  "title":    "总标题",
  "subtitle": "副标题/口径（可选）",
  "date":     "2026-10-01",
  "source":   "由 蒸馏成技能Skill 蒸馏产出",
  "sources":  ["《甲材料》（文本直读）", ...],  # 多份来源（可选；决定页腾出不出「来源总览」）
  "sections": [
     {"heading": "一、章节名", "core": "本章一句话核心",
      "points": ["要点1","要点2",...],          # 短要点 → 项目符号列表
      "paragraphs": ["成段正文…","成段正文…"]},   # 成段正文 → 独立段落（讲稿体/口播体的载体）
     ...
  ]
}

两种正文容器并存、职责不同、可同节同时用：
  - points     —— 短要点，渲染为项目符号列表（适合速览、卡片、清单）
  - paragraphs —— 成段的话，渲染为不加符号的独立段落（**讲稿体 / 口播体的唯一承载形态**）
文体层要求「每段一个落点」时，正文必须走 paragraphs；折进 points 会被逐段渲染成
项目符号，讲稿念出来是一串短横。两者缺省皆可省，缺一即该节少一块内容。

各生成器 outline schema 不同（md/txt/pdf 用 heading/core/body+paragraphs，docx 用 h/core/items+paras，
ppt 用 chapters+typed sections，xlsx 用 heading/core/items）；本模块做确定性映射，
不引入任何 LLM/随机，保证六个格式内容严格一致。

用法:
  from distill_skeleton import save_outline, load_outline, render_formats
  save_outline(outline, "runs/<任务>/.work/outline.json")  # 落盘唯一真相源（中间件归 .work/）
  produced = render_formats(outline, ["md","txt","ppt","pdf","docx","xlsx"], "out/")
"""
import json, os, re, sys

CANONICAL_KEYS = ("title", "subtitle", "date", "source", "sources", "sections")


def save_outline(outline, path):
    """落盘 canonical outline（UTF-8，稳定格式）。"""
    d = os.path.dirname(os.path.abspath(path))
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(outline, f, ensure_ascii=False, indent=2)
    return path


def load_outline(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ---- 确定性适配器（canonical -> 各生成器 outline）----
def _adapt_md(outline):
    return {
        "title": outline.get("title", ""),
        "subtitle": outline.get("subtitle", ""),
        "date": outline.get("date", ""),
        "source": outline.get("source", "由 蒸馏成技能Skill 蒸馏产出"),
        "sources": list(outline.get("sources", []) or []),
        "sections": [
            {"heading": s.get("heading", ""), "core": s.get("core", ""),
             "body": list(s.get("points", [])),
             "paragraphs": list(s.get("paragraphs", []))}
            for s in outline.get("sections", [])
        ],
    }


def _adapt_pdf(outline):
    return _adapt_md(outline)   # pdf 与 md/txt 同 schema


def _adapt_docx(outline):
    return {
        "title": outline.get("title", ""),
        "subtitle": outline.get("subtitle", ""),
        "source": outline.get("source", "由 蒸馏成技能Skill 蒸馏产出"),
        "sources": list(outline.get("sources", []) or []),
        "sections": [
            {"h": s.get("heading", ""), "core": s.get("core", ""),
             "items": list(s.get("points", [])),
             "paras": list(s.get("paragraphs", []))}
            for s in outline.get("sections", [])
        ],
    }


def _sheet_name(heading, used):
    """heading -> 合法且唯一的工作表名（去 Excel 禁用字符、≤31 字、重名加后缀）。"""
    name = re.sub(r"[\[\]:*?/\\]", "", str(heading or "")).strip() or "数据"
    name = name[:31]
    base = name
    i = 2
    while name in used:
        suf = "_%d" % i
        name = base[:31 - len(suf)] + suf
        i += 1
    used.add(name)
    return name


def _adapt_xlsx(outline):
    """canonical -> xlsx sheets 结构（build_xlsx 与 build_xlsx_chart 共同消费的 schema）。

    两代 xlsx 生成器读的是 outline["sheets"]（每项 {name, section_title,
    headers, rows, col_fmts}）；此处把 sections 逐节映射为工作表，保证 Excel 格式有内容。
    """
    used = set()
    sheets = []
    for s in outline.get("sections", []):
        heading = s.get("heading", "")
        rows = []
        core = s.get("core", "")
        if core:
            rows.append(["核心", core])
        for i, p in enumerate(s.get("points", []), 1):
            rows.append(["要点%d" % i, p])
        if not rows:
            rows.append(["说明", ""])
        sheets.append({
            "name": _sheet_name(heading, used),
            "section_title": heading,
            "headers": ["项目", "内容"],
            "rows": rows,
            "col_fmts": ["text", "text"],
        })
    if not sheets:
        sheets = [{"name": "数据", "section_title": "", "headers": ["项目", "内容"],
                   "rows": [["说明", ""]], "col_fmts": ["text", "text"]}]
    return {
        "title": outline.get("title", ""),
        "subtitle": outline.get("subtitle", ""),
        "date": outline.get("date", ""),
        "source": outline.get("source", "由 蒸馏成技能Skill 蒸馏产出"),
        "sources": list(outline.get("sources", []) or []),
        "sheets": sheets,
    }


def _adapt_ppt(outline):
    secs_in = outline.get("sections", [])
    chapters = [(str(i + 1), s.get("heading", ""), s.get("core", ""))
                for i, s in enumerate(secs_in)]
    secs = []
    for i, s in enumerate(secs_in, 1):
        secs.append({"type": "divider", "cur": i, "num": str(i),
                     "title": s.get("heading", ""), "lead": s.get("core", "")})
        pts = s.get("points", [])
        if pts:
            secs.append({"type": "cards", "title": s.get("heading", ""),
                         "items": [(p, []) for p in pts]})
    return {
        "title": outline.get("title", ""),
        "subtitle": outline.get("subtitle", ""),
        "attr": outline.get("source", "由 蒸馏成技能Skill 蒸馏产出"),
        "sources": list(outline.get("sources", []) or []),
        "chapters": chapters,
        "sections": secs,
        "closing": {"title": "谢谢", "points": ["由 蒸馏成技能Skill 蒸馏产出"]},
    }


def render_formats(outline, formats, out_dir, mode=None, palette=None,
                   font=None, scale=None, number=None, font_path=None):
    """从同一 canonical outline 渲染多个格式，返回 (produced, failed)。

    produced: 成功产物路径列表
    failed:   [{fmt, error, path}] 失败项（单格式失败不影响其余，对齐「单格式失败不影响其余」铁律）
    formats 取值: md / txt / ppt / pdf / docx / xlsx / xlsx_chart
    """
    d = os.path.dirname(os.path.abspath(__file__))
    if d not in sys.path:
        sys.path.insert(0, d)
    os.makedirs(out_dir, exist_ok=True)
    base_tk = dict(mode=mode, palette=palette, font=font, scale=scale, number=number)
    produced = []
    failed = []
    for fmt in formats:
        fmt = (fmt or "").lower()
        try:
            if fmt in ("md", "markdown"):
                from build_md_standard import build_md
                o = _adapt_md(outline)
                p = os.path.join(out_dir, "outline.md")
                build_md(o, p, **base_tk); produced.append(p)
            elif fmt == "txt":
                from build_txt_standard import build_txt
                o = _adapt_md(outline)
                p = os.path.join(out_dir, "outline.txt")
                build_txt(o, p, **base_tk); produced.append(p)
            elif fmt in ("ppt", "pptx"):
                from build_ppt_standard import render_outline as rppt
                o = _adapt_ppt(outline)
                p = os.path.join(out_dir, "outline.pptx")
                rppt(o, p, mode=mode, palette=palette, font=font, scale=scale)
                produced.append(p)
            elif fmt == "pdf":
                from build_pdf_standard import build_pdf
                o = _adapt_pdf(outline)
                p = os.path.join(out_dir, "outline.pdf")
                build_pdf(o, p, font_path=font_path, **base_tk); produced.append(p)
            elif fmt in ("docx", "word"):
                from build_docx_standard import render_outline as rdocx
                o = _adapt_docx(outline)
                p = os.path.join(out_dir, "outline.docx")
                rdocx(o, p, **base_tk); produced.append(p)
            elif fmt in ("xlsx", "excel"):
                from build_xlsx_standard import build_xlsx
                o = _adapt_xlsx(outline)
                p = os.path.join(out_dir, "outline.xlsx")
                build_xlsx(o, p, mode=mode, palette=palette,
                           font=font, scale=scale); produced.append(p)
            elif fmt in ("xlsx_chart", "excel_chart"):
                from build_xlsx_chart_standard import build_xlsx_chart
                o = _adapt_xlsx(outline)
                p = os.path.join(out_dir, "outline_chart.xlsx")
                build_xlsx_chart(o, p, mode=mode, palette=palette,
                                 font=font, scale=scale); produced.append(p)
            else:
                failed.append({"fmt": fmt, "error": "未知格式", "path": None})
        except Exception as e:
            failed.append({"fmt": fmt, "error": "%s: %s" % (type(e).__name__, e),
                           "path": None})
    return produced, failed


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] != "--self-test":
        sys.stderr.write("用法: python distill_skeleton.py --self-test\n")
        sys.exit(2)
    # 自测：用 demo canonical 渲染多格式，断言可产出 + 模块内容真写入
    import tempfile
    import zipfile
    demo = {
        "title": "示范大纲",
        "subtitle": "单一来源验证",
        "date": "2026-10-01",
        "source": "由 蒸馏成技能Skill 蒸馏产出",
        "sources": ["《甲材料》（文本直读）", "《乙材料》（PDF 文本层）"],
        "sections": [
            {"heading": "一、模块甲", "core": "甲的核心", "points": ["要点1", "要点2"]},
            {"heading": "二、模块乙", "core": "乙的核心", "points": ["要点A", "要点B"]},
        ],
    }
    td = tempfile.mkdtemp()
    produced, failed = render_formats(
        demo, ["md", "txt", "docx", "ppt", "xlsx", "xlsx_chart"], td)
    print("self-test 产出:", [os.path.basename(p) for p in produced], "失败:", failed)
    for p in produced:
        assert os.path.getsize(p) > 0, "空文件: %s" % p
    assert not failed, "有格式渲染失败: %s" % failed

    # 文本类：模块标题必须出现
    for p in produced:
        if p.endswith((".md", ".txt")):
            t = open(p, encoding="utf-8").read()
            for s in demo["sections"]:
                assert s["heading"] in t, "文本产物缺模块: %s -> %s" % (s["heading"], p)

    # 表格类：模块标题必须真写入工作表
    for p in produced:
        if p.endswith(".xlsx"):
            z = zipfile.ZipFile(p)
            blob = b"".join(z.read(n) for n in z.namelist() if n.endswith(".xml"))
            for s in demo["sections"]:
                assert s["heading"].encode("utf-8") in blob, \
                    "xlsx 未写入模块内容: %s -> %s" % (s["heading"], p)
            assert "\uff08\u7a7a\uff09".encode("utf-8") not in blob, \
                "xlsx 退回内置空表骨架: %s" % p
    # 来源总览必须穿过适配器进入产物 —— 防「适配器丢 sources」这类整条链路静默断开
    import constants as _C
    _ov = _C.SOURCE_OVERVIEW_PREFIX
    for p in produced:
        if p.endswith((".md", ".txt")):
            t = open(p, encoding="utf-8").read()
            assert _ov in t, "文本产物缺来源总览（适配器可能丢了 sources）: %s" % p
        elif p.endswith((".docx", ".pptx", ".xlsx")):
            z = zipfile.ZipFile(p)
            blob = b"".join(z.read(n) for n in z.namelist() if n.endswith(".xml"))
            assert _ov.encode("utf-8") in blob, "二进制产物缺来源总览（适配器可能丢了 sources）: %s" % p
    save_outline(demo, os.path.join(td, "outline.json"))
    print("self-test PASS（含来源总览透传断言）")
