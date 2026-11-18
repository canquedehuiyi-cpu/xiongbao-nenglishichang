# -*- coding: utf-8 -*-
"""
intake.py —— 统一多物料接料层（纯标准库·零第三方依赖）

收料端第一要务：用户投来的材料【永远是多份、且任意组合】——多链接、多网页、多文档
（txt/md/docx/pdf/pptx/xlsx/csv，一次十几个）、链接+文字、图片+文字、音视频+文字，
甚至三/四路混合；文字可能一次十万~五十万字。本脚本把这些【统一归一成一个 materials_plan】，
让下游 verify_sources（源完整性门禁）与 ingest_chunk（分块）按同一套单元对账，从结构上
消灭「漏接 / 漏蒸 / 崩坏」。

铁律（对齐 SKILL.md A0.3+）：
  - 每种形态一律按「N>=1」处理，绝不假设单一。
  - 任意 N 路组合并入【同一份】 materials_plan，不拆、不相互污染。
  - 单单元失败隔离：失败记入 plan.status="error"+note，不进 processed；verify_sources 会
    钉死（漏单元→exit≠0→不许出包）。
  - 媒体（图/音/视）委派 scripts/media_ingest.py（subprocess，复用其真分段/批量隔离/plan 产出）。

用法（可任意组合、重复）：
  python intake.py --url https://a.com --url https://b.com \
                   --file a.docx --file b.pdf --file "docs/*.txt" \
                   --file "a.docx;b.pdf;c.xlsx"   # 也支持分号同条多文件
                   --dir ./slides --text note.md --text - \
                   --out-dir runs/<任务>/.work/intake
  python intake.py --manifest spec.json --out-dir runs/<任务>/.work/intake

spec.json 形态：{"urls":[...],"files":[...],"dirs":[...],"texts":[...]}

产出（--out-dir）：
  materials_plan.json      : {"units":[{id,type,source,char_count,status,note,extraction_method,invisible_removed,invisible_groups}]}  全部单元（含失败）
  materials_processed.json : {"units":[{id,type,source,chars,extraction_method,invisible_removed}]}   仅成功提取单元
  corpus.txt               : 所有成功单元正文拼接（====[U001|type|source]==== 分隔），供 ingest_chunk.py 分块
  sources.json             : {sources:[{id,type,source,chars,status,extraction_method,invisible_removed,invisible_groups,note}],invisible_total,security_notes}
                             —— 逐份料的来源台账（N4 读取方式 / N7 来源追溯的唯一来源，
                                供结果声明与产物页脚「来源总览」引用）
  intake_summary.json      : {total,ok,failed,kinds:{},failed_units:[...],invisible_total,security_notes:[...]}

接料两问（缺一不可）：
  ① 这份材料能不能读（抽得出正文）
  ② 这份材料干不干净（有没有夹带不可见字符 —— 注入攻击面，一律先清再送下游，清到就如实报告）
"""
import sys, os, json, csv, glob, argparse, subprocess, tempfile

PY = sys.executable
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
import sanitize  # 接料清洗层（威胁模型）：清不可见字符并如实报告

# 每种形态「走了哪条路读出来的」——记进台账，供结果声明说清「怎么读的」。
# 取值是给人看的路名，不是内部实现名。
METHOD_OF = {
    "text": "文本直读",
    "csv": "表格直读",
    "docx": "Word 文档层",
    "pdf": "PDF 文本层",
    "pptx": "幻灯片文字层",
    "xlsx": "表格单元格",
    "web": "网页正文提取",
    "image": "图片识别",
    "audio": "音频转写",
    "video": "视频转写",
    "media": "媒体识别",
}

IMAGES = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tif", ".tiff"}
AUDIO = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac", ".wma"}
VIDEO = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".mpeg", ".mpg"}


def _kind_of(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".txt", ".md", ".markdown"):
        return "text"
    if ext == ".csv":
        return "csv"
    if ext == ".docx":
        return "docx"
    if ext == ".pdf":
        return "pdf"
    if ext in (".pptx", ".ppt"):
        return "pptx"
    if ext in (".xlsx", ".xlsm"):
        return "xlsx"
    if ext == ".doc":
        return "doc_legacy"
    if ext in IMAGES:
        return "image"
    if ext in AUDIO:
        return "audio"
    if ext in VIDEO:
        return "video"
    return "unknown"


def _read_text_file(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def _read_csv(path):
    rows = []
    with open(path, encoding="utf-8", errors="replace", newline="") as f:
        for r in csv.reader(f):
            rows.append(" | ".join(c for c in r))
    return "\n".join(rows)


def _ingest_local_text(kind, path):
    if kind == "csv":
        return _read_csv(path)
    return _read_text_file(path)


def _ingest_doc_like(kind, path):
    """docx/pdf/pptx/xlsx 走对应读取脚本（纯标准库）。"""
    if kind == "docx":
        import docx_ingest
        return "\n".join(docx_ingest.extract_docx(path))
    if kind == "pdf":
        import pdf_ingest
        return pdf_ingest.extract_pdf(path)
    if kind == "pptx":
        import pptx_ingest
        return "\n".join(pptx_ingest.to_lines(pptx_ingest.extract_pptx(path)))
    if kind == "xlsx":
        import xlsx_ingest
        return "\n".join(xlsx_ingest.to_lines(xlsx_ingest.extract_xlsx(path)))
    return ""


def _ingest_web(url, timeout=20, max_bytes=5 * 1024 * 1024):
    import web_ingest
    r = web_ingest.process_one(url, timeout, max_bytes)
    if r.get("blocks"):
        return r["blocks"][0]["text"], r.get("note", "")
    return "", r.get("note", "获取失败")


def _ingest_media_via_subprocess(paths, out_dir):
    """委派 media_ingest.py 批量处理，返回 [(id, type, source, text, ok, note), ...]。"""
    os.makedirs(out_dir, exist_ok=True)
    summary = os.path.join(out_dir, "media_summary.json")
    cmd = [PY, os.path.join(SCRIPT_DIR, "media_ingest.py"),
           "--files", ";".join(paths), "--out-dir", out_dir, "--summary", summary]
    try:
        subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=1800)
    except Exception as e:
        return [(None, "media", p, "", False, "media_ingest 调用失败：%s" % e) for p in paths]
    # 优先读 summary（含逐文件文本）
    results = []
    try:
        d = json.load(open(summary, encoding="utf-8"))
        items = d.get("results", d.get("units", []))
        for it in items:
            src = it.get("source", "")
            mtype = it.get("media_type", "media")
            blocks = it.get("blocks", []) or []
            text = "\n".join(b.get("text", "") for b in blocks if b.get("text"))
            ok = bool(text)
            note = it.get("note", "")
            results.append((None, mtype, src, text, ok, note))
    except Exception:
        results = []
    # summary 缺则退回 media_plan/processed
    if not results:
        try:
            plan = json.load(open(os.path.join(out_dir, "media_plan.json"), encoding="utf-8"))
            proc = json.load(open(os.path.join(out_dir, "media_processed.json"), encoding="utf-8"))
            ok_ids = {u.get("id") for u in proc.get("units", [])}
            for u in plan.get("units", []):
                results.append((u.get("id"), u.get("type", "media"), u.get("source", ""),
                                "", u.get("id") in ok_ids, ""))
        except Exception:
            results = [(None, "media", p, "", False, "media 门禁文件缺失") for p in paths]
    return results


def build_material_list(args, manifest):
    mats = []  # each: ("web"|"file"|"dir"|"text_raw", ref)
    if manifest:
        m = manifest
        for u in m.get("urls", []):
            mats.append(("web", u))
        for f in m.get("files", []):
            mats.append(("file", f))
        for d in m.get("dirs", []):
            mats.append(("dir", d))
        for t in m.get("texts", []):
            mats.append(("text_raw", t))
    for u in args.url:
        mats.append(("web", u))
    for raw in args.file:
        # 兼容分号分隔多文件：--file a.docx;b.pdf 等价于两次 --file
        for f in (part.strip() for part in raw.split(";") if part.strip()):
            # 支持简单 glob
            expanded = glob.glob(f)
            if expanded:
                for e in expanded:
                    mats.append(("file", e))
            else:
                mats.append(("file", f))
    for d in args.dir:
        mats.append(("dir", d))
    for t in args.text:
        mats.append(("text_raw", t))
    return mats


def main():
    ap = argparse.ArgumentParser(description="统一多物料接料层")
    ap.add_argument("--url", action="append", default=[])
    ap.add_argument("--file", action="append", default=[])
    ap.add_argument("--dir", action="append", default=[])
    ap.add_argument("--text", action="append", default=[],
                    help="文本文件；'-' 表示待从 stdin 读（少用）")
    ap.add_argument("--manifest", default=None)
    ap.add_argument("--out-dir", default="intake_out")
    ap.add_argument("--no-media", action="store_true",
                    help="跳过媒体委派（仅做文本/文档类接料）")
    args = ap.parse_args()

    manifest = None
    if args.manifest:
        manifest = json.load(open(args.manifest, encoding="utf-8"))

    mats = build_material_list(args, manifest)
    if not mats:
        sys.stderr.write("无任何投料；用法见脚本头。\n")
        sys.exit(2)

    os.makedirs(args.out_dir, exist_ok=True)

    plan_units = []
    processed_units = []
    corpus_parts = []
    failed_units = []
    source_ledger = []      # N4/N7 台账：逐份料的来源 + 读取方式 + 清洗情况
    security_report = []    # N3：清到不可见字符时给用户的一句如实报告
    kinds = {}
    uid = 0

    # 媒体路径先归集，统一一次委派
    media_paths = []

    def new_id():
        nonlocal uid
        uid += 1
        return "U%03d" % uid

    def add_unit(utype, source, text, note=""):
        uidn = new_id()
        kinds[utype] = kinds.get(utype, 0) + 1
        # N3 威胁模型：先清不可见字符（夹带面），再判能不能读；报告不含内部术语。
        clean, removed, groups = sanitize.sanitize_text(text)
        if removed:
            security_report.append(sanitize.report_line(source, removed, groups))
        text = clean
        method = METHOD_OF.get(utype, "")
        ok = bool(text and text.strip())
        status = "ok" if ok else "error"
        char_count = len(text) if text else 0
        plan_units.append({"id": uidn, "type": utype, "source": source,
                           "char_count": char_count, "status": status, "note": note,
                           "extraction_method": method, "invisible_removed": removed,
                           "invisible_groups": groups})
        source_ledger.append({"id": uidn, "type": utype, "source": source,
                              "chars": char_count, "status": status,
                              "extraction_method": method,
                              "invisible_removed": removed,
                              "invisible_groups": groups, "note": note})
        if ok:
            processed_units.append({"id": uidn, "type": utype,
                                    "source": source, "chars": char_count,
                                    "extraction_method": method,
                                    "invisible_removed": removed})
            corpus_parts.append("====[%s|%s|%s]====\n%s\n" % (uidn, utype, source, text))
        else:
            failed_units.append({"id": uidn, "type": utype, "source": source, "note": note})

    for mtype, ref in mats:
        try:
            if mtype == "web":
                text, note = _ingest_web(ref)
                add_unit("web", ref, text, note)
            elif mtype == "text_raw":
                if ref == "-":
                    text = sys.stdin.read()
                else:
                    text = _read_text_file(ref)
                add_unit("text", ref, text, "直接文本")
            elif mtype == "dir":
                for root, _, fns in os.walk(ref):
                    for fn in fns:
                        p = os.path.join(root, fn)
                        k = _kind_of(p)
                        if k == "unknown":
                            continue
                        if k in ("image", "audio", "video"):
                            media_paths.append(p)
                        else:
                            mats.append(("file", p))  # 延后到文件分支处理
            elif mtype == "file":
                k = _kind_of(ref)
                if k == "unknown":
                    uext = os.path.splitext(ref)[1].lower()
                    if uext in (".epub", ".mobi", ".azw3", ".azw"):
                        add_unit("unknown", ref, "",
                                 "电子书格式（%s）本包零依赖不解析，请先用阅读器导出 PDF/Word 再投" % uext)
                    else:
                        add_unit("unknown", ref, "", "不支持的格式，跳过")
                elif k in ("image", "audio", "video"):
                    media_paths.append(ref)
                elif k == "doc_legacy":
                    add_unit("doc_legacy", ref, "",
                             "旧版 .doc 二进制本包零依赖不解析，请另存为 .docx 再投")
                elif k in ("docx", "pdf", "pptx", "xlsx"):
                    text = _ingest_doc_like(k, ref)
                    add_unit(k, ref, text, "" if text.strip() else "未抽到正文（可能扫描版/无文本层）")
                else:  # text / csv
                    text = _ingest_local_text(k, ref)
                    add_unit(k, ref, text, "")
        except Exception as e:
            add_unit("error", ref, "", "接料异常：%s: %s" % (type(e).__name__, e))

    # 媒体统一委派（与文本/文档同一咽喉：一并清洗、记账、报告）
    if media_paths and not args.no_media:
        media_res = _ingest_media_via_subprocess(media_paths, os.path.join(args.out_dir, "media"))
        for mid, mtype, src, text, ok, note in media_res:
            add_unit(mtype, src, text, note)

    # 写产出
    with open(os.path.join(args.out_dir, "materials_plan.json"), "w", encoding="utf-8") as f:
        json.dump({"units": plan_units}, f, ensure_ascii=False, indent=2)
    with open(os.path.join(args.out_dir, "materials_processed.json"), "w", encoding="utf-8") as f:
        json.dump({"units": processed_units}, f, ensure_ascii=False, indent=2)
    with open(os.path.join(args.out_dir, "corpus.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(corpus_parts))
    # N4/N7 台账：逐份料的来源 + 读取方式 + 清洗情况（单一来源，供结果声明与页脚「来源总览」引用）
    with open(os.path.join(args.out_dir, "sources.json"), "w",
              encoding="utf-8", newline="\n") as f:
        json.dump({"sources": source_ledger,
                   "invisible_total": sum(u["invisible_removed"] for u in source_ledger),
                   "security_notes": security_report},
                  f, ensure_ascii=False, indent=2)
    summary = {
        "total": len(plan_units),
        "ok": len(processed_units),
        "failed": len(failed_units),
        "kinds": kinds,
        "failed_units": failed_units,
        "invisible_total": sum(u["invisible_removed"] for u in source_ledger),
        "security_notes": security_report,
    }
    with open(os.path.join(args.out_dir, "intake_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # 清到不可见字符时，明写在终端（用户能自己看到，不靠翻文件）
    for line in security_report:
        sys.stderr.write(line + "\n")

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
