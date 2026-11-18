#!/usr/bin/env python3
"""creation_engine.py — 创作引擎（1.0.6 新增：ST蒸馏/IM仿写/CO续写/PL润色/DL对白）

定位：以人类为主导的 AI 辅助创作。本引擎输出的是"供作者人工加工的改稿建议方案"，
不生成"可直接投稿的 AI 成品正文"。最终成稿须由作者人工主导完成并主动标识。

子命令:
    distill   <作者文本.md> [--out 风格.json]      提取作者风格档案（ST）
    imitate   <风格.json> <目标文本.md>            按风格档案给出改稿建议（IM）
    continue  <正文.md> [--mode 模式]              续写方向与钩子建议（CO）
    polish    <正文.md> [--lock 术语]              润色建议（PL）
    dialogue  <正文.md>                            对白增强建议（DL）

模式（三档，H-3）:
    conservative  保守：仅高置信度建议
    standard      标准：默认，常规建议
    deep          深度：含风格/叙事层面的扩展建议

说明: 全部为确定性规则引擎（零外部依赖，纯标准库）；建议仅供参考，由作者人工取舍。
"""

import json
import re
import sys
from pathlib import Path

from common import VERSION  # 版本单一来源

MODES = ("conservative", "standard", "deep")

# ---------- 通用工具 ----------

def _split_sents(text):
    return [s.strip() for s in re.split(r"(?<=[。！？；.!?])", text) if s.strip()]


def _norm(text):
    return re.sub(r"[\s，。！？；：、,.!?;:\"'“”‘’（）()\[\]{}]", "", text)


def _read(path):
    return Path(path).read_text(encoding="utf-8-sig")


def _need(mode, level):
    """三档强度过滤：level 1=保守 2=标准 3=深度。"""
    idx = {"conservative": 1, "standard": 2, "deep": 3}
    return idx.get(mode, 2) >= level


# ---------- ST 蒸馏 ----------

WEAK_VERBS = ["说", "想", "看", "走", "来", "去", "有", "做", "放", "拿"]
FLAT_ADJ = ["好", "坏", "大", "小", "多", "少", "快", "慢"]
TONE_WORDS = ["却", "竟", "偏偏", "居然", "果然", "难怪", "到底", "究竟", "可是", "不过"]


def distill(text, mode="standard"):
    """提取作者风格档案（8 维风格参数 + 可直接复用的改写偏好）。"""
    clean = _norm(text)
    if len(clean) < 100:
        return {"status": "skip", "reason": "文本过短（<100字），风格档案不具代表性"}
    sents = _split_sents(text)
    lens = [len(s) for s in sents if s]
    avg_len = round(sum(lens) / len(lens), 1) if lens else 0
    var = round((sum((l - avg_len) ** 2 for l in lens) / len(lens)) ** 0.5, 1) if lens else 0
    # 高频词（排除停用后）
    import collections
    tokens = re.findall(r"[\u4e00-\u9fff]{2,4}", clean)
    cnt = collections.Counter(tokens)
    top = [w for w, c in cnt.most_common(20) if w not in _norm_stop()][:10]
    # 标点习惯
    per_k = len(text) / 1000 if len(text) else 1
    dash = len(re.findall(r"—|——", text)) / per_k
    ell = len(re.findall(r"…|\.\.\.", text)) / per_k
    bang = len(re.findall(r"[!！]", text)) / per_k
    question = len(re.findall(r"[?？]", text)) / per_k
    # 段落风格
    paras = [p.strip() for p in re.split(r"\n+", text) if p.strip()]
    para_lens = [len(_norm(p)) for p in paras]
    para_style = "长短交错" if len(paras) >= 4 and max(para_lens) / (sum(para_lens) / len(para_lens)) > 1.8 else "均匀"
    # 结尾偏好
    tail = sents[-1][-6:] if sents else ""
    ending = "钩子/悬念" if any(w in tail for w in ("却", "?", "？", "吗", "么")) else "陈述收束"
    profile = {
        "version": VERSION,
        "mode": mode,
        "source_len": len(clean),
        "syntax": {"avg_sentence_len": avg_len, "sentence_std": var},
        "vocabulary": {"top_words": top},
        "punctuation": {"dash_per_k": round(dash, 1), "ellipsis_per_k": round(ell, 1),
                        "bang_per_k": round(bang, 1), "question_per_k": round(question, 1)},
        "paragraph": {"style": para_style, "avg_len": round(sum(para_lens) / len(para_lens), 1) if para_lens else 0},
        "ending": ending,
        "advice": "建议基于以上风格参数进行仿写；仿写成稿须由作者人工主导并主动标识AI辅助。",
    }
    return {"status": "ok", "profile": profile}


def _norm_stop():
    return {"一个", "这个", "那个", "我们", "你们", "他们", "自己", "什么", "这样", "那样",
            "因为", "所以", "但是", "然后", "现在", "已经", "可以", "还是", "不是", "就是"}


# ---------- IM 仿写 ----------

def imitate(profile, text, mode="standard"):
    """按风格档案对目标文本给出改稿建议（输出建议，非成品正文）。"""
    if not isinstance(profile, dict) or "syntax" not in profile:
        return {"status": "skip", "reason": "风格档案无效，请先用 distill 生成"}
    target = profile["syntax"].get("avg_sentence_len", 0)
    suggestions = []
    sents = _split_sents(text)
    for s in sents:
        n = len(_norm(s))
        # 句长对齐建议
        if target and abs(n - target) > target * 0.8 and _need(mode, 2):
            suggestions.append({
                "kind": "句长",
                "original": s[:40],
                "suggestion": f"目标句长约 {target} 字，当前 {n} 字，建议{'拆分' if n > target else '合并'}以贴近该风格",
                "reason": "句长形态是风格档案的显著维度",
            })
        # 平铺动词替换建议（标准模式及以上）
        if _need(mode, 2):
            for w in WEAK_VERBS:
                if re.search(w, s):
                    suggestions.append({
                        "kind": "动词",
                        "original": s[:40],
                        "suggestion": f"「{w}」较平，建议替换为带动作/神态的具体动词",
                        "reason": "作者档案偏好具体化动词（参考 top_words）",
                    })
                    break
    # 标点习惯对齐（profile 缺失该键时安全跳过）
    punct = profile.get("punctuation") or {}
    if punct.get("dash_per_k", 0) > 1 and _need(mode, 2):
        suggestions.append({"kind": "标点", "original": "", "suggestion": "该作者习惯使用破折号，可在关键处补充 1-2 处",
                            "reason": "对标作者标点习惯"})
    if len(suggestions) > 8:
        suggestions = suggestions[:8]
    return {"status": "ok", "profile_based": True, "suggestions": suggestions,
            "note": "以上为仿写改稿建议，成稿须作者人工主导并主动标识。"}


# ---------- CO 续写 ----------

def continue_story(text, mode="standard"):
    """续写方向建议：识别未闭合线索、人物状态、可延展钩子。"""
    sents = _split_sents(text)
    if len(sents) < 3:
        return {"status": "skip", "reason": "文本过短，无法分析续写方向"}
    # 未闭合线索：疑问/悬念/冲突词
    open_q = [s for s in sents[-8:] if re.search(r"[?？]|究竟|到底|为什么|难道|秘密|真相|还没|尚未", s)]
    # 人物状态（仅取"XX说/XX道＋对话标点"前的 2-3 字，避免把量词/名词误判为人名）
    raw_chars = re.findall(r"[\u4e00-\u9fff]{2,3}(?=[说道][:：，,])", text)
    _STOP_IN_NAME = "的了着把我你他她这那就不也都很在以及为"
    chars = [c for c in raw_chars
             if not any(ch in c for ch in _STOP_IN_NAME)
             and c not in ("因为", "所以", "但是", "然后", "可是", "忽然", "突然", "现在", "已经", "最终", "终于")]
    # 冲突词
    conflict = len(re.findall(r"杀|打|逃|追|闯|怒|仇|斗|争|抢|夺|危|险|死|血", text[-500:]))
    directions = []
    if open_q:
        directions.append({"kind": "解答线", "suggestion": "优先回收最近的悬念/疑问：", "anchor": open_q[-1][:30]})
    if chars:
        directions.append({"kind": "人物线", "suggestion": f"展开核心人物（{'、'.join(list(set(chars))[:3])}）的目标与阻碍", "anchor": ""})
    if conflict > 0:
        directions.append({"kind": "冲突升级", "suggestion": "延续最近的冲突并升级一个层级，形成新的阻碍", "anchor": ""})
    if not directions:
        directions.append({"kind": "推进线", "suggestion": "引入新的目标/阻碍推动剧情，避免停留在现状描述", "anchor": ""})
    return {"status": "ok", "directions": directions[:3],
            "note": "续写方向建议，实际成稿由作者人工主导并主动标识。"}


# ---------- PL 润色 ----------

def polish(text, locked=None, mode="standard"):
    """润色建议：平铺动词/空泛形容词/句式重复，输出 {original→suggestion}。"""
    locked = locked or []
    suggestions = []
    sents = _split_sents(text)
    for s in sents:
        n = _norm(s)
        for w in WEAK_VERBS:
            m = re.search(rf"{w}(?:了|着)?(?:说|道)?", s)
            if m and _need(mode, 2) and not any(l in s for l in locked):
                suggestions.append({"kind": "动词升级", "original": s[:40],
                                    "suggestion": f"「{m.group(0)}」升级为带情绪/动作的具体动词（如：{_verb_hint(w)}）",
                                    "reason": "平铺动词削弱画面感"})
                break
        for a in FLAT_ADJ:
            if re.search(rf"很{a}|非常{a}|特别{a}", s) and _need(mode, 2):
                suggestions.append({"kind": "空泛形容", "original": s[:40],
                                    "suggestion": f"「很{a}」改用具体细节/比喻呈现（避免空泛形容）", "reason": "空泛形容词信息量低"})
                break
    # 术语锁定保护
    term_ok = all(l in text for l in locked)
    return {"status": "ok", "suggestions": suggestions[:8],
            "locked_terms": locked, "locked_terms_preserved": term_ok,
            "note": "润色建议，成稿由作者人工主导；锁定术语须保留。"}


def _verb_hint(w):
    return {"说": "低语/嚷/沉声道", "想": "盘算/琢磨/思忖", "看": "瞥/扫/凝视", "走": "踱/冲/挪",
            "来": "折返/趋近", "去": "撤离/疾步", "放": "搁/撂", "拿": "攥/抄起"}.get(w, "更具体的动作动词")


# ---------- DL 对白 ----------

def dialogue(text, mode="standard"):
    """对白增强建议：僵硬对话句 → 补动作/神态/心理。"""
    sents = _split_sents(text)
    advice = []
    action = re.compile(r"说|道|喊|笑|皱眉|点头|摇头|抬头|低头|瞪|拍|站|走|坐|看|听|叹气")
    for s in sents:
        if ('"' in s or "“" in s or "「" in s or "『" in s) and not action.search(s) and len(s) < 60:
            advice.append({"kind": "对白加动作", "original": s[:40],
                           "suggestion": "给这句对白补一个伴随动作/神态/心理（先写动作再落台词）",
                           "reason": "对话无动作伴随，读感僵硬"})
    return {"status": "ok", "suggestions": advice[:6],
            "note": "对白增强建议，成稿由作者人工主导。"}


# ---------- CLI ----------

def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd = argv[0]
    mode = "standard"
    locked = []
    # 解析参数：--mode/--lock 与其取值从位置参数中剔除，避免取值被误当文件路径
    positional = []
    i = 1
    while i < len(argv):
        a = argv[i]
        if a == "--mode" and i + 1 < len(argv):
            mode = argv[i + 1]
            i += 2
            continue
        if a == "--lock" and i + 1 < len(argv):
            locked = argv[i + 1].split(",")
            i += 2
            continue
        if a.startswith("--"):
            i += 1
            continue
        positional.append(a)
        i += 1
    if mode not in MODES:
        print(f"未知模式: {mode}（可选: conservative/standard/deep）")
        return 1
    args = positional

    if cmd == "distill" and args:
        data = distill(_read(args[0]), mode)
        if data["status"] == "skip":
            print("跳过:", data["reason"])
            return 0
        if "--out" in argv:
            i = argv.index("--out")
            Path(argv[i + 1]).write_text(json.dumps(data["profile"], ensure_ascii=False, indent=2), encoding="utf-8")
            print("已保存风格档案:", argv[i + 1])
        else:
            print(json.dumps(data["profile"], ensure_ascii=False, indent=2))
        return 0
    if cmd == "imitate" and len(args) >= 2:
        try:
            profile = json.loads(Path(args[0]).read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"❌ 风格档案读取失败: {args[0]}（{e}）")
            return 1
        data = imitate(profile, _read(args[1]), mode)
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0
    if cmd == "continue" and args:
        print(json.dumps(continue_story(_read(args[0]), mode), ensure_ascii=False, indent=2))
        return 0
    if cmd == "polish" and args:
        print(json.dumps(polish(_read(args[0]), locked, mode), ensure_ascii=False, indent=2))
        return 0
    if cmd == "dialogue" and args:
        print(json.dumps(dialogue(_read(args[0]), mode), ensure_ascii=False, indent=2))
        return 0
    print(f"未知命令: {cmd}（可用: distill/imitate/continue/polish/dialogue）")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
