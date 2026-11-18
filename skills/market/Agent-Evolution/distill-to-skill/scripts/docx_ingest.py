# -*- coding: utf-8 -*-
"""
docx_ingest.py —— DOCX 摄取（纯标准库·零第三方依赖）

docx 是 OOXML zip 包，正文恒为 UTF-8 编码的 word/document.xml。
本脚本用 zipfile 解包 + xml.etree 解析，UTF-8 直接解码，
绝不裸读 xml、不靠宿主预览摘要、不猜编码 —— 从根上杜绝测试暴露的「编码有问题」报错。

用法:
  python docx_ingest.py <file.docx>            # 打印正文（段落一行、表格一行=" | "连接）
  python docx_ingest.py <file.docx> --json     # 输出 {"paragraphs":[...],"tables":[[...]]}
  from docx_ingest import extract_docx
  lines = extract_docx("x.docx")                # 返回按阅读顺序的文本行列表
"""
import sys, os, json, zipfile
import xml.etree.ElementTree as ET
import argparse

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _q(tag):
    return "{%s}%s" % (W, tag)


def _text_of(el):
    return "".join(t.text or "" for t in el.iter(_q("t")))


def extract_docx(path):
    """返回按文档阅读顺序的文本行列表（段落一行、表格一行=' | '连接单元格）。"""
    with zipfile.ZipFile(path) as z:
        data = z.read("word/document.xml")        # docx XML 恒 UTF-8
    root = ET.fromstring(data)
    body = root.find(_q("body"))
    if body is None:
        return []
    out = []
    for el in body:
        if el.tag == _q("p"):
            out.append(_text_of(el))
        elif el.tag == _q("tbl"):
            for tr in el.iter(_q("tr")):
                cells = [_text_of(tc) for tc in tr.findall(_q("tc"))]
                out.append(" | ".join(cells))
    return out


def _self_test():
    """离线自测：标准库手工造最小 docx（含段落+表格），读回断言文本真被抽出。"""
    import tempfile, zipfile
    td = tempfile.mkdtemp()
    p = os.path.join(td, "min.docx")
    xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="%s"><w:body>'
        '<w:p><w:r><w:t>正文甲</w:t></w:r></w:p>'
        '<w:p><w:r><w:t>正文乙</w:t></w:r></w:p>'
        '<w:tbl><w:tr>'
        '<w:tc><w:p><w:r><w:t>表头A</w:t></w:r></w:p></w:tc>'
        '<w:tc><w:p><w:r><w:t>表头B</w:t></w:r></w:p></w:tc>'
        '</w:tr></w:tbl>'
        '</w:body></w:document>' % W
    )
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("word/document.xml", xml.encode("utf-8"))
    lines = extract_docx(p)
    assert "正文甲" in lines, "段落未抽出: %s" % lines
    assert "正文乙" in lines, "段落未抽出: %s" % lines
    assert any(" | " in ln and "表头A" in ln and "表头B" in ln for ln in lines), \
        "表格未抽出: %s" % lines
    print("PASS extract_docx：%d 行，段落+表格齐" % len(lines))
    return 0


def main():
    ap = argparse.ArgumentParser(description="DOCX 摄取（纯标准库·UTF-8 解码）")
    ap.add_argument("--self-test", action="store_true", dest="self_test",
                    help="离线自测：手工造最小 docx 读回断言（不改动任何外部文件）")
    ap.add_argument("file", nargs="?")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        raise SystemExit(_self_test())
    if not args.file:
        ap.error("缺少 file 参数")
    lines = extract_docx(args.file)
    if args.json:
        paras, tables = [], []
        for ln in lines:
            (tables if " | " in ln else paras).append(ln)
        print(json.dumps({"paragraphs": paras, "tables": tables},
                         ensure_ascii=False, indent=2))
    else:
        print("\n".join(lines))


if __name__ == "__main__":
    main()
