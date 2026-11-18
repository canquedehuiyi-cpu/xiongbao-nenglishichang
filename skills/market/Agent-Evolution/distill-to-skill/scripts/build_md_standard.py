# -*- coding: utf-8 -*-
"""
build_md_standard.py —— B/C 模式 Markdown 标准生成器（纯标准库·零第三方依赖）

把蒸馏产物输出为结构清晰、可直接复制到知识库/协作平台的 Markdown。

输入 outline（dict）：
{
  "title":   "总标题",
  "subtitle":"副标题（可选）",
  "date":    "2026-09-30",
  "source":  "由 蒸馏成技能Skill 蒸馏产出",   # 顶部溯源署名（可被材料署名覆盖）
  "sources": ["《甲材料》（文本直读）", ...],  # 可选·多份材料时页脚出「来源总览」
  "kpi_cards": [                       # 可选
    {"label":"总销售额", "value":"¥1,058,572.06"},
    ...
  ],
  "sections":[
     {"heading":"一、章节", "core":"一句话核心",
      "items":["要点1","要点2"],
      "table":{"headers":[],"rows":[]},
      "paragraphs":["段落..."]},
     ...
  ]
}

硬规：
  - 顶部一行 source 署名（可被材料署名覆盖），底部一行恒定标准落款（`constants.FOOTER`）——两者独立，尾部落款不受 source 影响。
  - 标题层级只用 # / ## / ###，不超三层。
  - 表格对齐、中文表头，不出现英文列名。
  - 严禁 Agent 手搓 MD 结构。
"""
import datetime, os
import design_tokens
import constants


def _esc(s):
    return "" if s is None else str(s)


def _table_md(headers, rows):
    if not headers:
        return ""
    lines = []
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for row in rows:
        cells = [str(c) for c in row] + [""] * (len(headers) - len(row))
        lines.append("| " + " | ".join(cells[:len(headers)]) + " |")
    return "\n".join(lines)


def build_md(outline, out_path, mode=None, palette=None, font=None, scale=None, number=None):
    title = _esc(outline.get("title", "蒸馏精华"))
    subtitle = _esc(outline.get("subtitle", ""))
    date = _esc(outline.get("date") or datetime.date.today().isoformat())
    source = _esc(outline.get("source", constants.FOOTER))
    kpi_cards = outline.get("kpi_cards", [])
    sections = outline.get("sections", [])
    tok = design_tokens.resolve(mode=mode, palette=palette, font=font,
                                scale=scale, number=number, fmt="md")
    num_fn = tok["number"] if number else None  # number 未显式指定时保留原标题（不回归）

    lines = []
    lines.append(source)
    lines.append("")
    lines.append("# " + title)
    if subtitle:
        lines.append(subtitle)
    lines.append("（%s）" % date)
    lines.append("")

    if kpi_cards:
        lines.append("## 核心指标")
        lines.append("")
        for card in kpi_cards[:6]:
            lines.append("- **%s**：%s" % (_esc(card.get("label", "")), _esc(card.get("value", ""))))
        lines.append("")

    for i, sec in enumerate(sections, 1):
        h = design_tokens.number_heading(sec.get("heading", ""), 1, i, 0, num_fn)
        if h:
            lines.append("## " + _esc(h))
        core = _esc(sec.get("core", ""))
        if core:
            lines.append("**一句话核心：**" + core)
            lines.append("")
        for p in sec.get("paragraphs", []):
            lines.append(_esc(p))
            lines.append("")
        # 要点来源：items（本渲染器原生键）优先，否则取 body。
        # body 是 _adapt_md / _adapt_pdf 的统一 schema 键（md/txt/pdf 三格式同源）。
        items = list(sec.get("items", [])) or list(sec.get("body", []))
        for it in items:
            lines.append("- " + _esc(it))
        if items:
            lines.append("")
        tbl = sec.get("table")
        if tbl and tbl.get("headers"):
            lines.append(_table_md(tbl["headers"], tbl.get("rows", [])))
            lines.append("")

    lines.append("---")
    # 文末落款恒取标准落款常量 —— 与 docx / txt / pdf 三家写法对齐。
    # 顶部那一行才是 outline["source"]（可被材料署名覆盖）；文末落款不受 source 影响，
    # 否则常规路径（source＝材料名）下尾部落款会被顶掉。
    lines.append(constants.FOOTER)
    ov = constants.sources_overview(outline.get("sources"))
    if ov:
        lines.append(ov)
    lines.append("（%s）" % constants.disclaimer(outline.get("topic")))
    # 交付回执（闭环·反馈口）：紧随免责之后，是全文最后一行
    lines.append(constants.receipt_line(outline.get("receipt_tags")))

    text = "\n".join(lines).rstrip() + "\n"
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return out_path


def _self_test():
    """最小自测：渲染一次并断言**要点真写入**（不只断字节>0）。

    走临时目录，绝不写 scripts/ —— 否则验证产物会被下一次打包压进安装包。
    第三段故意用统一 schema 的 body 键，专门守住「键不匹配导致要点整段丢失」。
    """
    import tempfile
    demo = {
        "title": "自测标题",
        "subtitle": "自测副标题",
        "date": "2026-01-01",
        "source": "由 蒸馏成技能Skill 蒸馏产出",
        "sections": [
            {"heading": "一、甲模块", "core": "甲的核心句",
             "body": ["甲要点一", "甲要点二"]},
            {"heading": "二、乙模块", "core": "乙的核心句",
             "items": ["乙要点一"]},
        ],
    }
    p = os.path.join(tempfile.mkdtemp(), "self.md")
    build_md(demo, p)
    assert os.path.getsize(p) > 0, "产物为空: %s" % p
    t = open(p, encoding="utf-8").read()
    for must in ("自测标题", "一、甲模块", "甲的核心句", "甲要点一", "甲要点二",
                 "二、乙模块", "乙要点一",
                 constants.RECEIPT_PREFIX, constants.RECEIPT_BOUND):
        assert must in t, "md 产物缺内容: %s" % must
    # 来源总览（来源追溯）：多份材料必写进页脚；单份与无来源都不该冒出这行
    assert constants.SOURCE_OVERVIEW_PREFIX not in t, "无来源时不该出现来源总览"
    demo2 = dict(demo)
    demo2["sources"] = ["《甲材料》（文本直读）", "《乙材料》（PDF 文本层）"]
    p2 = os.path.join(tempfile.mkdtemp(), "self2.md")
    build_md(demo2, p2)
    t2 = open(p2, encoding="utf-8").read()
    assert constants.SOURCE_OVERVIEW_PREFIX in t2 and "2 份" in t2, "多份来源须写进页脚"
    assert "《甲材料》" in t2 and "《乙材料》" in t2, "来源总览须列全每一份"
    # 单份：只报份数，不罗列
    demo3 = dict(demo)
    demo3["sources"] = ["《甲材料》（文本直读）"]
    p3 = os.path.join(tempfile.mkdtemp(), "self3.md")
    build_md(demo3, p3)
    t3 = open(p3, encoding="utf-8").read()
    assert "1 份" in t3 and "《甲材料》" not in t3, "单份来源应只报份数"
    # source ≠ 落款（常规路径）：顶部署名可被材料名覆盖，但**文末落款必须恒为标准落款**。
    # 守的是「md 尾部落款被 source 顶掉」这一既有缺口 —— 别再把落款文本塞进 source 键来测。
    demo4 = dict(demo)
    demo4["source"] = "《甲材料》（文本直读）"
    p4 = os.path.join(tempfile.mkdtemp(), "self4.md")
    build_md(demo4, p4)
    t4 = open(p4, encoding="utf-8").read()
    head, _, tail = t4.partition("\n---\n")
    assert demo4["source"] in head, "顶部署名应取 source（本例＝材料名）"
    assert constants.FOOTER in tail, "文末落款必须恒为标准落款（不可被 source 顶掉）"
    assert demo4["source"] not in tail, "文末落款位不该出现材料署名"
    print("self-test PASS: %s (%d B)" % (os.path.basename(p), os.path.getsize(p)))


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default=None)
    ap.add_argument("--palette", default=None)
    ap.add_argument("--font", default=None)
    ap.add_argument("--scale", default=None)
    ap.add_argument("--number", default=None,
                    help="序号系统：arabic/cn/circle/none（不填=保留原标题，向后兼容）")
    ap.add_argument("--self-test", action="store_true",
                    help="最小自测：渲染一次并断言要点真写入（走临时目录，不写包内）")
    args = ap.parse_args()
    if args.self_test:
        _self_test()
        raise SystemExit(0)

    demo = {
        "title": "销售数据分析报告",
        "subtitle": "数据周期：2026年8月",
        "date": "2026-09-30",
        "source": "由 蒸馏成技能Skill 蒸馏产出",
        "kpi_cards": [
            {"label": "总销售额", "value": "¥1,058,572.06"},
            {"label": "总订单数", "value": "767"},
        ],
        "sections": [
            {"heading": "一、结算状态", "core": "已结算占绝对主导",
             "items": ["已结算 6400 行，占比 92.40%", "未结算 525 行，占比 7.60%"],
             "table": {"headers": ["结算状态", "订单行数", "占比"],
                       "rows": [["已结算", 6400, "92.40%"], ["未结算", 525, "7.60%"]]}},
            {"heading": "二、区域分布", "core": "华东领跑、华南追赶",
             "items": ["华东 3120 行，占比 45.0%", "华南 1680 行，占比 24.2%"]},
        ],
    }
    suffix = ("_%s" % args.mode) if args.mode else ""
    import tempfile
    out = os.path.join(tempfile.mkdtemp(), "销售报告_精华萃取%s.md" % suffix)
    build_md(demo, out, mode=args.mode, palette=args.palette,
             font=args.font, scale=args.scale, number=args.number)
    print("生成:", out, "|", os.path.getsize(out), "bytes")
