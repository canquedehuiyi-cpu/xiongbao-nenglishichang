# -*- coding: utf-8 -*-
"""verify_contract.py —— 产物契约联测（跨平台一致性 · 癸组机器判据）

把「规则写在文档里」变成「落在产物里」：**真跑包内 7 个生成器**，逐项断言产出满足
硬约束。任一断言失败即 exit≠0（供 `selfcheck.py --full` 当作一道门禁行）。

断言口径（与 references/bc-output-standards.md「Excel 两版共用硬约束（癸组）」同源）：
  全部 7 生成器 —— 均含统一溯源落款 + 免责主句（癸-3）
                   + 交付回执（前缀 / 零内容边界，带做法标签时另含「做法标签」字样）
  xlsx 标准表   —— numFmts 164–168；冻结行 = 表头行；autoFilter = 表宽；
                    日期写真序列值；docProps 无工具指纹（癸-4/5/7 与庚-13）
  xlsx 图表报告 —— 饼图 dPt ≥ 扇区数；显式令牌色；冻结行 = 表头行；
                    图表引用不写死 $X100；docProps 无工具指纹（癸-2/4/8）
  结构          —— 全部 XML 良构；PDF 头/尾/ToUnicode（庚-18）
  命名          —— 同批多格式同名干；后缀属枚举表；连接符半角 `_`（癸-12）
                    生成器产物一律按 `<材料名主干>_<动作后缀>.<ext>` 落盘

用法：
  python verify_contract.py            # 同 --self-test
  python verify_contract.py --self-test
产物一律落临时目录，绝不写包内任何位置（守自测残留复查纪律）。
"""
import os, sys, zipfile, tempfile, re

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import constants

FOOTER = constants.FOOTER
DISCLAIMER = constants.DISCLAIMER_MAIN
RECEIPT_PREFIX = constants.RECEIPT_PREFIX
RECEIPT_BOUND = constants.RECEIPT_BOUND
RECEIPT_TAG_WORD = constants.RECEIPT_TAG_WORD
# 做法标签测试值：刻意用 demo 里没出现过的字，便于 PDF 码点校验只认回执本身
RECEIPT_TAGS = "\u56de\u6267\u6807\u6ce8\u793a\u4f8b / B / Word / D1"
# 来源总览测试值（两份材料，走真实路径）
SOURCES_DEMO = ["《甲材料》（文本直读）", "《乙材料》（PDF 文本层）"]
OV_PREFIX = constants.SOURCE_OVERVIEW_PREFIX
TOOL_FINGERPRINTS = ("openpyxl", "python-pptx", "python-docx", "xlwt", "pandas", "xlsxwriter")


def _outline_base():
    """七个生成器共用的最小大纲（内容刻意避开免责声明用字，便于 PDF 码点校验）。"""
    return {
        "title": "契约联测", "subtitle": "s", "date": "2026-01-01",
        "source": FOOTER, "topic": "biz", "receipt_tags": RECEIPT_TAGS,
        # 来源追溯：多份材料 → 七生成器页脚都必须出「来源总览」
        "sources": ["《甲材料》（文本直读）", "《乙材料》（PDF 文本层）"],
        "sections": [{"heading": "一、甲", "core": "甲核", "body": ["甲要点"]}],
    }


def _zip_blob_text(path):
    z = zipfile.ZipFile(path)
    return "".join(z.read(n).decode("utf-8", "ignore")
                   for n in z.namelist() if n.endswith(".xml"))


def _check_zip_wellformed(path, fails, tag):
    z = zipfile.ZipFile(path)
    import xml.etree.ElementTree as ET
    for n in z.namelist():
        if n.endswith((".xml", ".rels")):
            try:
                ET.fromstring(z.read(n))
            except Exception as e:
                fails.append("%s：part %s 非良构（%s）" % (tag, n, e))


def check_contract():
    """返回失败清单（空 = 全过）。"""
    fails = []
    td = tempfile.mkdtemp()

    # ---------- 1) 七生成器：落款 + 免责全覆盖（癸-3） ----------
    built = {}

    # 产物一律按规范命名落盘（癸-12）：同批同名词干 + 后缀属枚举表
    NAME_BASE = "契约联测"
    import build_md_standard as MD
    p = os.path.join(td, NAME_BASE + "_\u7cbe\u534e\u8403\u53d6.md"); MD.build_md(_outline_base(), p)
    built["md"] = p

    import build_txt_standard as TXT
    p = os.path.join(td, NAME_BASE + "_\u7cbe\u534e\u8403\u53d6.txt"); TXT.build_txt(_outline_base(), p)
    built["txt"] = p

    import build_docx_standard as DOCX
    p = os.path.join(td, NAME_BASE + "_\u7cbe\u534e\u8403\u53d6.docx")
    DOCX.render_outline({"title": "契约联测", "subtitle": "s", "source": FOOTER,
                         "receipt_tags": RECEIPT_TAGS, "sources": SOURCES_DEMO,
                         "sections": [{"h": "一、甲", "core": "甲核",
                                       "items": ["甲要点"], "paras": ["甲段"]}]}, p)
    built["docx"] = p

    import build_ppt_standard as PPT
    p = os.path.join(td, NAME_BASE + "_\u7cbe\u534e\u8403\u53d6.pptx")
    PPT.render_outline({"title": "契约联测", "subtitle": "s", "attr": FOOTER,
                        "receipt_tags": RECEIPT_TAGS, "sources": SOURCES_DEMO,
                        "chapters": [("1", "一、甲", "甲核")],
                        "sections": [{"type": "divider", "cur": 1, "num": "1",
                                      "title": "一、甲", "lead": "甲核"},
                                     {"type": "cards", "title": "一、甲",
                                      "items": [("甲要点", [])]}],
                        "closing": {"title": "谢谢", "points": []}}, p)
    built["pptx"] = p

    import build_xlsx_standard as XS
    std_demo = {
        "title": "契约联测", "subtitle": "s", "date": "2026-01-01",
        "source": FOOTER, "topic": "biz", "receipt_tags": RECEIPT_TAGS,
        "sources": SOURCES_DEMO,
        "sheets": [{"name": "明细", "section_title": "明细",
                    "headers": ["日期", "项目", "金额", "占比", "编号"],
                    "rows": [["2026-08-01", "甲", 1234.5, 0.924, "00123"],
                             ["2026-08-02", "乙", 6789, 92.4, "00789"]]}],
    }
    p = os.path.join(td, NAME_BASE + "_\u6570\u636e\u8868.xlsx"); XS.build_xlsx(std_demo, p)
    built["xlsx"] = p

    import build_xlsx_chart_standard as XC
    chart_demo = {
        "title": "契约联测", "subtitle": "s", "date": "2026-01-01",
        "source": FOOTER, "topic": "biz", "receipt_tags": RECEIPT_TAGS,
        "sources": SOURCES_DEMO,
        "kpi_cards": [{"label": "甲", "value": 1, "fmt": "int"}],
        "sheets": [{"name": "甲表", "section_title": "甲表",
                    "headers": ["类目", "金额", "日期"],
                    "rows": [["甲", 1234.5, "2026-01-01"], ["乙", 6789, "2026-02-15"]],
                    "col_fmts": ["text", "currency", "date"],
                    "chart": {"type": "pie", "title": "甲占比", "cat_col": 0, "val_col": 1}}],
    }
    p = os.path.join(td, NAME_BASE + "_\u56fe\u8868\u5206\u6790.xlsx"); XC.build_xlsx_chart(chart_demo, p)
    built["xlsx_chart"] = p

    # PDF：中文子集编码不可直 grep → 用 ToUnicode CMap 码点校验
    import build_pdf_standard as PDF
    p = os.path.join(td, NAME_BASE + "_\u7cbe\u534e\u8403\u53d6.pdf")
    try:
        PDF.build_pdf(_outline_base(), p)
        built["pdf"] = p
    except RuntimeError as e:
        built["pdf"] = None
        fails.append("SKIP-pdf：未找到中文字体（%s）" % str(e).strip().splitlines()[0][:60])

    for tag, path in built.items():
        if not path:
            continue
        if tag in ("md", "txt"):
            text = open(path, encoding="utf-8").read()
        elif tag == "pdf":
            text = None
        else:
            text = _zip_blob_text(path)
        if text is not None:
            if FOOTER not in text:
                fails.append("%s：缺统一溯源落款" % tag)
            if DISCLAIMER not in text:
                fails.append("%s：缺免责声明主句" % tag)
            if RECEIPT_PREFIX not in text or RECEIPT_BOUND not in text:
                fails.append("%s：缺交付回执（前缀/零内容边界）" % tag)
            if RECEIPT_TAG_WORD not in text:
                fails.append("%s：传了 receipt_tags 却无「做法标签」字样" % tag)
            # 来源追溯：给了多份 sources，页脚必须出「来源总览」并列全每一份
            if OV_PREFIX not in text:
                fails.append("%s：给了多份来源却无「来源总览」" % tag)
            elif "2 份" not in text:
                fails.append("%s：来源总览未报份数" % tag)
            for s in SOURCES_DEMO:
                if s[:3] not in text:
                    fails.append("%s：来源总览漏列 %s" % (tag, s[:3]))

    # PDF 落款/免责：码点必须都出现在 ToUnicode CMap（demo 用字已避开这些字）
    if built.get("pdf"):
        raw = open(built["pdf"], "rb").read()
        if raw[:5] != b"%PDF-":
            fails.append("pdf：头标记缺失")
        if b"%%EOF" not in raw[-128:]:
            fails.append("pdf：尾标记缺失")
        if b"ToUnicode" not in raw:
            fails.append("pdf：未内嵌 ToUnicode")
        _pdf_probe = (FOOTER + DISCLAIMER + RECEIPT_PREFIX + RECEIPT_BOUND + RECEIPT_TAG_WORD
                      + constants.sources_overview(SOURCES_DEMO))
        for ch in _pdf_probe:
            if ord(ch) >= 0x4E00 and ("%04X" % ord(ch)).encode() not in raw:
                fails.append("pdf：落款/免责/回执/来源用字未进 ToUnicode（U+%04X）" % ord(ch))
                break

    # ---------- 2) xlsx 标准表契约 ----------
    z = zipfile.ZipFile(built["xlsx"])
    st = z.read("xl/styles.xml").decode("utf-8")
    for nid, code in ((164, "¥#,##0.00"), (165, "0.00%"), (166, "#,##0"),
                      (167, "#,##0.00"), (168, "yyyy-mm-dd")):
        if 'numFmtId="%d" formatCode="%s"' % (nid, code) not in st:
            fails.append("xlsx：numFmts 缺 %d/%s（癸-5）" % (nid, code))
    sx = z.read("xl/worksheets/sheet1.xml").decode("utf-8")
    if 'ySplit="4"' not in sx or 'topLeftCell="A5"' not in sx:
        fails.append("xlsx：冻结行 ≠ 表头行（癸-4）")
    if not re.search(r'<autoFilter ref="A4:E6"/>', sx):
        fails.append("xlsx：autoFilter 未覆盖表实际列数（庚-13）")
    if 's="9"' not in sx:
        fails.append("xlsx：日期列未套日期格式（庚-7）")
    cp = z.read("docProps/core.xml").decode("utf-8").lower()
    for bad in TOOL_FINGERPRINTS:
        if bad in cp:
            fails.append("xlsx：docProps 泄露工具指纹 %s（癸-7）" % bad)
    _check_zip_wellformed(built["xlsx"], fails, "xlsx")

    # ---------- 3) xlsx 图表报告契约 ----------
    zc = zipfile.ZipFile(built["xlsx_chart"])
    cxml = zc.read("xl/charts/chart1.xml").decode("utf-8")
    if cxml.count("<c:dPt>") < 2:
        fails.append("xlsx_chart：饼图未逐扇区配色（癸-2/庚-5）")
    if "$100" in cxml or ",100" in cxml or ":X100" in cxml:
        fails.append("xlsx_chart：图表引用写死到固定行（庚-8）")
    if not re.search(r'<a:srgbClr val="[0-9A-Fa-f]{6}"/>', cxml):
        fails.append("xlsx_chart：图表零显式令牌色（癸-2）")
    wsc = zc.read("xl/worksheets/sheet1.xml").decode("utf-8")
    if 'ySplit="8"' not in wsc or 'topLeftCell="A9"' not in wsc:
        fails.append("xlsx_chart：冻结行 ≠ 表头行（癸-4）")
    if '<autoFilter ref="B8:D10"/>' not in wsc:
        fails.append("xlsx_chart：autoFilter 未覆盖表实际列数（庚-13）")
    cpc = zc.read("docProps/core.xml").decode("utf-8").lower()
    for bad in TOOL_FINGERPRINTS:
        if bad in cpc:
            fails.append("xlsx_chart：docProps 泄露工具指纹 %s（癸-7）" % bad)
    _check_zip_wellformed(built["xlsx_chart"], fails, "xlsx_chart")

    for tag in ("docx", "pptx"):
        _check_zip_wellformed(built[tag], fails, tag)

    # ---------- 4) 输出命名公式契约（癸-12） ----------
    # 口径与 references/bc-output-standards.md「输出文件命名硬规」同源：
    #   公式 = <材料名主干>_<动作后缀>.<扩展名>；后缀须属枚举表；连接符半角 `_`；
    #   同批多格式（md/txt/docx/pptx/pdf）名干必须完全相同。
    SUFFIXES = ("\u6570\u636e\u8868", "\u6c47\u603b\u5206\u6790", "\u56fe\u8868\u5206\u6790",
                "\u7cbe\u534e\u8403\u53d6", "\u5b9a\u5411\u8403\u53d6")
    stems = {}
    for tag, path in built.items():
        if not path:
            continue
        fname = os.path.basename(path)
        stem = os.path.splitext(fname)[0]
        if "\uFF3F" in stem or " " in stem or "\u3000" in stem:
            fails.append("naming/%s：文件名含全角连接符或空格 → %s（癸-12）" % (tag, fname))
        hit = [s for s in SUFFIXES if stem.endswith("_" + s)]
        if not hit:
            fails.append("naming/%s：后缀不在枚举表内 → %s（癸-12）" % (tag, fname))
            continue
        base = stem[: -(len(hit[0]) + 1)]
        if not base:
            fails.append("naming/%s：名干为空 → %s（癸-12）" % (tag, fname))
        stems[tag] = base
    batch = [t for t in ("md", "txt", "docx", "pptx", "pdf") if t in stems]
    if batch:
        ref = stems[batch[0]]
        for t in batch[1:]:
            if stems[t] != ref:
                fails.append("naming：同批名干不一致 %s=%r vs %s=%r（癸-12）"
                             % (batch[0], ref, t, stems[t]))

    return fails


def check_contract_regular_path():
    """常规路径用例（守「md 尾部落款被 source 顶掉」缺口·P2-1）。

    上面 check_contract 把 source 填成落款文本 → md 尾部落款恰好=落款，测不到常规路径。
    本函数刻意让 source ≠ 落款（＝材料署名，真实场景），再验生成器落款位：
      · md：文末「--- 」之后必须出现**标准落款**（constants.FOOTER）——这是 P2-1 的直接判据。
      · 文本类可精确切末段；二进制类按各自落款位（docx/pptx 内置落款 part）整包查。
    ⚠️ 已知边界（不在本用例断言范围，另案）：xlsx 标准表的落款设计为「顶部 A1 行」、
    无文末落款位；常规路径下顶部即材料名、全表无恒定标准落款 —— 属另一处同源缺口，单独立项。
    """
    fails = []
    td = tempfile.mkdtemp()
    MATERIAL = "《甲材料》（文本直读）"
    base = {
        "title": "常规路径联测", "subtitle": "s", "date": "2026-01-01",
        "source": MATERIAL, "topic": "biz", "receipt_tags": RECEIPT_TAGS,
        "sources": SOURCES_DEMO,
        "sections": [{"heading": "一、甲", "core": "甲核", "body": ["甲要点"]}],
    }
    built = {}

    import build_md_standard as MD
    p = os.path.join(td, "常规路径联测_\u7cbe\u534e\u8403\u53d6.md"); MD.build_md(dict(base), p)
    built["md"] = p
    import build_txt_standard as TXT
    p = os.path.join(td, "常规路径联测_\u7cbe\u534e\u8403\u53d6.txt"); TXT.build_txt(dict(base), p)
    built["txt"] = p

    import build_docx_standard as DOCX
    p = os.path.join(td, "常规路径联测_\u7cbe\u534e\u8403\u53d6.docx")
    DOCX.render_outline({"title": "常规路径联测", "subtitle": "s", "source": MATERIAL,
                         "receipt_tags": RECEIPT_TAGS, "sources": SOURCES_DEMO,
                         "sections": [{"h": "一、甲", "core": "甲核",
                                       "items": ["甲要点"], "paras": ["甲段"]}]}, p)
    built["docx"] = p

    import build_ppt_standard as PPT
    p = os.path.join(td, "常规路径联测_\u7cbe\u534e\u8403\u53d6.pptx")
    PPT.render_outline({"title": "常规路径联测", "subtitle": "s", "attr": MATERIAL,
                        "receipt_tags": RECEIPT_TAGS, "sources": SOURCES_DEMO,
                        "chapters": [("1", "一、甲", "甲核")],
                        "sections": [{"type": "divider", "cur": 1, "num": "1",
                                      "title": "一、甲", "lead": "甲核"},
                                     {"type": "cards", "title": "一、甲",
                                      "items": [("甲要点", [])]}],
                        "closing": {"title": "谢谢", "points": []}}, p)
    built["pptx"] = p

    # md/txt：文末必须出现标准落款（md 用 --- 切末段；txt 落款在末段、无分隔线）
    for tag in ("md", "txt"):
        text = open(built[tag], encoding="utf-8").read()
        if tag == "md":
            head, sep, tail = text.partition("\n---\n")
            if not sep:
                fails.append("常规/md：无文末分隔线，无法定位落款段")
                continue
            if FOOTER not in tail:
                fails.append("常规/md：文末落款缺标准落款（被 source 顶掉·P2-1）")
            # 文末落款段不得出现「材料名独占一行」那种被顶掉的署名行
            if any(ln.strip() == MATERIAL for ln in tail.splitlines()):
                fails.append("常规/md：文末落款位出现材料署名（source 一物两用·P2-1）")
        else:
            if FOOTER not in text:
                fails.append("常规/txt：文末落款缺标准落款（被 source 顶掉）")
            if MATERIAL not in text:
                fails.append("常规/txt：顶部署名未取 source（本例＝材料名）")

    # docx/pptx：内置落款 part 整包查（顶部 source 与文末 FOOTER 都要在）
    for tag in ("docx", "pptx"):
        text = _zip_blob_text(built[tag])
        if FOOTER not in text:
            fails.append("常规/%s：产物内无标准落款（被 source 顶掉？）" % tag)
        if MATERIAL not in text:
            fails.append("常规/%s：顶部署名未取 source（本例＝材料名）" % tag)
    return fails


def _self_test():
    fails = check_contract() + check_contract_regular_path()
    hard = [f for f in fails if not f.startswith("SKIP-")]
    if hard:
        print("FAIL verify_contract：%d 项" % len(hard))
        for f in hard[:20]:
            print("   - " + f)
        return 1
    soft = ("；SKIP %d 项（无中文字体）" % len(fails)) if fails else ""
    print("PASS verify_contract：7 生成器落款/免责/交付回执 + 常规路径落款 + xlsx 两版契约全过%s" % soft)
    return 0


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="产物契约联测（癸组机器判据）")
    ap.add_argument("--self-test", action="store_true", dest="self_test")
    ap.parse_args()
    raise SystemExit(_self_test())
