# -*- coding: utf-8 -*-
"""
build_xlsx_standard.py —— B/C 模式 Excel 报表标准生成器（纯标准库·零第三方依赖）

设计令牌（与 PPT/DOCX 生成器同源，保证全格式视觉一致）：
  MAIN   = #16335B  主色（深蓝，标题带/表头填充）
  ACCENT = #E0A33E  强调（琥珀金，标题行填充）
  LIGHT  = #F4F6F9  浅底（隔行/说明区）
  BODY   = #1F2733  正文
  ANNOT  = #6B7480  注释灰

输入大纲 outline（dict）：
{
  "title":   "报表总标题",
  "subtitle":"副标题/口径说明（可选）",
  "date":    "2026-09-30",                # 缺省取当天
  "source":  "由 蒸馏成技能Skill 蒸馏产出",  # 溯源落款
  "sheets": [
     {
       "name":  "Sheet1",                 # 工作表名(≤31字)
       "caption":"本表说明（可选）",
       "headers":["列1","列2",...],         # 表头
       "rows":[ ["值","值",...], ... ],     # 数据行（字符串/数字均可）
       "note": "脚注（可选）"
     }, ...
  ]
}

用法：
  from build_xlsx_standard import build_xlsx
  build_xlsx(outline, "输出.xlsx")

硬规：
  - 严禁 Agent 手搓 xlsx 渲染；统一走本生成器，保证版式/字体/落款一致。
  - **默认语义＝全量搬运 + 规整**：rows 默认＝源表全部行全部列（只做表头统一 / 数字格式按列
    （金额 / 百分比 / 整数 / 数值 / 日期）/ 冻结表头 / 清空空行空列 / 工作表名中文化），
    **不减行、不换列、不预设维度**。日期列写**真日期序列值 + `yyyy-mm-dd`**（显示与源一致，
    但可排序 / 可透视 / 可算间隔），不像日期的串一律退回文本、绝不硬转。
  - **按方向汇总＝用户明确给出方向后才做**：用户说「按X汇总 / 只看X / 给我X的合计」才按方向聚合；
    **未给方向不得自行选维度** —— 本生成器不含任何默认聚合路径。
  - 免责声明：末行固定挂 `constants.disclaimer(topic)`，与顶部溯源落款是两句两处。
"""
import zipfile, datetime, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import design_tokens
import constants

MAIN_HEX = "16335B"
ACCENT_HEX = "E0A33E"
LIGHT_HEX = "F4F6F9"
BODY_HEX = "1F2733"
ANNOT_HEX = "6B7480"
WHITE_HEX = "FFFFFF"
FONT_NAME = "Microsoft YaHei"   # 默认字体（按所选模式覆盖）

# 数字格式 id（自定义；与 build_xlsx_chart_standard 同源，保证两张 Excel 口径一致）
FMT_CURRENCY = 164   # ¥#,##0.00
FMT_PERCENT  = 165   # 0.00%
FMT_INT      = 166   # #,##0
FMT_NUMBER   = 167   # #,##0.00
FMT_DATE     = 168   # yyyy-mm-dd（真日期序列值，可排序/透视）


def _esc(s):
    s = "" if s is None else str(s)
    return (s.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;").replace("'", "&apos;"))


def _col_letter(idx):  # 0-based -> A,B,...,Z,AA
    s = ""
    idx += 1
    while idx:
        idx, r = divmod(idx - 1, 26)
        s = chr(65 + r) + s
    return s


def _col_width(chars):
    w = max(8.0, min(60.0, chars * 1.15 + 2.0))
    return round(w, 1)


def _num_val(v):
    """返回单元格的「真数值」本体（保留 int/float 原类型）；非真数值返回 None。
    字符串一律不折算 —— 防「00123」类编号被转成 123 而丢前导零。"""
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return v
    return None


# ISO 日期（YYYY-MM-DD / YYYY/MM/DD / YYYY.MM.DD）→ Excel 序列值（1900 日期系统）
_DATE_RE = re.compile(r"^\s*(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})\s*$")


def _date_serial(v):
    """把 ISO 形态日期串折算为 Excel 序列值；不是日期返回 None。"""
    m = _DATE_RE.match("" if v is None else str(v))
    if not m:
        return None
    try:
        d = datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None
    return (d - datetime.date(1899, 12, 30)).days


def _detect_col_fmts(headers, rows):
    """按列头关键字 + 首个样本自动识别格式：currency/percent/int/date/number/text。
    仅在未显式给出 col_fmts 时作兜底；数值判据只看「真数值」，日期判据须列头像日期且样本为 ISO 日期。"""
    if not headers:
        return []
    fmts = []
    for c, h in enumerate(headers):
        hl = str(h).lower()
        first = None
        for r in rows:
            if c < len(r):
                first = r[c]
                break
        if any(k in hl for k in ["金额", "销售额", "收入", "营收", "价格", "单价", "总额", "总值", "利润", "成本"]):
            fmts.append("currency"); continue
        if any(k in hl for k in ["占比", "百分比", "率", "比例", "%"]):
            fmts.append("percent"); continue
        if any(k in hl for k in ["数量", "订单数", "客户数", "件数", "次数", "人数", "行数"]):
            fmts.append("int"); continue
        # 日期列：列头像日期 且 首个样本是 ISO 日期（双条件，防误判）
        if any(k in hl for k in ["日期", "时间", "date"]) and _date_serial(first) is not None:
            fmts.append("date"); continue
        nv = _num_val(first)
        if nv is None:
            fmts.append("text"); continue
        if nv == int(nv):
            fmts.append("int"); continue
        fmts.append("number")
    return fmts


def _style_idx_for_col(fmt):
    """返回 cellXfs 索引：text=3, currency=5, percent=6, int=7, number=8, date=9"""
    return {"currency": 5, "percent": 6, "int": 7, "number": 8, "date": 9, "text": 3}.get(fmt, 3)


def _cell_xml(ref, v, fmt):
    """按列格式产出一个单元格 XML：日期写序列值、数字写真数值、其余写文本（保前导零）。"""
    if fmt == "date":
        ser = _date_serial(v)
        if ser is not None:
            return '<c r="%s" s="9"><v>%s</v></c>' % (ref, ser)
        fmt = "text"  # 不像日期 → 退回文本，不硬转
    nv = _num_val(v)
    if nv is not None and fmt != "text":
        if fmt == "percent" and nv > 1:
            # 源值 >1 视为「百分数写法」（92.4 → 92.40%），折算成小数存储
            nv = nv / 100.0
        return '<c r="%s" s="%d"><v>%s</v></c>' % (ref, _style_idx_for_col(fmt), nv)
    return ('<c r="%s" s="3" t="inlineStr"><is><t xml:space="preserve">%s</t></is></c>'
            % (ref, _esc(v)))


def _sheet_xml(name, caption, headers, rows, note, disclaimer_text="", signature="", col_fmts=None,
               receipt_text="", overview_text=""):
    parts = []
    parts.append('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>')
    parts.append('<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">')
    # 视图：冻结前 4 行（落款行 + 标题行 + 说明行 + 表头行），数据自第 5 行起
    parts.append('<sheetViews><sheetView workbookViewId="0">'
                 '<pane ySplit="4" topLeftCell="A5" activePane="bottomLeft" state="frozen"/>'
                 '</sheetView></sheetViews>')
    # 列宽
    ncol = max(len(headers), max((len(r) for r in rows), default=0), 1)
    # 每列数字格式：显式 col_fmts 优先，缺省按列头/首个真数值兜底识别
    if col_fmts is None:
        col_fmts = _detect_col_fmts(headers, rows)
    widths = []
    for c in range(ncol):
        maxlen = len(str(headers[c])) if c < len(headers) else 4
        for r in rows:
            if c < len(r):
                maxlen = max(maxlen, len(str(r[c])))
        widths.append('<col min="%d" max="%d" width="%s" customWidth="1"/>'
                      % (c + 1, c + 1, _col_width(maxlen)))
    parts.append('<cols>%s</cols>' % "".join(widths))
    # 数据行
    parts.append('<sheetData>')
    last = _col_letter(ncol - 1)
    # 行1：溯源落款（可见 · 规范要求「顶部表头上方第一行」）
    parts.append('<row r="1"><c r="A1" s="4" t="inlineStr"><is><t xml:space="preserve">%s</t></is></c></row>'
                 % _esc(signature))
    # 行2：标题（合并）
    parts.append('<row r="2"><c r="A2" s="1" t="inlineStr"><is><t xml:space="preserve">%s</t></is></c></row>'
                 % _esc(name))
    # 行3：说明/口径
    cap = caption or ""
    parts.append('<row r="3"><c r="A3" s="4" t="inlineStr"><is><t xml:space="preserve">%s</t></is></c></row>'
                 % _esc(cap))
    # 行4：表头
    hdr_cells = []
    for c, h in enumerate(headers):
        ref = "%s4" % _col_letter(c)
        hdr_cells.append('<c r="%s" s="2" t="inlineStr"><is><t xml:space="preserve">%s</t></is></c>'
                          % (ref, _esc(h)))
    parts.append('<row r="4">%s</row>' % "".join(hdr_cells))
    # 数据行（自第 5 行起）
    for i, row in enumerate(rows):
        ridx = i + 5
        cells = []
        for c, v in enumerate(row):
            ref = "%s%d" % (_col_letter(c), ridx)
            fmt = col_fmts[c] if c < len(col_fmts) else "text"
            cells.append(_cell_xml(ref, v, fmt))
        parts.append('<row r="%d">%s</row>' % (ridx, "".join(cells)))
    # 末段三行（顺序固定：来源总览 → 免责声明 → 交付回执；仅最后一张表出现）
    # 来源总览：多份材料时给出「这份表由哪些材料来的」；单份/无来源不出行
    base = len(rows) + 5
    orow = 0
    if overview_text:
        orow = base
        parts.append('<row r="%d"><c r="A%d" s="4" t="inlineStr"><is><t xml:space="preserve">%s</t></is></c></row>'
                     % (orow, orow, _esc(overview_text)))
        base += 1
    # 免责声明（合规）：与顶部溯源落款是两句两处，不合并
    drow = 0
    if disclaimer_text:
        drow = base
        parts.append('<row r="%d"><c r="A%d" s="4" t="inlineStr"><is><t xml:space="preserve">%s</t></is></c></row>'
                     % (drow, drow, _esc(disclaimer_text)))
        base += 1
    # 交付回执（闭环·反馈口）：只随免责同表出现，紧跟免责下一行（保持「回执紧跟免责」）
    rrow = 0
    if disclaimer_text and receipt_text:
        rrow = base
        parts.append('<row r="%d"><c r="A%d" s="4" t="inlineStr"><is><t xml:space="preserve">%s</t></is></c></row>'
                     % (rrow, rrow, _esc(receipt_text)))
        base += 1
    parts.append('</sheetData>')
    # 自动筛选：范围 = 表实际列数 × （表头行 → 最后一数据行），末列不许漏（庚-13）
    # schema 顺序：autoFilter 必须排在 mergeCells 之前
    if rows:
        af_last = len(rows) + 4          # 数据自第 5 行起 → 最后一数据行 = len(rows)+4
        parts.append('<autoFilter ref="A4:%s%d"/>' % (last, af_last))
    # 合并落款行 / 标题行 / 说明行（+ 免责行）
    merges = ['<mergeCell ref="A1:%s1"/>' % last, '<mergeCell ref="A2:%s2"/>' % last,
              '<mergeCell ref="A3:%s3"/>' % last]
    if orow:
        merges.append('<mergeCell ref="A%d:%s%d"/>' % (orow, last, orow))
    if drow:
        merges.append('<mergeCell ref="A%d:%s%d"/>' % (drow, last, drow))
    if rrow:
        merges.append('<mergeCell ref="A%d:%s%d"/>' % (rrow, last, rrow))
    parts.append('<mergeCells count="%d">%s</mergeCells>' % (len(merges), "".join(merges)))
    parts.append('</worksheet>')
    return "".join(parts)


def build_xlsx(outline, out_path, mode=None, palette=None, font=None, scale=None):
    """生成 Excel 标准数据表。可选 token 参数（前置设计令牌库）：
    mode/palette/font/scale，含义同其他生成器；不选则默认 biz（与既有默认值一致）。"""
    global MAIN_HEX, ACCENT_HEX, LIGHT_HEX, BODY_HEX, ANNOT_HEX, FONT_NAME
    tok = design_tokens.resolve(mode=mode, palette=palette, font=font, scale=scale, fmt="xlsx")
    MAIN_HEX = tok["palette"]["MAIN"]
    ACCENT_HEX = tok["palette"]["ACCENT"]
    LIGHT_HEX = tok["palette"]["LIGHT"]
    BODY_HEX = tok["palette"]["BODY"]
    ANNOT_HEX = tok["palette"]["ANNOT"]
    FONT_NAME = tok["font_office"]
    title = outline.get("title", "蒸馏报表")
    subtitle = outline.get("subtitle", "")
    date = outline.get("date") or datetime.date.today().isoformat()
    source = outline.get("source", constants.FOOTER)
    sheets = outline.get("sheets", [])
    if not sheets:
        sheets = [{"name": "数据", "headers": ["项目", "内容"], "rows": [["（空）", ""]]}]

    # 内容类型
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
          '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
          '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>')
    for i in range(len(sheets)):
        ct += ('<Override PartName="/xl/worksheets/sheet%d.xml" '
               'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' % (i + 1))
    ct += '</Types>'

    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '<Relationship Id="rIdDocProps" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
            '</Relationships>')

    # workbook.xml
    wb_sheets = []
    for i, sh in enumerate(sheets):
        wb_sheets.append('<sheet name="%s" sheetId="%d" r:id="rId%d"/>'
                         % (_esc(sh.get("name", "Sheet%d" % (i + 1))[:31]), i + 1, i + 1))
    workbook = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                '<sheets>%s</sheets></workbook>' % "".join(wb_sheets))

    wb_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
               '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
               '<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
               % (len(sheets) + 1))
    for i in range(len(sheets)):
        wb_rels += ('<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet%d.xml"/>'
                    % (i + 1, i + 1))
    wb_rels += '</Relationships>'

    # 文档属性：报表总标题/副标题写入标准 core-properties。可见版式仍以工作表名＋小标题为主，
    # 让「总标题」有归属、可追溯（否则 title/subtitle 被读出却不写入任何 part）。
    core_props = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                  '<cp:coreProperties '
                  'xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
                  'xmlns:dc="http://purl.org/dc/elements/1.1/">'
                  '<dc:title>%s</dc:title><dc:subject>%s</dc:subject>'
                  '<dc:creator>%s</dc:creator></cp:coreProperties>'
                  % (_esc(title), _esc(subtitle), _esc(source)))

    # styles.xml
    # numFmts: 5 种自定义数字格式（与图表版同源）；须排在 fonts 之前（schema 顺序不可颠倒）
    styles = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
              '<numFmts count="5">'
              '<numFmt numFmtId="%d" formatCode="¥#,##0.00"/>'
              '<numFmt numFmtId="%d" formatCode="0.00%%"/>'
              '<numFmt numFmtId="%d" formatCode="#,##0"/>'
              '<numFmt numFmtId="%d" formatCode="#,##0.00"/>'
              '<numFmt numFmtId="%d" formatCode="yyyy-mm-dd"/>'
              '</numFmts>' % (FMT_CURRENCY, FMT_PERCENT, FMT_INT, FMT_NUMBER, FMT_DATE))
    # fonts: 0 默认 / 1 标题白字粗 / 2 表头白字粗 / 3 正文 / 4 说明灰
    styles += ('<fonts count="5">'
               '<font><sz val="11"/><name val="%s"/></font>'
               '<font><b/><sz val="16"/><color rgb="FF%s"/><name val="%s"/></font>'
               '<font><b/><sz val="11"/><color rgb="FF%s"/><name val="%s"/></font>'
               '<font><sz val="11"/><color rgb="FF%s"/><name val="%s"/></font>'
               '<font><i/><sz val="9"/><color rgb="FF%s"/><name val="%s"/></font>'
               '</fonts>' % (FONT_NAME, WHITE_HEX, FONT_NAME, WHITE_HEX, FONT_NAME,
                            BODY_HEX, FONT_NAME, ANNOT_HEX, FONT_NAME))
    # fills: 0 none / 1 gray125(必) / 2 ACCENT / 3 MAIN / 4 LIGHT
    styles += ('<fills count="5">'
               '<fill><patternFill patternType="none"/></fill>'
               '<fill><patternFill patternType="gray125"/></fill>'
               '<fill><patternFill patternType="solid"><fgColor rgb="FF%s"/></patternFill></fill>'
               '<fill><patternFill patternType="solid"><fgColor rgb="FF%s"/></patternFill></fill>'
               '<fill><patternFill patternType="solid"><fgColor rgb="FF%s"/></patternFill></fill>'
               '</fills>' % (ACCENT_HEX, MAIN_HEX, LIGHT_HEX))
    # borders: 0 none / 1 thin
    styles += ('<borders count="2">'
               '<border><left/><right/><top/><bottom/><diagonal/></border>'
               '<border><left style="thin"><color rgb="FFD8DEE6"/></left>'
               '<right style="thin"><color rgb="FFD8DEE6"/></right>'
               '<top style="thin"><color rgb="FFD8DEE6"/></top>'
               '<bottom style="thin"><color rgb="FFD8DEE6"/></bottom><diagonal/></border>'
               '</borders>')
    # cellXfs: 0 默认 / 1 标题 / 2 表头 / 3 正文文本(顶对齐换行) / 4 说明
    #          5 金额 / 6 百分比 / 7 整数 / 8 数值 / 9 日期 —— 数字列统一右对齐 + 细边框
    styles += ('<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
               '<cellXfs count="10">'
               '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
               '<xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="left" vertical="center"/></xf>'
               '<xf numFmtId="0" fontId="2" fillId="3" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf>'
               '<xf numFmtId="0" fontId="3" fillId="0" borderId="1" xfId="0" applyFont="1" applyBorder="1" applyAlignment="1"><alignment horizontal="left" vertical="top" wrapText="1"/></xf>'
               '<xf numFmtId="0" fontId="4" fillId="0" borderId="0" xfId="0" applyFont="1" applyAlignment="1"><alignment horizontal="left" vertical="center" wrapText="1"/></xf>'
               '<xf numFmtId="%d" fontId="3" fillId="0" borderId="1" xfId="0" applyNumberFormat="1" applyFont="1" applyBorder="1" applyAlignment="1"><alignment horizontal="right" vertical="center"/></xf>'
               '<xf numFmtId="%d" fontId="3" fillId="0" borderId="1" xfId="0" applyNumberFormat="1" applyFont="1" applyBorder="1" applyAlignment="1"><alignment horizontal="right" vertical="center"/></xf>'
               '<xf numFmtId="%d" fontId="3" fillId="0" borderId="1" xfId="0" applyNumberFormat="1" applyFont="1" applyBorder="1" applyAlignment="1"><alignment horizontal="right" vertical="center"/></xf>'
               '<xf numFmtId="%d" fontId="3" fillId="0" borderId="1" xfId="0" applyNumberFormat="1" applyFont="1" applyBorder="1" applyAlignment="1"><alignment horizontal="right" vertical="center"/></xf>'
               '<xf numFmtId="%d" fontId="3" fillId="0" borderId="1" xfId="0" applyNumberFormat="1" applyFont="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf>'
               '</cellXfs></styleSheet>' % (FMT_CURRENCY, FMT_PERCENT, FMT_INT, FMT_NUMBER, FMT_DATE))

    # 组装 zip
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("xl/workbook.xml", workbook)
        z.writestr("xl/_rels/workbook.xml.rels", wb_rels)
        z.writestr("xl/styles.xml", styles)
        z.writestr("docProps/core.xml", core_props)
        for i, sh in enumerate(sheets):
            z.writestr("xl/worksheets/sheet%d.xml" % (i + 1),
                       _sheet_xml(sh.get("name", "Sheet%d" % (i + 1)),
                                  # 小标题取键：section_title（_adapt_xlsx 的规范键）优先，
                                  # 兼容 caption（本渲染器原生 demo 键）。若只认 caption，
                                  # 经适配层渲染时每页小标题会整段丢失（chart 版两键兼容）。
                                  sh.get("section_title", sh.get("caption", "")),
                                  sh.get("headers", []),
                                  sh.get("rows", []),
                                  sh.get("note", ""),
                                  # 免责声明只落最后一张表下方（与顶部落款两句两处）
                                  constants.disclaimer(outline.get("topic"))
                                  if i == len(sheets) - 1 else "",
                                  # 可见溯源落款：每张表顶部第一行
                                  sh.get("source", source),
                                  # 每列数字格式（显式优先，缺省自动识别）
                                  sh.get("col_fmts"),
                                  # 交付回执：只随最后一张表的免责同现
                                  constants.receipt_line(outline.get("receipt_tags"))
                                  if i == len(sheets) - 1 else "",
                                  # 来源总览：多份材料时随最后一张表出现（与免责/回执同属末段）
                                  constants.sources_overview(outline.get("sources"))
                                  if i == len(sheets) - 1 else ""))
    return out_path


def _self_test():
    """最小自测：渲染一次并断言**要点与小标题真写入**工作表 XML。

    走临时目录，不写 scripts/。断言要点与小标题（section_title / caption）真写入工作表 XML。
    """
    import tempfile, zipfile
    demo = {
        "title": "自测报表",
        "subtitle": "自测口径",
        "date": "2026-01-01",
        "source": "由 蒸馏成技能Skill 蒸馏产出",
        "sheets": [
            {"name": "甲表", "section_title": "甲表小标题",
             "headers": ["项目", "内容", "金额", "日期"],
             "rows": [["要点A", "内容A", 1234.5, "2026-01-01"],
                      ["要点B", "内容B", 6789, "2026-02-15"]],
             "col_fmts": ["text", "text", "currency", "date"]},
        ],
    }
    p = os.path.join(tempfile.mkdtemp(), "self.xlsx")
    build_xlsx(demo, p)
    assert os.path.getsize(p) > 0, "产物为空: %s" % p
    z = zipfile.ZipFile(p)
    blob = b"".join(z.read(n) for n in z.namelist() if n.endswith(".xml"))
    for must in ("自测报表", "甲表小标题", "要点A", "内容A", "要点B", "内容B",
                 constants.DISCLAIMER_MAIN,
                 constants.RECEIPT_PREFIX, constants.RECEIPT_BOUND):
        assert must.encode("utf-8") in blob, "xlsx 未写入内容: %s" % must
    assert "\uff08\u7a7a\uff09".encode("utf-8") not in blob, "xlsx 退回内置空表骨架"
    # 可见落款断言：顶部第一行必须有溯源落款（规范「顶部表头上方第一行」）
    sx = z.read("xl/worksheets/sheet1.xml").decode("utf-8")
    assert constants.FOOTER in sx, "标准表缺可见溯源落款（应在顶部第一行）"
    # Q1-d 全量搬运断言：源 2 行 → 数据行恰好占第 5、6 行，且无任何汇总痕迹（零预设维度）
    assert '<row r="5">' in sx and '<row r="6">' in sx, "默认未全量搬运（数据行缺失）"
    for w in ("合计", "小计", "汇总", "总计"):
        assert w not in sx, "默认产物出现汇总痕迹（应零预设维度）: %s" % w
    # 数字格式断言：金额列套 style 5（人民币 numFmt）且以真数值写入（非文本）
    st = z.read("xl/styles.xml").decode("utf-8")
    assert '<numFmt numFmtId="%d"' % FMT_CURRENCY in st, "styles.xml 缺金额数字格式定义"
    assert 's="5"' in sx, "金额列未套用金额格式样式（style 5）"
    assert "<v>1234.5</v>" in sx and "<v>6789</v>" in sx, "数字单元格未以数值形式写入"
    # 日期断言：日期列写「真日期序列值 + yyyy-mm-dd」，不再是 inlineStr 文本
    assert '<numFmt numFmtId="%d"' % FMT_DATE in st, "styles.xml 缺日期数字格式定义"
    assert 's="9"' in sx, "日期列未套用日期格式样式（style 9）"
    _ser = _date_serial("2026-01-01")
    assert _ser is not None and ("<v>%d</v>" % _ser) in sx, "日期未写成序列值（仍为文本）"
    # 字符串列不得被误折成数字（防「00123」类编号失真）
    assert 't="inlineStr"' in sx, "文本单元格未按文本写入"
    # 庚-4 / 癸-4：冻结行 = 表头所在行（落款+标题+口径+表头 = 4，topLeftCell=A5）
    assert 'ySplit="4"' in sx and 'topLeftCell="A5"' in sx, "冻结行数 ≠ 表头行"
    # 庚-13：自动筛选范围 = 表实际列数（4 列 A..D × 表头行→末数据行）
    assert '<autoFilter ref="A4:D6"/>' in sx, "筛选范围未覆盖表实际列数（庚-13）"
    # 癸-7：文档属性存在且不含任何工具指纹
    cp = z.read("docProps/core.xml").decode("utf-8")
    for _bad in ("openpyxl", "python-pptx", "xlwt", "pandas"):
        assert _bad not in cp.lower(), "文档属性泄露工具指纹: %s" % _bad
    # 庚-18：全部 XML/rels 必须良构（防前缀悬空 → Excel 提示修复）
    import xml.etree.ElementTree as _ET
    for _n in z.namelist():
        if _n.endswith((".xml", ".rels")):
            _ET.fromstring(z.read(_n))
    print("self-test PASS: %s (%d B, %d parts)"
          % (os.path.basename(p), os.path.getsize(p), len(z.namelist())))


if __name__ == "__main__":
    import argparse, json
    ap = argparse.ArgumentParser(description="生成 Excel 标准数据表（前置设计令牌库）")
    ap.add_argument("outline", nargs="?", help="大纲 JSON 路径")
    ap.add_argument("out", nargs="?", help="输出 .xlsx 路径")
    ap.add_argument("--mode", help="模板模式: biz/lean/report/warm/red/sky/teal/violet")
    ap.add_argument("--palette", help="配色族: amber/red/sky/teal/warm/ink/violet")
    ap.add_argument("--font", help="字体族: hei/song/kai/deng")
    ap.add_argument("--scale", help="字号规格: standard/compact/report")
    ap.add_argument("--self-test", action="store_true",
                    help="最小自测：渲染一次并断言要点与小标题真写入（走临时目录）")
    args = ap.parse_args()
    if args.self_test:
        _self_test()
        raise SystemExit(0)
    if args.outline and args.out:
        with open(args.outline, "r", encoding="utf-8") as f:
            demo = json.load(f)
        build_xlsx(demo, args.out, mode=args.mode, palette=args.palette,
                   font=args.font, scale=args.scale)
        print("生成:", args.out, "| 模式:", args.mode or "biz(默认)")
        raise SystemExit
    demo = {
        "title": "SkillHub 新功能精华萃取 · 报表",
        "subtitle": "2026-09 产品更新摘要 · 三大新功能数据透视",
        "date": "2026-09-30",
        "source": "由 蒸馏成技能Skill 蒸馏产出",
        "sheets": [
            {
                "name": "功能清单",
                "caption": "本次上线三大功能及前置条件",
                "headers": ["功能", "作用", "关键规则", "前置条件"],
                "rows": [
                    ["绑定 GitHub 账号", "后续导入/认领的入场券", "标准 OAuth 认证", "无"],
                    ["GitHub 一键批量导入", "60 秒内发布公开仓库 Skill", "单次≤5个；自动扫 SKILL.md", "已绑定 GitHub"],
                    ["ClawHub 镜像一键认领", "声明所有权并接管管理", "自动比对已镜像 Skill", "已绑定 GitHub"],
                ],
                "note": "数据来源：SkillHub 产品更新公告（完整原生萃取）",
            },
            {
                "name": "安全拦截阈值",
                "caption": "导入防护机制量化指标",
                "headers": ["拦截项", "阈值", "处置"],
                "rows": [
                    ["仓库归档体积", ">20 MiB", "拦截"],
                    ["候选目录体积", ">10 MiB", "拦截"],
                    ["文件数", ">200", "拦截"],
                    ["二进制文件", ".doc/.pdf/.png 等", "过滤并 Toast 提示"],
                ],
            },
        ],
    }
    import tempfile
    out = os.path.join(tempfile.mkdtemp(), "SkillHub_数据表.xlsx")
    build_xlsx(demo, out, mode=args.mode, palette=args.palette,
               font=args.font, scale=args.scale)
    print("生成:", out, "|", os.path.getsize(out), "bytes", "| 模式:", args.mode or "biz(默认)")
