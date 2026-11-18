# -*- coding: utf-8 -*-
"""
build_docx_standard.py —— 蒸馏成技能Skill · B/C 模式 Word(DOCX) 标准版「可执行生成器」
================================================================================
纯标准库（zipfile + 手写 OOXML）生成符合引擎「B/C 模式标准件规格」的 .docx。
不依赖 python-docx / python-pptx，任何托管环境都能跑；各平台 Agent 直接调用本脚本，
不要再手搓 docx XML（手搓必出失控产物：逐段/逐标题插分页、内容复制、字号乱）。

锁死项（与 SKILL.md B/C 标准件规格一致）：
  - A4 页面 11906×16838，四边 1″(1440) 页边距
  - 固定样式：标题1(#16335B,16pt,粗) / 标题2(#2E6E9E,13pt,粗) / 正文(12pt) / 要点列表(• 前缀)
  - 微软雅黑 + 内置琥珀金蓝令牌
  - 顶部一行溯源落款 + 文末落款段
  - 【严禁逐段落/逐标题插分页符】——防失控分页；仅在 outline 某节显式 section_break=True 时
    才在该一级标题前插一个分页，默认内容连续流排。
设计令牌与 build_ppt_standard.py 同源。
================================================================================
"""
import zipfile, os, json, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import design_tokens
import constants

W_NS   = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

# 默认令牌（与既有默认值一致，不回归）；render_outline 会按所选模式覆盖这些全局
_TOK0 = design_tokens.resolve(mode=design_tokens.DEFAULT_MODE, fmt="docx")
FONT   = _TOK0["font_office"]
MAIN   = _TOK0["palette"]["MAIN"]
AUX    = _TOK0["palette"]["AUX"]
BODY   = _TOK0["palette"]["BODY"]
ANNOT  = _TOK0["palette"]["ANNOT"]
BORDER = _TOK0["palette"]["BORDER"]
SCALE  = _TOK0["scale"]["docx"]   # 半磅单位：cover/h1/h2/h3/body/core/annot/page

def esc(t):
    return (t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))

def _rpr(size, bold=False, color=BODY):
    b = ' w:b="1"' if bold else ''
    return (f'<w:rPr><w:rFonts w:ascii="{FONT}" w:hAnsi="{FONT}" w:eastAsia="{FONT}"/>'
            f'<w:sz w:val="{size}"/><w:szCs w:val="{size}"/>'
            f'<w:color w:val="{color}"/></w:rPr>')

def para(text, size=24, bold=False, color=BODY, before=0, after=120,
         jc=None, indent_left=None, hanging=None, style=None):
    ppr = '<w:pPr>'
    if style:
        ppr += f'<w:pStyle w:val="{style}"/>'
    if jc:
        ppr += f'<w:jc w:val="{jc}"/>'
    if indent_left is not None:
        hg = f' w:hanging="{hanging}"' if hanging is not None else ''
        ppr += f'<w:ind w:left="{indent_left}"{hg}/>'
    ppr += f'<w:spacing w:before="{before}" w:after="{after}"/>'
    ppr += '</w:pPr>'
    run = f'<w:r>{_rpr(size, bold, color)}<w:t xml:space="preserve">{esc(text)}</w:t></w:r>'
    return f'<w:p>{ppr}{run}</w:p>'

def bullet(text, size=24, color=BODY):
    return para("• " + text, size=size, color=color,
                indent_left=420, hanging=280, after=80)


def table(headers, rows, header_fill=MAIN, body_color=BODY):
    """渲染 Word 表格：表头深蓝底白字，正文深灰，细边框"""
    tbl_pr = ('<w:tblPr><w:tblW w:w="5000" w:type="pct"/>'
              '<w:tblBorders><w:top w:val="single" w:sz="4" w:space="0" w:color="%s"/>'
              '<w:left w:val="single" w:sz="4" w:space="0" w:color="%s"/>'
              '<w:bottom w:val="single" w:sz="4" w:space="0" w:color="%s"/>'
              '<w:right w:val="single" w:sz="4" w:space="0" w:color="%s"/>'
              '<w:insideH w:val="single" w:sz="4" w:space="0" w:color="%s"/>'
              '<w:insideV w:val="single" w:sz="4" w:space="0" w:color="%s"/></w:tblBorders>'
              '<w:tblCellMar><w:top w:w="80" w:type="dxa"/>'
              '<w:left w:w="120" w:type="dxa"/>'
              '<w:bottom w:w="80" w:type="dxa"/>'
              '<w:right w:w="120" w:type="dxa"/></w:tblCellMar></w:tblPr>') % (
              BORDER, BORDER, BORDER, BORDER, BORDER, BORDER)
    tbl_grid = '<w:tblGrid>' + ''.join('<w:gridCol/>' for _ in headers) + '</w:tblGrid>'
    rows_xml = []
    hdr_cells = []
    for h in headers:
        hdr_cells.append(
            '<w:tc><w:tcPr><w:shd w:val="clear" w:color="auto" w:fill="%s"/>'
            '<w:vAlign w:val="center"/></w:tcPr><w:p><w:pPr><w:jc w:val="center"/></w:pPr>'
            '<w:r><w:rPr><w:rFonts w:ascii="%s" w:hAnsi="%s" w:eastAsia="%s"/>'
            '<w:b/><w:sz w:val="20"/><w:szCs w:val="20"/><w:color w:val="FFFFFF"/></w:rPr>'
            '<w:t xml:space="preserve">%s</w:t></w:r></w:p></w:tc>' % (header_fill, FONT, FONT, FONT, esc(h)))
    rows_xml.append('<w:tr>%s</w:tr>' % "".join(hdr_cells))
    for row in rows:
        cells = []
        for c, v in enumerate(row):
            cells.append(
                '<w:tc><w:tcPr><w:vAlign w:val="center"/></w:tcPr><w:p>'
                '<w:r><w:rPr><w:rFonts w:ascii="%s" w:hAnsi="%s" w:eastAsia="%s"/>'
                '<w:sz w:val="21"/><w:szCs w:val="21"/><w:color w:val="%s"/></w:rPr>'
                '<w:t xml:space="preserve">%s</w:t></w:r></w:p></w:tc>' % (FONT, FONT, FONT, body_color, esc(str(v))))
        while len(cells) < len(headers):
            cells.append(
                '<w:tc><w:tcPr><w:vAlign w:val="center"/></w:tcPr><w:p>'
                '<w:r><w:rPr><w:rFonts w:ascii="%s" w:hAnsi="%s" w:eastAsia="%s"/>'
                '<w:sz w:val="21"/><w:szCs w:val="21"/><w:color w:val="%s"/></w:rPr>'
                '<w:t xml:space="preserve"> </w:t></w:r></w:p></w:tc>' % (FONT, FONT, FONT, body_color))
        rows_xml.append('<w:tr>%s</w:tr>' % "".join(cells))
    return '<w:tbl>%s%s%s</w:tbl>' % (tbl_pr, tbl_grid, "".join(rows_xml))


def page_break():
    # 仅在 outline 显式 section_break=True 时调用
    return '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'

def render_outline(outline, out_path, mode=None, palette=None, font=None, scale=None, number=None):
    """入口：outline 为结构化大纲（与题材无关），驱动生成标准 .docx。
    可选 token 参数（前置设计令牌库）：
      mode=预设模式(biz/lean/report/warm/red/sky/teal/violet)，或自由组合
      palette=配色族 / font=字体族(hei/song/kai/deng) / scale=字号规格(standard/compact/report)
      number=序号系统(arabic/cn/circle/none·不填=保留原标题，向后兼容)
    不选则用默认 biz（与既有默认值一致）。
    """
    global FONT, MAIN, AUX, BODY, ANNOT, BORDER, SCALE
    tok = design_tokens.resolve(mode=mode, palette=palette, font=font, scale=scale, number=number, fmt="docx")
    FONT   = tok["font_office"]
    MAIN   = tok["palette"]["MAIN"]
    AUX    = tok["palette"]["AUX"]
    BODY   = tok["palette"]["BODY"]
    ANNOT  = tok["palette"]["ANNOT"]
    BORDER = tok["palette"]["BORDER"]
    SCALE  = tok["scale"]["docx"]
    num_fn = tok["number"] if number else None  # number 未显式指定→保留原标题（不回归）
    """入口：outline 为结构化大纲（与题材无关），驱动生成标准 .docx。
    outline = {
      "title": str, "subtitle": str(可选),
      "source": str(可选·顶部溯源落款),
      "footer": str(可选·文末落款, 缺省用标准落款),
      "sections": [
        {"h": 一级标题, "h2": 二级标题(可选), "core": 一句话核心(可选),
         "items": [要点...], "paras": [段落...], "section_break": True(可选·起新页)},
        ...
      ]
    }
    """
    body = []
    title = outline.get("title", "")
    subtitle = outline.get("subtitle", "")
    footer = outline.get("footer", constants.FOOTER)

    # 顶部一行溯源落款
    if outline.get("source"):
        body.append(para(outline["source"], size=SCALE["annot"], color=ANNOT, after=80))

    if title:
        body.append(para(title, size=SCALE["cover"], bold=True, color=MAIN, jc="center", after=120))
    if subtitle:
        body.append(para(subtitle, size=SCALE["h2"], color=AUX, jc="center", after=200))

    for i, sec in enumerate(outline.get("sections", []), 1):
        if sec.get("section_break"):
            body.append(page_break())
        h = design_tokens.number_heading(sec.get("h"), 1, i, 0, num_fn)
        if h:
            body.append(para(h, size=SCALE["h1"], bold=True, color=MAIN,
                             before=360, after=160, style="Heading1"))
        h2 = design_tokens.number_heading(sec.get("h2"), 2, 1, i, num_fn)
        if h2:
            body.append(para(h2, size=SCALE["h2"], bold=True, color=AUX,
                             before=200, after=120, style="Heading2"))
        core = sec.get("core")
        if core:
            body.append(para(core, size=SCALE["core"], bold=True, color=ANNOT, after=80))
        # 先成段正文、后要点列表 —— 与 md / txt / pdf 三家顺序对齐（跨格式同序）。
        for p in sec.get("paras", []):
            body.append(para(p, size=SCALE["body"], color=BODY, after=120))
        for it in sec.get("items", []):
            body.append(bullet(it, size=SCALE["body"], color=BODY))
        tbl = sec.get("table")
        if tbl:
            body.append(table(tbl.get("headers", []), tbl.get("rows", [])))

    # 文末落款段（溯源）+ 免责声明（合规）——两句两处，上下相邻、不合并
    body.append(para(footer, size=SCALE["annot"], color=ANNOT, before=240, after=0, jc="center"))
    ov = constants.sources_overview(outline.get("sources"))
    if ov:
        body.append(para(ov, size=SCALE["annot"], color=ANNOT, before=40, after=0, jc="center"))
    body.append(para(constants.disclaimer(outline.get("topic")),
                     size=SCALE["annot"], color=ANNOT, before=40, after=0, jc="center"))
    # 交付回执（闭环·反馈口）——紧随免责之后，三句三处、互不合并
    body.append(para(constants.receipt_line(outline.get("receipt_tags")),
                     size=SCALE["annot"], color=ANNOT, before=40, after=0, jc="center"))

    body_xml = "".join(body)
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        f'<w:document xmlns:w="{W_NS}"><w:body>{body_xml}'
        '<w:sectPr>'
        '<w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="1440" w:bottom="1440" w:left="1440" w:right="1440" '
        'w:header="720" w:footer="720" w:gutter="0"/>'
        '</w:sectPr></w:body></w:document>'
    )

    styles = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        f'<w:styles xmlns:w="{W_NS}">'
        '<w:docDefaults><w:rPrDefault><w:rPr>'
        f'<w:rFonts w:ascii="{FONT}" w:hAnsi="{FONT}" w:eastAsia="{FONT}"/>'
        f'<w:sz w:val="24"/><w:szCs w:val="24"/><w:color w:val="{BODY}"/>'
        '</w:rPr></w:rPrDefault></w:docDefaults>'
        '<w:style w:type="paragraph" w:default="1" w:styleId="Normal">'
        '<w:name w:val="Normal"/></w:style>'
        '<w:style w:type="paragraph" w:styleId="Heading1">'
        '<w:name w:val="heading 1"/><w:basedOn w:val="Normal"/>'
        '<w:pPr><w:outlineLvl w:val="0"/></w:pPr></w:style>'
        '<w:style w:type="paragraph" w:styleId="Heading2">'
        '<w:name w:val="heading 2"/><w:basedOn w:val="Normal"/>'
        '<w:pPr><w:outlineLvl w:val="1"/></w:pPr></w:style>'
        '</w:styles>'
    )

    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
        '</Types>'
    )

    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
        '</Relationships>'
    )

    doc_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
        '</Relationships>'
    )

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", root_rels)
        z.writestr("word/document.xml", document)
        z.writestr("word/styles.xml", styles)
        z.writestr("word/_rels/document.xml.rels", doc_rels)

    return out_path


def _self_test():
    """最小自测：渲染一次并断言**要点真写入**。走临时目录，不写 scripts/。"""
    import tempfile, zipfile
    demo = {
        "title": "自测文档",
        "subtitle": "自测副标题",
        "source": "由 蒸馏成技能Skill 蒸馏产出",
        "sections": [
            {"h": "一、甲模块", "core": "甲的核心句",
             "items": ["甲要点一", "甲要点二"],
             "paras": ["甲段落一"]},
        ],
    }
    p = os.path.join(tempfile.mkdtemp(), "self.docx")
    render_outline(demo, p)
    assert os.path.getsize(p) > 0, "产物为空: %s" % p
    z = zipfile.ZipFile(p)
    blob = b"".join(z.read(n) for n in z.namelist() if n.endswith(".xml"))
    for must in ("自测文档", "一、甲模块", "甲的核心句", "甲要点一", "甲要点二", "甲段落一",
                 constants.FOOTER, constants.DISCLAIMER_MAIN,
                 constants.RECEIPT_PREFIX, constants.RECEIPT_BOUND):
        assert must.encode("utf-8") in blob, "docx 未写入内容: %s" % must
    print("self-test PASS: %s (%d B)" % (os.path.basename(p), os.path.getsize(p)))


if __name__ == "__main__":
    import sys, argparse
    ap = argparse.ArgumentParser(description="生成 Word(DOCX) 标准版（前置设计令牌库）")
    ap.add_argument("outline", nargs="?", help="大纲 JSON 路径")
    ap.add_argument("out", nargs="?", help="输出 .docx 路径")
    ap.add_argument("--mode", help="模板模式: biz/lean/report/warm/red/sky/teal/violet")
    ap.add_argument("--palette", help="配色族: amber/red/sky/teal/warm/ink/violet")
    ap.add_argument("--font", help="字体族: hei/song/kai/deng")
    ap.add_argument("--scale", help="字号规格: standard/compact/report")
    ap.add_argument("--number", help="序号系统: arabic/cn/circle/none（不填=保留原标题）")
    ap.add_argument("--self-test", action="store_true",
                    help="最小自测：渲染一次并断言要点真写入（走临时目录）")
    args = ap.parse_args()
    if args.self_test:
        _self_test()
        raise SystemExit(0)
    if args.outline and args.out:
        with open(args.outline, "r", encoding="utf-8") as f:
            outline = json.load(f)
        render_outline(outline, args.out, mode=args.mode, palette=args.palette,
                       font=args.font, scale=args.scale, number=args.number)
        print("DOCX 已生成:", args.out, "| 模式:", args.mode or "biz(默认)",
              "| 序号:", args.number or "保留原标题")
    else:
        # 自检示例：用 SkillHub 内容生成一份标准 docx
        demo = {
            "title": "SkillHub 新功能精华萃取",
            "subtitle": "GitHub 一键导入 Skill · ClawHub 镜像 Skill 一键认领",
            "source": constants.FOOTER,
            "sections": [
                {"h": "一、本次更新解决的两个核心痛点",
                 "core": "一句话核心：把从 GitHub 搬 Skill 与认领 ClawHub 镜像，从手工变一键。",
                 "items": ["痛点一：GitHub 迁移流程繁琐（打 zip、手抄 slug/名称/版本号）",
                           "痛点二：ClawHub 镜像的 Skill 无法声明所有权、无法管理"],
                 "paras": ["三大新功能：绑定 GitHub / 一键批量导入 / 一键认领镜像。"]},
                {"h": "二、绑定 GitHub 账号——入场券",
                 "core": "一句话核心：绑定是所有导入与认领的前置门票。",
                 "items": ["入口：个人中心左侧栏底部 / 我的 Skills 顶部蓝色卡片",
                           "流程：标准 GitHub OAuth；结果：显示头像 + 已绑定绿标"]},
            ]
        }
        suffix = ("_%s" % (args.mode or "biz")) + ("_num%s" % args.number if args.number else "")
        import tempfile
        out = os.path.join(tempfile.mkdtemp(),
                           "SkillHub_精华萃取%s.docx" % suffix)
        render_outline(demo, out, mode=args.mode, palette=args.palette,
                       font=args.font, scale=args.scale, number=args.number)
        print("自检 DOCX 已生成:", out, "| 模式:", args.mode or "biz(默认)",
              "| 序号:", args.number or "保留原标题")
