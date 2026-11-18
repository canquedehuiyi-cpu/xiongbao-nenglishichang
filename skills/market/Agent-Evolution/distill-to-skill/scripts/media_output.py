#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""media_output.py — 同源媒体「档一·裁剪/选择」路由层

定位：
- 仅做「档一·裁剪/选择」：保留原素材精华，不重生成。
  · 音频/视频：按上游蒸馏产出的精华段时间码裁出片段（ffmpeg）。
  · 图片：按清晰度/尺寸评分选 best-N（opencv / Pillow）。
- 不做「档二·重生成」：TTS 重讲、AI 视频、AI 图一律不在此脚本内。
- 原则：环境提供、只写路由、不捆绑。ffmpeg / opencv / Pillow 由宿主提供，
  缺失即优雅降级（明确报错 + 装法指引），不崩、不产出半成品。

与核心蒸馏的关系：
- 本脚本不替用户做蒸馏决策；它消费上游（media_ingest 锚定文本块 / 四段式）
  产出的「精华段时间标记」，把标记落成真实裁剪动作。
- 仅在用户明确要求同源裁剪/选择、且环境具备对应工具时才调用；默认不产同源媒体，
  不主动引导（见 SKILL.md A0.4 媒体投料产出口径）。

零第三方依赖：本文件本身仅用 Python 标准库做探测/路由/清单；真正的编解码交给
宿主 ffmpeg / opencv / Pillow。
"""

import argparse
import json
import os
import shutil
import subprocess
import sys


# ---------------------------------------------------------------------------
# 环境探测（优雅降级基础）
# ---------------------------------------------------------------------------
def _have_ffmpeg():
    return shutil.which("ffmpeg") is not None


def _have_cv2():
    try:
        import importlib.util as u
        return u.find_spec("cv2") is not None
    except Exception:
        return False


def _have_pil():
    try:
        import importlib.util as u
        return u.find_spec("PIL") is not None
    except Exception:
        return False


def _norm_timecode(tc):
    """把 MM:SS / HH:MM:SS / 秒数 统一成 ffmpeg 接受的字符串。"""
    tc = str(tc).strip()
    if tc.replace(".", "").isdigit():
        return tc  # 纯秒数
    parts = tc.split(":")
    if len(parts) in (2, 3) and all(p.replace(".", "").isdigit() for p in parts):
        return tc
    raise ValueError("时间码格式应为 秒数 / MM:SS / HH:MM:SS，收到：%r" % tc)


# ---------------------------------------------------------------------------
# 档一·音频/视频裁剪（ffmpeg）
# ---------------------------------------------------------------------------
def trim_media(inp, out, start, end, kind):
    """按精华段时间码裁出片段。kind: 'audio' | 'video'。"""
    if not _have_ffmpeg():
        raise RuntimeError(
            "本环境未安装 ffmpeg，无法裁音频/视频。\n"
            "装法：Windows 下载 ffmpeg 并加入 PATH；macOS `brew install ffmpeg`；"
            "Linux `apt install ffmpeg`。\n"
            "装好后再调用本脚本；或把时间码清单交给剪映/即梦/可灵自行裁剪。"
        )
    if not os.path.isfile(inp):
        raise RuntimeError("输入文件不存在：%s" % inp)
    start = _norm_timecode(start)
    end = _norm_timecode(end)
    out_dir = os.path.dirname(os.path.abspath(out))
    if out_dir and not os.path.isdir(out_dir):
        os.makedirs(out_dir, exist_ok=True)
    if kind == "audio":
        cmd = ["ffmpeg", "-y", "-i", inp, "-ss", start, "-to", end, "-c", "copy", out]
    else:  # video：重编码以保证兼容（较慢，长视频建议外部平台）
        cmd = ["ffmpeg", "-y", "-i", inp, "-ss", start, "-to", end,
               "-c:v", "libx264", "-c:a", "aac", out]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        raise RuntimeError("ffmpeg 裁剪失败（退出码 %s）：%s"
                           % (e.returncode, (e.stderr or b"").decode("utf-8", "ignore")[:400]))
    if not os.path.isfile(out):
        raise RuntimeError("ffmpeg 未产出文件（未知原因）：%s" % out)
    return {
        "input": os.path.abspath(inp),
        "output": os.path.abspath(out),
        "start": start,
        "end": end,
        "kind": kind,
        "bytes": os.path.getsize(out),
    }


# ---------------------------------------------------------------------------
# 档一·图片选 best-N（opencv / Pillow 评分）
# ---------------------------------------------------------------------------
def _sharpness_variance(img_path):
    """用拉普拉斯方差估清晰度（需 cv2）。"""
    import cv2
    import numpy as np
    g = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
    if g is None:
        return 0.0
    return float(cv2.Laplacian(g, cv2.CV_64F).var())


def select_images(in_dir, out_dir, n, strategy="sharp"):
    """从 in_dir 选清晰度/尺寸 top-N 图片复制到 out_dir。"""
    if not (_have_cv2() or _have_pil()):
        raise RuntimeError(
            "本环境未安装 opencv-python 或 Pillow，无法评分选图。\n"
            "装法：`pip install opencv-python-headless` 或 `pip install Pillow`。\n"
            "装好后再调用；或依下方清单手动挑选。"
        )
    if not os.path.isdir(in_dir):
        raise RuntimeError("输入目录不存在：%s" % in_dir)
    exts = (".jpg", ".jpeg", ".png", ".bmp", ".webp")
    files = [os.path.join(in_dir, f) for f in os.listdir(in_dir)
             if f.lower().endswith(exts)]
    if not files:
        raise RuntimeError("输入目录无图片文件：%s" % in_dir)
    scored = []
    for fp in files:
        try:
            if strategy == "sharp" and _have_cv2():
                score = _sharpness_variance(fp)
            elif _have_pil():
                from PIL import Image
                with Image.open(fp) as im:
                    score = float(im.size[0] * im.size[1])  # 像素面积
            else:
                score = 0.0
        except Exception:
            score = -1.0
        scored.append((fp, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    top = scored[: max(1, min(n, len(scored)))]
    os.makedirs(out_dir, exist_ok=True)
    picked = []
    for fp, score in top:
        dst = os.path.join(out_dir, os.path.basename(fp))
        shutil.copy(fp, dst)
        picked.append({"src": fp, "score": round(score, 2), "dst": dst})
    return {
        "in_dir": os.path.abspath(in_dir),
        "out_dir": os.path.abspath(out_dir),
        "strategy": strategy,
        "total": len(files),
        "picked_n": len(picked),
        "picked": picked,
    }


# ---------------------------------------------------------------------------
# 剪辑清单产出（供用户自产参考，也供本脚本自身留痕）
# ---------------------------------------------------------------------------
def write_cutlist(summary, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    return path


# ---------------------------------------------------------------------------
# 自检（降级路径 + 参数校验，不依赖外部媒体工具）
# ---------------------------------------------------------------------------
def self_test():
    ok = True
    log = []
    # 1) 探测函数返回布尔
    for name, fn in (("ffmpeg", _have_ffmpeg), ("cv2", _have_cv2), ("PIL", _have_pil)):
        try:
            r = fn()
            assert isinstance(r, bool)
            log.append("[PASS] 探测 %s -> %s" % (name, r))
        except Exception as e:
            ok = False
            log.append("[FAIL] 探测 %s -> %s" % (name, e))
    # 2) 时间码归一化
    for tc, exp in (("90", "90"), ("1:30", "1:30"), ("0:01:30", "0:01:30")):
        try:
            assert _norm_timecode(tc) == exp
            log.append("[PASS] 时间码 %s -> %s" % (tc, exp))
        except Exception as e:
            ok = False
            log.append("[FAIL] 时间码 %s -> %s" % (tc, e))
    # 3) 非法时间码应报错
    try:
        _norm_timecode("abc")
        ok = False
        log.append("[FAIL] 非法时间码未报错")
    except ValueError:
        log.append("[PASS] 非法时间码 -> 正确抛 ValueError")
    # 4) 无 ffmpeg 时 trim 应优雅降级（明确 RuntimeError，不崩）
    if not _have_ffmpeg():
        try:
            trim_media("x.mp3", "o.mp3", "0", "10", "audio")
            ok = False
            log.append("[FAIL] 无 ffmpeg 时 trim 未降级")
        except RuntimeError as e:
            msg = str(e)
            assert "ffmpeg" in msg and ("PATH" in msg or "brew" in msg or "apt" in msg)
            log.append("[PASS] 无 ffmpeg 优雅降级（带装法指引）")
    # 5) 无 cv2/PIL 时 select 应优雅降级
    if not (_have_cv2() or _have_pil()):
        try:
            select_images(".", "./_out", 3)
            ok = False
            log.append("[FAIL] 无 cv2/PIL 时 select 未降级")
        except RuntimeError as e:
            msg = str(e)
            assert "opencv" in msg or "Pillow" in msg
            log.append("[PASS] 无 cv2/PIL 优雅降级（带装法指引）")
    log.append("SELF_TEST_%s" % ("OK" if ok else "FAIL"))
    return ok, log


def main(argv=None):
    p = argparse.ArgumentParser(description="同源媒体档一裁剪/选择路由（仅裁剪/选择，不重生成）")
    sub = p.add_subparsers(dest="cmd")

    pt = sub.add_parser("trim", help="按时间码裁音频/视频片段")
    pt.add_argument("--input", required=True)
    pt.add_argument("--output", required=True)
    pt.add_argument("--start", required=True, help="秒数/MM:SS/HH:MM:SS")
    pt.add_argument("--end", required=True)
    pt.add_argument("--kind", choices=["audio", "video"], required=True)

    ps = sub.add_parser("select", help="图片选 best-N")
    ps.add_argument("--in-dir", required=True)
    ps.add_argument("--out-dir", required=True)
    ps.add_argument("--n", type=int, required=True)
    ps.add_argument("--strategy", choices=["sharp", "size"], default="sharp")

    p.add_argument("--cutlist", help="把结果写成剪辑清单 JSON 的路径")
    p.add_argument("--self-test", action="store_true", help="跑自检（降级路径+参数校验）")

    args = p.parse_args(argv)
    if args.self_test:
        ok, log = self_test()
        print("\n".join(log))
        return 0 if ok else 1
    if args.cmd == "trim":
        res = trim_media(args.input, args.output, args.start, args.end, args.kind)
    elif args.cmd == "select":
        res = select_images(args.in_dir, args.out_dir, args.n, args.strategy)
    else:
        p.error("需指定子命令（trim/select）或 --self-test")
        return 2
    if args.cutlist:
        write_cutlist(res, args.cutlist)
        res["cutlist"] = os.path.abspath(args.cutlist)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
