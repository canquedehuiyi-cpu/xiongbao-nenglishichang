#!/usr/bin/env python3
"""entity_tracking.py — 实体状态机 + 角色/剧情追踪（1.0.7 新增：P-1~P-6）

把人物/物品/地点当作"实体"建模，跨章节追踪状态与一致性，为整本书级创作提供
结构洞察（纯本地启发式，零外部依赖）：

    P-1 实体抽取与状态建模
    P-2 跨章节状态一致性（死亡后复活/物品凭空出现/位置跳跃矛盾）
    P-3 时间线追踪（时间词推进 + 时序矛盾）
    P-4 伏笔与回收（前文埋点 → 后文回收 / 未回收提示）
    P-5 剧情线推进摘要（每章事件 + 人物状态快照）
    P-6 角色声线档案（口头禅/高频词/句长偏好，说话不像自己的提示）

用法:
    python3 entity_tracking.py <书.md>              # 整本追踪
    python3 entity_tracking.py <书.md> --json       # JSON 输出
    python3 entity_tracking.py <书.md> --chapter 3  # 仅看第 3 章摘要

说明:
    本引擎为本地启发式估算（非权威），实体抽取/状态判定/伏笔回收均可能误报；
    所有"冲突/提示"以"建议人工确认"结尾，不替代人工审读。
"""

import json
import re
import sys
from collections import Counter, OrderedDict
from pathlib import Path

from common import VERSION, read_text

# ---------- 章节切分（与 pipeline 同口径：第X章 / Chapter N） ----------

CHAPTER_RE = re.compile(r"(?:\n\s*|^)(?:第[一二三四五六七八九十百千\d]+章[^\n]*|Chapter\s+\d+[^\n]*)(?:\n|$)")


def split_chapters(text):
    """按章节标题切分，返回 [(章节标题, 正文)]；无标题时整体作为单章。"""
    parts = []
    matches = list(CHAPTER_RE.finditer(text))
    if not matches:
        return [("正文", text)]
    for i, m in enumerate(matches):
        title = m.group(0).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if body:
            parts.append((title, body))
    return parts


# ---------- 实体抽取（P-1） ----------

# 中文停用词（专名抽取过滤）：常见虚词/泛指词，避免被当作实体
STOPWORDS = set("的了是在有和就都而及与或 一个 我们 不 你们 她们 它们 这那 这样 那样 这个 那个 什么 怎么 为什么 因为 所以 如果 但是 那么 其 其中 这些 那些 之乎者也 吧 吗 呢 啊 呀 嘛 哦 嗯 恩 唉 喂 哈 嘿".split())

# 高频泛指词（出现多但非实体）：按字数过滤时的额外排除
GENERIC = set("时候地方事情东西时间话声音眼神目光表情心情情绪气氛气息身影脚步手眼嘴脸眼泪光云风天气空气院子房间屋子门口窗前身后面前身边眼前心中心里脑海思绪念头想法感觉问题答案真相秘密消息线索证据理由原因结果办法方法道路前程命运生死成败得失进退恩怨爱恨情仇江湖天下世界人间岁月人生日子夜晚白天清晨黄昏半夜午夜过去未来现在此刻当下瞬间什么怎么为什么因为所以如果但是然而其实只是就是还是或者而且以及由于因此可是不过已经正在将要一直突然忽然终于原来到底究竟难道居然竟然反正毕竟不管无论除非假如只要既然却才又再便也还更太很非常十分特别最更加逐渐慢慢轻轻静静默默缓缓低声高声大声说道开口闭嘴转身回头抬头低头点头摇头笑了笑大声喊叫".split())

# 常见 2~4 字虚词/代词组合（非实体，滑动窗口过滤）
COMMON_2 = set("这个那个这些那些我们你们他们它们这样那样这里那里谁人大家众人一切所有每个任何其中此间眼下如今当初之前之后以前以后前后左右上下内外之间之时之日之处之人之事之地之王之中之上之下之外之内从而因而以免以便既已早已尚未未曾从来向来原本本来似乎仿佛好像犹如如同宛如恰似乃至以及连同伴随随着向着朝着对着".split())

# ---------- 数据源：entity_rules（来自 antiai_blacklist.json 单一数据源） ----------

def _load_entity_rules():
    """从黑名单 JSON 的 entity_rules 分区加载状态/时间/伏笔规则（带默认回退）。"""
    base = Path(__file__).resolve().parent.parent
    p = base / "references" / "antiai_blacklist.json"
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f).get("entity_rules", {})
    except Exception:
        return {}


_ER = _load_entity_rules()

# 状态词表（关键词 → 状态）
STATE_DEATH = tuple(_ER.get("state_death", ("死了", "身亡", "去世", "被杀", "遇害", "殒命", "战死", "丧命", "陨落")))
STATE_COMA = tuple(_ER.get("state_coma", ("昏迷", "晕倒", "晕厥", "昏过去", "不省人事", "昏迷不醒")))
STATE_GONE = tuple(_ER.get("state_gone", ("离开", "消失", "离去", "走了", "失踪", "远走", "下落不明", "不见了")))
STATE_ARRIVE = tuple(_ER.get("state_arrive", ("出现", "登场", "赶到", "现身", "露面", "回来了", "归来", "抵达")))
STATE_HOLD = tuple(_ER.get("state_hold", ("握着", "拿着", "带着", "持有", "腰间", "手中", "握紧", "攥着")))

# 时间词（相对推进/时段标记，用于 P-3 时间轴）
TIME_WORDS = {k: v for k, v in _ER.get("time_words", {
    "次日": 1, "第二天": 1, "第二日": 1, "翌日": 1, "隔日": 1, "第二天一早": 1,
    "三天后": 3, "三日后": 3, "几日后": 3, "数日后": 3, "半月后": 15, "半个月后": 15,
    "一个月后": 30, "一月后": 30, "半年后": 180, "一年后": 365, "翌年": 365,
    "当晚": 0, "当天": 0, "当天夜里": 0, "同一天": 0,
}).items()}
TIME_MARK = tuple(_ER.get("time_marks", ("黄昏", "深夜", "清晨", "午夜", "午后", "傍晚", "黎明", "晚上", "白天", "夜里")))

# 伏笔埋点词 / 回收词（P-4）
FORESHADOW_HIT = tuple(_ER.get("foreshadow_hit", ("奇怪的是", "却不知", "究竟", "之谜", "神秘", "不对劲",
                                                  "蹊跷", "疑惑", "难道", "似乎隐藏", "有些古怪", "说不清", "隐隐觉得")))
PAYOFF_HIT = tuple(_ER.get("payoff_hit", ("原来", "真相", "才知", "终于明白", "恍然大悟", "水落石出", "揭开", "谜底", "这才知道")))


def is_entity_candidate(w):
    """2~4 字高频中文串，排除停用/泛指/常见虚词后作为实体候选。"""
    if not w or not re.fullmatch(r"[\u4e00-\u9fff]{2,4}", w):
        return False
    if w in STOPWORDS or w in GENERIC or w in COMMON_2:
        return False
    # 排除纯叠词/明显非专名
    if len(set(w)) == 1:
        return False
    return True


def extract_entities(chapters):
    """P-1 实体抽取：滑动窗口统计 2~4 字串频率，出现≥3 次且非泛指词才记名。

    用滑动窗口（而非 findall 整段切块）保证"少年陈望"中的"陈望"等 2~3 字
    实体名能独立出现并被统计；低频的非词串（如"年陈"）因次数不足被过滤。
    """
    counter = Counter()
    for _, body in chapters:
        # 排除对话内容（对话里的词多为人称/口语，噪声大）
        prose = re.sub(r"“[^”]*”|『[^』]*』", "", body)
        for run in re.findall(r"[\u4e00-\u9fff]{2,}", prose):
            n = len(run)
            for L in (4, 3, 2):
                if L > n:
                    continue
                for i in range(n - L + 1):
                    w = run[i:i + L]
                    if is_entity_candidate(w):
                        counter[w] += 1
    entities = [w for w, c in counter.items() if c >= 3]
    # 长实体吞噬短串：若某候选是更长候选的子串且出现次数不高于更长者，
    # 说明它多半只是长实体切分出的碎片（如"黑衣"之于"黑衣人"），予以剔除。
    by_len = sorted(entities, key=lambda w: -len(w))
    keep = []
    for w in by_len:
        if any(w in longer and counter[longer] >= counter[w] for longer in by_len if len(longer) > len(w)):
            continue
        keep.append(w)
    # 按出现次数降序，最多 60 个
    keep.sort(key=lambda w: -counter[w])
    return keep[:60]


def detect_entity_state(entity, body):
    """P-1 状态检测：扫描正文中实体附近的死亡/昏迷/消失/抵达/持物状态词。

    返回 {state: 是否命中}；同一实体的多个状态可能同时出现（如"重伤昏迷"）。
    """
    states = {"death": False, "coma": False, "gone": False, "arrive": False, "hold": False}
    for m in re.finditer(re.escape(entity), body):
        ctx = body[max(0, m.start() - 20):m.end() + 20]
        if any(w in ctx for w in STATE_DEATH):
            states["death"] = True
        if any(w in ctx for w in STATE_COMA):
            states["coma"] = True
        if any(w in ctx for w in STATE_GONE):
            states["gone"] = True
        if any(w in ctx for w in STATE_ARRIVE):
            states["arrive"] = True
        if any(w in ctx for w in STATE_HOLD):
            states["hold"] = True
    return states


# ---------- 时间线（P-3） ----------

def extract_time_flow(chapters):
    """P-3 时间轴：每章相对时间推进（天）+ 时段标记。"""
    flow = []
    cursor = 0  # 累计天数（相对起点）
    for idx, (title, body) in enumerate(chapters, start=1):
        step = 0
        marks = []
        for tw, d in TIME_WORDS.items():
            if tw in body:
                step = d  # 取最后一个命中的推进值（更接近章尾）
        for tm in TIME_MARK:
            if tm in body:
                marks.append(tm)
        cursor += step
        flow.append({"chapter": idx, "title": title, "day_offset": cursor,
                     "step_days": step, "marks": list(dict.fromkeys(marks))})
    return flow


def detect_time_conflicts(flow):
    """P-3 时序矛盾：章节相对时间出现倒退（如"三天后"之后又"次日"）→ 提示。"""
    conflicts = []
    for i in range(1, len(flow)):
        prev, cur = flow[i - 1], flow[i]
        # 若上一章有明确推进、本章相对偏移反而小于上一章结尾偏移 → 疑似回拨
        if prev["step_days"] > 0 and cur["day_offset"] < prev["day_offset"]:
            conflicts.append({
                "chapter": cur["chapter"],
                "prev_day": prev["day_offset"],
                "cur_day": cur["day_offset"],
                "item": f"第{prev['chapter']}章推进至第 {prev['day_offset']} 天，第{cur['chapter']}章却回到第 {cur['day_offset']} 天，疑似时序回拨",
                "action": "请核对时间线是否合理（倒叙需显式标注）",
            })
    return conflicts


# ---------- 伏笔与回收（P-4） ----------

def extract_foreshadows(chapters):
    """P-4 伏笔：命中埋点词的句子记为埋点（去重，限量）。"""
    hits = []
    for idx, (_, body) in enumerate(chapters, start=1):
        for s in re.split(r"(?<=[。！？；])", body):
            if any(w in s for w in FORESHADOW_HIT):
                s2 = s.strip()
                if 6 <= len(s2) <= 60:
                    hits.append({"chapter": idx, "text": s2})
    # 去重
    seen = set()
    uniq = []
    for h in hits:
        if h["text"] not in seen:
            seen.add(h["text"])
            uniq.append(h)
    return uniq[:30]


def find_payoffs(chapters, foreshadows):
    """P-4 回收检测：埋点之后章节若出现回收词，则视为已回收。"""
    total = len(chapters)
    for f in foreshadows:
        paid = False
        for idx in range(f["chapter"], total + 1):
            _, body = chapters[idx - 1]
            if any(w in body for w in PAYOFF_HIT):
                paid = True
                break
        f["paid"] = paid


# ---------- 角色声线档案（P-6） ----------

def extract_dialogues(body):
    """提取对话片段列表（引号内内容）。"""
    return re.findall(r"“[^”]+”", body)


def entity_dialogue_stats(entity, chapters):
    """P-6 统计某实体所在段落附近的对话（实体名前后 40 字内的引号）。"""
    stats = {"sentences": [], "avg_len": 0.0, "top_words": [], "interjections": []}
    for _, body in chapters:
        for m in re.finditer(re.escape(entity), body):
            start = max(0, m.start() - 40)
            end = min(len(body), m.end() + 40)
            ctx = body[start:end]
            for d in extract_dialogues(ctx):
                t = d.strip("“”")
                if 2 <= len(t) <= 40:
                    stats["sentences"].append(t)
    if stats["sentences"]:
        stats["avg_len"] = round(sum(len(s) for s in stats["sentences"]) / len(stats["sentences"]), 1)
        words = []
        for s in stats["sentences"]:
            words.extend(re.findall(r"[\u4e00-\u9fff]{2,3}", s))
        c = Counter(w for w in words if w not in GENERIC and w not in STOPWORDS)
        stats["top_words"] = [w for w, _ in c.most_common(5)]
        stats["interjections"] = [w for w in ("嗯", "呵", "哼", "哈", "罢了", "也罢", "咦")
                                  if any(w in s for s in stats["sentences"])]
    return stats


# ---------- 主流程 ----------

def run_tracking(text):
    """整本追踪入口。返回结构化报告。"""
    chapters = split_chapters(text)
    entities = extract_entities(chapters)

    # P-1/P-2 每章状态 + 跨章一致性
    chapter_state = []  # {chapter, entities: {entity: states}}
    state_log = OrderedDict()  # entity → [{chapter, state}]
    for idx, (title, body) in enumerate(chapters, start=1):
        ent_states = {}
        for e in entities:
            st = detect_entity_state(e, body)
            if any(st.values()):
                ent_states[e] = {k: v for k, v in st.items() if v}
                for k, v in st.items():
                    if v:
                        state_log.setdefault(e, []).append({"chapter": idx, "state": k})
        chapter_state.append({"chapter": idx, "title": title, "entity_states": ent_states})

    # P-2 状态冲突：死亡/消失后再出现行动 → 建议人工确认
    conflicts = []
    for e, records in state_log.items():
        death_chap = [r["chapter"] for r in records if r["state"] == "death"]
        gone_chap = [r["chapter"] for r in records if r["state"] == "gone"]
        later_active = [r["chapter"] for r in records
                        if r["state"] in ("arrive", "hold") and death_chap and r["chapter"] > min(death_chap)]
        if death_chap and later_active:
            conflicts.append({
                "entity": e, "type": "死亡后复现",
                "item": f"「{e}」第 {death_chap[0]} 章被记为死亡，但第 {later_active[0]} 章又出现活动状态",
                "action": "若为复活/回忆/同名需显式交代，否则疑似状态矛盾",
            })
        elif gone_chap and later_active:
            conflicts.append({
                "entity": e, "type": "离开后复现",
                "item": f"「{e}」第 {gone_chap[0]} 章离开，第 {later_active[0]} 章又现",
                "action": "请核对离场后回归是否有合理交代",
            })

    # P-3 时间线
    flow = extract_time_flow(chapters)
    time_conflicts = detect_time_conflicts(flow)

    # P-4 伏笔
    foreshadows = extract_foreshadows(chapters)
    find_payoffs(chapters, foreshadows)
    unpaid = [f for f in foreshadows if not f["paid"]]

    # P-5 每章摘要：事件要点（取每章首尾若干句）+ 状态快照
    summaries = []
    for idx, (title, body) in enumerate(chapters, start=1):
        sents = [s.strip() for s in re.split(r"(?<=[。！？；])", body) if len(s.strip()) >= 6][:3]
        ent_here = list((chapter_state[idx - 1].get("entity_states") or {}).keys())[:8]
        summaries.append({
            "chapter": idx, "title": title,
            "key_points": sents,
            "active_entities": ent_here,
        })

    # P-6 声线档案（仅对对话量≥3 句的实体）
    voices = {}
    for e in entities:
        st = entity_dialogue_stats(e, chapters)
        if len(st["sentences"]) >= 3:
            voices[e] = {"avg_len": st["avg_len"], "top_words": st["top_words"],
                         "interjections": st["interjections"], "quote_count": len(st["sentences"])}

    return {
        "version": VERSION,
        "status": "ok",
        "chapters_count": len(chapters),
        "entities_count": len(entities),
        "entities": entities,
        "state_log": {k: v for k, v in state_log.items()},
        "conflicts": conflicts,
        "time_flow": flow,
        "time_conflicts": time_conflicts,
        "foreshadows": foreshadows,
        "unpaid_foreshadows": unpaid,
        "chapter_summaries": summaries,
        "voices": voices,
        "disclaimer": "本引擎为本地启发式估算（非权威），实体/状态/伏笔判定可能误报；冲突与提示均以人工确认为准。",
    }


def report(r, chapter_only=None):
    print(f"══ 实体状态机 + 角色/剧情追踪报告 v{r['version']} ══")
    print(f"章节数: {r['chapters_count']} | 识别实体: {r['entities_count']} 个")
    if r["conflicts"]:
        print("\n【状态一致性冲突】")
        for c in r["conflicts"]:
            print(f"  ⚠ {c['item']}")
            print(f"    → {c['action']}")
    else:
        print("\n状态一致性: 未检出明显冲突")
    if r["time_conflicts"]:
        print("\n【时间线提示】")
        for c in r["time_conflicts"]:
            print(f"  ⚠ {c['item']} → {c['action']}")
    if r["unpaid_foreshadows"]:
        print(f"\n【未回收伏笔】{len(r['unpaid_foreshadows'])} 处（建议后续安排回收）")
        for f in r["unpaid_foreshadows"][:10]:
            print(f"  第{f['chapter']}章: {f['text'][:40]}")
    if r["voices"]:
        print(f"\n【角色声线档案】{len(r['voices'])} 个")
        for name, v in list(r["voices"].items())[:12]:
            print(f"  {name}: 均句长 {v['avg_len']} | 高频词 {v['top_words'][:3]} | 口头禅 {v['interjections'][:3]}")
    if chapter_only:
        for s in r["chapter_summaries"]:
            if s["chapter"] == chapter_only:
                print(f"\n【第 {chapter_only} 章摘要】{s['title']}")
                for kp in s["key_points"]:
                    print(f"  · {kp[:50]}")
                if s["active_entities"]:
                    print(f"  活跃实体: {'、'.join(s['active_entities'])}")
    else:
        print("\n【全书章节摘要】")
        for s in r["chapter_summaries"]:
            pts = " / ".join(x[:18] for x in s["key_points"])
            print(f"  第{s['chapter']}章: {pts[:60]}")
    print(f"\n{r['disclaimer']}")


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    filepath = argv[0]
    as_json = "--json" in argv
    chapter_only = None
    if "--chapter" in argv:
        i = argv.index("--chapter")
        try:
            chapter_only = int(argv[i + 1]) if i + 1 < len(argv) else None
        except ValueError:
            chapter_only = None
    try:
        text = read_text(filepath)
    except Exception as e:
        print(f"❌ 读取失败: {filepath}（{e}）")
        return 1
    r = run_tracking(text)
    if as_json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        report(r, chapter_only)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
