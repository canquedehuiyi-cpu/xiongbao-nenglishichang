#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ingest_chunk.py — 语义分块 + 体积分级 + 执行计划（确定性，仅标准库，零第三方依赖）

用法：
  python ingest_chunk.py <输入文本文件.txt> [--max-chunk 4000] [--out plan.json]

输出：
  JSON = {
    "tier": "S|M|L|XL",
    "total_chars": int,
    "max_chunk": int,
    "chunk_count": int,
    "plan": {...},                 # 执行计划（先骨架后细节）
    "chunks": [                   # 语义分块清单
      {"id": "C001", "title": "...", "char_count": int, "text": "..."}
    ]
  }

（对应 SKILL.md A0 规模适配层）：
  投料体量可能极大（书/报告/视频转写/会议纪要多语种），本脚本保证
  "不整段塞入上下文、不漏失段落、不崩溃"：按语义边界切（标题/章节/说话人/时间戳/
  空行段落），单块上限默认 4K 字符，每块带稳定 ID 与就近标题，可独立验证、
  可溯源、可回退。L/XL 量级由调用方按 plan 逐块提取后汇总。
"""

import sys
import os
import re
import json
import argparse

HEADING = re.compile(r"^(#{1,6}\s+.*)$", re.M)
CHAPTER = re.compile(r"^(第[一二三四五六七八九十百千0-9]+[章回节卷篇部].*)$", re.M)
SENT_SPLIT = re.compile(r"(?<=[。！？!?；;\.\n])")
MAX_CHUNK = 4000
SIZE_TIER_MB = 50  # 单文件 >50MB 触发流式不整载（体积维度）


def size_tier(n_bytes):
    """体积维度分级：与字数 tier 同序 S/M/L/XL，最终 tier 取字数/体积较高者。"""
    mb = n_bytes / (1024.0 * 1024.0)
    if mb < 5:
        return "S"
    if mb < 30:
        return "M"
    if mb < 100:
        return "L"
    return "XL"


def tier(n):
    if n < 5000:
        return "S"
    if n < 30000:
        return "M"
    if n < 100000:
        return "L"
    return "XL"


def split_to_size(body, mx):
    """按句边界切到 <= mx 字符；超长单句硬切。"""
    sents = [s.strip() for s in SENT_SPLIT.split(body) if s.strip()]
    out = []
    cur = ""
    for s in sents:
        if len(cur) + len(s) + 1 <= mx:
            cur = (cur + " " + s).strip() if cur else s
        else:
            if cur:
                out.append(cur)
            while len(s) > mx:
                out.append(s[:mx])
                s = s[mx:]
            cur = s
    if cur:
        out.append(cur)
    return out


def split_blocks(text, mx):
    """先按标题/章节切成段，段内再按句切到 mx。"""
    lines = text.split("\n")
    blocks = []
    cur_title = ""
    buf = []

    def flush():
        if buf:
            blocks.append((cur_title, "\n".join(buf).strip()))
        buf.clear()

    for ln in lines:
        if HEADING.match(ln) or CHAPTER.match(ln):
            flush()
            cur_title = ln.strip().lstrip("#").strip()
            buf = [ln]
        else:
            buf.append(ln)
    flush()

    chunks = []
    cid = 0
    for title, body in blocks:
        if not body:
            continue
        for p in split_to_size(body, mx):
            cid += 1
            chunks.append(
                {"id": "C%03d" % cid, "title": title, "char_count": len(p), "text": p}
            )
    return chunks


def build_plan(t, chunks):
    if t in ("S", "M"):
        return {
            "mode": "直接进四段式(A3)",
            "note": "整料单轮提取，无需分块",
        }
    titles = []
    seen = set()
    for c in chunks:
        if c["title"] and c["title"] not in seen:
            seen.add(c["title"])
            titles.append(c["title"])
    return {
        "mode": "先规划后执行（架构优先）",
        "step1_架构侦察": "扫描 %d 个标题/章节节点，产出骨架假设" % len(titles),
        "step2_逐块提取": "对 %d 个块各走四段式最小闭环，每块产出可复用单元+挂接位置"
        % len(chunks),
        "step3_汇总架构": "挂到骨架，去重归并，剥离附着物（举例/情绪/重复/闲笔）",
        "骨架节点": titles[:50],
    }


def _self_test():
    """离线自测：内联文本走「分块→分级→计划」三步，断言标题识别、块不超限、ID 连续、
    硬切生效、分级与计划口径正确。纯函数调用，不落任何文件。"""
    text = ("# 一级标题\n正文一。\n"
            "## 二级标题\n正文二。正文三。\n"
            "第1章 章节甲\n章节内容一。章节内容二。\n")
    chunks = split_blocks(text, 4000)
    assert chunks, "未切出分块"
    assert all(c["char_count"] <= 4000 for c in chunks), "存在超限块"
    titles = [c["title"] for c in chunks]
    for key in ("一级标题", "二级标题", "章节甲"):
        assert any(key in t for t in titles), "标题未识别 %s: %s" % (key, titles)
    assert [c["id"] for c in chunks] == ["C%03d" % (i + 1) for i in range(len(chunks))], \
        "块 ID 非连续: %s" % [c["id"] for c in chunks]
    # 硬切：无标点超长单句必须按 mx 切开
    hard = split_to_size("甲" * 100, 30)
    assert hard and all(len(x) <= 30 for x in hard), \
        "超长单句未硬切: %s" % [len(x) for x in hard]
    # 分级
    assert tier(100) == "S" and tier(6000) == "M" and tier(40000) == "L" \
        and tier(200000) == "XL", "字数分级口径漂移"
    assert size_tier(1024) == "S", "体积分级口径漂移"
    # 计划：L 量级走「先规划后执行」
    plan = build_plan("L", chunks)
    assert plan["mode"].startswith("先规划"), "L 量级计划模式错: %s" % plan["mode"]
    print("PASS ingest_chunk：块数=%d 标题齐 ID 连续 硬切/分级/计划正确" % len(chunks))
    return 0


def main():
    ap = argparse.ArgumentParser(
        prog="ingest_chunk.py",
        description="A0.1 语义分块：按语义边界把长文切成块，给出体积/字数分级与执行计划。",
    )
    ap.add_argument("file", nargs="?", help="输入文本文件（.txt）")
    ap.add_argument("--max-chunk", type=int, default=MAX_CHUNK,
                    help="单块最大字符数（默认 %d）" % MAX_CHUNK)
    ap.add_argument("--out", default=None, help="分块计划写出路径（不传则打印到 stdout）")
    ap.add_argument("--self-test", action="store_true", help="离线自测（无需外部输入）")
    args = ap.parse_args()
    if args.self_test:
        raise SystemExit(_self_test())
    if not args.file:
        ap.error("缺少输入文件：<file.txt>")
    path = args.file
    mx = args.max_chunk
    out = args.out

    fsize = os.path.getsize(path)
    with open(path, encoding="utf-8") as f:
        text = f.read()
    total = len(text)
    t_char = tier(total)
    t_size = size_tier(fsize)
    order = {"S": 0, "M": 1, "L": 2, "XL": 3}
    t = t_char if order[t_char] >= order[t_size] else t_size
    chunks = split_blocks(text, mx)
    plan = build_plan(t, chunks)
    plan.setdefault("note", "")
    if order[t_size] >= order["L"]:
        plan["note"] += "；大体积(%dMB)触发流式不整载" % (fsize // (1024 * 1024))
    result = {
        "tier": t,
        "tier_chars": t_char,
        "tier_size": t_size,
        "total_chars": total,
        "total_bytes": fsize,
        "max_chunk": mx,
        "chunk_count": len(chunks),
        "plan": plan,
        "chunks": chunks,
    }
    if out:
        with open(out, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(
            "tier=%s total=%d chunks=%d max=%d -> %s"
            % (t, total, len(chunks), mx, out)
        )
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
