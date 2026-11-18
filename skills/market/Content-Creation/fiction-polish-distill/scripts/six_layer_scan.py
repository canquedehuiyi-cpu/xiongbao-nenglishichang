#!/usr/bin/env python3
"""six_layer_scan.py — AI 痕迹六层扫描（1.0.7 新增：R-1~R-7）

把"AI 感"拆成六个可量化层级，单次扫描输出分层报告，并给出
"你的 AI 感主要来自哪一层" 结论（供作者定位修改，非权威判定）：

    R-1 词层   高频 AI 词（黑名单词级规则命中）
    R-2 语层   套话短语（黑名单短语级规则命中）
    R-3 句层   句式单一 / 重复句式
    R-4 语义层 语义重复 / 车轱辘话 / 论证空转（1.0.7 补强）
    R-5 指纹层 风格一致性 / 句长分布漂移
    R-6 行为层 对话无信息增量 / 事件密度低 / 无具体细节

用法:
    python3 six_layer_scan.py <文本.md>          # 分层报告
    python3 six_layer_scan.py <文本.md> --json   # JSON 输出
    python3 six_layer_scan.py <文本.md> --profile 用户旧作.md   # 对比个人风格档案（T-4）

说明:
    全部为本地启发式估算（零外部依赖，复用 antiai_blacklist.json 单一数据源）；
    各层分数仅供作者自查定位，不替代平台检测。
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

from common import VERSION, read_text

# ---------- 数据源 ----------

def load_rules():
    """加载黑名单 rules（单一数据源）。"""
    base = Path(__file__).resolve().parent.parent
    path = base / "references" / "antiai_blacklist.json"
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        return d.get("rules", [])
    except Exception:
        return []


def _load_section(name, default):
    """从黑名单 JSON 读取指定分区（带默认回退）。"""
    base = Path(__file__).resolve().parent.parent
    path = base / "references" / "antiai_blacklist.json"
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f).get(name, default)
    except Exception:
        return default


BF = _load_section("behavior_features", {})


def _iter_terms():
    """遍历黑名单全部 pattern 拆分出的词项。"""
    for r in load_rules():
        for term in r.get("pattern", "").split("|"):
            term = term.strip()
            if term:
                yield term


META = re.compile(r"[.*+?\[\](){}|^$\\]")


def _is_regex(term):
    return bool(META.search(term))


def layer_word(text):
    """R-1 词层：短词（≤3 字，非正则）高频出现。"""
    hits = []
    for term in _iter_terms():
        if len(term) <= 3 and not _is_regex(term) and text.count(term) >= 2:
            hits.append(term)
    uniq = list(dict.fromkeys(hits))
    score = min(100, len(uniq) * 12)
    return score, uniq[:8]


def layer_phrase(text):
    """R-2 语层：≥4 字短语（含正则模式）出现。"""
    hits = []
    for term in _iter_terms():
        if len(term) >= 4:
            if _is_regex(term):
                if re.search(term, text):
                    hits.append(term)
            elif term in text:
                hits.append(term)
    uniq = list(dict.fromkeys(hits))
    score = min(100, len(uniq) * 15)
    return score, uniq[:8]


def _sentence_lens(text):
    sents = [s.strip() for s in re.split(r"(?<=[。！？；.!?])", text) if len(s.strip()) >= 2]
    return [len(s) for s in sents]


def layer_sentence(text):
    """R-3 句层：句长分布过窄（CV 低）+ 连续句同开头。"""
    lens = _sentence_lens(text)
    if len(lens) < 4:
        return 0, []
    mean = sum(lens) / len(lens)
    if mean == 0:
        return 0, []
    std = (sum((x - mean) ** 2 for x in lens) / len(lens)) ** 0.5
    cv = std / mean
    # 句长 CV 过低 → 句式过于整齐
    score = max(0, min(100, int((0.35 - cv) * 200))) if cv < 0.35 else 0
    # 连续句以相同词/字开头（重复句式）
    sents = [s for s in re.split(r"(?<=[。！？；.!?])", text) if s.strip()]
    same_start = 0
    for i in range(1, len(sents)):
        a = sents[i - 1].strip()[:2]
        b = sents[i].strip()[:2]
        if a and a == b:
            same_start += 1
    score = min(100, score + same_start * 10)
    return score, [f"连续{same_start}处同字开头"] if same_start else []


def layer_semantic(text):
    """R-4 语义层（1.0.7 补强）：复用 quality_depth.semantic_repetition（单一实现）。

    相邻句 n-gram 重叠（车轱辘话）+ 同义反复；阈值来自黑名单 JSON semantic_features 分区。
    判定以 semantic_repetition 的 pass 为准：未检出重复为 0 分，检出问题按重叠率给分（最低 45）。
    """
    try:
        from quality_depth import semantic_repetition as _sr
        r = _sr(text)
    except Exception:
        return 0, []
    if r.get("pass") is None or r.get("pass") is True:
        return 0, []
    value = r.get("value", 0.0)
    score = max(45, min(100, int(value * 100)))
    return score, [r.get("detail", "")]


def build_profile(text):
    """T-4 用户风格档案：平均句长/句长 CV/高频 2~3 字词。"""
    lens = _sentence_lens(text)
    if not lens:
        return None
    mean = sum(lens) / len(lens)
    std = (sum((x - mean) ** 2 for x in lens) / len(lens)) ** 0.5
    cv = std / mean if mean else 0.0
    words = []
    for w in re.findall(r"[\u4e00-\u9fff]{2,3}", text):
        if w not in GENERIC_WORDS:
            words.append(w)
    top = [w for w, _ in Counter(words).most_common(20)]
    return {"avg_len": round(mean, 1), "cv": round(cv, 3), "top_words": top}


# 风格档案用过滤词（跨模块通用高泛指词，避免把"什么/一样"当风格词）
GENERIC_WORDS = set("什么怎么为什么因为所以如果但是然而其实只是就是还是或者而且以及由于因此可是不过已经正在将要一直突然忽然终于原来到底究竟难道居然竟然反正毕竟不管无论除非假如只要既然却才又再便也还更太很非常十分特别最更加然后接着最后首先其次这样那样这个那个这些那些我们你们他们自己".split())


def layer_fingerprint(text, profile=None):
    """R-5 指纹层：
    - 提供 profile 时：对比当前文本与用户风格档案的距离（像不像自己写）
    - 未提供时：前/后半句长分布漂移 + 句长熵过低（过于工整）
    """
    lens = _sentence_lens(text)
    if len(lens) < 6:
        return 0, []
    mean = sum(lens) / len(lens)
    std = (sum((x - mean) ** 2 for x in lens) / len(lens)) ** 0.5
    cv = std / mean if mean else 0.0
    if profile:
        dist = abs(mean - profile["avg_len"])
        prof_words = set(profile["top_words"])
        cur_words = set(w for w in re.findall(r"[\u4e00-\u9fff]{2,3}", text)
                        if w not in GENERIC_WORDS)
        overlap = len(prof_words & cur_words) / max(1, len(prof_words))
        # 距离分：句长差越大、高频词重合越低 → 越"不像自己"
        score = min(100, int(dist * 10) + int((1 - overlap) * 40))
        return score, [f"均句长差 {dist:.1f} | 高频词重合 {overlap:.0%}"]
    half = len(lens) // 2
    a, b = lens[:half], lens[half:]
    ma = sum(a) / len(a)
    mb = sum(b) / len(b)
    drift = abs(ma - mb)
    drift_score = min(50, int(drift * 8))
    tidy = max(0, min(50, int((0.30 - cv) * 200))) if cv < 0.30 else 0
    return drift_score + tidy, [f"前后均句长差 {abs(ma - mb):.1f}" if drift > 2 else f"句长过整(CV={cv:.2f})"]


def layer_behavior(text):
    """R-6 行为层：对话无信息增量（僵硬）+（长文本）事件密度低/无具体细节。

    事件密度与具象细节两个子指标仅在文本足够长时启用，
    避免短文本因"没有写打杀/感官词"而被误报为 AI 痕迹。
    """
    dial_actions = BF.get("dialogue_action_words", ["说", "道", "喊", "问", "答", "叹", "笑", "吼", "低语", "喃喃", "嘀咕"])
    event_words = BF.get("event_words", ["突然", "猛地", "骤然", "爆发", "冲突", "大战", "转身", "抬头", "回头", "拦住", "追", "逃", "打", "杀", "抢", "救"])
    sense_words = BF.get("sense_words", ["攥", "颤", "凉", "烫", "腥", "涩", "哑", "刺", "麻", "痛", "香", "臭", "蓝", "黑", "白", "红"])
    ev_thr = BF.get("event_density_threshold", 1.5)
    se_thr = BF.get("sense_density_threshold", 2.0)
    min_len = BF.get("min_text_len", 300)
    # 对话僵硬：引号对话内不含动作描述的比例
    dial = re.findall(r"“[^”]+”", text)
    stiff = 0
    for d in dial:
        if not re.search("|".join(re.escape(w) for w in dial_actions), d):
            stiff += 1
    dial_ratio = stiff / len(dial) if dial else 0.0
    score = int(dial_ratio * 50)
    reasons = []
    if dial_ratio > 0.6:
        reasons.append(f"对话{stiff}/{len(dial)}句无动作信息")
    # 长文本才启用密度惩罚
    if len(text) >= min_len:
        events = sum(1 for w in event_words if w in text)
        per_k = events / (len(text) / 1000)
        senses = sum(1 for w in sense_words if w in text)
        sense_per_k = senses / (len(text) / 1000)
        if per_k < ev_thr:
            score += 20
            reasons.append(f"事件密度低({per_k:.1f}/千字)")
        if sense_per_k < se_thr:
            score += 15
            reasons.append(f"具象细节少({sense_per_k:.1f}/千字)")
    return min(100, score), reasons[:3]


LAYERS = [
    ("词层", "AI高频词", layer_word),
    ("语层", "套话短语", layer_phrase),
    ("句层", "句式单一", layer_sentence),
    ("语义层", "语义重复/空转", layer_semantic),
    ("指纹层", "风格一致性", layer_fingerprint),
    ("行为层", "AI行为模式", layer_behavior),
]


def run_scan(text, profile=None):
    """六层扫描主入口。profile 为可选用户风格档案（T-4）。"""
    results = []
    for name, desc, fn in LAYERS:
        if name == "指纹层":
            score, examples = layer_fingerprint(text, profile)
        else:
            score, examples = fn(text)
        results.append({"layer": name, "desc": desc, "score": score, "examples": examples})
    # R-7 结论：AI 感主要来自哪一层（取分数最高且 >30 的层）
    scored = [r for r in results if r["score"] > 30]
    scored.sort(key=lambda r: -r["score"])
    main_layers = [r["layer"] for r in scored[:2]] if scored else []
    overall = round(sum(r["score"] for r in results) / len(results))
    return {
        "version": VERSION,
        "status": "ok",
        "overall_score": overall,
        "layers": results,
        "main_sources": main_layers,
        "conclusion": (f"AI感主要来自: {'、'.join(main_layers)}（建议优先处理该层）"
                       if main_layers else "各层均未检出明显AI痕迹"),
        "profile_used": bool(profile),
        "disclaimer": "六层扫描为本地启发式估算（非权威），供作者自查定位；不替代平台检测。",
    }


def report(r):
    print(f"══ AI 痕迹六层扫描报告 v{r['version']} ══")
    print(f"综合 AI 痕迹分: {r['overall_score']}/100")
    print(f"结论: {r['conclusion']}")
    for L in r["layers"]:
        bar = "█" * (L["score"] // 10)
        print(f"\n[{L['layer']}] {L['desc']}: {L['score']}/100 {bar}")
        if L["examples"]:
            print("  命中: " + "、".join(str(e) for e in L["examples"]))
    print(f"\n{r['disclaimer']}")


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    filepath = argv[0]
    as_json = "--json" in argv
    profile = None
    if "--profile" in argv:
        i = argv.index("--profile")
        if i + 1 < len(argv):
            try:
                profile = build_profile(read_text(argv[i + 1]))
            except Exception as e:
                print(f"⚠ 用户风格档案读取失败: {e}（将跳过档案对比）")
    try:
        text = read_text(filepath)
    except Exception as e:
        print(f"❌ 读取失败: {filepath}（{e}）")
        return 1
    r = run_scan(text, profile)
    if as_json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        report(r)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
