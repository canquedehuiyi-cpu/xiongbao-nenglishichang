# -*- coding: utf-8 -*-
"""
build_xlsx_chart_standard.py —— B/C 模式「图表分析报告」标准生成器（纯标准库·零第三方依赖）

以《销售数据分析报告》为标杆，把"数据表 + 图表"的版式、配色、数字格式、
图表尺寸、中文表达全部锁死在代码里。Agent 严禁手搓 xlsx。

设计令牌（与 PPT/DOCX/PDF 同源）：
  MAIN   = #16335B  主色（深蓝，标题/表头/柱状图主色）
  ACCENT = #E0A33E  强调（琥珀金，KPI 强调/饼图切片）
  AUX    = #2E6E9E  辅助（科技蓝，第二系列/折线）
  LIGHT  = #F4F6F9  浅底
  BODY   = #1F2733  正文
  ANNOT  = #6B7480  注释灰
  BORDER = #D8DEE6  边框

输入 outline（dict），支持两种模式：

【模式 R · 标准报告】推荐用于"图表分析报告"格式：
{
  "title":   "销售数据分析报告",
  "subtitle":"数据周期：2026年8月1日 - 2026年8月31日",
  "date":    "2026-09-30",
  "source":  "由 蒸馏成技能Skill 蒸馏产出",
  "kpi_cards": [                      # 仅首页显示，最多 6 项
    {"label":"总销售额", "value":1058572.06, "fmt":"currency"},
    {"label":"总订单数", "value":767,        "fmt":"int"},
    {"label":"客户数量", "value":189,        "fmt":"int"},
    {"label":"商品种类", "value":293,        "fmt":"int"},
    {"label":"日均销售额","value":35013.67,   "fmt":"currency"},
    {"label":"客单价",   "value":1415.15,    "fmt":"currency"},
  ],
  "sheets": [
     {
       "name": "总览",                 # 工作表名(≤31字)，必须中文
       "section_title": "结算状态分布", # 本页小标题
       "headers": ["结算状态", "订单行数", "占比(%)"],
       "rows": [
          ["已结算", 6400, 0.9240],
          ["未结算", 525,  0.0760],
       ],
       "col_fmts": ["text", "int", "percent"],  # 每列格式
       "chart": {
           "type": "pie",               # pie | column | bar | line
           "title": "结算状态占比",
           "data_label": True,
           "cat_col": 0,                # 类别列索引
           "val_col": 1,                # 数值列索引
       }
     },
     ...
  ]
}

【模式 S · 简单多表】保持兼容：
{
  "title": "报表总标题",
  "subtitle": "副标题",
  "sheets": [{"name":"Sheet1","headers":[],"rows":[],"chart":{...}}]
}

硬规：
  - 严禁 Agent 手搓 xlsx 渲染；统一走本生成器。
  - 图表与数据在同一工作表，绝不把图表挂到空 Sheet 上。
  - 工作表名、标题、表头必须中文；出现英文表名视为不合格。
  - 金额/百分比/整数/日期必须按固定 numFmt 输出，禁止浮点裸奔；日期写**真日期序列值 + `yyyy-mm-dd`**。
  - 标题用**强调色标题带**（与标准数据表同一房式，防两版 Excel 观感分裂）。
  - 饼图**逐扇区（dPt）**分配令牌色板，保证强调色/辅助色真的用上；折线/柱/条按令牌主色。
  - 图表 cat/val 引用按**实际数据行**生成区间，并写入 strCache/numCache（第三方预览器不显示空白图）。
  - 每页底部固定溯源落款 + 免责声明（两句两处）。
"""
import zipfile, datetime, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import design_tokens
import constants

MAIN_HEX   = "16335B"
ACCENT_HEX = "E0A33E"
AUX_HEX    = "2E6E9E"
LIGHT_HEX  = "F4F6F9"
BODY_HEX   = "1F2733"
ANNOT_HEX  = "6B7480"
BORDER_HEX = "D8DEE6"
WHITE_HEX  = "FFFFFF"
FONT_NAME  = "Microsoft YaHei"   # 默认字体（按所选模式覆盖）

# 图表配色盘（顺序使用，按所选模式覆盖）
CHART_COLORS = [
    "16335B", "E0A33E", "2E6E9E", "5B8DB8", "C97B2C",
    "7A9CBF", "F4C76A", "3A5A80", "D9A84E", "8FA8C0",
]

# 数字格式 id（自定义）
FMT_CURRENCY = 164   # ¥#,##0.00
FMT_PERCENT  = 165   # 0.00%
FMT_INT      = 166   # #,##0
FMT_NUMBER   = 167   # #,##0.00
FMT_DATE     = 168   # yyyy-mm-dd（真日期序列值，可排序/透视）


def _esc(s):
    s = "" if s is None else str(s)
    return (s.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;").replace("'", "&apos;"))


def _col_letter(idx):
    s = ""
    idx += 1
    while idx:
        idx, r = divmod(idx - 1, 26)
        s = chr(65 + r) + s
    return s


def _col_width(chars):
    return round(max(8.0, min(60.0, chars * 1.15 + 2.0)), 1)


def _sheet_ref(sheet_name, start, end):
    n = _esc(sheet_name)
    if re.search(r"[ '\[\]*?/\\:]", n):
        n = "'" + n.replace("'", "''") + "'"
    return "%s!$%s" % (n, start) if end is None else "%s!$%s:$%s" % (n, start, end)


def _num_val(v):
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v)
    try:
        return float(v)
    except Exception:
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
    """按列头/内容自动识别格式：currency/percent/int/number/text"""
    if not headers:
        return []
    fmts = []
    for c, h in enumerate(headers):
        hl = str(h).lower()
        # 1. 列头关键字
        if any(k in hl for k in ["金额", "销售额", "收入", "营收", "价格", "单价", "总额", "总值", "利润", "成本"]):
            fmts.append("currency"); continue
        if any(k in hl for k in ["占比", "百分比", "率", "比例", "%"]):
            fmts.append("percent"); continue
        if any(k in hl for k in ["数量", "订单数", "客户数", "件数", "次数", "人数", "行数"]):
            fmts.append("int"); continue
        # 日期列：列头像日期 且 首个样本是 ISO 日期（双条件，防误判）
        if any(k in hl for k in ["日期", "时间", "date"]) and _date_serial(_first_sample(rows, c)) is not None:
            fmts.append("date"); continue
        # 2. 按第一行数据推断
        sample = _first_sample(rows, c)
        nv = _num_val(sample)
        if nv is None:
            fmts.append("text"); continue
        if isinstance(sample, str) and "%" in sample:
            fmts.append("percent"); continue
        if abs(nv) >= 10000 and isinstance(sample, float):
            fmts.append("currency"); continue
        if abs(nv) < 100 and nv != int(nv):
            fmts.append("percent"); continue
        if nv == int(nv):
            fmts.append("int"); continue
        fmts.append("number")
    return fmts


def _first_sample(rows, c):
    for r in rows:
        if c < len(r):
            return r[c]
    return None


def _style_idx_for_col(fmt):
    """返回 cellXfs 索引：text=3, currency=5, percent=6, int=7, number=8, date=9"""
    return {"currency": 5, "percent": 6, "int": 7, "number": 8, "date": 9, "text": 3}.get(fmt, 3)


def _build_styles_xml():
    """构造 styles.xml：5 种字体 + 7 种填充 + 2 种边框 + 9 种 cellXfs + 4 种自定义数字格式"""
    # fonts: 0 默认 11pt / 1 大标题 16pt 粗 白（配强调色标题带）/ 2 表头 11pt 粗 白 / 3 正文 10pt 深灰
    #        4 说明 9pt 斜 灰 / 5 KPI 数值 14pt 粗 深蓝 / 6 KPI 标签 9pt 灰
    fonts = ('<fonts count="7">'
             '<font><sz val="10"/><name val="%s"/></font>'
             '<font><b/><sz val="16"/><color rgb="FF%s"/><name val="%s"/></font>'
             '<font><b/><sz val="11"/><color rgb="FF%s"/><name val="%s"/></font>'
             '<font><sz val="10"/><color rgb="FF%s"/><name val="%s"/></font>'
             '<font><i/><sz val="9"/><color rgb="FF%s"/><name val="%s"/></font>'
             '<font><b/><sz val="14"/><color rgb="FF%s"/><name val="%s"/></font>'
             '<font><sz val="9"/><color rgb="FF%s"/><name val="%s"/></font>'
             '</fonts>' % (FONT_NAME, WHITE_HEX, FONT_NAME, WHITE_HEX, FONT_NAME,
                          BODY_HEX, FONT_NAME, ANNOT_HEX, FONT_NAME, MAIN_HEX, FONT_NAME,
                          ANNOT_HEX, FONT_NAME))

    # fills: 0 none / 1 gray125 / 2 MAIN / 3 ACCENT / 4 LIGHT / 5 KPI 卡片底 / 6 隔行浅底
    fills = ('<fills count="7">'
             '<fill><patternFill patternType="none"/></fill>'
             '<fill><patternFill patternType="gray125"/></fill>'
             '<fill><patternFill patternType="solid"><fgColor rgb="FF%s"/></patternFill></fill>'
             '<fill><patternFill patternType="solid"><fgColor rgb="FF%s"/></patternFill></fill>'
             '<fill><patternFill patternType="solid"><fgColor rgb="FF%s"/></patternFill></fill>'
             '<fill><patternFill patternType="solid"><fgColor rgb="FFF4F6F9"/></patternFill></fill>'
             '<fill><patternFill patternType="solid"><fgColor rgb="FFF8FAFC"/></patternFill></fill>'
             '</fills>' % (MAIN_HEX, ACCENT_HEX, LIGHT_HEX))

    # borders: 0 none / 1 thin 全边框
    borders = ('<borders count="2">'
               '<border><left/><right/><top/><bottom/><diagonal/></border>'
               '<border><left style="thin"><color rgb="FFD8DEE6"/></left>'
               '<right style="thin"><color rgb="FFD8DEE6"/></right>'
               '<top style="thin"><color rgb="FFD8DEE6"/></top>'
               '<bottom style="thin"><color rgb="FFD8DEE6"/></bottom><diagonal/></border>'
               '</borders>')

    # numFmts: 自定义 5 种
    numfmts = ('<numFmts count="5">'
               '<numFmt numFmtId="%d" formatCode="¥#,##0.00"/>'
               '<numFmt numFmtId="%d" formatCode="0.00%%"/>'
               '<numFmt numFmtId="%d" formatCode="#,##0"/>'
               '<numFmt numFmtId="%d" formatCode="#,##0.00"/>'
               '<numFmt numFmtId="%d" formatCode="yyyy-mm-dd"/>'
               '</numFmts>' % (FMT_CURRENCY, FMT_PERCENT, FMT_INT, FMT_NUMBER, FMT_DATE))

    # cellXfs:
    # 0 默认 / 1 大标题(强调色标题带) / 2 表头 / 3 正文文本 / 4 说明
    # 5 金额 / 6 百分比 / 7 整数 / 8 数值 / 9 日期
    xfs = ('<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
           '<cellXfs count="10">'
           '<xf numFmtId="0"   fontId="0" fillId="0" borderId="0" xfId="0"/>'
           '<xf numFmtId="0"   fontId="1" fillId="3" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1"><alignment horizontal="left" vertical="center"/></xf>'
           '<xf numFmtId="0"   fontId="2" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf>'
           '<xf numFmtId="0"   fontId="3" fillId="0" borderId="1" xfId="0" applyFont="1" applyBorder="1" applyAlignment="1"><alignment horizontal="left" vertical="top" wrapText="1"/></xf>'
           '<xf numFmtId="0"   fontId="4" fillId="0" borderId="0" xfId="0" applyFont="1" applyAlignment="1"><alignment horizontal="left" vertical="center" wrapText="1"/></xf>'
           '<xf numFmtId="%d" fontId="3" fillId="0" borderId="1" xfId="0" applyNumberFormat="1" applyFont="1" applyBorder="1" applyAlignment="1"><alignment horizontal="right" vertical="center"/></xf>'
           '<xf numFmtId="%d" fontId="3" fillId="0" borderId="1" xfId="0" applyNumberFormat="1" applyFont="1" applyBorder="1" applyAlignment="1"><alignment horizontal="right" vertical="center"/></xf>'
           '<xf numFmtId="%d" fontId="3" fillId="0" borderId="1" xfId="0" applyNumberFormat="1" applyFont="1" applyBorder="1" applyAlignment="1"><alignment horizontal="right" vertical="center"/></xf>'
           '<xf numFmtId="%d" fontId="3" fillId="0" borderId="1" xfId="0" applyNumberFormat="1" applyFont="1" applyBorder="1" applyAlignment="1"><alignment horizontal="right" vertical="center"/></xf>'
           '<xf numFmtId="%d" fontId="3" fillId="0" borderId="1" xfId="0" applyNumberFormat="1" applyFont="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf>'
           '</cellXfs>' % (FMT_CURRENCY, FMT_PERCENT, FMT_INT, FMT_NUMBER, FMT_DATE))

    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '%s%s%s%s%s</styleSheet>' % (numfmts, fonts, fills, borders, xfs))


def _kpi_xml(kpi_cards, start_row=5):
    """生成 KPI 卡片区 XML，1 行 6 列等分；返回 (rows_xml, used_rows)"""
    if not kpi_cards:
        return "", 0
    cards = kpi_cards[:6]
    n = len(cards)
    # 每卡占 2 列（标签+数值），6 卡占 12 列；从 B 列开始
    col_start = 1
    cells = []
    merge_cells = []
    for i, card in enumerate(cards):
        c = col_start + i * 2
        label = str(card.get("label", ""))
        value = card.get("value", 0)
        fmt = card.get("fmt", "int")
        style_label = 4
        style_value = 5 if fmt == "currency" else (7 if fmt == "int" else 8)
        nv = _num_val(value)
        col_l = _col_letter(c)
        col_r = _col_letter(c + 1)
        # 标签跨两列
        cells.append('<c r="%s%d" s="%d" t="inlineStr"><is><t xml:space="preserve">%s</t></is></c>'
                     % (col_l, start_row, style_label, _esc(label)))
        merge_cells.append('<mergeCell ref="%s%d:%s%d"/>' % (col_l, start_row, col_r, start_row))
        # 数值
        if nv is not None:
            # 百分比数值以 0.924 存，格式会显示 92.40%
            if fmt == "percent" and nv > 1 and isinstance(value, (int, float)):
                nv = nv / 100.0
            cells.append('<c r="%s%d" s="%d"><v>%s</v></c>'
                         % (col_l, start_row + 1, style_value, nv))
        else:
            cells.append('<c r="%s%d" s="%d" t="inlineStr"><is><t xml:space="preserve">%s</t></is></c>'
                         % (col_l, start_row + 1, style_value, _esc(value)))
        merge_cells.append('<mergeCell ref="%s%d:%s%d"/>' % (col_l, start_row + 1, col_r, start_row + 1))

    row_xml = '<row r="%d">%s</row>' % (start_row, "".join(cells))
    # 第二行数值已在 cells 里，但 row r 需要单独一行
    # 修正：按 row 分组
    row1_cells = []
    row2_cells = []
    for i, card in enumerate(cards):
        c = col_start + i * 2
        label = str(card.get("label", ""))
        value = card.get("value", 0)
        fmt = card.get("fmt", "int")
        style_label = 4
        style_value = 5 if fmt == "currency" else (7 if fmt == "int" else 8)
        nv = _num_val(value)
        col_l = _col_letter(c)
        if nv is not None:
            if fmt == "percent" and nv > 1:
                nv = nv / 100.0
            vcell = '<c r="%s%d" s="%d"><v>%s</v></c>' % (col_l, start_row + 1, style_value, nv)
        else:
            vcell = '<c r="%s%d" s="%d" t="inlineStr"><is><t xml:space="preserve">%s</t></is></c>' % (col_l, start_row + 1, style_value, _esc(value))
        row1_cells.append('<c r="%s%d" s="%d" t="inlineStr"><is><t xml:space="preserve">%s</t></is></c>' % (col_l, start_row, style_label, _esc(label)))
        row2_cells.append(vcell)
    row_xml = '<row r="%d">%s</row><row r="%d">%s</row>' % (
        start_row, "".join(row1_cells), start_row + 1, "".join(row2_cells))
    return row_xml, 2, merge_cells


def _table_xml(headers, rows, start_row, col_fmts, col_start=1):
    """生成数据表 XML，支持从任意列开始（col_start 为 0-based）；返回 (rows_xml, n_rows, merge_cells)"""
    merge_cells = []
    # 表头行
    hdr_cells = []
    for c, h in enumerate(headers):
        ref = "%s%d" % (_col_letter(col_start + c), start_row)
        hdr_cells.append('<c r="%s" s="2" t="inlineStr"><is><t xml:space="preserve">%s</t></is></c>'
                         % (ref, _esc(h)))
    rows_xml = ['<row r="%d">%s</row>' % (start_row, "".join(hdr_cells))]
    # 数据行
    for i, row in enumerate(rows):
        ridx = start_row + 1 + i
        row_cells = []
        for c, v in enumerate(row):
            ref = "%s%d" % (_col_letter(col_start + c), ridx)
            fmt = col_fmts[c] if c < len(col_fmts) else "text"
            if fmt == "date":
                ser = _date_serial(v)
                if ser is not None:
                    row_cells.append('<c r="%s" s="9"><v>%d</v></c>' % (ref, ser))
                    continue
                fmt = "text"  # 不像日期 → 退回文本，不硬转
            style = _style_idx_for_col(fmt)
            nv = _num_val(v)
            if nv is not None and fmt != "text":
                if fmt == "percent" and nv > 1 and isinstance(v, (int, float)):
                    nv = nv / 100.0
                row_cells.append('<c r="%s" s="%d"><v>%s</v></c>' % (ref, style, nv))
            else:
                row_cells.append('<c r="%s" s="%d" t="inlineStr"><is><t xml:space="preserve">%s</t></is></c>'
                                 % (ref, style, _esc(v)))
        rows_xml.append('<row r="%d">%s</row>' % (ridx, "".join(row_cells)))
    return "".join(rows_xml), len(rows) + 1, merge_cells


def _worksheet_xml_report(idx, sh, outline, has_chart, chart_idx):
    """标准报告版式：标题带 → KPI（首页）→ 小标题 → 左侧表 + 右侧图 → 落款"""
    title = outline.get("title", "数据分析报告")
    subtitle = outline.get("subtitle", "")
    source = outline.get("source", constants.FOOTER)
    kpi_cards = outline.get("kpi_cards", []) if idx == 0 else []
    section_title = sh.get("section_title", sh.get("caption", ""))

    headers = sh.get("headers", [])
    rows = sh.get("rows", [])
    col_fmts = sh.get("col_fmts", []) or _detect_col_fmts(headers, rows)

    # 先做版式游标演算：冻结行必须覆盖到**表头行**（否则一往下滚表头就没了）
    _cur = 4
    if kpi_cards:
        _cur += 2 + 1          # KPI 卡片占 2 行 + 空 1 行
    if section_title:
        _cur += 1              # 小标题 1 行
    table_start_row = _cur

    parts = []
    parts.append('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>')
    # xmlns:r 必须声明：本页有 <drawing r:id="rId1"/>，前缀悬空会让 XML 不合法（Excel 会提示修复）
    parts.append('<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">')
    # 冻结行 = 表头所在行（标题 / KPI / 小标题 / 表头一并冻住），topLeftCell 指向表头下一行
    parts.append('<sheetViews><sheetView workbookViewId="0">'
                 '<pane ySplit="%d" topLeftCell="A%d" activePane="bottomLeft" state="frozen"/>'
                 '</sheetView></sheetViews>' % (table_start_row, table_start_row + 1))

    # 列宽：A 列留空，B-F 给表（约 5 列），G-O 给图，之后留空
    table_cols = max(len(headers), 1)
    chart_start_col = max(table_cols + 2, 6)  # 图表从 G 列开始
    total_cols = max(chart_start_col + 10, 15)
    widths = []
    widths.append('<col min="1" max="1" width="1.5" customWidth="1"/>')  # A 列边距
    for c in range(table_cols):
        maxlen = len(str(headers[c])) if c < len(headers) else 4
        for r in rows:
            if c < len(r):
                maxlen = max(maxlen, len(str(r[c])))
        widths.append('<col min="%d" max="%d" width="%s" customWidth="1"/>'
                      % (c + 2, c + 2, _col_width(maxlen)))
    # 图表区列宽
    for c in range(chart_start_col, total_cols + 1):
        widths.append('<col min="%d" max="%d" width="12" customWidth="1"/>' % (c + 1, c + 1))
    parts.append('<cols>%s</cols>' % "".join(widths))
    parts.append('<sheetData>')

    merges = []
    # 行1：大标题
    parts.append('<row r="1"><c r="B1" s="1" t="inlineStr"><is><t xml:space="preserve">%s</t></is></c></row>' % _esc(title))
    merges.append('<mergeCell ref="B1:%s1"/>' % _col_letter(total_cols))
    # 行2：副标题
    parts.append('<row r="2"><c r="B2" s="4" t="inlineStr"><is><t xml:space="preserve">%s</t></is></c></row>' % _esc(subtitle))
    merges.append('<mergeCell ref="B2:%s2"/>' % _col_letter(total_cols))

    cur_row = 4
    # KPI 卡片区（仅首页）
    if kpi_cards:
        kpi_xml, kpi_rows, kpi_merges = _kpi_xml(kpi_cards, start_row=cur_row)
        parts.append(kpi_xml)
        merges.extend(kpi_merges)
        cur_row += kpi_rows + 1  # 空一行

    # 小标题
    if section_title:
        parts.append('<row r="%d"><c r="B%d" s="1" t="inlineStr"><is><t xml:space="preserve">%s</t></is></c></row>'
                     % (cur_row, cur_row, _esc(section_title)))
        merges.append('<mergeCell ref="B%d:%s%d"/>' % (cur_row, _col_letter(chart_start_col - 1), cur_row))
        cur_row += 1

    # 数据表（左侧，从 B 列开始）——table_start_row 已在上方版式演算定死（单一事实源）
    assert cur_row == table_start_row, "版式游标与冻结行演算不一致（%d vs %d）" % (cur_row, table_start_row)
    table_xml, table_nrows, table_merges = _table_xml(headers, rows, table_start_row, col_fmts, col_start=1)
    parts.append(table_xml)
    merges.extend(table_merges)
    cur_row += table_nrows + 1

    # 落款（溯源）+ 来源总览 + 免责声明（合规）——紧邻不合并
    footer_row = max(cur_row, 20)
    parts.append('<row r="%d"><c r="B%d" s="4" t="inlineStr"><is><t xml:space="preserve">%s</t></is></c></row>'
                 % (footer_row, footer_row, _esc(source)))
    merges.append('<mergeCell ref="B%d:%s%d"/>' % (footer_row, _col_letter(total_cols), footer_row))
    nxt = footer_row + 1
    # 来源总览（多份材料时）：紧贴落款之下、免责之上
    ov = constants.sources_overview(outline.get("sources"))
    if ov:
        parts.append('<row r="%d"><c r="B%d" s="4" t="inlineStr"><is><t xml:space="preserve">%s</t></is></c></row>'
                     % (nxt, nxt, _esc(ov)))
        merges.append('<mergeCell ref="B%d:%s%d"/>' % (nxt, _col_letter(total_cols), nxt))
        nxt += 1
    drow = nxt
    parts.append('<row r="%d"><c r="B%d" s="4" t="inlineStr"><is><t xml:space="preserve">%s</t></is></c></row>'
                 % (drow, drow, _esc(constants.disclaimer(outline.get("topic")))))
    merges.append('<mergeCell ref="B%d:%s%d"/>' % (drow, _col_letter(total_cols), drow))
    # 交付回执（闭环·反馈口）：紧跟免责之下一行
    rrow = drow + 1
    parts.append('<row r="%d"><c r="B%d" s="4" t="inlineStr"><is><t xml:space="preserve">%s</t></is></c></row>'
                 % (rrow, rrow, _esc(constants.receipt_line(outline.get("receipt_tags")))))
    merges.append('<mergeCell ref="B%d:%s%d"/>' % (rrow, _col_letter(total_cols), rrow))

    parts.append('</sheetData>')
    # 自动筛选：范围 = 数据表实际列数 × （表头行 → 末数据行），末列不许漏（庚-13）
    if rows:
        _tcols = max(len(headers), max((len(r) for r in rows), default=0), 1)
        parts.append('<autoFilter ref="B%d:%s%d"/>'
                     % (table_start_row, _col_letter(1 + _tcols - 1), table_start_row + len(rows)))
    parts.append('<mergeCells count="%d">%s</mergeCells>' % (len(merges), "".join(merges)))
    if has_chart:
        parts.append('<drawing r:id="rId1"/>')
    parts.append('</worksheet>')
    # 返回几何：图表起始列 + 表格表头行 + 数据行数（供图表引用按实际行数动态生成）
    return "".join(parts), chart_start_col, table_start_row, len(rows)


def recommend_chart_type(headers, rows):
    """按「数据形态 → 推荐图型」规则推荐图型（与 bc-output-standards「Excel 图表选型」表同源）。

    规则（可被用户一句话覆盖，Agent 无需凭记忆）：
      时间/序号列 + 数值列           → line（看走势）
      看占比（数值列全在 0~1 且合计≈1） → pie（看构成，类别 ≤7）
      分类列 + 数值列，类别 >8 或名称长 → bar（横过来）
      分类列 + 数值列，类别 ≤8        → column（比大小·兜底）
    """
    if not headers or not rows:
        return "column"
    ncol = max(len(headers), max((len(r) for r in rows), default=0))
    # 数值列 = 多数行为真数值的列；类别列 = 第一个非数值列
    num_cols, cat_col = [], None
    for c in range(ncol):
        vals = [r[c] for r in rows if c < len(r)]
        if vals and all(_date_serial(v) is None for v in vals) and \
                sum(1 for v in vals if _num_val(v) is not None) >= max(1, len(vals) // 2):
            num_cols.append(c)
        elif cat_col is None:
            cat_col = c
    if not num_cols:
        return "column"
    val_col = num_cols[0]
    h = str(headers[cat_col]).lower() if (cat_col is not None and cat_col < len(headers)) else ""
    if any(k in h for k in ["日期", "时间", "月份", "年", "月", "date", "time"]):
        return "line"
    nums = []
    for r in rows:
        if val_col < len(r):
            nv = _num_val(r[val_col])
            if nv is not None:
                nums.append(nv)
    if nums and len(nums) <= 7 and all(0 <= v <= 1 for v in nums) and abs(sum(nums) - 1.0) < 0.02:
        return "pie"
    n = len(rows)
    avg_len = (sum(len(str(r[cat_col])) for r in rows if cat_col < len(r)) / max(1, n)) if cat_col is not None else 0
    if n > 8 or avg_len >= 6:
        return "bar"
    return "column"


def _chart_xml(title, ctype, cat_range, val_range, series_name, data_label,
               colors=None, cat_vals=None, val_vals=None):
    """生成 chart1.xml（柱状/条形/饼图/折线）。

    庚-5：饼图按扇区逐点（dPt）分配令牌色板，保证强调色/辅助色真的用上；
    庚-8：cat/val 引用按**实际数据行**生成区间，并写入 strCache / numCache
          （防第三方预览器因缓存为空而显示空白图）。
    """
    colors = colors or CHART_COLORS
    base_color = colors[0]
    cat_vals = cat_vals or []
    val_vals = val_vals or []

    # 数据标签
    dLbls_common = ('<c:dLbls><c:showVal val="1"/><c:showCatName val="0"/>'
                    '<c:showSerName val="0"/><c:showPercent val="0"/></c:dLbls>') if data_label else ""
    pie_dLbls = ('<c:dLbls><c:showVal val="0"/><c:showCatName val="1"/>'
                 '<c:showSerName val="0"/><c:showPercent val="1"/></c:dLbls>') if data_label else ""

    tx_ref = ('<c:tx><c:strRef><c:f>%s</c:f><c:strCache><c:ptCount val="1"/>'
              '<c:pt idx="0"><c:v>%s</c:v></c:pt></c:strCache></c:strRef></c:tx>'
              % (val_range, _esc(series_name)))

    # 单系列统一色（column/bar/line）；饼图改用 dPt 逐扇区上色
    spPr = ('<c:spPr><a:solidFill xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            '<a:srgbClr val="%s"/></a:solidFill>'
            '<a:ln xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:noFill/></a:ln>'
            '</c:spPr>' % base_color)

    # 类别缓存 + 数值缓存（按实际点数写入，第三方预览器也画得出）
    cat_cache = ('<c:strCache><c:ptCount val="%d"/>%s</c:strCache>'
                 % (len(cat_vals),
                    "".join('<c:pt idx="%d"><c:v>%s</c:v></c:pt>' % (i, _esc(v))
                            for i, v in enumerate(cat_vals))))
    num_pts = []
    for i, v in enumerate(val_vals):
        nv = _num_val(v)
        num_pts.append('<c:pt idx="%d"><c:v>%s</c:v></c:pt>' % (i, 0 if nv is None else nv))
    num_cache = ('<c:numCache><c:formatCode>General</c:formatCode><c:ptCount val="%d"/>%s</c:numCache>'
                 % (len(val_vals), "".join(num_pts)))

    # 饼图：逐扇区（dPt）分配令牌色板，令牌色循环使用（强调色/辅助色因此真的出现）
    dpt_xml = ""
    if ctype in ("pie",):
        for i in range(len(val_vals)):
            col = colors[i % len(colors)]
            dpt_xml += ('<c:dPt><c:idx val="%d"/><c:invertIfNegative val="0"/><c:spPr>'
                        '<a:solidFill xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
                        '<a:srgbClr val="%s"/></a:solidFill></c:spPr></c:dPt>' % (i, col))

    ser_common = ('<c:ser><c:idx val="0"/><c:order val="0"/>%s%s%s'
                  '<c:cat><c:strRef><c:f>%s</c:f>%s</c:strRef></c:cat>'
                  '<c:val><c:numRef><c:f>%s</c:f>%s</c:numRef></c:val>'
                  '</c:ser>' % (tx_ref, spPr, dpt_xml, cat_range, cat_cache, val_range, num_cache))

    if ctype in ("column", "col"):
        plot = ('<c:barChart><c:barDir val="col"/><c:grouping val="clustered"/>'
                '<c:varyColors val="0"/>%s%s<c:gapWidth val="120"/>'
                '<c:axId val="100"/><c:axId val="101"/></c:barChart>'
                '<c:catAx><c:axId val="100"/><c:scaling><c:orientation val="minMax"/></c:scaling>'
                '<c:delete val="0"/><c:axPos val="b"/><c:majorGridlines/>'
                '<c:tickLblPos val="nextTo"/><c:crossAx val="101"/><c:crosses val="autoZero"/><c:auto val="1"/><c:lblAlgn val="ctr"/><c:lblOffset val="100"/></c:catAx>'
                '<c:valAx><c:axId val="101"/><c:scaling><c:orientation val="minMax"/></c:scaling>'
                '<c:delete val="0"/><c:axPos val="l"/><c:majorGridlines/>'
                '<c:numFmt formatCode="General" sourceLinked="1"/><c:tickLblPos val="nextTo"/><c:crossAx val="100"/><c:crosses val="autoZero"/><c:crossBetween val="between"/></c:valAx>'
                % (ser_common, dLbls_common))
    elif ctype in ("bar",):
        plot = ('<c:barChart><c:barDir val="bar"/><c:grouping val="clustered"/>'
                '<c:varyColors val="0"/>%s%s<c:gapWidth val="120"/>'
                '<c:axId val="100"/><c:axId val="101"/></c:barChart>'
                '<c:catAx><c:axId val="100"/><c:scaling><c:orientation val="minMax"/></c:scaling>'
                '<c:delete val="0"/><c:axPos val="l"/><c:majorGridlines/>'
                '<c:tickLblPos val="nextTo"/><c:crossAx val="101"/><c:crosses val="autoZero"/><c:auto val="1"/><c:lblAlgn val="ctr"/><c:lblOffset val="100"/></c:catAx>'
                '<c:valAx><c:axId val="101"/><c:scaling><c:orientation val="minMax"/></c:scaling>'
                '<c:delete val="0"/><c:axPos val="b"/><c:majorGridlines/>'
                '<c:numFmt formatCode="General" sourceLinked="1"/><c:tickLblPos val="nextTo"/><c:crossAx val="100"/><c:crosses val="autoZero"/><c:crossBetween val="between"/></c:valAx>'
                % (ser_common, dLbls_common))
    elif ctype in ("line",):
        plot = ('<c:lineChart><c:grouping val="standard"/>'
                '<c:varyColors val="0"/>%s%s'
                '<c:axId val="100"/><c:axId val="101"/></c:lineChart>'
                '<c:catAx><c:axId val="100"/><c:scaling><c:orientation val="minMax"/></c:scaling>'
                '<c:delete val="0"/><c:axPos val="b"/><c:majorGridlines/>'
                '<c:tickLblPos val="nextTo"/><c:crossAx val="101"/><c:crosses val="autoZero"/><c:auto val="1"/><c:lblAlgn val="ctr"/><c:lblOffset val="100"/></c:catAx>'
                '<c:valAx><c:axId val="101"/><c:scaling><c:orientation val="minMax"/></c:scaling>'
                '<c:delete val="0"/><c:axPos val="l"/><c:majorGridlines/>'
                '<c:numFmt formatCode="General" sourceLinked="1"/><c:tickLblPos val="nextTo"/><c:crossAx val="100"/><c:crosses val="autoZero"/><c:crossBetween val="between"/></c:valAx>'
                % (ser_common, dLbls_common))
    elif ctype in ("pie",):
        plot = ('<c:pieChart><c:varyColors val="1"/>%s%s<c:firstSliceAng val="0"/></c:pieChart>'
                % (ser_common, pie_dLbls))
    else:
        raise ValueError("不支持的 chart 类型: %s" % ctype)

    title_xml = ('<c:title><c:tx><c:rich><a:bodyPr xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"/>'
                 '<a:lstStyle xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"/>'
                 '<a:p xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
                 '<a:pPr><a:defRPr sz="1600" b="1"><a:solidFill><a:srgbClr val="%s"/></a:solidFill></a:defRPr></a:pPr>'
                 '<a:r><a:rPr sz="1600" b="1"><a:solidFill><a:srgbClr val="%s"/></a:solidFill></a:rPr><a:t>%s</a:t></a:r>'
                 '</a:p></c:rich></c:tx><c:overlay val="0"/></c:title>' % (BODY_HEX, BODY_HEX, _esc(title)))

    legend = ('<c:legend><c:legendPos val="r"/><c:overlay val="0"/></c:legend>'
              if ctype not in ("pie",) else "")

    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<c:chartSpace xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart" '
            'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<c:date1904 val="0"/><c:chart>%s<c:plotArea>%s</c:plotArea>%s<c:plotVisOnly val="1"/></c:chart></c:chartSpace>'
            % (title_xml, plot, legend))


def _drawing_xml(chart_rid, from_col, from_row, to_col, to_row):
    """图表锚定：从 from_col/from_row 到 to_col/to_row（0-based）"""
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<xdr:wsDr xmlns:xdr="http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing" '
            'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<xdr:twoCellAnchor editAs="oneCell">'
            '<xdr:from><xdr:col>%d</xdr:col><xdr:colOff>0</xdr:colOff><xdr:row>%d</xdr:row><xdr:rowOff>0</xdr:rowOff></xdr:from>'
            '<xdr:to><xdr:col>%d</xdr:col><xdr:colOff>0</xdr:colOff><xdr:row>%d</xdr:row><xdr:rowOff>0</xdr:rowOff></xdr:to>'
            '<xdr:graphicFrame>'
            '<xdr:nvGraphicFramePr><xdr:cNvPr id="1" name="图表"/><xdr:cNvGraphicFramePr><a:graphicFrameLocks noGrp="1"/></xdr:cNvGraphicFramePr></xdr:nvGraphicFramePr>'
            '<xdr:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/></xdr:xfrm>'
            '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/chart">'
            '<c:chart xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" r:id="%s"/>'
            '</a:graphicData></a:graphic>'
            '</xdr:graphicFrame><xdr:clientData/>'
            '</xdr:twoCellAnchor></xdr:wsDr>' % (from_col, from_row, to_col, to_row, chart_rid))


def _worksheet_xml_simple(idx, sh, outline):
    """兼容 simple 模式：标题 + 表 + 图"""
    return _worksheet_xml_report(idx, sh, outline, bool(sh.get("chart")), idx)


def build_xlsx_chart(outline, out_path, mode=None, palette=None, font=None, scale=None):
    """生成 Excel 图表分析报告。可选 token 参数（前置设计令牌库）：
    mode/palette/font/scale，含义同其他生成器；不选则默认 biz（与既有默认值一致）。"""
    global MAIN_HEX, ACCENT_HEX, AUX_HEX, LIGHT_HEX, BODY_HEX, ANNOT_HEX, BORDER_HEX, FONT_NAME, CHART_COLORS
    tok = design_tokens.resolve(mode=mode, palette=palette, font=font, scale=scale, fmt="xlsx")
    MAIN_HEX = tok["palette"]["MAIN"]
    ACCENT_HEX = tok["palette"]["ACCENT"]
    AUX_HEX = tok["palette"]["AUX"]
    LIGHT_HEX = tok["palette"]["LIGHT"]
    BODY_HEX = tok["palette"]["BODY"]
    ANNOT_HEX = tok["palette"]["ANNOT"]
    BORDER_HEX = tok["palette"]["BORDER"]
    FONT_NAME = tok["font_office"]
    CHART_COLORS = [MAIN_HEX, ACCENT_HEX, AUX_HEX, "5B8DB8", "C97B2C",
                    "7A9CBF", "F4C76A", "3A5A80", "D9A84E", "8FA8C0"]
    title = outline.get("title", "蒸馏图表报告")
    subtitle = outline.get("subtitle", "")
    date = outline.get("date") or datetime.date.today().isoformat()
    source = outline.get("source", constants.FOOTER)
    sheets = outline.get("sheets", [])
    if not sheets:
        sheets = [{"name": "数据", "headers": ["项目", "内容"], "rows": [["（空）", ""]]}]

    # 若未给 subtitle 但有 date，自动补一个标准副标题
    if not subtitle:
        subtitle = "数据周期：%s" % date

    # 兼容：simple 模式没有 section_title，用 caption
    for sh in sheets:
        if not sh.get("section_title") and sh.get("caption"):
            sh["section_title"] = sh["caption"]

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
    chart_sheets = [(i, sh) for i, sh in enumerate(sheets) if sh.get("chart")]
    for ci, (i, sh) in enumerate(chart_sheets):
        ct += ('<Override PartName="/xl/charts/chart%d.xml" '
               'ContentType="application/vnd.openxmlformats-officedocument.drawingml.chart+xml"/>' % (ci + 1))
        ct += ('<Override PartName="/xl/drawings/drawing%d.xml" '
               'ContentType="application/vnd.openxmlformats-officedocument.drawingml.spreadsheetDrawing+xml"/>' % (ci + 1))
    ct += '</Types>'

    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '<Relationship Id="rIdDocProps" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
            '</Relationships>')

    # 文档属性：只写品牌落款，**绝不写任何工具指纹**（癸-7；与标准表同源，防两版口径分裂）
    core_props = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                  '<cp:coreProperties '
                  'xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
                  'xmlns:dc="http://purl.org/dc/elements/1.1/">'
                  '<dc:title>%s</dc:title><dc:subject>%s</dc:subject>'
                  '<dc:creator>%s</dc:creator></cp:coreProperties>'
                  % (_esc(title), _esc(subtitle), _esc(source)))

    wb_sheets = []
    for i, sh in enumerate(sheets):
        name = _esc(sh.get("name", "Sheet%d" % (i + 1))[:31])
        wb_sheets.append('<sheet name="%s" sheetId="%d" r:id="rId%d"/>' % (name, i + 1, i + 1))
    workbook = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                '<sheets>%s</sheets></workbook>' % "".join(wb_sheets))

    wb_rels_parts = ['<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>' % (len(sheets) + 1)]
    for i in range(len(sheets)):
        wb_rels_parts.append('<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet%d.xml"/>'
                             % (i + 1, i + 1))
    wb_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
               '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">%s</Relationships>'
               % "".join(wb_rels_parts))

    styles = _build_styles_xml()

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("xl/workbook.xml", workbook)
        z.writestr("xl/_rels/workbook.xml.rels", wb_rels)
        z.writestr("xl/styles.xml", styles)
        z.writestr("docProps/core.xml", core_props)

        # worksheet xml + rels
        geom = {}
        for i, sh in enumerate(sheets):
            has_chart = bool(sh.get("chart"))
            ws_xml, chart_start_col, tstart, nrows = _worksheet_xml_report(i, sh, outline, has_chart, i)
            geom[i] = (chart_start_col, tstart, nrows)
            z.writestr("xl/worksheets/sheet%d.xml" % (i + 1), ws_xml)
            if has_chart:
                z.writestr("xl/worksheets/_rels/sheet%d.xml.rels" % (i + 1),
                           ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/drawing" Target="../drawings/drawing%d.xml"/>'
                            '</Relationships>' % (i + 1)))

        # chart + drawing
        for ci, (i, sh) in enumerate(chart_sheets):
            chart = sh["chart"]
            ctitle = chart.get("title", sh.get("section_title", sh.get("name", "图表")))
            data_label = chart.get("data_label", True)
            headers = sh.get("headers", [])
            rows = sh.get("rows", [])
            if len(headers) < 2 or not rows:
                continue
            # 癸-8：未显式给类型时由生成器按选型规则自动定（Agent 不必凭记忆；用户一句话可覆盖）
            ctype = (chart.get("type") or "").strip() or recommend_chart_type(headers, rows)

            chart_start_col, table_start_row, n_data = geom[i]
            cat_col = chart.get("cat_col", 0)
            val_col = chart.get("val_col", 1)
            # 庚-8：引用**实际数据行**（表从 B 列起，数据自表头下一行到末行），不再写死到第 100 行
            cl = _col_letter(1 + cat_col)
            vl = _col_letter(1 + val_col)
            data_first = table_start_row + 1
            data_last = table_start_row + n_data
            sheet_name = sh.get("name", "Sheet%d" % (i + 1))
            cat_range = _sheet_ref(sheet_name, "%s%d" % (cl, data_first), "%s%d" % (cl, data_last))
            val_range = _sheet_ref(sheet_name, "%s%d" % (vl, data_first), "%s%d" % (vl, data_last))
            series_name = headers[val_col] if val_col < len(headers) else "数值"
            cat_vals = [r[cat_col] if cat_col < len(r) else "" for r in rows]
            val_vals = [r[val_col] if val_col < len(r) else 0 for r in rows]

            z.writestr("xl/charts/chart%d.xml" % (ci + 1),
                       _chart_xml(ctitle, ctype, cat_range, val_range, series_name, data_label,
                                  cat_vals=cat_vals, val_vals=val_vals))
            z.writestr("xl/charts/_rels/chart%d.xml.rels" % (ci + 1),
                       ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>'))

            # 图表锚定区域：从 chart_start_col 到 chart_start_col+9，行 3-18
            chart_from_col = chart_start_col
            chart_from_row = 2  # 0-based，第3行
            chart_to_col = chart_start_col + 9
            chart_to_row = 17   # 0-based，第18行
            z.writestr("xl/drawings/drawing%d.xml" % (ci + 1),
                       _drawing_xml("rId1", chart_from_col, chart_from_row, chart_to_col, chart_to_row))
            z.writestr("xl/drawings/_rels/drawing%d.xml.rels" % (ci + 1),
                       ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/chart" Target="../charts/chart%d.xml"/>'
                        '</Relationships>' % (ci + 1)))

    return out_path


def _self_test():
    """离线自测：用最小带图表大纲渲一次，做**内容级 + 呈现级断言**：
    内容（小标题/表头/行值真写入）+ 图表 part 存在 + 数字格式/日期序列值/饼图 dPt/引用动态化。"""
    import tempfile, zipfile
    demo = {
        "title": "自测图表报表",
        "subtitle": "自测口径",
        "date": "2026-01-01",
        "source": "由 蒸馏成技能Skill 蒸馏产出",
        "topic": "biz",
        "kpi_cards": [{"label": "总量", "value": 1234, "fmt": "int"}],
        "sheets": [{
            "name": "甲表",
            "section_title": "甲表小标题",
            "headers": ["类目", "金额", "日期"],
            "rows": [["甲类", 1234.5, "2026-01-01"], ["乙类", 6789, "2026-02-15"]],
            "col_fmts": ["text", "currency", "date"],
            "chart": {"type": "pie", "title": "甲类占比",
                      "cat_col": 0, "val_col": 1},
        }],
    }
    td = tempfile.mkdtemp()
    out = os.path.join(td, "selftest.xlsx")
    build_xlsx_chart(demo, out)
    assert os.path.exists(out) and os.path.getsize(out) > 0, "未产出 xlsx"
    z = zipfile.ZipFile(out)
    names = z.namelist()
    blob = b"".join(z.read(n) for n in names)
    for key in ("甲表小标题", "类目", "甲类", "乙类"):
        assert key.encode("utf-8") in blob, "内容「%s」未写入任何 part" % key
    assert any("chart" in n for n in names), "未产出图表 part：%s" % names
    # 落款 + 免责（合规双句）
    assert constants.FOOTER.encode("utf-8") in blob, "图表报告缺溯源落款"
    assert constants.DISCLAIMER_MAIN.encode("utf-8") in blob, "图表报告缺免责声明"
    assert constants.RECEIPT_PREFIX.encode("utf-8") in blob, "图表报告缺交付回执"
    assert constants.RECEIPT_BOUND.encode("utf-8") in blob, "图表报告回执缺零内容边界"
    # 数字格式 + 强调色标题带（与标准表同房式）
    st = z.read("xl/styles.xml").decode("utf-8")
    assert '<numFmt numFmtId="%d"' % FMT_CURRENCY in st, "styles 缺金额数字格式"
    assert '<numFmt numFmtId="%d"' % FMT_DATE in st, "styles 缺日期数字格式"
    assert '<xf numFmtId="0"   fontId="1" fillId="3"' in st, "标题未用强调色标题带（庚-10 未收敛）"
    # 数据表：日期写真序列值（style 9），不写文本
    ws = z.read("xl/worksheets/sheet1.xml").decode("utf-8")
    assert 's="9"' in ws, "日期列未套用日期格式（style 9）"
    _ser = _date_serial("2026-01-01")
    assert _ser is not None and ("<v>%d</v>" % _ser) in ws, "日期未写成序列值"
    # 图表：饼图逐扇区 dPt ≥ 2；引用按实际数据行（表头行 8 → 数据 9~10，不再是 $X100）；缓存写实际点数
    cxml = z.read("xl/charts/chart1.xml").decode("utf-8")
    assert cxml.count("<c:dPt>") >= 2, "饼图未逐扇区配色（庚-5）"
    assert "甲表!$B9:$B10" in cxml and "甲表!$C9:$C10" in cxml, "图表引用未按实际数据行生成（庚-8）"
    assert '<c:ptCount val="2"/>' in cxml, "图表缓存未写入实际点数（庚-8）"
    # 癸-4 / 庚-4：冻结行 = 表头所在行（标题+KPI+小标题+表头 = 8，topLeftCell=A9）
    assert 'ySplit="8"' in ws and 'topLeftCell="A9"' in ws, "图表报告冻结行 ≠ 表头行"
    # 庚-13：筛选范围 = 数据表实际列数（表从 B 列起、3 列 → B..D）
    assert '<autoFilter ref="B8:D10"/>' in ws, "筛选范围未覆盖表实际列数（庚-13）"
    # 癸-7：文档属性存在且不含任何工具指纹
    assert "docProps/core.xml" in names, "图表报告缺文档属性"
    cp = z.read("docProps/core.xml").decode("utf-8")
    for _bad in ("openpyxl", "python-pptx", "xlwt", "pandas"):
        assert _bad not in cp.lower(), "文档属性泄露工具指纹: %s" % _bad
    # 庚-18：全部 XML/rels 必须良构（防 r:id 等前缀悬空 → Excel 提示修复）
    import xml.etree.ElementTree as _ET
    for _n in names:
        if _n.endswith((".xml", ".rels")):
            _ET.fromstring(z.read(_n))
    # 癸-8：选型规则做进生成器（时间列→折线 / 占比→饼 / 类别多或名长→条形 / 兜底柱形）
    assert recommend_chart_type(["月份", "销售额"], [["2026-01", 1], ["2026-02", 2]]) == "line"
    assert recommend_chart_type(["状态", "占比"], [["已结算", 0.9], ["未结算", 0.1]]) == "pie"
    assert recommend_chart_type(["客户名", "金额"], [["某某某某某某客户", i] for i in range(20)]) == "bar"
    assert recommend_chart_type(["等级", "数量"], [["甲", 1], ["乙", 2]]) == "column"
    print("PASS build_xlsx_chart：%d B，内容+图表+数字格式+日期+dPt+动态引用+冻结+筛选+XML良构 齐" % os.path.getsize(out))
    return 0


if __name__ == "__main__":
    import argparse, json
    ap = argparse.ArgumentParser(description="生成 Excel 图表分析报告（前置设计令牌库）")
    ap.add_argument("--self-test", action="store_true", dest="self_test",
                    help="离线自测：最小带图表大纲渲染 + 内容/图表 part 断言")
    ap.add_argument("outline", nargs="?", help="大纲 JSON 路径")
    ap.add_argument("out", nargs="?", help="输出 .xlsx 路径")
    ap.add_argument("--mode", help="模板模式: biz/lean/report/warm/red/sky/teal/violet")
    ap.add_argument("--palette", help="配色族: amber/red/sky/teal/warm/ink/violet")
    ap.add_argument("--font", help="字体族: hei/song/kai/deng")
    ap.add_argument("--scale", help="字号规格: standard/compact/report")
    args = ap.parse_args()
    if args.self_test:
        raise SystemExit(_self_test())
    if args.outline and args.out:
        with open(args.outline, "r", encoding="utf-8") as f:
            demo = json.load(f)
        build_xlsx_chart(demo, args.out, mode=args.mode, palette=args.palette,
                         font=args.font, scale=args.scale)
        print("生成:", args.out, "| 模式:", args.mode or "biz(默认)")
        raise SystemExit
    demo = {
        "title": "销售数据分析报告",
        "subtitle": "数据周期：2026年8月1日 - 2026年8月31日",
        "date": "2026-09-30",
        "source": "由 蒸馏成技能Skill 蒸馏产出",
        "kpi_cards": [
            {"label": "总销售额", "value": 1058572.06, "fmt": "currency"},
            {"label": "总订单数", "value": 767, "fmt": "int"},
            {"label": "客户数量", "value": 189, "fmt": "int"},
            {"label": "商品种类", "value": 293, "fmt": "int"},
            {"label": "日均销售额", "value": 35013.67, "fmt": "currency"},
            {"label": "客单价", "value": 1415.15, "fmt": "currency"},
        ],
        "sheets": [
            {
                "name": "总览",
                "section_title": "结算状态分布",
                "headers": ["结算状态", "订单行数", "占比(%)"],
                "rows": [
                    ["已结算", 6400, 0.9240],
                    ["未结算", 525, 0.0760],
                ],
                "col_fmts": ["text", "int", "percent"],
                "chart": {"type": "pie", "title": "结算状态占比", "data_label": True, "cat_col": 0, "val_col": 1},
            },
            {
                "name": "业务员销售排名",
                "section_title": "业务员销售排名",
                "headers": ["业务员", "销售金额", "销售数量", "订单数"],
                "rows": [
                    ["梁诚", 975643.80, 21093, 623],
                    ["周银", 51830.87, 1050, 53],
                    ["余丹", 30622.93, 698, 26],
                    ["销售2", 13457.96, 284, 36],
                    ["-", 13415.33, 323, 26],
                    ["销售1", 452.90, 12, 3],
                ],
                "col_fmts": ["text", "currency", "int", "int"],
                "chart": {"type": "column", "title": "业务员销售额", "data_label": True, "cat_col": 0, "val_col": 1},
            },
            {
                "name": "日销售趋势",
                "section_title": "每日销售趋势",
                "headers": ["日期", "销售额", "订单数"],
                "rows": [
                    ["2026-08-01", 32150.5, 23],
                    ["2026-08-02", 28400.0, 19],
                    ["2026-08-03", 41200.75, 31],
                    ["2026-08-04", 36500.0, 27],
                    ["2026-08-05", 29800.0, 21],
                ],
                "col_fmts": ["text", "currency", "int"],
                "chart": {"type": "line", "title": "每日销售趋势", "data_label": False, "cat_col": 0, "val_col": 1},
            },
        ],
    }
    import tempfile as _tf
    out = os.path.join(_tf.mkdtemp(), "销售单_图表分析.xlsx")
    build_xlsx_chart(demo, out, mode=args.mode, palette=args.palette,
                     font=args.font, scale=args.scale)
    print("生成:", out, "|", os.path.getsize(out), "bytes", "| 模式:", args.mode or "biz(默认)")
