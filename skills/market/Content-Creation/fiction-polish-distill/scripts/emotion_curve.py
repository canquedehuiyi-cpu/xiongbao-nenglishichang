#!/usr/bin/env python3
"""emotion_curve.py — 情绪曲线量化器 + 人味情感质量（1.0.7 新增：Q-1~Q-5）

把整章/整本书的情绪起伏量化成"段落粒度情绪曲线"，并量化"人味情感质量"——
区分"告诉读者感受"（直白情感标签）vs"让读者感受"（动作/身体/环境具象表达）。

    Q-1 段落粒度情绪强度打分（词汇情绪权重 + 事件强度 + 冲突密度）
    Q-2 情绪曲线输出（段落 → 情绪强度，平缓区/标签区标记）
    Q-3 对标平台维度（起点爽点分布 / 番茄"情绪波动平缓"）
    Q-4 人味情感质量（情感标签密度 vs 具象表达占比）
    Q-5 情感改写建议（平缓区/标签区给出方向）

用法:
    python3 emotion_curve.py <文本.md>              # 文本曲线报告
    python3 emotion_curve.py <文本.md> --json       # JSON 输出

说明:
    情绪强度为本地启发式估算（非权威），仅作作者自查参考；
    对标平台维度以官方公告口径为参考，不替代平台判定。
"""

import json
import re
import sys

from common import VERSION, read_text

# ---------- 情绪词库（含强度权重） ----------

POS_STRONG = ("狂喜", "欣喜若狂", "激动不已", "兴奋", "雀跃", "热血沸腾", "扬眉吐气", "意气风发", "振奋", "亢奋")
POS_MID = ("高兴", "开心", "喜悦", "欣慰", "满足", "愉快", "舒心", "欣喜", "欢喜", "快意", "畅快", "痛快")
POS_WEAK = ("轻松", "平静", "安稳", "宁静", "淡然", "松弛", "恬淡")

NEG_STRONG = ("愤怒", "暴怒", "怒不可遏", "悲痛欲绝", "绝望", "崩溃", "憎恨", "仇恨", "痛不欲生", "撕心裂肺", "心如刀割")
NEG_MID = ("悲伤", "难过", "伤心", "焦虑", "不安", "恐惧", "害怕", "沮丧", "失望", "委屈", "心酸", "痛苦", "懊恼", "惭愧")
NEG_WEAK = ("烦闷", "无聊", "低落", "惆怅", "怅然", "落寞", "茫然", "无奈", "疲惫")

POS_WORDS = {w: 3.0 for w in POS_STRONG} | {w: 2.0 for w in POS_MID} | {w: 1.0 for w in POS_WEAK}
NEG_WORDS = {w: -3.0 for w in NEG_STRONG} | {w: -2.0 for w in NEG_MID} | {w: -1.0 for w in NEG_WEAK}

# 事件强度词（冲突/反转/揭示 → 情绪强度放大）
EVENT_STRONG = ("爆发", "骤变", "逆转", "血溅", "惨死", "背叛", "揭露", "阴谋", "大战", "决裂", "身死", "灭门", "真相大白", "惊天")
EVENT_MID = ("冲突", "争吵", "对峙", "追赶", "受伤", "发现", "异变", "转折", "埋伏", "围攻", "惊变", "危机", "追杀")
EVENT_WEAK = ("相遇", "重逢", "告别", "回忆", "疑惑", "试探", "犹豫", "沉默")

# 身体反应/动作具象表达（"让读者感受"）
BODILY = ("攥紧", "颤抖", "发抖", "咬紧", "发白", "发青", "红眼眶", "喉头", "哽咽", "攥拳", "冷汗",
          "心跳", "胸口发闷", "泪", "咬牙", "指甲掐进", "喘不上气", "脸色煞白", "手抖", "腿软", "屏住呼吸", "倒吸一口凉气")
# 环境/氛围暗示（"让读者感受"）
AMBIENT = ("风声", "雨声", "夜色", "暗", "冷", "死寂", "阴沉", "寂静", "空荡", "昏暗", "萧瑟", "苍凉", "浓雾")

# 直白情感标签（"告诉读者感受"）：检测"情绪词"紧邻"他/她/我/心里/心中"等主体
LABEL_PAT = re.compile(r"(?:他|她|我|你|心里|心中|内心|心头|满心|忍不住|感到|觉得|显得)[^\n。！？，]{0,6}(愤怒|悲伤|伤心|高兴|开心|焦虑|恐惧|害怕|失望|委屈|绝望|紧张|兴奋|激动|难过|痛苦|不安|欣喜|欢喜|生气|恼火)")

PUNCT = "。！？；"


def split_paragraphs(text):
    """按空行/换行切段；无空行时按句群（每 3 句一段）兜底。"""
    paras = [p.strip() for p in re.split(r"\n\s*\n|\n", text) if p.strip()]
    if len(paras) >= 2:
        return paras
    # 单段兜底：按句群切分
    sents = [s.strip() for s in re.split(r"(?<=[。！？；])", text) if s.strip()]
    return ["".join(sents[i:i + 3]) for i in range(0, len(sents), 3)]


def para_emotion(para):
    """Q-1 段落情绪强度：词汇情绪加权 + 事件强度放大 + 冲突密度。返回 (-1~1, 依据)。"""
    score = 0.0
    reasons = []
    pos_hits = [w for w in POS_WORDS if w in para]
    neg_hits = [w for w in NEG_WORDS if w in para]
    if pos_hits:
        score += max(POS_WORDS[w] for w in pos_hits)
        reasons.append("正面词:" + ",".join(pos_hits[:3]))
    if neg_hits:
        score += min(NEG_WORDS[w] for w in neg_hits)
        reasons.append("负面词:" + ",".join(neg_hits[:3]))
    # 事件强度放大
    for w in EVENT_STRONG:
        if w in para:
            score += 2.0 if score >= 0 else -2.0
            reasons.append("强事件:" + w)
            break
    for w in EVENT_MID:
        if w in para:
            score += 1.0 if score >= 0 else -1.0
            reasons.append("事件:" + w)
            break
    # 归一化到 -1~1
    score = max(-1.0, min(1.0, score / 4.0))
    return round(score, 2), reasons


def detect_flat_zone(scores, window=3, threshold=0.35):
    """Q-3 平缓区检测：连续 window 段情绪强度绝对值均低于 threshold。"""
    zones = []
    i = 0
    n = len(scores)
    while i <= n - window:
        seg = scores[i:i + window]
        if all(abs(s) <= threshold for s in seg):
            j = i
            while j + 1 < n and abs(scores[j + 1]) <= threshold:
                j += 1
            zones.append({"start": i + 1, "end": j + 1, "len": j - i + 1})
            i = j + 1
        else:
            i += 1
    return zones


def detect_peaks(scores, window=2):
    """Q-3 爽点/情绪峰值：局部极大且强度超过前后邻段。"""
    peaks = []
    for i in range(1, len(scores) - 1):
        if scores[i] > scores[i - 1] and scores[i] >= scores[i + 1] and abs(scores[i]) > 0.35:
            peaks.append({"para": i + 1, "strength": scores[i]})
    return peaks


def human_touch_quality(text, paras):
    """Q-4 人味情感质量：具象表达占比 = 身体/环境具象 / (情感标签 + 具象)。"""
    label_hits = len(LABEL_PAT.findall(text))
    bodily = sum(1 for w in BODILY if w in text)
    ambient = sum(1 for w in AMBIENT if w in text)
    concrete = bodily + ambient
    total = label_hits + concrete
    quality = round(concrete / total * 100) if total else 50  # 无信号给中性 50
    return {
        "label_hits": label_hits,
        "bodily_hits": bodily,
        "ambient_hits": ambient,
        "concrete_hits": concrete,
        "quality_score": quality,  # 0-100，越高越"让读者感受"
    }


def run_curve(text):
    paras = split_paragraphs(text)
    scores = []
    details = []
    for p in paras:
        sc, reasons = para_emotion(p)
        scores.append(sc)
        details.append({"para": len(details) + 1, "strength": sc, "reasons": reasons[:3]})
    flat_zones = detect_flat_zone(scores)
    peaks = detect_peaks(scores)
    touch = human_touch_quality(text, paras)
    # 曲线波动统计（对标番茄"情绪波动平缓"）
    import statistics
    variance = round(statistics.pvariance(scores), 4) if len(scores) >= 2 else 0.0
    emotional_flat = variance < 0.06 and len(scores) >= 3
    # 爽点密度（对标起点"每章节奏"）
    peak_density = round(len(peaks) / max(1, len(paras)) * 100, 1)
    return {
        "version": VERSION,
        "status": "ok",
        "para_count": len(paras),
        "curve": scores,
        "details": details,
        "flat_zones": flat_zones,
        "peaks": peaks,
        "variance": variance,
        "emotional_flat": emotional_flat,
        "peak_density": peak_density,
        "human_touch": touch,
        "suggestions": suggest(flat_zones, touch, len(scores)),
        "disclaimer": "情绪强度为本地启发式估算（非权威），仅作作者自查参考；对标平台维度以官方公告口径为参考。",
    }


def suggest(flat_zones, touch, n):
    """Q-5 情感改写建议。"""
    s = []
    if flat_zones:
        for z in flat_zones[:3]:
            s.append(f"第 {z['start']}~{z['end']} 段情绪平缓（连续 {z['len']} 段），建议加入冲突/反转或情绪转折点")
    if touch["label_hits"] > 0 and touch["quality_score"] < 50:
        s.append(f"情感标签偏多（{touch['label_hits']} 处直白标签），建议把'他很伤心'类改写成具体动作/身体反应/环境暗示")
    if not s and n >= 3:
        s.append("情绪起伏与具象表达整体良好，可继续保持")
    return s


def report(r):
    print(f"══ 情绪曲线量化器报告 v{r['version']} ══")
    print(f"段落数: {r['para_count']} | 情绪方差: {r['variance']} "
          f"{'（偏平缓 ⚠）' if r['emotional_flat'] else ''}")
    print("情绪曲线（-1 至 +1，* 表示段落）:")
    for d in r["details"]:
        bar = "▁" * max(0, int((d["strength"] + 1) * 6))
        print(f"  {d['para']:>3} {d['strength']:+.2f} {bar} {' '.join(d['reasons'])}")
    if r["flat_zones"]:
        print(f"\n平缓区: " + "、".join(f"{z['start']}-{z['end']}" for z in r["flat_zones"]))
    if r["peaks"]:
        print(f"情绪峰值(爽点): " + "、".join(f"#{p['para']}({p['strength']:+.1f})" for p in r["peaks"]))
    t = r["human_touch"]
    print(f"\n人味情感质量: {t['quality_score']}/100（标签 {t['label_hits']} | "
          f"具象-身体 {t['bodily_hits']} | 具象-环境 {t['ambient_hits']}）")
    print("\n【建议】")
    for s in r["suggestions"]:
        print(f"  · {s}")
    print(f"\n{r['disclaimer']}")


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    filepath = argv[0]
    as_json = "--json" in argv
    try:
        text = read_text(filepath)
    except Exception as e:
        print(f"❌ 读取失败: {filepath}（{e}）")
        return 1
    r = run_curve(text)
    if as_json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        report(r)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
