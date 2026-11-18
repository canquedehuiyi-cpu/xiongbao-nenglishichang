#!/usr/bin/env python3
"""quality_depth.py — 深度文本质量检测引擎（1.0.6 新增，E-1/E-2）

对标 2026 年网文平台公开的 AI 治理维度，把"平台惩罚项"转化为"质量检测项"。
所有检测均为本地启发式估算，输出带"估算/非权威"标注，不承诺通过任何平台检测。

E-1 质量层新增维度（接入 quality_check.py）:
    word_frequency_anomaly   词频异常（高频词过度集中）
    sentence_uniformity      句式单一（句首/句式模板重复）
    emotion_flatness         情绪波动平缓（情绪表达稀疏或分布不均）
    logic_coherence          逻辑连贯性（因果断链/指代跳变，启发式）
    style_consistency        写作风格一致性（前后语体漂移）
    semantic_repetition      语义重复/车轱辘话（相邻句 n-gram 重叠 + 同义反复，1.0.7）

E-2 叙事层新增维度（接入 narrative_check.py）:
    stiff_dialogue           对话僵硬（无动作伴随/无信息增量）
    repeated_sentences       语句重复（相似句堆叠）
    empty_plot               空洞水文（事件密度低）
    pacing_distribution      节奏/爽点分布（段落长度与短句节奏）

用法: 本模块为库，供 quality_check.py / narrative_check.py / opening_check.py 导入。
"""

import json
import re
from collections import Counter
from pathlib import Path

try:
    from common import tokenize  # 与全库共享的可选依赖层（jieba 可选）
except ImportError:
    def tokenize(text, lang="zh"):
        """兜底分词：字符级 2-gram（避免本模块在无 common 时不可用）。"""
        clean = re.sub(r"[\s，。！？；：、,.!?;:\"'“”‘’（）()\[\]{}]", "", text)
        return [clean[i:i + 2] for i in range(max(0, len(clean) - 1)) if clean[i:i + 2]]


# ---------- 工具 ----------

def _split_sents(text):
    """按中英日韩句末标点切句，保留标点。"""
    return [s.strip() for s in re.split(r"(?<=[。！？；.!?])", text) if s.strip()]


def _norm(text):
    return re.sub(r"[\s，。！？；：、,.!?;:\"'“”‘’（）()\[\]{}]", "", text)


# ---------- E-1 质量层新增维度 ----------

def word_frequency_anomaly(text, lang="zh"):
    """词频异常（E-1）：TOP 高频词占比过高 → 用词贫乏、AI 风格。

    返回 {pass, value, detail}；value 为 TOP10 词块覆盖率(%)。
    """
    tokens = tokenize(text, lang)
    if len(tokens) < 40:
        return {"pass": None, "value": 0, "detail": "样本过短，跳过词频异常检测"}
    cnt = Counter(tokens)
    total = len(tokens)
    top10 = sum(n for _, n in cnt.most_common(10))
    share = top10 / total * 100
    # 覆盖率 > 45% 判为用词过度集中（AI 词频异常特征），启发式阈值
    ok = share <= 45
    detail = f"TOP10 词块覆盖 {share:.1f}%{'（用词集中，建议增加变化）' if not ok else ''}"
    return {"pass": ok, "value": round(share, 1), "detail": detail}


def sentence_uniformity(text, lang="zh"):
    """句式单一（E-1）：句首字分布过度集中 + 短句占比失衡。

    AI 文本句式模板化：句首重复率高、句长集中在同一区间。
    """
    sents = _split_sents(text)
    if len(sents) < 6:
        return {"pass": None, "value": 0, "detail": "样本过短，跳过句式单一检测"}
    heads = [_norm(s)[:2] for s in sents if _norm(s)]
    if not heads:
        return {"pass": None, "value": 0, "detail": "无可分析的句子"}
    hc = Counter(heads)
    top_head = hc.most_common(1)[0][1] / len(heads) * 100
    lens = [len(_norm(s)) for s in sents]
    mid = [l for l in lens if 8 <= l <= 30]
    mid_ratio = len(mid) / len(lens) * 100
    # 句首重复 > 30% 或 中句占比 > 85%（句式过于整齐）→ 判句式单一
    ok = not (top_head > 30 or mid_ratio > 85)
    detail = (f"句首重复 {top_head:.0f}% / 中句占比 {mid_ratio:.0f}%"
              + ("" if ok else "（句式过于整齐，建议长短错落）"))
    return {"pass": ok, "value": round(max(top_head, mid_ratio), 1), "detail": detail}


def emotion_flatness(text, lang="zh"):
    """情绪波动平缓（E-1）：情绪标记词分布稀疏或全文无起伏。

    启发式：全文情绪词命中率极低（<0.2/千字）或集中出现在单一段落（分布不均）。
    """
    EMOTION = re.compile(
        r"愤怒|愤怒地|焦虑|兴奋|紧张|恐惧|悲伤|高兴|激动|委屈|失望|震惊|"
        r"angry|anxious|excited|nervous|afraid|sad|happy|moved|disappointed|"
        r"怒|喜|哀|楽|悲し|恐れ|ドキドキ|"
        r"화|기쁨|슬픔|긴장|두려", re.IGNORECASE)
    sents = _split_sents(text)
    if len(sents) < 6:
        return {"pass": None, "value": 0, "detail": "样本过短，跳过情绪波动检测"}
    per_sent = [1 if EMOTION.search(s) else 0 for s in sents]
    hits = sum(per_sent)
    rate = hits / (len(text) / 1000)
    # 情绪词过少（<0.3/千字）→ 情绪表达稀薄（AI 情绪平缓特征）
    ok = rate >= 0.3
    detail = f"情绪词密度 {rate:.2f}/千字" + ("" if ok else "（情绪表达稀薄，建议加入身体反应/心理起伏）")
    return {"pass": ok, "value": round(rate, 2), "detail": detail}


def logic_coherence(text, lang="zh"):
    """逻辑连贯性（E-1，启发式）：指代密度与因果连接失衡。

    检测：第三人称指代词密度过高（指代跳变风险）+ 因果/转折词缺失或滥用。
    仅作自查参考，标注非权威。
    """
    if len(text) < 100:
        return {"pass": None, "value": 0, "detail": "样本过短，跳过逻辑连贯性检测"}
    pronoun_n = len(re.findall(r"他|她|它|他们|她们|它们|他[们]?[的]?", text))
    causal_n = len(re.findall(r"因为|所以|因此|然而|但是|不过|于是|由于", text))
    # 指代词/百字
    pro_rate = pronoun_n / (len(text) / 100)
    # 有因果/转折词则视为衔接存在；指代过密且转折词过少 → 提示断链风险
    ok = True
    detail = f"指代密度 {pro_rate:.1f}/百字，衔接词 {causal_n} 处"
    if pro_rate > 6 and causal_n < 3:
        ok = False
        detail += "（指代密集且衔接词少，建议核查指代跳变）"
    return {"pass": ok, "value": round(pro_rate, 1), "detail": detail}


def style_consistency(text, lang="zh"):
    """写作风格一致性（E-1）：前后半段语体/句长/用词漂移。

    把文本切为前后两半，比较句长分布与用词熵的差异；差异大 → 风格漂移。
    """
    if len(text) < 300:
        return {"pass": None, "value": 0, "detail": "样本过短，跳过风格一致性检测"}
    half = len(text) // 2
    a, b = text[:half], text[half:]

    def sent_len_profile(t):
        lens = [len(_norm(s)) for s in _split_sents(t) if _norm(s)]
        if not lens:
            return 0.0
        mean = sum(lens) / len(lens)
        var = (sum((l - mean) ** 2 for l in lens) / len(lens)) ** 0.5
        return round(mean + var, 1)

    pa, pb = sent_len_profile(a), sent_len_profile(b)
    diff = abs(pa - pb)
    # 句长形态差异 > 12 → 语体/节奏漂移明显
    ok = diff <= 12
    detail = f"前后半句长形态 {pa} vs {pb}（差异 {diff:.1f}）" + ("" if ok else "（风格漂移，建议统一语体）")
    return {"pass": ok, "value": round(diff, 1), "detail": detail}


# ---------- E-2 叙事层新增维度 ----------

def stiff_dialogue(text, lang="zh"):
    """对话僵硬（E-2）：对话句无伴随动作/无信息增量。

    启发式：纯"说话"句（引号内独立成句且前后无动作描写）占比过高。
    """
    sents = _split_sents(text)
    if len(sents) < 6:
        return {"pass": None, "value": 0, "detail": "样本过短，跳过对话僵硬检测"}
    # 引号内对话句
    quote_sents = [s for s in sents if ('"' in s or "“" in s or "「" in s or "『" in s)]
    if not quote_sents:
        return {"pass": None, "value": 0, "detail": "无对话句，跳过"}
    # 对话句是否伴随动作/表情/心理描写
    action = re.compile(r"说|道|喊|笑|皱眉|点头|摇头|抬头|低头|瞪|拍|站|走|坐|看|听|叹气|沉吟")
    stiff = [s for s in quote_sents if not action.search(s) and len(s) < 60]
    stiff_ratio = len(stiff) / len(quote_sents) * 100
    ok = stiff_ratio <= 60
    detail = f"对话句 {len(quote_sents)} 句，纯对话无动作伴随 {len(stiff)} 句（{stiff_ratio:.0f}%）" \
             + ("" if ok else "（对话僵硬，建议伴随动作/神态描写）")
    return {"pass": ok, "value": round(stiff_ratio, 1), "detail": detail}


def repeated_sentences(text, lang="zh"):
    """语句重复（E-2）：相似句子堆叠。

    用 8 字片段滑动窗口，检测文本中重复出现的片段（排除标点）。
    """
    if len(text) < 100:
        return {"pass": None, "value": 0, "detail": "样本过短，跳过语句重复检测"}
    clean = _norm(text)
    if len(clean) < 16:
        return {"pass": None, "value": 0, "detail": "文本过短，跳过语句重复检测"}
    grams = Counter(clean[i:i + 8] for i in range(len(clean) - 7))
    dup = {g: n for g, n in grams.items() if n >= 3}
    ok = len(dup) == 0
    detail = f"重复 8 字片段 {len(dup)} 种" + ("" if ok else f"（如『{sorted(dup)[:2]}』重复出现，建议改写）")
    return {"pass": ok, "value": len(dup), "detail": detail}


def empty_plot(text, lang="zh"):
    """空洞水文（E-2）：事件密度低。

    动作/变化类动词密度过低 + 段落无推进 → 流水账/无有效剧情。
    """
    if len(text) < 100:
        return {"pass": None, "value": 0, "detail": "样本过短，跳过事件密度检测"}
    event = re.compile(
        r"杀|打|逃|追|冲|闯|砸|抢|夺|救|摔|倒|跳|跑|走|进|出|遇|撞|破|夺|"
        r"run|fight|escape|chase|break|grab|fall|jump|kill|save|"
        r"戦|走る|逃げ|倒れ|ぶつか|"
        r"달|싸우|도망|부수|잡", re.IGNORECASE)
    event_n = len(event.findall(text))
    rate = event_n / (len(text) / 1000)
    ok = rate >= 1.0
    detail = f"事件动作密度 {rate:.1f}/千字" + ("" if ok else "（事件密度低，疑似流水账/空洞水文，建议增加剧情推进）")
    return {"pass": ok, "value": round(rate, 1), "detail": detail}


def pacing_distribution(text, lang="zh"):
    """节奏/爽点分布（E-2）：段落长度分布 + 短句节奏点。

    全为长段落（节奏平缓）或全为极短段（碎节奏）都提示节奏问题；
    理想：长短段落交错。
    """
    paras = [p.strip() for p in re.split(r"\n+", text) if p.strip()]
    if len(paras) < 4:
        return {"pass": None, "value": 0, "detail": "段落过少，跳过节奏检测"}
    plens = [len(_norm(p)) for p in paras]
    short = [p for p in plens if p < 30]
    long_ = [p for p in plens if p > 120]
    short_ratio = len(short) / len(paras) * 100
    long_ratio = len(long_) / len(paras) * 100
    # 短段 > 80% 或 长段 > 80% → 节奏失衡
    ok = not (short_ratio > 80 or long_ratio > 80)
    detail = f"段落 {len(paras)} 段：短段 {short_ratio:.0f}% / 长段 {long_ratio:.0f}%" \
             + ("" if ok else "（节奏失衡，建议长短段落交错营造爽点起伏）")
    return {"pass": ok, "value": round(max(short_ratio, long_ratio), 1), "detail": detail}


def ja_ko_politeness(text, lang):
    """日韩语体一致性（E-7）：语体混用是日韩轻小说/网文 AI 味高频特征。

    日文: です/ます（敬体）与 だ/である（常体）混用
    韩文: 합니다/ㅂ니다（正式）与 해요（半敬）与 해（半语）混用
    """
    if lang == "ja":
        polite = len(re.findall(r"です|ます|でした|ました", text))
        plain = len(re.findall(r"[^でま]だ。|である|だった。", text))
        if polite == 0 and plain == 0:
            return {"pass": None, "value": 0, "detail": "未检出明显语体标记，跳过"}
        mix = polite > 0 and plain > 0
        return {"pass": not mix, "value": round(abs(polite - plain), 1),
                "detail": f"敬体 {polite} 处 / 常体 {plain} 处" + ("（语体混用，建议统一）" if mix else "")}
    if lang == "ko":
        formal = len(re.findall(r"합니다|ㅂ니다|습니다|입니다", text))
        informal = len(re.findall(r"해요|예요|이에요", text))
        plain = len(re.findall(r"해\.|한다\.|이다\.", text))
        if formal == 0 and informal == 0 and plain == 0:
            return {"pass": None, "value": 0, "detail": "未检出明显语体标记，跳过"}
        active = [v for v in (formal, informal, plain) if v > 0]
        mix = len(active) >= 2
        return {"pass": not mix, "value": round(max(active), 1),
                "detail": f"正式 {formal} / 半敬 {informal} / 半语 {plain}" + ("（语体混用，建议统一）" if mix else "")}
    return {"pass": None, "value": 0, "detail": "非日韩文本，跳过"}


# ---------- 汇总 ----------

def _load_semantic_features():
    """从黑名单 JSON 的 semantic_features 分区读取语义层阈值（单一数据源，带默认回退）。"""
    try:
        p = Path(__file__).resolve().parent.parent / "references" / "antiai_blacklist.json"
        with open(p, encoding="utf-8") as f:
            return json.load(f).get("semantic_features", {})
    except Exception:
        return {}


_SF = _load_semantic_features()


def semantic_repetition(text, lang="zh"):
    """语义重复/车轱辘话（E-1，1.0.7）：相邻句 n-gram 重叠 + 同义反复。

    与 six_layer_scan 的 R-4 语义层共用此实现（单一实现，避免重复逻辑）。
    参数来自黑名单 JSON semantic_features 分区（单一数据源）。
    """
    ngram = _SF.get("overlap_ngram", 2)
    min_overlap = _SF.get("overlap_min_count", 2)
    len_delta = _SF.get("same_sentence_len_delta", 2)
    ratio_high = _SF.get("overlap_ratio_high", 0.3)
    sents = _split_sents(text)
    sents = [s.strip() for s in sents if len(s.strip()) >= 4]
    if len(sents) < 3:
        return {"pass": None, "value": 0.0, "detail": "样本过短，跳过语义重复检测"}

    def ngrams(s, n):
        s = re.sub(r"\s", "", s)
        return {s[i:i + n] for i in range(len(s) - n + 1)}

    overlap_pairs = 0
    for i in range(1, len(sents)):
        a, b = ngrams(sents[i - 1], ngram), ngrams(sents[i], ngram)
        if not a or not b:
            continue
        if len(a & b) >= min_overlap:
            overlap_pairs += 1
    overlap_ratio = overlap_pairs / (len(sents) - 1)

    repeat = 0
    for i in range(1, len(sents)):
        a, b = sents[i - 1].strip(), sents[i].strip()
        if abs(len(a) - len(b)) <= len_delta and a[:-2] == b[:-2]:
            repeat += 1

    ok = not (overlap_ratio > ratio_high or repeat >= 3)
    detail = (f"相邻句重叠率 {overlap_ratio:.0%}，同式反复 {repeat} 处"
              + ("" if ok else "（车轱辘话/语义空转，建议删减重复、提升信息增量）"))
    return {"pass": ok, "value": round(overlap_ratio, 2), "detail": detail}


DEPTH_CHECKS_QUALITY = [  # E-1 质量层
    ("词频异常", word_frequency_anomaly),
    ("句式单一", sentence_uniformity),
    ("情绪波动", emotion_flatness),
    ("逻辑连贯", logic_coherence),
    ("风格一致", style_consistency),
    ("语义重复", semantic_repetition),  # 1.0.7 新增（供 six_layer_scan R-4 复用）
]

DEPTH_CHECKS_NARRATIVE = [  # E-2 叙事层
    ("对话僵硬", stiff_dialogue),
    ("语句重复", repeated_sentences),
    ("事件密度", empty_plot),
    ("节奏分布", pacing_distribution),
]


def run_quality_depth(text, lang="zh", which="quality"):
    """运行指定组的深度检测，返回 [{name, pass, value, detail}]。

    which: quality（E-1） / narrative（E-2）
    """
    table = DEPTH_CHECKS_QUALITY if which == "quality" else DEPTH_CHECKS_NARRATIVE
    out = []
    for name, fn in table:
        try:
            r = fn(text, lang)
        except Exception:
            r = {"pass": None, "value": 0, "detail": "检测异常，跳过"}
        out.append({"name": name, "pass": r.get("pass"), "value": r.get("value"),
                    "detail": r.get("detail", "")})
    return out


if __name__ == "__main__":
    import sys
    from pathlib import Path

    if len(sys.argv) < 2:
        print("用法: python3 quality_depth.py <文件.md> [quality|narrative]")
        sys.exit(1)
    filepath = sys.argv[1]
    if filepath in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)
    which = sys.argv[2] if len(sys.argv) > 2 else "quality"
    text = Path(filepath).read_text(encoding="utf-8-sig")
    try:
        from quality_check import detect_language
        lang = detect_language(text)
    except Exception:
        lang = "zh"
    results = run_quality_depth(text, lang, which)
    print(f"🔍 深度检测（{which}层）: {filepath}  [启发式估算，非权威检测]")
    for r in results:
        mark = "✅" if r["pass"] else ("➖" if r["pass"] is None else "❌")
        print(f"  {mark} {r['name']}: {r['detail']}")
