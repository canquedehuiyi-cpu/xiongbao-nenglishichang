# -*- coding: utf-8 -*-
"""verify_baseline.py —— 内容级基线门禁（golden snapshot·纯标准库）

比对产出的解析后语义指纹，检测内容漂移。

本脚本对每个格式产物提取【解析后语义】的四档指纹，与 tests/golden.json 比对：

  ① 模块标题序列（强）—— 与大纲一致，逐字逐序；不等即 exit≠0
  ①′ 模块内容探针命中集（强）—— 各模块核心句与全部要点，在解析后文本里做子串命中；
      命中集合变化即 exit≠0
  ② 文本字符数（中）—— 允许 ±5%（字符数不受换行符差异影响，跨平台稳定）
  ③ 字节数（弱）—— 允许 ±10%，且仅同平台比对（跨平台换行/字体嵌入必漂）

不进指纹：字体名、XML 节点顺序、创建时间、压缩率。
docx/pptx/xlsx 都是 zip 容器，内部原始字节天然有差异 —— 故一律取【解析后语义】，
不对原始字节取 hash。

★ 覆盖边界声明 —— 「哪些变了会被抓、哪些不抓」写在这里，不靠人记：

  在范围内（本门禁的靶区 = 内容本体）：
    · 模块标题序列（强）        —— 逐字逐序，不等即 FAIL
    · 模块内容探针命中集（强）  —— 核心句与要点命中集合变化即 FAIL
    · 文本字符数（中）          —— ±5%
    · 字节区间（弱）            —— ±10%，仅同平台

  不在范围内（有意排除，不属内容本体）：
    · 页眉 / 页脚 / 落款（含盖戳语） / 页码编号等版式性文本
    · 字体名 / 颜色 / 留白 / 行距等版式属性
    · XML 节点顺序 / 创建时间 / 压缩率等容器层差异

  含义：改落款、改页脚文案，本门禁**不会响**（在边界内）；此类变更由人工与发布清单核对。
  要把落款或页脚也纳入拦截：把其文本加进下方 PROBES 即可，比对逻辑无需改动 ——
  探针命中集直接进强档指纹，加进去即被同等对待。

分级：
  真·内容漂移（强/中/弱）-> FAIL，阻断出包；
  环境差异提示（如基线跨平台）-> WARN，不阻断。提示级与漂移级分离上报。

用法：
  python verify_baseline.py --baseline [--root <包根>]        # 比对，漂移则 exit 1
  python verify_baseline.py --bless --reason "改了…" [--root]  # 更新基线（须给理由，写 bless_log）
  python verify_baseline.py --self-test                        # 离线自测
"""
import argparse
import datetime
import json
import os
import re
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
BYTES_TOL = 0.10
CHARS_TOL = 0.05
GOLDEN_NAME = os.path.join("tests", "golden.json")

# 固定基准大纲（指纹的唯一来源；改动它等同改基线口径）
DEMO = {
    "title": "基线基准大纲",
    "subtitle": "内容漂移检测",
    "date": "2026-10-02",
    "source": "由 蒸馏成技能Skill 蒸馏产出",
    "sections": [
        {"heading": "一、模块甲", "core": "甲的核心", "points": ["要点1", "要点2"]},
        {"heading": "二、模块乙", "core": "乙的核心", "points": ["要点A", "要点B"]},
        {"heading": "三、模块丙", "core": "丙的核心", "points": ["要点甲", "要点乙", "要点丙"]},
    ],
}
# pdf 无标准库文本解析 → 不进基线（信任同源渲染）
FORMATS = ["md", "txt", "docx", "pptx", "xlsx", "xlsx_chart"]

# 探针文本：核心句 + 每模块全部要点。只取标题序列时，某格式「要点整段丢失」
# 不会被发现（例如 _adapt_md 给 body 而 build_md 读 items，md 要点会全丢、标题却对得上）。
# 探针是在解析后文本里做子串命中，命中集合进强档指纹 —— 丢内容必然触发漂移告警。
PROBES = []
for _s in DEMO["sections"]:
    if _s.get("core"):
        PROBES.append(_s["core"])
    PROBES.extend(_s.get("points", []))


def _fmt_of(path):
    b = os.path.basename(path).lower()
    if b.endswith("_chart.xlsx"):
        return "xlsx_chart"
    ext = os.path.splitext(b)[1]
    return {".md": "md", ".txt": "txt", ".docx": "docx",
            ".pptx": "pptx", ".xlsx": "xlsx", ".pdf": "pdf"}.get(ext, ext.lstrip("."))


def _text_plain(p):
    return open(p, encoding="utf-8", errors="replace").read()


def _text_docx(p):
    sys.path.insert(0, HERE)
    from docx_ingest import extract_docx
    return "\n".join(extract_docx(p))


def _text_pptx(p):
    z = zipfile.ZipFile(p)
    buf = []
    for n in z.namelist():
        if re.match(r"ppt/slides/slide\d+\.xml$", n):
            x = z.read(n).decode("utf-8", "ignore")
            buf += re.findall(r"<a:t[^>]*>(.*?)</a:t>", x, re.S)
    return "\n".join(buf)


def _text_xlsx(p):
    z = zipfile.ZipFile(p)
    buf = []
    for n in z.namelist():
        if n.endswith("sharedStrings.xml") or re.match(r"xl/worksheets/sheet\d+\.xml$", n):
            x = z.read(n).decode("utf-8", "ignore")
            buf += re.findall(r"<t[^>]*>(.*?)</t>", x, re.S)
    return "\n".join(buf)


def extract_text(fmt, path):
    """取解析后语义文本；无法解析的格式返回 None（该类不打指纹）。"""
    try:
        if fmt in ("md", "txt"):
            return _text_plain(path)
        if fmt == "docx":
            return _text_docx(path)
        if fmt == "pptx":
            return _text_pptx(path)
        if fmt in ("xlsx", "xlsx_chart"):
            return _text_xlsx(path)
    except Exception:
        return None
    return None


def fingerprint(version="", out_dir=None):
    """渲染固定大纲 → 提取三段指纹。返回 (fp, failed)。"""
    sys.path.insert(0, HERE)
    from distill_skeleton import render_formats
    td = out_dir or tempfile.mkdtemp(prefix="golden_")
    produced, failed = render_formats(DEMO, FORMATS, td)
    want = [s["heading"] for s in DEMO["sections"]]
    formats = {}
    for p in produced:
        fmt = _fmt_of(p)
        t = extract_text(fmt, p)
        if t is None:
            continue
        formats[fmt] = {
            "headings": [h for h in want if h in t],   # ①按序列出实际出现的模块标题
            "headings_expect": len(want),
            "probe_hits": [k for k in PROBES if k in t],  # ①′模块内容（核心句/要点）命中集合
            "probe_expect": len(PROBES),
            "chars": len(t),                            # ②字符数（跨平台稳定）
            "bytes": os.path.getsize(p),                # ③字节数（仅同平台比对）
        }
    fp = {
        "schema": 2,
        "version": version,
        "platform": sys.platform,
        "formats": formats,
    }
    return fp, failed


def compare(cur, base):
    """比对当前指纹与基线。

    返回 (diffs, notes)：
      diffs = 真·内容漂移 —— 调用方须判 FAIL 并阻断出包；
      notes = 环境/口径差异提示 —— 只报 WARN，绝不计入漂移数。

    分开上报：跨平台换基（如基线在 Linux bless、在 Windows 复核）时字节段本就不同，
    「平台不同」按提示级处理、不计入漂移；提示级与漂移级分别上报，不靠字符串前缀过滤。
    """
    diffs, notes = [], []
    same_platform = (cur.get("platform") == base.get("platform"))
    for fmt, b in sorted(base.get("formats", {}).items()):
        c = cur.get("formats", {}).get(fmt)
        if not c:
            diffs.append("[强] 格式 %s 在本次渲染中缺失" % fmt)
            continue
        if c["headings"] != b["headings"]:
            diffs.append("[强] %s 模块标题序列变化: %s -> %s"
                         % (fmt, b["headings"], c["headings"]))
        b_probe = b.get("probe_hits")
        if b_probe is not None and c.get("probe_hits") != b_probe:
            lost = [k for k in b_probe if k not in c.get("probe_hits", [])]
            diffs.append("[强] %s 模块内容命中变化（基线 %d/%s -> 本次 %d/%s）%s"
                         % (fmt, len(b_probe), b.get("probe_expect"),
                            len(c.get("probe_hits", [])), c.get("probe_expect"),
                            ("；丢失: %s" % lost[:6]) if lost else ""))
        if b.get("chars"):
            d = abs(c["chars"] - b["chars"]) / float(b["chars"])
            if d > CHARS_TOL:
                diffs.append("[中] %s 文本字符数 %d -> %d（偏离 %.1f%%，超 ±%.0f%%）"
                             % (fmt, b["chars"], c["chars"], d * 100, CHARS_TOL * 100))
        if same_platform and b.get("bytes"):
            d = abs(c["bytes"] - b["bytes"]) / float(b["bytes"])
            if d > BYTES_TOL:
                diffs.append("[弱] %s 字节数 %d -> %d（偏离 %.1f%%，超 ±%.0f%%）"
                             % (fmt, b["bytes"], c["bytes"], d * 100, BYTES_TOL * 100))
    for fmt in sorted(set(cur.get("formats", {})) - set(base.get("formats", {}))):
        diffs.append("[强] 基线缺失格式 %s（本次新出现）" % fmt)
    if not same_platform:
        notes.append("[提示] 平台不同（基线 %s / 本次 %s）——字节段已跳过，只比结构；"
                     "此项为环境差异提示，不计入漂移。如需同平台基线，"
                     "请在本平台 `--bless --reason \"同步本平台基线\"`。"
                     % (base.get("platform"), cur.get("platform")))
    return diffs, notes


def golden_path(root):
    return os.path.join(root, GOLDEN_NAME)


def main():
    ap = argparse.ArgumentParser(description="内容级基线门禁（golden snapshot）")
    ap.add_argument("--baseline", action="store_true", help="与基线比对，漂移则 exit 1")
    ap.add_argument("--bless", action="store_true", help="更新基线（须同时给 --reason）")
    ap.add_argument("--reason", default=None, help="--bless 的理由（写入 bless_log 留痕）")
    ap.add_argument("--root", default=None, help="技能包根目录（默认：本脚本上一级）")
    ap.add_argument("--self-test", action="store_true", help="离线自测")
    args = ap.parse_args()
    root = args.root or os.path.dirname(HERE)

    if args.self_test:
        sys.exit(0 if _selftest() else 1)

    if args.bless:
        if not (args.reason or "").strip():
            sys.stderr.write("拒绝：--bless 必须同时给出 --reason（基线放宽须留痕）\n")
            sys.exit(2)
        fp, failed = fingerprint()
        # 版本号取自 _meta.json（有则用）
        try:
            fp["version"] = json.load(open(os.path.join(root, "_meta.json"),
                                           encoding="utf-8")).get("version", "")
        except Exception:
            pass
        gp = golden_path(root)
        log = []
        if os.path.isfile(gp):
            try:
                log = json.load(open(gp, encoding="utf-8")).get("bless_log", []) or []
            except Exception:
                log = []
        log.append({
            "at": datetime.datetime.now().isoformat(timespec="seconds"),
            "by": os.environ.get("USERNAME") or os.environ.get("USER") or "unknown",
            "version": fp["version"],
            "reason": args.reason.strip(),
        })
        fp["bless_log"] = log
        os.makedirs(os.path.dirname(gp), exist_ok=True)
        # newline="\n"：显式写 LF。Windows 下 open(...,"w") 默认把 \n 翻成 \r\n，
        # 会让 golden.json 成为包内唯一 CRLF 文件，违反全包 LF 纪律（且进 zip 后同样带 \r）。
        with open(gp, "w", encoding="utf-8", newline="\n") as f:
            json.dump(fp, f, ensure_ascii=False, indent=2, sort_keys=True)
        print("基线已更新: %s（第 %d 次 bless，理由: %s）" % (gp, len(log), args.reason.strip()))
        for fmt in sorted(fp["formats"]):
            v = fp["formats"][fmt]
            print("  %-11s 模块 %d/%d  字符 %d  字节 %d"
                  % (fmt, len(v["headings"]), v["headings_expect"], v["chars"], v["bytes"]))
        sys.exit(0)

    if not args.baseline:
        sys.stderr.write("用法: --baseline 比对 / --bless --reason … 更新 / --self-test\n")
        sys.exit(2)

    gp = golden_path(root)
    if not os.path.isfile(gp):
        print("SKIP: 无基线文件 %s（首版请先跑 --bless --reason \"建立基线\"）" % gp)
        sys.exit(2)

    base = json.load(open(gp, encoding="utf-8"))
    cur, failed = fingerprint()
    print("基线版本: %s（bless %d 次）  当前平台: %s / 基线平台: %s"
          % (base.get("version", "?"), len(base.get("bless_log", []) or []),
             cur["platform"], base.get("platform")))
    print("")
    diffs, notes = compare(cur, base)
    if notes:
        print("WARN（环境差异提示，不计入漂移、不阻断出包）:")
        for n in notes:
            print("  - %s" % n)
        print("")
    if diffs:
        print("VERDICT: FAIL —— 内容指纹漂移 %d 处：" % len(diffs))
        for d in diffs:
            print("  - %s" % d)
        print("")
        print("处置：确认是预期变化 -> verify_baseline.py --bless --reason \"…\" 更新基线；")
        print("      非预期 -> 回退本次改动。未确认前不许出包。")
        sys.exit(1)
    n = len(cur["formats"])
    print("VERDICT: PASS —— %d 个格式指纹与基线一致（模块标题序列 / 内容探针 / 字符数 / 字节区间）" % n)
    if failed:
        print("（渲染失败项: %s，不在基线范围）" % failed)
    sys.exit(0)


def _selftest():
    """自测 7 用例：① 指纹可复现；② 同源两次一致；③ 识别标题序列变化；④ 识别字符数偏离；
    ⑤ 识别字节区间偏离；⑥ 识别要点丢失；⑦ 跨平台只出提示、不计漂移。"""
    fp1, f1 = fingerprint()
    assert not f1, "渲染失败: %s" % f1
    assert fp1["formats"], "指纹为空"
    for fmt, v in fp1["formats"].items():
        assert v["headings"], "%s 未检出模块标题" % fmt
        assert v["chars"] > 0 and v["bytes"] > 0, "%s 计数异常" % fmt
    print("用例1 指纹提取: PASS（%d 格式，探针 %d 条）" % (len(fp1["formats"]), len(PROBES)))

    fp2, _ = fingerprint()
    d0, n0 = compare(fp2, fp1)
    assert not d0 and not n0, "同源渲染两次应完全一致，实得漂移: %s / 提示: %s" % (d0, n0)
    print("用例2 同源可复现（两次指纹一致）: PASS")

    bad = json.loads(json.dumps(fp1))
    bad["formats"]["md"]["headings"] = ["一、模块甲"]
    d, _ = compare(fp2, bad)
    assert any("模块标题序列变化" in x for x in d), "未识别标题序列变化: %s" % d
    print("用例3 识别标题序列变化（强）: PASS")

    bad2 = json.loads(json.dumps(fp1))
    bad2["formats"]["md"]["chars"] = 10
    d2, _ = compare(fp2, bad2)
    assert any("字符数" in x for x in d2), "未识别字符数偏离: %s" % d2
    print("用例4 识别字符数偏离（中）: PASS")

    bad3 = json.loads(json.dumps(fp1))
    bad3["formats"]["md"]["bytes"] = 10
    d3, _ = compare(fp2, bad3)
    assert any("字节数" in x for x in d3), "未识别字节数偏离: %s" % d3
    print("用例5 识别字节区间偏离（弱·同平台）: PASS")

    bad4 = json.loads(json.dumps(fp1))
    bad4["formats"]["md"]["probe_hits"] = []
    d4, _ = compare(fp2, bad4)
    assert any("模块内容命中变化" in x for x in d4), "未识别要点丢失: %s" % d4
    print("用例6 识别要点丢失（强档）: PASS")

    # 用例7：跨平台只出提示、不计入漂移。
    other = "linux" if fp1["platform"] != "linux" else "win32"
    fp_other = json.loads(json.dumps(fp1))
    fp_other["platform"] = other
    d7, n7 = compare(fp_other, fp1)
    assert not d7, "跨平台不得计入漂移，实得: %s" % d7
    assert n7 and any("平台不同" in x for x in n7), "跨平台应产出提示，实得: %s" % n7
    print("用例7 跨平台降级为提示（WARN 级·不计漂移）: PASS")

    print("self-test PASS")
    return True


if __name__ == "__main__":
    main()
