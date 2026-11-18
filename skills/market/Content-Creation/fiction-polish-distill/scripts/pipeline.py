#!/usr/bin/env python3
"""pipeline.py — 统一创作工作流（1.0.6 新增：W-1 + E-6 章节级检测；1.0.7 接入 P/Q/R 引擎）

一条命令跑通"安全过滤 → 质量检测 → 深度维度 → 叙事 → 开篇 → 去味 → 合规 → 原创自查
→ AI痕迹六层扫描 → 情绪曲线 → 实体追踪"，并支持按章节拆分做章节级/全书级聚合报告（E-6）。

用法:
    python3 pipeline.py <文件.md>                         # 单文本全流程
    python3 pipeline.py <文件.md> --platform 晋江          # 指定合规体检平台
    python3 pipeline.py <文件.md> --mode 标准             # 三档去味模式
    python3 pipeline.py <文件.md> --json                  # JSON 输出
    python3 pipeline.py <文件.md> --chapters              # 章节级聚合报告

说明: 通过调用各模块 CLI 聚合（各模块为权威实现，避免重复逻辑）；
      各模块输出均标注"估算/非权威检测"，本流程不承诺通过任何平台检测。
"""

import json
import re
import subprocess
import sys
from pathlib import Path

from common import VERSION  # 版本单一来源

SCRIPTS = Path(__file__).resolve().parent
PY = sys.executable


def _run_script(name, *args):
    """调用 scripts 目录下脚本，返回 (returncode, parsed_json_or_None)。"""
    cmd = [PY, str(SCRIPTS / name), *args]
    try:
        r = subprocess.run(cmd, capture_output=True, encoding="utf-8", timeout=300)
        try:
            data = json.loads(r.stdout)
        except json.JSONDecodeError:
            data = None
        return r.returncode, data, r.stdout[:200]
    except Exception as e:
        return -1, None, str(e)


def _split_chapters(text):
    m = re.split(r"(?:\n\s*|^)(?:第[一二三四五六七八九十百\d]+章[^\n]*|Chapter\s+\d+[^\n]*)(?:\n|$)", text)
    return [c.strip() for c in m if c.strip()]


def run_pipeline(text, platform="起点", mode="标准", chapters=False):
    """统一流水线：调用各模块聚合。"""
    lang = "zh"
    try:
        sys.path.insert(0, str(SCRIPTS))
        from quality_check import detect_language
        lang = detect_language(text)
    except Exception:
        pass

    # 1. 安全过滤 + 2. 质量检测（quality_check 一次执行内含安全前置过滤）
    tmp = SCRIPTS / "_pipeline_tmp.md"
    tmp.write_text(text, encoding="utf-8")
    rc, quality, qerr = _run_script("quality_check.py", str(tmp), "--json")
    result = {"version": VERSION, "lang": lang, "platform": platform, "mode": mode}

    # 红线拦截：质量检测返回 blocked 时终止流水线，不进入后续创作模块
    if isinstance(quality, dict) and quality.get("status") == "blocked":
        result["quality"] = quality
        result["blocked"] = True
        result["blocked_reason"] = "内容安全未通过（红线拦截），已终止流水线"
        tmp.unlink(missing_ok=True)
        return result
    result["quality"] = quality

    # 4. 叙事检测（E-2）
    rc, narrative, nerr = _run_script("narrative_check.py", str(tmp), "--json")
    result["narrative"] = narrative

    # 5. 开篇体检（E-3）
    rc, opening, oerr = _run_script("opening_check.py", str(tmp), "--platform", platform, "--json")
    result["opening"] = opening

    # 6. 去味闭环（三档模式）
    mode_en = {"保守": "conservative", "标准": "standard", "深度": "deep"}.get(mode, "standard")
    rc, deai, derr = _run_script("deai_loop.py", str(tmp), "--mode", mode_en, "--json")
    result["deai"] = deai

    # 7. 合规体检（CP-2）
    rc, comp, cerr = _run_script("compliance_engine.py", "platform", str(tmp), "--platform", platform)
    result["compliance"] = comp

    # 8. 原创自查（OR-2）
    rc, orig, orr = _run_script("originality_check.py", "self", str(tmp))
    result["originality"] = orig

    # 9. AI痕迹六层扫描（R，1.0.7）
    rc, sixl, serr = _run_script("six_layer_scan.py", str(tmp), "--json")
    result["six_layer"] = sixl

    # 10. 情绪曲线（Q，1.0.7）
    rc, emo, eerr = _run_script("emotion_curve.py", str(tmp), "--json")
    result["emotion_curve"] = emo

    # 11. 实体状态机（P，1.0.7，整本级洞察）
    rc, ent, eerr2 = _run_script("entity_tracking.py", str(tmp), "--json")
    result["entity_tracking"] = ent

    # 12. E-6 章节级聚合
    if chapters:
        chaps = _split_chapters(text)
        per_chap = []
        for i, c in enumerate(chaps, 1):
            ctmp = SCRIPTS / f"_pipeline_chap{i}.md"
            ctmp.write_text(c, encoding="utf-8")
            rc, cq, _ = _run_script("quality_check.py", str(ctmp), "--json")
            # 统一信封：score 为 {value, threshold, pass, anti_ai_score} 或 None
            score_obj = (cq or {}).get("score") if isinstance(cq, dict) else None
            score_val = score_obj.get("value") if isinstance(score_obj, dict) else score_obj
            anti = score_obj.get("anti_ai_score") if isinstance(score_obj, dict) else None
            per_chap.append({"chapter": i, "score": score_val, "anti_ai": anti,
                             "chars": len(c.replace("\n", ""))})
            ctmp.unlink(missing_ok=True)
        result["chapters"] = per_chap
        if per_chap:
            scores = [c["score"] for c in per_chap if c["score"] is not None]
            result["chapters_summary"] = {
                "chapter_count": len(per_chap),
                "avg_score": round(sum(scores) / len(scores), 1) if scores else None,
                "weakest_chapter": min(per_chap, key=lambda c: c["score"] if c["score"] is not None else 999) if per_chap else None,
            }

    tmp.unlink(missing_ok=True)
    return result


def report(result, as_json=False):
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print(f"══ 统一创作工作流报告 v{result['version']} ══")
    print(f"语言: {result['lang']} | 合规平台口径: {result['platform']} | 去味模式: {result['mode']}")
    if result.get("blocked"):
        print(f"\n⛔ {result.get('blocked_reason', '内容安全未通过，流水线已终止')}")
        print("请先移除违规内容，再重新运行。")
        return
    q = result.get("quality") or {}
    print(f"\n[质量检测] status={q.get('status')} 综合通过率={q.get('score', {}).get('value') if isinstance(q.get('score'), dict) else q.get('score')}")
    d = result.get("deai") or {}
    if d.get("final"):
        print(f"[去味闭环] 实际轮数={d.get('rounds_used')} 人工质感评分: {d.get('rounds', [{}])[0].get('scores', {}).get('anti_ai_score')} → {d.get('final', {}).get('anti_ai_score')}")
    o = result.get("opening") or {}
    if o.get("checks"):
        fails = sum(1 for c in o["checks"] if c.get("pass") is False)
        print(f"[开篇体检] {o.get('platform')} 口径: {fails} 项待优化")
    c = result.get("compliance") or {}
    if c.get("summary"):
        risks = c["summary"].get("risk_matrix", [])
        lvl = "、".join(r["level"] for r in risks)
        print(f"[合规体检] {c['summary'].get('platform')}: 风险等级 {lvl}")
    n = result.get("narrative") or {}
    print(f"[叙事检测] 维度: {len(n) if isinstance(n, dict) else 0}")
    sl = result.get("six_layer") or {}
    if sl.get("layers"):
        print(f"[AI痕迹六层扫描] 综合 {sl.get('overall_score')}/100 | 结论: {sl.get('conclusion')}")
    ec = result.get("emotion_curve") or {}
    if ec.get("curve"):
        print(f"[情绪曲线] {ec.get('para_count')} 段 | 平缓区 {len(ec.get('flat_zones', []))} 处 | 峰值 {len(ec.get('peaks', []))} 处 | 人味质量 {ec.get('human_touch', {}).get('quality_score')}/100")
    et = result.get("entity_tracking") or {}
    if et.get("entities_count") is not None:
        print(f"[实体追踪] 实体 {et.get('entities_count')} | 状态冲突 {len(et.get('conflicts', []))} | 未回收伏笔 {len(et.get('unpaid_foreshadows', []))} | 声线档案 {len(et.get('voices', {}))}")
    if result.get("chapters"):
        s = result["chapters_summary"]
        print(f"[章节级] {s['chapter_count']} 章 | 均分 {s['avg_score']} | 最弱章: 第{s['weakest_chapter']['chapter']}章 ({s['weakest_chapter']['score']})")
    print("\n说明: 各模块输出为启发式估算/自查参考，不承诺通过任何平台检测；")
    print("发布前请按《人工智能生成合成内容标识办法》主动声明 AI 辅助。")


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    as_json = "--json" in argv
    chapters = "--chapters" in argv
    platform = "起点"
    mode = "标准"
    # 解析参数：--platform/--mode 与其取值从位置参数中剔除，避免取值被误当文件路径
    positional = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--platform" and i + 1 < len(argv):
            platform = argv[i + 1]
            i += 2
            continue
        if a == "--mode" and i + 1 < len(argv):
            mode = argv[i + 1]
            i += 2
            continue
        i += 1
        if a.startswith("--"):
            continue
        positional.append(a)
    paths = positional
    if not paths:
        print("请指定文本文件")
        return 1
    text = Path(paths[0]).read_text(encoding="utf-8-sig")
    result = run_pipeline(text, platform, mode, chapters)
    report(result, as_json)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
