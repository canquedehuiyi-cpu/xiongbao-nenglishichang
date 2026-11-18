#!/usr/bin/env python3
"""deai_loop.py — 检测-去味闭环（段级检测 → 针对性去味 → 复检，最多 3 轮）

将质量检测与去味引擎串成闭环：
    第 0 轮: 段级检测（人工质感评分/统计特征/残留/连接词/情感直球）→ 定位问题段
    每 轮:   对问题段应用规则化去味（连接词打散/套话删除/情感具象化/残留清除）
    复 检:   重新评分，输出"去味前后评分对比报告"

用法:
    python3 deai_loop.py <文件.md>                # 默认标准模式（2轮）
    python3 deai_loop.py <文件.md> --rounds 3     # 指定轮数（1-5）
    python3 deai_loop.py <文件.md> --mode 标准     # 三档模式: 保守(1轮)/标准(2轮)/深度(4轮)
    python3 deai_loop.py <文件.md> --json         # JSON 输出

模式（H-3 三档）:
    保守      conservative   1 轮（最小干预，适合已较自然文本）
    标准      standard       2 轮（默认，常规处理）
    深度      deep           4 轮（最大处理，适合 AI 味重的长文本）

说明:
    全部为确定性规则（同文本必同结果），零外部依赖；
    输出为"写作特征改善对比"，不承诺通过任何 AI 检测（检测技术持续升级）；
    处理完成请按《人工智能生成合成内容标识办法》与平台规则主动声明 AI 辅助。
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from quality_check import (  # noqa: E402
    detect_language,
    load_blacklist,
    rules_by_language,
    split_sentences,
    check_sentence_cv,
    calc_anti_ai_score,
    residue_scan,
    perplexity_estimate,
    burstiness_score,
    lexical_diversity,
)

from common import VERSION  # 版本单一来源（common.py）
BLACKLIST_FILE = Path(__file__).resolve().parent.parent / "references" / "antiai_blacklist.json"


def load_engine_rules():
    """从黑名单 JSON 的 engine_rules 分区加载引擎词表（单一数据源）。

    缺失/损坏时明确报错退出，不在代码内维护第二份词表。
    """
    data = load_blacklist()
    er = data.get("engine_rules")
    if not isinstance(er, dict):
        print("❌ 黑名单缺少 engine_rules 分区，请确认 skill 目录结构完整")
        sys.exit(2)
    return er


_ENGINE_RULES = load_engine_rules()

# ---- 规则化去味表（确定性替换；词表统一来自 antiai_blacklist.json 的 engine_rules） ----

# 1. AI 逻辑连接词 → 删除（让句子直接开始，形成"无连接词"自然跳接）
CONNECTOR_DROP = list(_ENGINE_RULES.get("connector_drop") or [])
# 2. 套话开头（删除）
CLICHE_OPEN = list(_ENGINE_RULES.get("cliche_open") or [])
# 3. 情感直球 → 身体反应（行为化）
EMOTION_TO_ACTION = dict(_ENGINE_RULES.get("emotion_to_action") or {})
# 4. 硬残留 → 删除整句（AI 对话痕迹，如"以下是为您修改…"）
HARD_RESIDUE_KEEP = list(_ENGINE_RULES.get("hard_residue_keep") or [])
# 5. 语境词表（多模态选择：武侠/都市/日常/奇幻——替换时结合语境避免千篇一律）
CONTEXT_WORDS = dict(_ENGINE_RULES.get("context_words") or {})


def build_replacement_pool(rule):
    """从规则构建多模态替换池：仅取 alternatives（异质可执行候选）。

    注意：replacement 字段是"策略描述"（如"行为化（攥拳/红眼…）"），
    不是可执行替换文本——绝不进池，避免把说明文字替换进正文。
    """
    return [a for a in (rule.get("alternatives") or []) if a]


class ReplacementTracker:
    """同文本防重复轮换：全局追踪（跨 feel 感知），同一替换词最近 4 次不重复；
    不同情感共用池时也感知已用词（避免多情感全用池头词）；池耗尽如实重置。"""

    def __init__(self):
        self.recent = []

    def pick(self, pool):
        if not pool:
            return None
        for cand in pool:
            if cand not in self.recent:
                self.recent.append(cand)
                if len(self.recent) > 4:
                    self.recent.pop(0)
                return cand
        # 池内候选全部用过 → 重置轮换（如实降级，报告会提示重复词供人工微调）
        self.recent = []
        return pool[0]

    def recent_used(self):
        return list(self.recent)


def load_groups(lang):
    blacklist = load_blacklist()
    return rules_by_language(blacklist, lang)


def apply_deai(sentence, groups, tracker=None, rule_log=None, rules=None):
    """对单个句子应用规则化去味（多模态选择：替换池 + 防重复轮换），返回 (新句, 改动数)。

    rules 为黑名单 rules 列表；由调用方一次性加载传入，避免每句重复读文件（性能）。
    """
    new = sentence
    changed = 0
    for w in CONNECTOR_DROP + CLICHE_OPEN:
        if w not in new:
            continue
        # 优先连同紧邻逗号一起删除，避免残留"句首逗号"瑕疵
        for sep in ("，", ","):
            if w + sep in new:
                new = new.replace(w + sep, "", 1)
                changed += 1
                break
        else:
            new = new.replace(w, "", 1)
            changed += 1
    # 情感直球：从黑名单规则加载多模态替换池（alternatives）→ 防重复轮换选择
    if tracker is not None:
        for rule in rules:
            if rule.get("category") not in ("情感直球", "emotional_labels", "感情直球", "감정직구"):
                continue
            if not rule.get("alternatives"):
                continue
            pat = rule.get("pattern", "")
            for feel in pat.split("|"):
                if feel and feel in new:
                    pool = build_replacement_pool(rule)
                    chosen = tracker.pick(pool)
                    if chosen and chosen != feel:
                        new = new.replace(feel, chosen, 1)
                        changed += 1
                        if rule_log is not None:
                            rule_log.append({"rule": rule["id"], "from": feel, "to": chosen})
    # 兜底（无 alternatives 规则覆盖的情感词）：固定映射兼容保留
    for feel, action in EMOTION_TO_ACTION.items():
        if feel in new:
            new = new.replace(feel, action)
            changed += 1
    for w in HARD_RESIDUE_KEEP:
        if w in new:
            return "", changed + 1  # 硬残留句直接移除
    if changed > 0:
        # 清理删除连接词后残留的句首标点与连续标点
        new = re.sub(r"^[\s，。；：、,]+", "", new)
        new = re.sub(r"[，。；：、,]{2,}", lambda m: m.group(0)[-1], new)
    return new, changed


_SENT_KEEP = re.compile(r"([^。！？!?；;\n]+[。！？!?；;]?)")


def split_keep_seps(text):
    """按句末标点切分并保留分隔符（区别于 quality_check.split_sentences 的剥离版）。

    用于改稿输出路径，避免重拼接时丢失句号/问号等句末标点。
    """
    return [s for s in _SENT_KEEP.findall(text) if s.strip()]


def detect_issues(text, lang, groups, rules=None):
    """段级检测：返回问题句列表（句子 + 问题标签）。

    情感直球检测覆盖跨语言（中/英/日/韩）——从黑名单规则的情感直球类
    （情感直球/emotional_labels/感情直球/감정직구）加载 pattern，大小写不敏感匹配。
    rules 由调用方一次性传入，避免重复读文件。
    """
    emo_terms = []
    emo_cats = ("情感直球", "emotional_labels", "感情直球", "감정직구")
    for rule in (rules if rules is not None else load_blacklist()["rules"]):
        if rule.get("category") in emo_cats:
            for term in rule.get("pattern", "").split("|"):
                if term and term not in emo_terms:
                    emo_terms.append(term)
    issues = []
    for s in split_sentences(text, lang):
        tags = []
        if len(s) < 2:
            continue
        for w in CONNECTOR_DROP + CLICHE_OPEN:
            if w in s:
                tags.append(f"连接词[{w}]")
                break
        for term in emo_terms:
            if term.lower() in s.lower():
                tags.append(f"情感直球[{term}]")
                break
        for w in HARD_RESIDUE_KEEP:
            if w in s:
                tags.append("硬残留")
                break
        if tags:
            issues.append({"sentence": s[:50], "tags": tags})
    return issues


def round_scores(text, lang, groups):
    """计算当前评分（人工质感评分 + 统计特征 + 残留数 + 连接词密度）。"""
    sent_cv, sent_count = check_sentence_cv(text, lang)
    anti = calc_anti_ai_score(text, lang, groups, sent_cv, sent_count)
    ppl = perplexity_estimate(text)
    burst = burstiness_score(text)
    ttr = lexical_diversity(text)
    res = residue_scan(text)
    conn_count = sum(text.count(w) for w in CONNECTOR_DROP)
    return {
        "anti_ai_score": anti,
        "perplexity": ppl,
        "burstiness": burst,
        "ttr": ttr,
        "residue_total": len(res),
        "residue_hard": len([h for h in res if h["type"] == "hard"]),
        "connector_count": conn_count,
    }


def run_loop(text, max_rounds=3):
    lang = detect_language(text)
    groups = load_groups(lang)
    tracker = ReplacementTracker()
    rule_log = []
    rules = load_blacklist()["rules"]  # 一次性加载，供各轮复用
    report = {"version": VERSION, "lang": lang, "rounds": [], "final": {}, "replacement_log": rule_log}

    for rnd in range(max_rounds + 1):
        scores = round_scores(text, lang, groups)
        report["rounds"].append({"round": rnd, "scores": scores})
        if rnd == max_rounds:
            break
        # 段级定位问题句
        issues = detect_issues(text, lang, groups, rules)
        if not issues:
            break  # 无问题句，提前收敛
        # 逐句去味（多模态替换：替换池 + 防重复轮换；保留句末标点）
        out_sents = []
        changed_total = 0
        for s in split_keep_seps(text):
            if len(s) < 2:
                out_sents.append(s)
                continue
            new, ch = apply_deai(s, groups, tracker, rule_log, rules)
            if new:
                out_sents.append(new)
            changed_total += ch
        text = "".join(out_sents)
        if changed_total == 0:
            break  # 无可改内容，停止

    report["rounds_used"] = len(report["rounds"]) - 1
    report["final"] = report["rounds"][-1]["scores"]
    report["output_text"] = text

    # 替换后复检：替换多样性检查（同一替换词高频重复（≥3 次）= 新的 AI 行为风险；
    # 间隔 4+ 句的 2 次复用属正常轮换，不提示）
    from collections import Counter
    used_words = Counter(e["to"] for e in rule_log)
    repeats = {w: c for w, c in used_words.items() if c >= 3}
    report["replacement_diversity"] = {
        "total_replacements": len(rule_log),
        "unique_words": len(used_words),
        "repeated_words": repeats,
        "note": "存在高频重复替换词（≥3次），建议人工微调" if repeats else "替换多样性良好（相邻替换不重复）",
    }
    return report, text


def print_report(report):
    print("══ 检测-去味闭环报告 ══")
    print(f"版本: {report['version']} | 语言: {report['lang']} | 实际轮数: {report['rounds_used']}")
    first = report["rounds"][0]["scores"]
    last = report["final"]
    print("\n| 指标 | 去味前 | 去味后 | 变化 |")
    print("|------|--------|--------|------|")
    for key, label in [
        ("anti_ai_score", "人工质感评分"),
        ("perplexity", "困惑度"),
        ("burstiness", "突发性"),
        ("ttr", "词汇多样性"),
        ("connector_count", "AI连接词数"),
        ("residue_hard", "硬残留"),
        ("residue_total", "残留总数"),
    ]:
        a, b = first.get(key), last.get(key)
        if a is None or b is None:
            continue
        diff = b - a
        arrow = "↑" if diff > 0 else ("↓" if diff < 0 else "—")
        print(f"| {label} | {a} | {b} | {arrow}{abs(diff):.1f} |")

    # 替换多样性（多模态）报告
    rule_log = report.get("replacement_log") or []
    div = report.get("replacement_diversity") or {}
    if rule_log:
        print("\n替换多样性（多模态选择）:")
        for e in rule_log[:8]:
            print(f"  [{e['rule']}] {e['from']} → {e['to']}")
        if div.get("repeated_words"):
            print(f"  ⚠ 高频重复替换词: {div['repeated_words']}（≥3次，建议人工微调，避免替换后重复=新 AI 行为）")
        else:
            print(f"  ✅ 相邻替换不重复（{div.get('total_replacements')} 次替换 / {div.get('unique_words')} 个不同词，防重复轮换生效）")

    print("\n说明: 以上为写作特征改善对比，不承诺通过任何 AI 检测（检测技术持续升级）。")
    print("合规提示: 本输出为 AI 辅助产出，发布前请按《人工智能生成合成内容标识办法》")
    print("与目标平台规则主动声明'包含 AI 辅助创作'；请勿伪造创作过程或隐瞒 AI 使用。")

    out_text = report.get("output_text")
    if out_text:
        print("\n════ 改稿后文本（请作者人工复核、按需进一步修改后再使用）════")
        print(out_text)
        print("════ 改稿后文本（完）════")


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    as_json = "--json" in argv
    max_rounds = 2  # 默认标准模式
    # 三档模式（H-3）：保守 1 轮 / 标准 2 轮 / 深度 4 轮
    MODE_ROUNDS = {"conservative": 1, "standard": 2, "deep": 4}
    MODE_ALIAS = {"保守": "conservative", "标准": "standard", "深度": "deep"}
    if "--mode" in argv:
        i = argv.index("--mode")
        if i + 1 < len(argv):
            m = argv[i + 1]
            m = MODE_ALIAS.get(m, m)
            if m in MODE_ROUNDS:
                max_rounds = MODE_ROUNDS[m]
    if "--rounds" in argv:
        i = argv.index("--rounds")
        if i + 1 < len(argv):
            try:
                max_rounds = max(1, min(5, int(argv[i + 1])))
            except ValueError:
                pass
    path = argv[0]
    p = Path(path)
    if not p.exists():
        print(f"文件不存在: {path}")
        return 1
    text = p.read_text(encoding="utf-8-sig", errors="replace")
    report, out_text = run_loop(text, max_rounds)
    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_report(report)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
