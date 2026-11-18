# -*- coding: utf-8 -*-
"""
pdf_ingest.py —— PDF 摄取（纯标准库·零第三方依赖·best-effort）

PDF 不是 UTF-8 文本包（不像 docx/pptx），标准库无法直接读正文。本脚本做【尽力而为】提取：
  1. zip/file 字节中定位 stream…endstream 内容流；
  2. FlateDecode 流用 zlib 解压（无 filter 流直接用原始字节）；
  3. 从内容流解析 Tj / TJ 文本算子，抽取字面串与十六进制串；
  4. WinAnsi 高位字节做常见字符映射，其余按 latin-1 保字节。
扫描版 / 无文本层 / CJK 未带 ToUnicode 的 PDF 可能抽不出或抽出乱码 —— 此时返回空串 +
状态说明，由调用方降级（请用户补文字稿 / 传带文本层的 PDF），绝不崩、不静默造假。

用法:
  python pdf_ingest.py <file.pdf>           # 打印抽取正文
  python pdf_ingest.py <file.pdf> --json     # 输出 {"chars":int,"text":..., "note":...}
  from pdf_ingest import extract_pdf
  text = extract_pdf("x.pdf")                # 返回正文串（可能为空）
"""
import sys, os, json, re, zlib, argparse

# 极简 WinAnsiEncoding 高位映射（覆盖常见标点/符号；CJK 需 ToUnicode，未覆盖）
WINANSI = {
    0x85: "\u2026", 0x91: "\u2018", 0x92: "\u2019", 0x93: "\u201c",
    0x94: "\u201d", 0x95: "\u2022", 0x96: "\u2013", 0x97: "\u2014",
    0x80: "\u20ac", 0xA0: "\u00a0", 0xAB: "\u00ab", 0xBB: "\u00bb",
}


def _decode_bytes(b):
    """latin-1 保字节后，按 WinAnsi 映射常见高位字符。"""
    s = b.decode("latin-1", "replace")
    out = []
    for ch in s:
        o = ord(ch)
        if o in WINANSI:
            out.append(WINANSI[o])
        else:
            out.append(ch)
    return "".join(out)


def _parse_string_literal(s, i):
    """从 s[i]=='(' 开始，解析字面串，返回 (decoded_str, next_index)。"""
    j = i + 1
    depth = 1
    lit = []
    n = len(s)
    esc = {"n": "\n", "r": "\r", "t": "\t", "b": "\b", "f": "\f",
           "\\": "\\", "(": "(", ")": ")"}
    while j < n and depth > 0:
        cc = s[j]
        if cc == "\\":
            nxt = s[j + 1] if j + 1 < n else ""
            if nxt in "01234567":
                octal = s[j + 1:j + 4]
                try:
                    lit.append(chr(int(octal, 8) & 0xFF))
                except ValueError:
                    lit.append(nxt)
                j += 4
                continue
            lit.append(esc.get(nxt, nxt))
            j += 2
        elif cc == "(":
            depth += 1
            lit.append("(")
            j += 1
        elif cc == ")":
            depth -= 1
            if depth == 0:
                j += 1
                break
            lit.append(")")
            j += 1
        else:
            lit.append(cc)
            j += 1
    return "".join(lit), j


def _extract_text_from_content(data):
    """从单条内容流字节中抽 Tj/TJ 文本，返回字符串列表。"""
    s = data.decode("latin-1", "replace")
    out = []
    buf = []          # 累积 ('str', text)
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c == "(":
            txt, i = _parse_string_literal(s, i)
            buf.append(("str", txt))
        elif c == "<" and i + 1 < n and s[i + 1] != "<":
            j = i + 1
            hexd = []
            while j < n and s[j] != ">":
                hexd.append(s[j])
                j += 1
            j += 1
            try:
                raw = bytes.fromhex("".join(hexd).strip())
                buf.append(("str", _decode_bytes(raw)))
            except Exception:
                buf.append(("str", ""))
            i = j
        elif c == "[":
            buf = []          # TJ 数组内的串只算本数组
            i += 1
        elif c == "T" and s[i:i + 2] == "Tj":
            if buf:
                last = buf.pop()
                if last[0] == "str":
                    out.append(last[1])
            i += 2
        elif c == "T" and s[i:i + 2] == "TJ":
            texts = [t for (k, t) in buf if k == "str"]
            buf = []
            out.append("".join(texts))
            i += 2
        else:
            i += 1
    return out


def _extract_streams(raw):
    """返回所有 stream…endstream 块的解压后字节（FlateDecode 用 zlib，否则原字节）。"""
    chunks = []
    for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", raw, re.S):
        data = m.group(1)
        # 去掉尾部可能的多余空白
        try:
            dec = zlib.decompress(data)
        except Exception:
            dec = data
        chunks.append(dec)
    return chunks


def extract_pdf(path):
    """返回抽取的正文串（可能为空）。"""
    with open(path, "rb") as f:
        raw = f.read()
    chunks = _extract_streams(raw)
    texts = []
    for ch in chunks:
        texts += _extract_text_from_content(ch)
    body = "\n".join(t for t in texts if t.strip())
    return body


def _self_test():
    """离线自测：标准库手工造最小 PDF（未压缩内容流），读回断言文本真被抽出。

    覆盖三类文本算子：字面串 `(..)` / TJ 数组 `[(..) .. (..)] TJ` / 十六进制串 `<..>`。
    纯标准库、不依赖任何字体 —— 保证本自测在任何环境都能跑（不像 build_pdf 需中文字体）。
    """
    import tempfile
    content = (
        b"BT /F1 12 Tf (Hello Ingest) Tj ET\n"
        b"BT [(He) -20 (llo)] TJ ET\n"
        b"BT <576F726C64> Tj ET\n"
    )
    raw = (b"%PDF-1.4\n1 0 obj\n<<>>\nstream\n" + content
           + b"\nendstream\nendobj\n%%EOF\n")
    td = tempfile.mkdtemp()
    p = os.path.join(td, "min.pdf")
    with open(p, "wb") as f:
        f.write(raw)
    text = extract_pdf(p)
    for key in ("Hello Ingest", "Hello", "World"):
        assert key in text, "未抽出 %r：%r" % (key, text)
    print("PASS extract_pdf：字面串/十六进制串/TJ 数组三类均抽出")
    return 0


def main():
    ap = argparse.ArgumentParser(description="PDF 摄取（纯标准库·best-effort）")
    ap.add_argument("--self-test", action="store_true", dest="self_test",
                    help="离线自测：手工造最小 PDF 读回断言（不改动任何外部文件）")
    ap.add_argument("file", nargs="?")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        raise SystemExit(_self_test())
    if not args.file:
        ap.error("缺少 file 参数")
    text = extract_pdf(args.file)
    note = ""
    if not text.strip():
        note = "未抽到正文（可能为扫描版/无文本层/CJK 未带 ToUnicode）；请用户补文字稿或传带文本层的 PDF"
    if args.json:
        print(json.dumps({"chars": len(text), "text": text, "note": note},
                         ensure_ascii=False, indent=2))
    else:
        print(text if text.strip() else ("[空] " + note))


if __name__ == "__main__":
    main()
