#!/usr/bin/env python3
"""red_blue_review.py — 红蓝对抗审稿室（1.0.7 新增：S-1~S-4）

聚合实体状态机（M1）、情绪曲线（M2）、六层扫描（M3）的检测结果，
用"红队挑刺 × 蓝队辩护 → 裁定清单"的方式输出结构化的审稿报告：

    S-1 红队（挑刺）：实体矛盾/时间回拨/平缓区/高 AI 痕迹层/语义重复/对话僵硬
    S-2 蓝队（辩护）：情绪峰值/具象表达/低 AI 痕迹层/伏笔埋点
    S-3 裁定：按严重度给出"优先修复"清单 + "建议保留"亮点
    S-4 诚实定位：所有判据为本地启发式，非真人评审

用法:
    python3 red_blue_review.py <书.md>          # 红蓝审稿报告
    python3 red_blue_review.py <书.md> --json   # JSON 输出
    python3 red_blue_review.py <书.md> --focus 叙事   # 仅输出某类问题

说明:
    本工具是聚合审稿台，红蓝判据全部来自本地启发式引擎（非权威）；
    裁定的"优先级"仅供作者参考，不替代真人编辑与平台判定。
"""

import json
import sys

from common import VERSION, read_text
from entity_tracking import run_tracking
from emotion_curve import run_curve
from six_layer_scan import run_scan


def run_review(text):
    """S-1~S-3 聚合审稿主入口。"""
    et = run_tracking(text)
    ec = run_curve(text)
    sl = run_scan(text)

    # ---- 红队：挑刺 ----
    red = []
    for c in et.get("conflicts", []):
        red.append({"severity": "高", "kind": c.get("type", "状态矛盾"),
                    "item": c.get("item", ""), "action": c.get("action", ""),
                    "source": "entity_tracking"})
    for c in et.get("time_conflicts", []):
        red.append({"severity": "高", "kind": "时间线矛盾",
                    "item": c.get("item", ""), "action": c.get("action", ""),
                    "source": "entity_tracking"})
    for z in ec.get("flat_zones", []):
        red.append({"severity": "中", "kind": "情绪平缓区",
                    "item": f"第 {z['start']}~{z['end']} 段连续情绪平缓（{z['len']} 段）",
                    "action": "建议加入冲突/反转/情绪转折点", "source": "emotion_curve"})
    for L in sl.get("layers", []):
        if L["score"] > 50:
            red.append({"severity": "中", "kind": f"AI痕迹-{L['layer']}",
                        "item": f"{L['desc']} 得分 {L['score']}/100"
                                + (f"（命中: {'、'.join(str(e) for e in L['examples'][:3])}）" if L["examples"] else ""),
                        "action": "按该层示例逐处改写", "source": "six_layer_scan"})
    # 语义重复（车轱辘话）单独列为低-中
    for L in sl.get("layers", []):
        if L["layer"] == "语义层" and L["score"] > 30 and L["score"] <= 50:
            red.append({"severity": "低", "kind": "语义重复",
                        "item": f"{L['desc']} 得分 {L['score']}/100",
                        "action": "删减重复表述，提升信息增量", "source": "six_layer_scan"})

    # ---- 蓝队：辩护/亮点 ----
    blue = []
    for p in ec.get("peaks", []):
        blue.append({"kind": "情绪峰值(爽点)", "item": f"第 {p['para']} 段情绪峰值 {p['strength']:+.1f}",
                     "note": "保持该段张力"})
    t = ec.get("human_touch", {})
    if t.get("quality_score", 0) >= 60:
        blue.append({"kind": "人味具象表达", "item": f"具象表达质量 {t['quality_score']}/100",
                     "note": "让读者感受的表达方式，值得保持"})
    for f in et.get("foreshadows", [])[:3]:
        if f.get("paid"):
            blue.append({"kind": "伏笔已回收", "item": f"第{f['chapter']}章伏笔后文回收",
                         "note": "前后呼应，结构完整"})
    if not blue:
        blue.append({"kind": "基础结构", "item": "未检出明显亮点（可能文本过短或偏平淡）",
                     "note": "建议补充冲突与具体细节"})

    # ---- 裁定：优先级排序 ----
    pri_order = {"高": 0, "中": 1, "低": 2}
    red.sort(key=lambda x: pri_order.get(x["severity"], 3))
    high = [r for r in red if r["severity"] == "高"]
    verdict = ("需优先修复高优先级问题" if high else
               ("整体无明显硬伤，可进入打磨阶段" if len(red) <= 2 else "存在若干中低优先级问题，建议逐项处理"))

    return {
        "version": VERSION,
        "status": "ok",
        "red_team": red,
        "blue_team": blue,
        "verdict": verdict,
        "summary": {
            "red_count": len(red),
            "high_count": len(high),
            "blue_count": len(blue),
        },
        "disclaimer": "红蓝判据全部来自本地启发式引擎（非权威）；裁定优先级仅供作者参考，不替代真人编辑与平台判定。",
    }


def report(r, focus=None):
    print(f"══ 红蓝对抗审稿室报告 v{r['version']} ══")
    s = r["summary"]
    print(f"红队挑刺 {s['red_count']} 项（高优先级 {s['high_count']} 项） | 蓝队亮点 {s['blue_count']} 项")
    print(f"裁定: {r['verdict']}")
    if not focus or focus in ("红", "red", "叙事", "问题"):
        print("\n【红队 · 挑刺】")
        if not r["red_team"]:
            print("  （无检出问题）")
        for item in r["red_team"]:
            print(f"  [{item['severity']}] {item['kind']}: {item['item']}")
            print(f"       → {item['action']}")
    if not focus or focus in ("蓝", "blue", "亮点"):
        print("\n【蓝队 · 辩护/亮点】")
        for item in r["blue_team"]:
            print(f"  · {item['kind']}: {item['item']}（{item['note']}）")
    print(f"\n{r['disclaimer']}")


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    filepath = argv[0]
    as_json = "--json" in argv
    focus = None
    if "--focus" in argv:
        i = argv.index("--focus")
        if i + 1 < len(argv):
            focus = argv[i + 1]
    try:
        text = read_text(filepath)
    except Exception as e:
        print(f"❌ 读取失败: {filepath}（{e}）")
        return 1
    r = run_review(text)
    if as_json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        report(r, focus)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
