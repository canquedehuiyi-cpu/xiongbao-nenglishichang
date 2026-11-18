#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""eval_mapper.py —— 评语命题化定位路由器（2026-11-11 v152，备案 112）

定位
----
把评测报告的评语（方向词散文）降维成原子命题，路由到既有门禁/走查，输出
「方向 → 文件＋行号」命中报告。**只做路由器：复用既有扫描器，不重写任何扫描逻辑。**

用法
----
    python scripts/eval_mapper.py <包目录> --comment <评语文件或"评语原文">
    python scripts/eval_mapper.py <包目录> --comment-file <评语.txt>
    python scripts/eval_mapper.py --self-test

五步流程（真源：自用层复盘册「评语命题化定位」节；本脚本内置路由表为机读真源）
    ① 评语原文落盘（禁止凭印象归类）
    ② 拆原子命题：一句一个可判断真伪的判断句
    ③ 三维分流：该认（结构使然，明写不改理由）/ 真问题
    ④ 路由执行：机检类跑对应扫描器；走查类出带行号的人工比对清单
    ⑤ 输出报告：零分数——只出「命题 → 位置 → 证据 → 修法方向 → 预期效果」

零分数纪律：本工具任何输出不含分数字段——分数评判机制不在我们手里，
报告只对命题与位置负责（出报告规范，备案 112）。
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys

# ============ 路由表（内置真源：方向词 → 命题类型 → 路由） ============
# route 形态：
#   ("scan", <脚本名>)            → 跑既有扫描器，汇总命中
#   ("multi", [<脚本名>, ...])    → 跑多个扫描器
#   ("manual", <走查说明>)        → 机器扫不出，出人工走查清单
# fix_hint：命中后的修法方向（一句，不写实现细节——细节以真源册为准）
DIRECTION_MAP = [
    {"words": ["不一致", "不完全一致", "不统一", "同文", "前后矛盾", "矛盾"],
     "type": "同文漂移（双源/多源措辞或数值不同）",
     "route": ("scan", "run_regression"),
     "fix_hint": "命中处按「唯一真源＋指针」收敛；改内容只改真源一处"},
    {"words": ["阈值", "数字", "数值", "口径不一"],
     "type": "数字/阈值漂移",
     "route": ("multi", ["threshold_scan", "numeric_consistency_scan"]),
     "fix_hint": "改数先改阈值总表对应行并走备案，再改产物"},
    {"words": ["缺失", "缺少", "没有", "未见"],
     "type": "机制/分支缺失",
     "route": ("scan", "run_regression"),
     "fix_hint": "先确认机制应落在状态机还是纪律区，再按既有同类机制补装"},
    {"words": ["格式", "口令", "混用"],
     "type": "口令/格式混用",
     "route": ("multi", ["interaction_closure_scan", "keyword_mapping_scan"]),
     "fix_hint": "口令引用双格式规矩：凭据【】加粗、叙述「」——只改字面不改机制"},
    {"words": ["兜底", "回落", "中断", "超时"],
     "type": "兜底/中断链缺口",
     "route": ("scan", "interaction_closure_scan"),
     "fix_hint": "按既有回落四类对号入座，禁止新造第二套恢复路"},
    {"words": ["冗长", "较多", "庞大", "体量", "阅读"],
     "type": "体量/初次难定位",
     "route": ("multi", ["threshold_scan", "visual_layer_scan"]),
     "fix_hint": "体量超限先改阈值总表对应行并走备案；结构优化走既有导航行机制"},
    {"words": ["重复", "复述"],
     "type": "跨册复述（C 维重复扣分机检落点）",
     "route": ("scan", "repeat_scan"),
     "fix_hint": "非豁免命中收敛为单点真源＋指针行；设计性同文对子已在扫描器豁免名单（新增对子须备案登记）"},
    {"words": ["描述", "listing", "上架", "名称"],
     "type": "描述/上架形态",
     "route": ("scan", "publish_form_scan"),
     "fix_hint": "按出包形态规范逐字段对齐，禁止手工逐处改名称族"},
    {"words": ["引导", "语气", "体验", "友好"],
     "type": "交互体验（机器扫不出）",
     "route": ("manual", "屏面逐屏走查：屏尾行动行唯一性＋三段式反馈＋语气档位，逐屏记行号"),
     "fix_hint": "对照视觉分层规矩逐屏比对，命中记行号后按既有屏面规范修"},
]

SELF_USE_NOTE = "（本工具为路由器；扫描逻辑真源在各既有扫描器，修法则以真源册为准）"


def split_sentences(text):
    """评语 → 原子命题（按句切，过滤过短句）。"""
    parts = re.split(r"[。！？！？;\n；]+", text)
    return [p.strip() for p in parts if len(p.strip()) >= 4]


def match_directions(sent):
    """一句命题 → 命中的路由条目列表（按方向词匹配）。"""
    hits = []
    for entry in DIRECTION_MAP:
        for w in entry["words"]:
            if w in sent:
                hits.append(entry)
                break
    return hits


def run_scanner(root, script):
    """跑既有扫描器（子进程），返回 (ok, 原始输出)。扫描器真源不改。
    script 允许省略 .py 扩展名（路由表写短名）。"""
    here = os.path.dirname(os.path.abspath(__file__))
    sp = os.path.join(here, script if script.endswith(".py") else script + ".py")
    if not os.path.exists(sp):
        return None, "%s 不存在（跳过，扫描器缺件）" % script
    try:
        r = subprocess.run([sys.executable, sp, root], capture_output=True,
                           text=True, timeout=300, encoding="utf-8", errors="replace")
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except Exception as e:  # noqa: BLE001
        return None, "执行异常: %s" % e


def extract_hits(script, output):
    """从扫描器输出提取命中明细。判定以 verdict/FAIL 行为准——PASS 输出零命中，
    禁止把 JSON 结构字段行（problems: [ 等）误计为命中（v153 实战修正）。"""
    is_fail = ('"verdict": "FAIL"' in output
               or re.search(r"(?m)^FAIL\b", output) is not None)
    if not is_fail:
        return []
    hits = []
    for line in output.split("\n"):
        s = line.strip()
        if not s:
            continue
        if s.startswith("FAIL") or s.startswith("- ") or s.startswith('{"tool"'):
            if '"problems": []' in s or '"verdict": "PASS"' in s:
                continue
            hits.append(s[:200])
    return hits[:12] or ["FAIL（明细见扫描器原始输出）"]


def map_comment(root, comment):
    """主流程：评语 → 命题分流 → 路由执行 → 报告 dict（零分数）。"""
    sents = split_sentences(comment)
    if not sents:
        return {"ok": False, "error": "评语为空或无有效命题句（fail-closed，禁止瞎跑）"}
    scan_cache = {}  # script → (rc, hits)；同一扫描器只跑一次，多个命题共享结果
    items = []
    manual_list = []
    unmatched = []
    for sent in sents:
        dirs = match_directions(sent)
        if not dirs:
            unmatched.append(sent)
            continue
        for d in dirs:
            kind, arg = d["route"]
            scripts = arg if kind == "multi" else [arg]
            if kind == "manual":
                manual_list.append({
                    "命题": sent[:60],
                    "命题类型": d["type"],
                    "走查方法": arg,
                    "修法方向": d["fix_hint"],
                })
            else:
                for script in scripts:
                    if script not in scan_cache:
                        rc, out = run_scanner(root, script)
                        scan_cache[script] = (rc, extract_hits(script, out) if rc is not None else [])
                    rc, hits = scan_cache[script]
                    items.append({
                        "命题": sent[:60],
                        "命题类型": d["type"],
                        "路由": script,
                        "扫描状态": "缺件跳过" if rc is None else ("PASS 无命中" if not hits else "FAIL %d 处" % len(hits)),
                        "命中位置": hits,
                        "修法方向": d["fix_hint"],
                    })
            if "manual_follow" in d and kind != "manual":
                manual_list.append({
                    "命题": sent[:60],
                    "命题类型": d["type"] + "·附加走查",
                    "走查方法": d["manual_follow"],
                    "修法方向": "命中后收敛为单点真源＋指针行",
                })
    if unmatched:
        manual_list.append({
            "命题": "；".join(u[:40] for u in unmatched[:5]),
            "命题类型": "未命中方向词（机器无路由）",
            "走查方法": "逐句人工比对全包（建议从主文档直达表与对应分册双向核对）",
            "修法方向": "人工定位后按真源册口径修",
        })
    return {"ok": True, "零分数纪律": "本报告不含任何分数，只对命题与位置负责",
            "命题总数": len(sents), "机检路由数": len(items),
            "机检结果": items, "人工走查清单": manual_list, "附注": SELF_USE_NOTE}


def self_test():
    """阳/阴用例：阳=方向词正确路由；阴=空评语 fail-closed。"""
    import tempfile
    r = tempfile.mkdtemp()
    # 阴：空评语
    res = map_comment(r, "")
    assert not res["ok"] and "fail-closed" in res["error"], "阴例未拦: %s" % res
    # 阳：方向词路由（不要求扫描器存在——缺件也应正确路由并标注跳过）
    res2 = map_comment(r, "部分规范重复，存在前后不完全一致；缺少强制中断机制。")
    assert res2["ok"], "阳例失败"
    types = " ".join(i["命题类型"] for i in res2["机检结果"]) + " ".join(i["命题类型"] for i in res2["人工走查清单"])
    assert "同文漂移" in types and "机制/分支缺失" in types and "跨册复述" in types, "路由缺口: %s" % types
    assert "分数" not in json.dumps(res2, ensure_ascii=False).replace("零分数纪律", "").replace("不含任何分数", ""), "报告泄漏分数字段"
    print(json.dumps({"ok": True, "self_test": "阳/阴 2 用例通过（路由正确＋空评语拦截＋零分数）",
                      "方向词条目": len(DIRECTION_MAP)}, ensure_ascii=False))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="评语命题化定位路由器（只路由，不重写扫描逻辑；输出零分数）")
    ap.add_argument("root", nargs="?", help="包目录")
    ap.add_argument("--comment", default=None, help="评语原文（或短文本）")
    ap.add_argument("--comment-file", dest="comment_file", default=None, help="评语文件路径")
    ap.add_argument("--self-test", dest="self_test", action="store_true")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    if not args.root or (not args.comment and not args.comment_file):
        ap.print_help()
        return 2
    comment = args.comment or ""
    if args.comment_file:
        if not os.path.exists(args.comment_file):
            print(json.dumps({"ok": False, "error": "评语文件不存在: %s" % args.comment_file}, ensure_ascii=False))
            return 2
        comment = io.open(args.comment_file, encoding="utf-8").read()
    res = map_comment(args.root, comment)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
