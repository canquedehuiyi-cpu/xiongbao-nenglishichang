# -*- coding: utf-8 -*-
"""
xlsx_ingest.py —— XLSX 摄取（纯标准库·零第三方依赖）

XLSX 是 OOXML zip 包：xl/sharedStrings.xml 存共享字符串，xl/worksheets/sheetN.xml
存单元格（引用 sharedStrings 或内联或数值）。本脚本用 zipfile + xml.etree 解析，
UTF-8 解码，按「工作表」还原行列文本。不按字符数分级（见 SKILL.md O3 大表规则），
只取可读文本供后续结构化提取。

用法:
  python xlsx_ingest.py <file.xlsx>           # 打印（每表一空行分隔，单元格用 | 连接）
  python xlsx_ingest.py <file.xlsx> --json     # 输出 {"sheets":[{"name":..,"rows":[[..]]}]}
  from xlsx_ingest import extract_xlsx
  sheets = extract_xlsx("x.xlsx")              # 返回 [{"name":str,"rows":[[str,...]]}, ...]
"""
import sys, os, json, zipfile, re
import xml.etree.ElementTree as ET
import argparse

MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def _qn(ns, tag):
    return "{%s}%s" % (ns, tag)


def _load_shared(z, data):
    """返回共享字符串列表（按 <si> 顺序）；支持富文本 <r><t>。"""
    if "xl/sharedStrings.xml" not in data:
        return []
    root = ET.fromstring(z.read("xl/sharedStrings.xml"))
    out = []
    for si in root.findall(_qn(MAIN, "si")):
        # 直接 <t> 或 富文本 <r><t>
        texts = [t.text or "" for t in si.iter(_qn(MAIN, "t"))]
        out.append("".join(texts))
    return out


def _sheet_name(z, data, sheet_file):
    """从 workbook.xml + rels 反查工作表名（尽力而为）。"""
    try:
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        rid_map = {r.get("Id"): r.get("Target") for r in rels}
        # sheet_file 形如 ppt/../sheet1.xml 实际是 xl/worksheets/sheet1.xml
        base = sheet_file.replace("xl/", "")
        name = None
        for sh in wb.findall(_qn(MAIN, "sheets") + "/" + _qn(MAIN, "sheet")):
            rid = sh.get(_qn(REL, "id"))
            tgt = rid_map.get(rid, "")
            tgt = tgt.lstrip("/").replace("xl/", "")
            if tgt == base or tgt.endswith(base):
                name = sh.get("name")
                break
        return name or base
    except Exception:
        return sheet_file


def extract_xlsx(path):
    with zipfile.ZipFile(path) as z:
        data = {n: True for n in z.namelist()}
        shared = _load_shared(z, data)
        sheet_files = sorted(
            [n for n in z.namelist() if n.startswith("xl/worksheets/sheet") and n.endswith(".xml")],
            key=lambda n: int("".join(ch for ch in n if ch.isdigit()) or 0),
        )
        sheets = []
        for sf in sheet_files:
            try:
                root = ET.fromstring(z.read(sf))
            except Exception:
                continue
            rows = []
            for row in root.iter(_qn(MAIN, "row")):
                cells = []
                for c in row.findall(_qn(MAIN, "c")):
                    t = c.get("t")
                    v = c.find(_qn(MAIN, "v"))
                    is_inline = c.find(_qn(MAIN, "is"))
                    val = ""
                    if t == "s" and v is not None:
                        try:
                            val = shared[int(v.text)]
                        except (ValueError, IndexError):
                            val = ""
                    elif t == "inlineStr" and is_inline is not None:
                        val = "".join(tt.text or "" for tt in is_inline.iter(_qn(MAIN, "t")))
                    elif v is not None:
                        val = v.text or ""
                    cells.append(val)
                if any(cells):
                    rows.append(cells)
            sheets.append({"name": _sheet_name(z, data, sf), "rows": rows})
    return sheets


def to_lines(sheets):
    out = []
    for s in sheets:
        out.append("【工作表 %s】" % s["name"])
        for r in s["rows"]:
            out.append(" | ".join(r))
        out.append("")
    return out


def _self_test():
    """离线自测：标准库手工造最小 xlsx（内联串+共享串+数值），读回断言三类均可抽。"""
    import tempfile, zipfile
    td = tempfile.mkdtemp()
    p = os.path.join(td, "min.xlsx")
    relns = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    ss = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<sst xmlns="%s"><si><t>共享甲</t></si><si><t>共享乙</t></si></sst>' % MAIN)
    sheet = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             '<worksheet xmlns="%s"><sheetData>'
             '<row r="1"><c r="A1" t="inlineStr"><is><t>列头甲</t></is></c>'
             '<c r="B1" t="inlineStr"><is><t>列头乙</t></is></c></row>'
             '<row r="2"><c r="A2" t="s"><v>0</v></c><c r="B2"><v>42</v></c></row>'
             '<row r="3"><c r="A3" t="s"><v>1</v></c></row>'
             '</sheetData></worksheet>' % MAIN)
    wb = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<workbook xmlns="%s" xmlns:r="%s"><sheets>'
          '<sheet name="甲表" sheetId="1" r:id="rId1"/></sheets></workbook>' % (MAIN, relns))
    wbrels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
              '<Relationship Id="rId1" Type="%s/worksheet" Target="worksheets/sheet1.xml"/>'
              '</Relationships>' % relns)
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("xl/sharedStrings.xml", ss.encode("utf-8"))
        z.writestr("xl/worksheets/sheet1.xml", sheet.encode("utf-8"))
        z.writestr("xl/workbook.xml", wb.encode("utf-8"))
        z.writestr("xl/_rels/workbook.xml.rels", wbrels.encode("utf-8"))
    sheets = extract_xlsx(p)
    assert sheets, "未抽到工作表"
    rows = sheets[0]["rows"]
    assert rows[0] == ["列头甲", "列头乙"], "内联串行错: %s" % rows[0]
    assert rows[1][0] == "共享甲" and rows[1][1] == "42", "共享串/数值行错: %s" % rows[1]
    assert rows[2][0] == "共享乙", "共享串行错: %s" % rows[2]
    print("PASS extract_xlsx：内联串/共享串/数值三类均抽出，表名=%s" % sheets[0]["name"])
    return 0


def main():
    ap = argparse.ArgumentParser(description="XLSX 摄取（纯标准库·UTF-8 解码）")
    ap.add_argument("--self-test", action="store_true", dest="self_test",
                    help="离线自测：手工造最小 xlsx 读回断言（不改动任何外部文件）")
    ap.add_argument("file", nargs="?")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        raise SystemExit(_self_test())
    if not args.file:
        ap.error("缺少 file 参数")
    sheets = extract_xlsx(args.file)
    if args.json:
        print(json.dumps({"sheets": sheets}, ensure_ascii=False, indent=2))
    else:
        print("\n".join(to_lines(sheets)).strip())


if __name__ == "__main__":
    main()
