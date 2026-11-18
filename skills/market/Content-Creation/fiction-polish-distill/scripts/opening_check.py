#!/usr/bin/env python3
"""opening_check.py — 开篇引擎（E-3，1.0.6 新增）

平台专属开篇体检（对标各平台公开的开篇要求）:
    起点: 前 300 字须有冲突/悬念/目标，拒绝背景铺垫式开局
    番茄: 前 50 字须有钩子（对话/冲突/悬念/反常）
    晋江: 情感/人物 CP 感前置，避免流水账交代
通用: 前 3 章结构（每章结尾钩子）、人物/目标引入

用法:
    python3 opening_check.py <文件.md>                # 单文件开篇体检
    python3 opening_check.py <文件.md> --platform 起点  # 指定平台口径
    python3 opening_check.py <文件.md> --json          # JSON 输出

说明: 全部为确定性规则检测（启发式估算，非权威检测），结果仅供作者自查参考。
"""

import json
import re
import sys
from pathlib import Path

from common import VERSION  # 版本单一来源

# 钩子特征：对话/冲突/悬念/反常/行动
HOOK_PAT = re.compile(
    r"[\"“「『]|忽然|突然|竟然|居然|没想到|却|但|可是|究竟|到底|为什么|凭什么|"
    r"死|杀|逃|追|撞|跌|砸|冲|吼|惊|愣|僵|怕|怒|冰|血|泪|刀|剑|枪|毒|"
    r"\?|？|!|！")
CONFLICT_PAT = re.compile(r"杀|打|逃|追|闯|怒|仇|恨|斗|争|抢|夺|逼|挡|拦|破|陷|危|险|死|血")
SUSPENSE_PAT = re.compile(r"究竟|到底|为什么|凭什么|难道|秘密|真相|谜|未知|疑问|为何|怎么会")
GOAL_PAT = re.compile(r"要|必须|一定|得|目标|计划|打算|想|渴望|发誓|决定|承诺")
BACKGROUND_PAT = re.compile(r"众所周知|在当今|随着.*发展|从古至今|自古以来|话说|很久很久以前|这是一个|世界设定|背景介绍")
EMOTION_PAT = re.compile(r"心|情|爱|恨|怒|笑|泪|颤|紧|痛|喜|悲|酸")


def _chars(t):
    return re.sub(r"\s", "", t)


def _split_sents(text):
    return [s.strip() for s in re.split(r"(?<=[。！？；.!?])", text) if s.strip()]


def check_hook(text, limit, label):
    """前 limit 字钩子检测。"""
    head = _chars(text)[:limit]
    if not head:
        return {"pass": False, "detail": f"{label}：无有效文本"}
    hits = HOOK_PAT.findall(head)
    ok = len(hits) >= 1
    return {"pass": ok, "detail": f"{label}：前 {limit} 字钩子特征 {len(hits)} 处{'（建议以冲突/悬念/反常开局）' if not ok else ''}"}


def check_conflict(text, limit, label):
    """前 limit 字冲突/悬念检测。"""
    head = _chars(text)[:limit]
    conf = len(CONFLICT_PAT.findall(head))
    susp = len(SUSPENSE_PAT.findall(head))
    ok = conf >= 1 or susp >= 1
    return {"pass": ok,
            "detail": f"{label}：冲突 {conf} 处 / 悬念 {susp} 处{'（前300字宜出现冲突或悬念，避免纯背景铺垫）' if not ok else ''}"}


def check_goal(text, limit, label):
    """前 limit 字目标引入。"""
    head = _chars(text)[:limit]
    g = len(GOAL_PAT.findall(head))
    ok = g >= 1
    return {"pass": ok, "detail": f"{label}：目标/动机词 {g} 处{'（宜尽快引入人物目标或动机）' if not ok else ''}"}


def check_no_background(text, limit, label):
    """前 limit 字是否以背景铺垫开局（起点红线）。"""
    head = _chars(text)[:limit]
    b = len(BACKGROUND_PAT.findall(head))
    ok = b == 0
    return {"pass": ok, "detail": f"{label}：背景铺垫特征 {b} 处{'（建议以具体场景/事件切入，勿用世界观铺垫开头）' if not ok else ''}"}


def check_chapter_hooks(text):
    """前 3 章结构：按章节标记切分，检查每章结尾钩子。"""
    chaps = re.split(r"\n\s*(?:第[一二三四五六七八九十百\d]+章|Chapter\s+\d+)\s*\n", text)
    chaps = [c.strip() for c in chaps if c.strip()]
    if len(chaps) < 1:
        return {"pass": None, "detail": "未识别到章节标记，跳过前3章检查"}
    out = []
    for i, c in enumerate(chaps[:3], 1):
        tail = _split_sents(c[-200:])
        hook = False
        for s in tail[-2:]:
            if HOOK_PAT.search(s) or s.endswith(("?", "？")):
                hook = True
        out.append({"chapter": i, "hook": hook})
    all_hook = all(x["hook"] for x in out)
    return {"pass": all_hook,
            "detail": "前3章结尾钩子: " + ", ".join(f"第{x['chapter']}章{'有' if x['hook'] else '无'}" for x in out)}


def check_emotion_front(text, platform):
    """晋江口径：情感/人物 CP 感前置。"""
    head = _chars(text)[:300]
    e = len(EMOTION_PAT.findall(head))
    ok = e >= 2
    return {"pass": ok, "detail": f"晋江：前300字情感/人物标记 {e} 处{'（晋江宜情感前置，尽快建立人物关系/情绪张力）' if not ok else ''}"}


PLATFORM_CHECKS = {
    "起点": [
        lambda t: check_hook(t, 300, "起点"),
        lambda t: check_conflict(t, 300, "起点"),
        lambda t: check_goal(t, 300, "起点"),
        lambda t: check_no_background(t, 300, "起点"),
    ],
    "番茄": [
        lambda t: check_hook(t, 50, "番茄"),
        lambda t: check_conflict(t, 50, "番茄"),
    ],
    "晋江": [
        lambda t: check_emotion_front(t, "晋江"),
        lambda t: check_hook(t, 300, "晋江"),
    ],
}


def run_opening_check(text, platform=None):
    if platform and platform in PLATFORM_CHECKS:
        checks = PLATFORM_CHECKS[platform]
        label = platform
    else:
        checks = PLATFORM_CHECKS["起点"]
        label = "起点（默认口径）"
    results = [c(text) for c in checks]
    results.append(check_chapter_hooks(text))
    return {"platform": label, "checks": results}


def report(data, as_json=False):
    if as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    print(f"📌 开篇体检（{data['platform']}口径）— 启发式估算，非权威检测")
    for c in data["checks"]:
        if "detail" in c:
            m = "✅" if c["pass"] else ("➖" if c["pass"] is None else "❌")
            print(f"  {m} {c['detail']}")
    fails = sum(1 for c in data["checks"] if c.get("pass") is False)
    print(f"\n结论: {'✅ 开篇达标' if fails == 0 else f'⚠ {fails} 项待优化'}")
    print("⚖️ 合规提示: 本报告为启发式自查参考，不承诺通过任何平台检测；发布前请按《人工智能生成合成内容标识办法》主动声明 AI 辅助创作。")


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    args = list(argv)
    as_json = "--json" in args
    platform = None
    if "--platform" in args:
        i = args.index("--platform")
        if i + 1 < len(args):
            platform = args[i + 1]
        # 同时移除 "--platform" 与它的取值，避免平台名被误当作文件路径
        args = [a for j, a in enumerate(args) if a != "--platform" and not (j == i + 1)]
    paths = [a for a in args if not a.startswith("--") and a not in ("--json",)]
    if not paths:
        print("请指定文本文件")
        return 1
    text = Path(paths[0]).read_text(encoding="utf-8-sig")
    data = run_opening_check(text, platform)
    data["version"] = VERSION
    report(data, as_json)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
