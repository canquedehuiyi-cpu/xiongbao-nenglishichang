# -*- coding: utf-8 -*-
"""
verify_multiformat.py —— 跨格式一致性门禁（纯标准库·零第三方依赖）

保证「多格式同源」：比对 canonical outline 的模块标题集合，
逐一确认各产物（md/txt/docx/pptx）都含全部模块标题、且数量一致；
并比对 `paragraphs`（成段正文）存活——每段的开头片段必须出现在产物里。
模块缺失/数量不等/成段正文丢失 → exit≠0（fail-closed，不许交付）。
（pdf 无标准库文本解析，信任同源渲染，跳过比对但打印 SKIP。）

注意：本门禁查「模块集合/数量」与「成段正文存活」；内容一致性的根本保证是
distill_skeleton.render_formats 从同一 outline 确定性渲染（结构上不可能漂移）。
成段正文另设一条内容级断言，是因为它曾与要点列表分属两个容器键，
只验「模块标题在不在」照不出「成段正文整段没进产物」。

用法:
  python verify_multiformat.py --outline runs/<任务>/.work/outline.json \
        --files out/outline.md out/outline.txt out/outline.docx out/outline.pptx
"""
import sys, os, json, re, zipfile
import argparse

SEPS = ("、", "：", ":", "·", "—")
PARA_PROBE_LEN = 12          # 段落存活探针取每段开头 12 字（避免换行/空格差异误报）


def module_names(outline):
    names = []
    for s in outline.get("sections", []):
        h = s.get("heading") or s.get("h") or ""
        for sep in SEPS:
            h = h.split(sep)[-1]
        h = h.strip()
        if h:
            names.append(h)
    return names


def paragraph_probes(outline):
    """每节 paragraphs 的开头片段（见 PARA_PROBE_LEN）。空段落、过短段落跳过。"""
    out = []
    for s in outline.get("sections", []):
        for p in (s.get("paragraphs") or []):
            t = re.sub(r"\s+", "", str(p))
            if len(t) >= PARA_PROBE_LEN:
                out.append(t[:PARA_PROBE_LEN])
    return out


def extract_text(path):
    low = path.lower()
    if low.endswith((".md", ".txt")):
        return open(path, encoding="utf-8", errors="replace").read()
    if low.endswith(".docx"):
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from docx_ingest import extract_docx
        return "\n".join(extract_docx(path))
    if low.endswith(".pptx"):
        z = zipfile.ZipFile(path)
        buf = []
        for n in z.namelist():
            if re.match(r"ppt/slides/slide\d+\.xml$", n):
                x = z.read(n).decode("utf-8", "ignore")
                buf += re.findall(r"<a:t[^>]*>(.*?)</a:t>", x, re.S)
        return "\n".join(buf)
    return None   # pdf 等无标准库解析 → 信任同源


def main():
    ap = argparse.ArgumentParser(description="跨格式一致性门禁")
    ap.add_argument("--outline", required=True)
    ap.add_argument("--files", required=True, nargs="+")
    args = ap.parse_args()
    outline = json.load(open(args.outline, encoding="utf-8"))
    names = module_names(outline)
    paras = paragraph_probes(outline)
    ok = True
    for f in args.files:
        t = extract_text(f)
        if t is None:
            print("SKIP(信任同源): %s" % f)
            continue
        present = [n for n in names if n and n in t]
        missing = [n for n in names if n and n not in t]
        if missing:
            ok = False
            print("FAIL %s 缺模块(%d/%d): %s" % (f, len(present), len(names), missing))
        else:
            print("OK %s 模块 %d/%d 全在" % (f, len(present), len(names)))
        if paras:
            flat = re.sub(r"\s+", "", t)
            lost = [p for p in paras if p not in flat]
            if lost:
                ok = False
                print("FAIL %s 成段正文丢失(%d/%d): 例 %s"
                      % (f, len(paras) - len(lost), len(paras), lost[0]))
            else:
                print("OK %s 成段正文 %d/%d 全在" % (f, len(paras), len(paras)))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
