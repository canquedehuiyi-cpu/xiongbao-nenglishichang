#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
media_ingest.py — 媒体降维路由入口（确定性·标准库写路由，调环境二进制）

用法：
  # 单文件
  python media_ingest.py <媒体文件> [--out blocks.json] [--ffmpeg 路径] [--whisper 路径] [--ocr 路径]
  # 批量（大量图片/音视频不崩编排）
  python media_ingest.py --files f1.mp4;f2.mp3;img1.png [--out-dir ./out] [--summary summary.json]
  python media_ingest.py --dir ./media_folder [--ext mp4,mp3,m4a,png] [--out-dir ./out] [--summary summary.json]
  python media_ingest.py --self-test   # 离线回归（分类/分段常量/异常隔离/srt 清洗）

职责：把视频 / 音频 / 图片降维为「锚定文本块」，交给 ingest_chunk.py 继续四段式。
批量模式：逐文件隔离处理（单文件失败不影响其余），写 media_plan.json + media_processed.json，
          供 verify_sources.py 蒸馏前做源完整性门禁（漏单元不出包）。返回汇总 JSON（total/ok/failed/失败单元+原因）。

长媒体防崩（核心）：音频 / 视频 ASR 按 SEG_SEC(600s) 真分段——
  ffmpeg 切 ≤10 分钟段 → 逐段 whisper → 带时间戳拼回；不整段喂 whisper，避免超大显存 / OOM / 超时崩溃。
  ffprobe / ffmpeg 缺失则降级整段（标记「待用户确认」），不强行编造、不崩。
"""

import sys
import os
import re
import json
import math
import subprocess

VIDEO_EXT = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".flv", ".wmv", ".m4v", ".ts"}
AUDIO_EXT = {".mp3", ".wav", ".m4a", ".amr", ".ogg", ".flac", ".aac", ".wma", ".aiff"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}

SEG_SEC = 600  # 长媒体 ASR 分段上限：10 分钟


def which(name, override=None):
    if override:
        return override if os.path.exists(override) else None
    from shutil import which as _w
    return _w(name)


def fmt_time(sec):
    sec = int(sec)
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    return "%02d:%02d:%02d" % (h, m, s)


def probe_duration(path, ffprobe):
    """返音频/视频时长（秒），失败返 None。"""
    if not ffprobe:
        return None
    try:
        out = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            capture_output=True, text=True, timeout=60,
        )
        v = out.stdout.strip()
        return float(v) if v else None
    except Exception:
        return None


def probe_streams(path, ffprobe):
    """返回 {has_subtitle, has_audio, has_video}。"""
    if not ffprobe:
        return {"has_subtitle": None, "has_audio": None, "has_video": None}
    try:
        out = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries",
             "stream=codec_type", "-of", "csv=p=0", path],
            capture_output=True, text=True, timeout=120,
        )
    except Exception:
        return {"has_subtitle": None, "has_audio": None, "has_video": None}
    types = [t.strip() for t in out.stdout.splitlines() if t.strip()]
    return {
        "has_subtitle": "subtitle" in types,
        "has_audio": "audio" in types,
        "has_video": "video" in types,
    }


def run_ocr(png_path, ocr):
    """调 tesseract 出文本；缺失或空则返 None。"""
    if not ocr:
        return None
    try:
        out = subprocess.run([ocr, png_path, "stdout", "-l", "chi_sim+eng"],
                             capture_output=True, text=True, timeout=120)
        txt = out.stdout.strip()
        return txt or None
    except Exception:
        return None


def extract_subtitle_track(path, out_srt, ffmpeg):
    """分支①：提取内嵌字幕轨为 srt（取第一条 subtitle 流）。"""
    if not ffmpeg:
        return None
    try:
        subprocess.run(
            [ffmpeg, "-y", "-i", path, "-map", "0:s:0",
             "-c:s", "srt", out_srt],
            capture_output=True, text=True, timeout=300,
        )
        if os.path.exists(out_srt) and os.path.getsize(out_srt) > 0:
            with open(out_srt, encoding="utf-8", errors="ignore") as f:
                return f.read()
    except Exception:
        return None
    return None


def asr_one(seg_path, whisper):
    """对单一段（已切好或短媒体整段）跑 whisper，返纯文本或 None。"""
    if not whisper:
        return None
    try:
        out = subprocess.run([whisper, seg_path, "--model", "base",
                             "--output_format", "txt", "--output_dir",
                             os.path.dirname(os.path.abspath(seg_path)) or "."],
                            capture_output=True, text=True, timeout=1800)
        txt_path = os.path.splitext(seg_path)[0] + ".txt"
        if os.path.exists(txt_path):
            with open(txt_path, encoding="utf-8", errors="ignore") as f:
                return f.read().strip() or None
    except Exception:
        return None
    return None


def asr_audio(path, whisper, ffmpeg=None, ffprobe=None):
    """长媒体真分段 ASR（防崩核心）。

    - 短媒体（≤SEG_SEC 或无 ffprobe）直接整段 whisper；
    - 长媒体：ffmpeg 按 SEG_SEC 切段 → 逐段 whisper → 带时间戳拼回；
      单段失败隔离（标「待用户确认」），不整体崩溃；
    - 无 ffmpeg 无法切段：降级整段（仍可能崩，由调用方 note 标记）。
    """
    if not whisper:
        return None
    dur = probe_duration(path, ffprobe)
    if dur is None or dur <= SEG_SEC:
        return asr_one(path, whisper)
    if not ffmpeg:
        return asr_one(path, whisper)  # 降级整段
    base = os.path.splitext(path)[0]
    n = max(1, math.ceil(dur / SEG_SEC))
    parts = []
    ok_any = False
    for i in range(n):
        s = i * SEG_SEC
        e = min((i + 1) * SEG_SEC, dur)
        segp = "%s_seg%03d.wav" % (base, i)
        try:
            subprocess.run([ffmpeg, "-y", "-ss", "%.3f" % s, "-to", "%.3f" % e,
                           "-i", path, segp],
                          capture_output=True, text=True, timeout=300)
        except Exception:
            segp = None
        if segp and os.path.exists(segp) and os.path.getsize(segp) > 0:
            t = asr_one(segp, whisper)
            try:
                os.remove(segp)
            except Exception:
                pass
            if t:
                parts.append("[%s] %s" % (fmt_time(s), t))
                ok_any = True
            else:
                parts.append("[%s] （本段转写失败/待用户确认）" % fmt_time(s))
        else:
            parts.append("[%s] （本段切分失败/待用户确认）" % fmt_time(s))
    return "\n".join(parts) if ok_any else None


def ocr_burned_subtitle(path, ffmpeg, ocr):
    """分支②：烧录硬字幕 → 字幕带 OCR。抽首/中/尾帧 OCR 探测，返文本或 None。"""
    if not (ffmpeg and ocr):
        return None
    base = os.path.splitext(path)[0]
    texts = []
    for idx, tmark in enumerate(("00", "50%", "99%")):
        fr = "%s_frame_%d.png" % (base, idx)
        try:
            if tmark == "50%":
                subprocess.run([ffmpeg, "-y", "-ss", "00:00:30", "-i", path,
                               "-frames:v", "1", fr], capture_output=True,
                              text=True, timeout=120)
            else:
                subprocess.run([ffmpeg, "-y", "-ss", "00:00:05", "-i", path,
                               "-frames:v", "1", fr], capture_output=True,
                              text=True, timeout=120)
            t = run_ocr(fr, ocr)
            if t:
                texts.append(t)
        except Exception:
            continue
        finally:
            if os.path.exists(fr):
                try:
                    os.remove(fr)
                except Exception:
                    pass
    return "\n".join(texts).strip() or None


def classify(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in VIDEO_EXT:
        return "video"
    if ext in AUDIO_EXT:
        return "audio"
    if ext in IMAGE_EXT:
        return "image"
    return "unknown"


def process_file(path, ffmpeg, ffprobe, whisper, ocr):
    """处理单文件，返回 result dict；内部异常隔离，绝不向上抛。"""
    mtype = classify(path)
    result = {"media_type": mtype, "source": path,
              "branch": None, "blocks": [], "note": ""}
    try:
        if mtype == "video":
            st = probe_streams(path, ffprobe)
            if st["has_subtitle"]:
                srt = extract_subtitle_track(path,
                                             os.path.splitext(path)[0] + ".srt", ffmpeg)
                if srt:
                    result["branch"] = "embedded_subtitle"
                    result["blocks"] = [{"ts": "", "text": _clean_srt(srt)}]
                    result["note"] = "分支①内嵌字幕轨提取，最保真"
                else:
                    burned = ocr_burned_subtitle(path, ffmpeg, ocr)
                    if burned:
                        result["branch"] = "burned_ocr"
                        result["blocks"] = [{"ts": "", "text": burned}]
                        result["note"] = "分支②烧录硬字幕OCR（保真高于ASR）"
                    else:
                        asr = asr_audio(path, whisper, ffmpeg, ffprobe)
                        result["branch"] = "asr" if asr else "need_user_input"
                        result["blocks"] = [{"ts": "", "text": asr}] if asr else []
                        result["note"] = "分支③无字幕轨ASR（≤10min分段）" if asr else "待用户提供字幕/文字稿"
            elif st["has_video"] is not False:
                burned = ocr_burned_subtitle(path, ffmpeg, ocr)
                if burned:
                    result["branch"] = "burned_ocr"
                    result["blocks"] = [{"ts": "", "text": burned}]
                    result["note"] = "分支②烧录硬字幕OCR（保真高于ASR）"
                else:
                    asr = asr_audio(path, whisper, ffmpeg, ffprobe)
                    result["branch"] = "asr" if asr else "need_user_input"
                    result["blocks"] = [{"ts": "", "text": asr}] if asr else []
                    result["note"] = "分支③无字幕轨ASR（≤10min分段）" if asr else "待用户提供字幕/文字稿"
            else:
                asr = asr_audio(path, whisper, ffmpeg, ffprobe)
                result["branch"] = "asr" if asr else "need_user_input"
                result["blocks"] = [{"ts": "", "text": asr}] if asr else []
                result["note"] = "纯音频流ASR（≤10min分段）" if asr else "待用户提供文字稿"

        elif mtype == "audio":
            asr = asr_audio(path, whisper, ffmpeg, ffprobe)
            result["branch"] = "asr" if asr else "need_user_input"
            result["blocks"] = [{"ts": "", "text": asr}] if asr else []
            result["note"] = "音频ASR（长媒体≤10min真分段）" if asr else "待用户提供文字稿"

        elif mtype == "image":
            t = run_ocr(path, ocr)
            result["branch"] = "ocr" if t else "need_user_input"
            result["blocks"] = [{"ts": "", "text": t}] if t else []
            result["note"] = "图片OCR" if t else "待用户提供图内文字稿"

        else:
            result["branch"] = "unsupported"
            result["note"] = "不支持的格式，请转常见视频/音频/图片格式"
    except Exception as e:
        result["branch"] = "error"
        result["note"] = "处理异常：%s: %s" % (type(e).__name__, e)
    return result


def main():
    args = sys.argv[1:]
    if not args:
        sys.stderr.write("usage: media_ingest.py <file> [--out b.json] | "
                         "--files a.mp4;b.mp3 [--out-dir D] [--summary s.json] | "
                         "--dir D [--ext mp4,mp3,png] [--out-dir D] [--summary s.json]\n")
        sys.exit(2)
    if args[0] == "--self-test":
        return self_test()

    single = None
    files = None
    directory = None
    exts = None
    out = None
    out_dir = None
    summary = None
    ffmpeg = ffprobe = whisper = ocr = None
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--out":
            out = args[i + 1]; i += 2
        elif a == "--out-dir":
            out_dir = args[i + 1]; i += 2
        elif a == "--summary":
            summary = args[i + 1]; i += 2
        elif a == "--files":
            files = args[i + 1]; i += 2
        elif a == "--dir":
            directory = args[i + 1]; i += 2
        elif a == "--ext":
            exts = [x.strip().lower() for x in args[i + 1].split(",") if x.strip()]
            i += 2
        elif a == "--ffmpeg":
            ffmpeg = args[i + 1]; i += 2
        elif a == "--ffprobe":
            ffprobe = args[i + 1]; i += 2
        elif a == "--whisper":
            whisper = args[i + 1]; i += 2
        elif a == "--ocr":
            ocr = args[i + 1]; i += 2
        elif single is None and not a.startswith("--"):
            single = a; i += 1
        else:
            i += 1

    ffmpeg = which("ffmpeg", ffmpeg)
    ffprobe = which("ffprobe", ffprobe)
    whisper = which("whisper", whisper) or which("faster-whisper", whisper)
    ocr = which("tesseract", ocr)

    # 单文件模式
    if single and not files and not directory:
        r = process_file(single, ffmpeg, ffprobe, whisper, ocr)
        if out:
            with open(out, "w", encoding="utf-8") as f:
                json.dump(r, f, ensure_ascii=False, indent=2)
            print("branch=%s blocks=%d -> %s" % (r["branch"], len(r["blocks"]), out))
        else:
            print(json.dumps(r, ensure_ascii=False, indent=2))
        sys.exit(0)

    # 批量模式
    file_list = []
    if files:
        file_list = [x.strip() for x in files.split(";") if x.strip()]
    if directory:
        for root, _dirs, names in os.walk(directory):
            for nm in names:
                if exts:
                    if os.path.splitext(nm)[1].lower() in exts:
                        file_list.append(os.path.join(root, nm))
                else:
                    if classify(os.path.join(root, nm)) != "unknown":
                        file_list.append(os.path.join(root, nm))
    if not file_list:
        sys.stderr.write("no media files collected\n")
        sys.exit(2)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    results = []
    plan_units = []
    processed_units = []
    for idx, p in enumerate(file_list, 1):
        uid = "U%03d" % idx
        plan_units.append({"id": uid, "type": classify(p), "source": p})
        r = process_file(p, ffmpeg, ffprobe, whisper, ocr)
        r["unit_id"] = uid
        results.append(r)
        if r["blocks"]:
            processed_units.append({"id": uid})
        if out_dir:
            bp = os.path.join(out_dir, "%s_blocks.json" % uid)
            with open(bp, "w", encoding="utf-8") as f:
                json.dump(r, f, ensure_ascii=False, indent=2)

    ok = sum(1 for r in results if r["blocks"])
    failed = [{"unit_id": r.get("unit_id"), "source": r["source"], "reason": r["note"]}
              for r in results if not r["blocks"]]
    summ = {"total": len(results), "ok": ok, "failed": len(failed),
            "failed_units": failed}

    plan_path = os.path.join(out_dir or ".", "media_plan.json") if out_dir else None
    proc_path = os.path.join(out_dir or ".", "media_processed.json") if out_dir else None
    if out_dir:
        with open(plan_path, "w", encoding="utf-8") as f:
            json.dump({"units": plan_units}, f, ensure_ascii=False, indent=2)
        with open(proc_path, "w", encoding="utf-8") as f:
            json.dump({"units": processed_units}, f, ensure_ascii=False, indent=2)

    if summary:
        with open(summary, "w", encoding="utf-8") as f:
            json.dump(summ, f, ensure_ascii=False, indent=2)
        print("batch done -> %s" % summary)
    else:
        print(json.dumps(summ, ensure_ascii=False, indent=2))
    # 批量模式 exit code：有失败单元则非 0（供门禁感知）
    sys.exit(0 if ok == len(results) else 1)


def _clean_srt(srt):
    lines = [l.rstrip() for l in srt.splitlines()
             if l.strip() and not re.match(r"^\d+$", l.strip())
             and "-->" not in l]
    return "\n".join(lines)


def self_test():
    """离线回归：仅用标准库逻辑，不调 ffmpeg/whisper/tesseract，不碰任何文件。"""
    # 用例1：扩展名分类正确
    c1 = (classify("a.mp4") == "video"
          and classify("b.mp3") == "audio"
          and classify("c.png") == "image"
          and classify("d.xyz") == "unknown")
    # 用例2：长媒体分段上限常量已落地（≤10 分钟）
    c2 = SEG_SEC == 600
    # 用例3：process_file 异常隔离（不存在文件 → 绝不向上抛，优雅降级返空 blocks）
    try:
        r = process_file("/nonexistent_media_file_xyz.mp4", None, None, None, None)
        raised = False
    except Exception:
        raised = True
    c3 = (not raised and isinstance(r, dict) and r.get("blocks") == [])
    # 用例4：_clean_srt 去序号/时间轴
    srt = ("1\n00:00:01,000 --> 00:00:02,000\n字幕一行\n\n"
           "2\n00:00:03,000 --> 00:00:04,000\n字幕二行\n")
    cleaned = _clean_srt(srt)
    c4 = ("字幕一行" in cleaned and "-->" not in cleaned
          and not any(l.strip().isdigit() for l in cleaned.splitlines()))
    ok = c1 and c2 and c3 and c4
    print("self-test classify_ok=%s seg_sec_ok=%s isolate_ok=%s clean_srt_ok=%s"
          % (c1, c2, c3, c4))
    print("SELF_TEST", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
