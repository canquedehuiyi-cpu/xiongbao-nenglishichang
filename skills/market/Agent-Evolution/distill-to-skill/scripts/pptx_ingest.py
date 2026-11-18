# -*- coding: utf-8 -*-
"""
pptx_ingest.py —— PPTX 摄取（纯标准库·零第三方依赖）

PPTX 是 OOXML zip 包，正文在 ppt/slides/slideN.xml 的 <a:t> 元素里（UTF-8）。
本脚本用 zipfile 解包 + xml.etree 解析，UTF-8 直接解码，绝不裸读 xml、不猜编码。
返回按「幻灯片」分块的正文文本行列表；笔记页(noteSlide)一并抽取。

用法:
  python pptx_ingest.py <file.pptx>           # 打印正文（每页一空行分隔）
  python pptx_ingest.py <file.pptx> --json     # 输出 {"slides":[{"idx":1,"texts":[...]}]}
  from pptx_ingest import extract_pptx
  slides = extract_pptx("x.pptx")              # 返回 [{"idx":int,"texts":[...]}, ...]
"""
import sys, os, json, zipfile
import xml.etree.ElementTree as ET
import argparse

A = "http://schemas.openxmlformats.org/drawingml/2006/main"


def _q(tag):
    return "{%s}%s" % (A, tag)


def _text_of(el):
    return "".join(t.text or "" for t in el.iter(_q("t")))


def extract_pptx(path):
    """返回按幻灯片分块的列表：[{'idx':int,'texts':[str,...]}, ...]。"""
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
    slides = []
    # 收集 slideN.xml（N 升序）
    slide_files = sorted(
        [n for n in names if n.startswith("ppt/slides/slide") and n.endswith(".xml")],
        key=lambda n: int("".join(ch for ch in n if ch.isdigit()) or 0),
    )
    for i, sf in enumerate(slide_files, 1):
        try:
            root = ET.fromstring(zipfile.ZipFile(path).read(sf))
        except Exception:
            continue
        texts = [_text_of(el).strip() for el in root.iter(_q("p"))
                 if _text_of(el).strip()]
        slides.append({"idx": i, "texts": texts})
    # 笔记页（可选，附在对应 slide 后）
    note_files = sorted(
        [n for n in names if n.startswith("ppt/notesSlides/notesSlide") and n.endswith(".xml")],
        key=lambda n: int("".join(ch for ch in n if ch.isdigit()) or 0),
    )
    for i, nf in enumerate(note_files, 1):
        try:
            root = ET.fromstring(zipfile.ZipFile(path).read(nf))
        except Exception:
            continue
        ntexts = [_text_of(el).strip() for el in root.iter(_q("p"))
                  if _text_of(el).strip()]
        if ntexts and i - 1 < len(slides):
            slides[i - 1]["texts"] += ["（笔记）" + t for t in ntexts]
        else:
            slides.append({"idx": i, "texts": ["（笔记）" + t for t in ntexts]})
    return slides


def to_lines(slides):
    out = []
    for s in slides:
        out.append("【幻灯片 %d】" % s["idx"])
        out.extend(s["texts"])
        out.append("")
    return out


def _self_test():
    """离线自测：标准库手工造最小 pptx（两页），读回断言文本真被抽出。"""
    import tempfile, zipfile
    td = tempfile.mkdtemp()
    p = os.path.join(td, "min.pptx")
    def _slide(title, body):
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<p:sld xmlns:a="%s" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
            '<p:cSld><p:spTree><p:sp><p:txBody>'
            '<a:p><a:r><a:t>%s</a:t></a:r></a:p>'
            '<a:p><a:r><a:t>%s</a:t></a:r></a:p>'
            '</p:txBody></p:sp></p:spTree></p:cSld></p:sld>' % (A, title, body)
        )
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("ppt/slides/slide1.xml", _slide("第一页标题", "第一页要点").encode("utf-8"))
        z.writestr("ppt/slides/slide2.xml", _slide("第二页标题", "第二页要点").encode("utf-8"))
    slides = extract_pptx(p)
    assert len(slides) == 2, "页数应为 2，实得 %d" % len(slides)
    flat = ["".join(s["texts"]) for s in slides]
    for key in ("第一页标题", "第一页要点", "第二页标题", "第二页要点"):
        assert any(key in t for t in flat), "未抽出 %s：%s" % (key, flat)
    print("PASS extract_pptx：%d 页，文本齐" % len(slides))
    return 0


def main():
    ap = argparse.ArgumentParser(description="PPTX 摄取（纯标准库·UTF-8 解码）")
    ap.add_argument("--self-test", action="store_true", dest="self_test",
                    help="离线自测：手工造最小 pptx 读回断言（不改动任何外部文件）")
    ap.add_argument("file", nargs="?")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        raise SystemExit(_self_test())
    if not args.file:
        ap.error("缺少 file 参数")
    slides = extract_pptx(args.file)
    if args.json:
        print(json.dumps({"slides": slides}, ensure_ascii=False, indent=2))
    else:
        print("\n".join(to_lines(slides)).strip())


if __name__ == "__main__":
    main()
