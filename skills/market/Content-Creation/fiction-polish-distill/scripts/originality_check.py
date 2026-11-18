#!/usr/bin/env python3
"""originality_check.py — 原创自查引擎（1.0.6 新增：OR-1/OR-2）

呼应 2026《网络文学行业反洗稿自律公约》与 900+ 作家联署的《网络文学反抄袭倡议书》：
    compare  <甲.md> <乙.md>         洗稿/融梗自查：两文本 n-gram 重合度 + 模板结构重合
    self     <正文.md>                同质化指数自查：全文内部模板/句式重复度

说明:
    1. 本工具仅做"本地自查提示"，输出"同质化风险提示"，非权威查重判定。
    2. 重大发表风险请使用专业查重服务（如平台官方查重/权威第三方）。
    3. 全部为确定性本地计算（零外部依赖）。
"""

import json
import re
import sys

from common import VERSION, read_text


def _norm(text):
    return re.sub(r"[\s，。！？；：、,.!?;:\"'“”‘’（）()\[\]{}]", "", text)


def _ngrams(text, n):
    t = _norm(text)
    if len(t) < n:
        return []
    return [t[i:i + n] for i in range(len(t) - n + 1)]


def _overlap_ngram(a, b, n):
    """两文本 n-gram 重合率（0-1）。"""
    ga = set(_ngrams(a, n))
    gb = set(_ngrams(b, n))
    if not ga or not gb:
        return 0.0
    return len(ga & gb) / min(len(ga), len(gb))


# 洗稿常见模板结构（用于"换词不换骨架"的模板重合检测）
_TEMPLATES = [
    r"随着.{2,12}的发展",
    r"在.{2,12}的背景下",
    r"不仅.{0,6}而且.{0,6}",
    r"总而言之.{0,20}",
    r"众所周知.{0,20}",
    r"首先.{0,20}其次.{0,20}最后.{0,20}",
    r"他?（?:感到|觉得）.{0,8}(?:愤怒|悲伤|开心|焦虑)",
    r"值得一提的是.{0,20}",
]


def compare(a, b):
    """洗稿/融梗自查：n-gram 重合 + 模板重合。"""
    overlap2 = _overlap_ngram(a, b, 2)
    overlap4 = _overlap_ngram(a, b, 4)
    overlap8 = _overlap_ngram(a, b, 8)
    # 模板重合
    tpl_a = {p for p in _TEMPLATES if re.search(p, _norm(a))}
    tpl_b = {p for p in _TEMPLATES if re.search(p, _norm(b))}
    tpl_overlap = len(tpl_a & tpl_b)
    # 同质化指数（启发式加权）
    idx = round(overlap8 * 60 + overlap4 * 25 + overlap2 * 5 + min(tpl_overlap * 3, 10), 1)
    level = "低" if idx < 15 else ("中" if idx < 25 else "高")
    return {
        "status": "ok",
        "version": VERSION,
        "bigram_overlap": round(overlap2 * 100, 1),
        "4gram_overlap": round(overlap4 * 100, 1),
        "8gram_overlap": round(overlap8 * 100, 1),
        "template_overlap": tpl_overlap,
        "homogeneity_index": idx,
        "risk_level": level,
        "advice": {
            "低": "重合度较低，未见明显洗稿/融梗特征（本地自查，非权威）",
            "中": "存在一定重合，建议逐句比对并改写重复片段（本地自查，非权威）",
            "高": "重合度偏高，存在洗稿/融梗风险，建议大幅改写核心句并避免相同骨架（本地自查，重大风险请用专业查重）",
        }[level],
    }


def self_check(text):
    """同质化指数自查：全文内部模板/句式重复度。"""
    sents = [s.strip() for s in re.split(r"(?<=[。！？；.!?])", text) if s.strip()]
    if len(sents) < 5:
        return {"status": "skip", "reason": "句子过少，无法评估同质化"}
    clean = _norm(text)
    # 句式开头重复
    heads = [_norm(s)[:2] for s in sents if _norm(s)]
    from collections import Counter
    hc = Counter(heads)
    top_head = hc.most_common(1)[0][1] / len(heads) * 100 if heads else 0
    # 长片段重复
    grams = Counter(clean[i:i + 8] for i in range(len(clean) - 7))
    dup = sum(1 for g, n in grams.items() if n >= 3)
    idx = round(top_head * 0.6 + min(dup * 4, 40), 1)
    level = "低" if idx < 20 else ("中" if idx < 30 else "高")
    return {
        "status": "ok",
        "version": VERSION,
        "sentence_head_repeat_pct": round(top_head, 1),
        "repeated_8gram_kinds": dup,
        "homogeneity_index": idx,
        "risk_level": level,
        "advice": {
            "低": "句式/开头重复度低（本地自查，非权威）",
            "中": "句首重复偏高，建议打散句式模板",
            "高": "同质化明显，建议系统改写句式骨架与高频片段",
        }[level],
    }


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd = argv[0]
    args = [a for a in argv[1:] if not a.startswith("--")]
    if cmd == "compare" and len(args) >= 2:
        print(json.dumps(compare(read_text(args[0]), read_text(args[1])), ensure_ascii=False, indent=2))
        return 0
    if cmd == "self" and args:
        print(json.dumps(self_check(read_text(args[0])), ensure_ascii=False, indent=2))
        return 0
    print(f"未知命令: {cmd}（可用: compare/self）")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
