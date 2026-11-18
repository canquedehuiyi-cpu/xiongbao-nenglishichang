#!/usr/bin/env python3
"""compliance_engine.py — 合规引擎（1.0.6 新增：CP-1~CP-5）

直击 2026 监管与平台 AI 治理要求，帮助作者"证明人类主导 + 满足标识义务"：
    manifest   <处理记录.json>            生成《AI辅助使用申报清单》（CP-1）
    platform   <文本.md> --platform <平台> 平台合规体检（允许级别/越界预警/时效溯源）（CP-2）
                                           可选 --live 强制联网核实最新政策并并入结果（O-4）
    ratio      <原稿.md> <改稿.md>        人工改写比例 / 人类主导度（CP-3）
    trail      <原稿.md> <改稿.md> [--out] 创作留痕（CP-4）
    label      [--platform <平台>]        标识提醒（CP-5）

平台: 起点 / 番茄 / 晋江（口径见 references/antiai_blacklist.json 的 platform_policies；
实时动态请运行 scripts/platform_policy_check.py 联网核实）

说明:
    1. 本引擎不提供去除标识/规避检测手段，仅做"质量优化 + 主动声明"。
    2. ratio 只能算"改写比例"，无法判定"是否真人改写"，平台以人工复核为准。
    3. 全部为确定性本地计算（零外部依赖），结果供作者自查参考。
"""

import json
import re
import sys
from pathlib import Path

from common import VERSION, read_text  # 版本单一来源 + BOM 安全读取

PLATFORM_ALLOWED = {
    "起点": {"allowed": ["灵感设定", "大纲搭建", "校对润色", "排版优化"],
            "red_lines": ["AI 占比 >10% 触发处理", "AI 生成内容须人工改写 >30%", "核心剧情/人设/爽点必须人类原创"]},
    "番茄": {"allowed": ["30% 以上人工加工", "核心剧情/人物由人工完成"],
            "red_lines": ["AI 粗制滥造", "语句重复", "逻辑断裂", "对话僵硬", "无有效剧情", "空洞水文"]},
    "晋江": {"allowed": ["文字型·校对级", "创意型·要素级", "创意型·粗纲级"],
            "red_lines": ["文字型·描写级", "文字型·叙事级", "创意型·细纲级", "代写正文"]},
}


def _overlap_ratio(a, b):
    """字符级重合度（0-1），用于人工改写比例估算。"""
    if not a or not b:
        return 1.0
    # 以改稿字符为单位，统计与原稿相同的连续片段占比
    b_clean = re.sub(r"\s", "", b)
    a_clean = re.sub(r"\s", "", a)
    if not b_clean:
        return 0.0
    keep = 0
    i = 0
    n = len(b_clean)
    while i < n:
        # 找最长的原稿子串匹配
        best = 0
        for ln in range(min(12, n - i), 0, -1):
            if b_clean[i:i + ln] in a_clean:
                best = ln
                break
        keep += best
        i += max(1, best)
    return keep / n


# ---------- CP-1 申报清单 ----------

def manifest(record):
    """根据处理记录生成《AI辅助使用申报清单》。"""
    if not isinstance(record, dict):
        return {"status": "skip", "reason": "处理记录无效"}
    modules = record.get("modules", []) if isinstance(record.get("modules"), list) else []
    texts = record.get("text_scope", "单段/章节")
    has_direct_out = bool(record.get("direct_prose", False))
    # 平台允许级别勾选（默认以各平台允许的"校对/润色/要素级"为参照）
    checks = []
    for m in modules:
        if m in ("deai", "去味", "quality", "质检"):
            checks.append({"module": m, "level": "校对级（文字润色）", "platform_ok": "起点✅/番茄✅/晋江✅"})
        elif m in ("polish", "润色"):
            checks.append({"module": m, "level": "校对级（文字润色）", "platform_ok": "起点✅/番茄✅/晋江✅"})
        elif m in ("imitate", "仿写", "continue", "续写"):
            checks.append({"module": m, "level": "创意型（方向建议）", "platform_ok": "起点✅/番茄✅/晋江: 细纲级禁止，建议仅用方向建议"})
        else:
            checks.append({"module": m, "level": "其他", "platform_ok": "请按平台规则自查"})
    if has_direct_out:
        checks.append({"module": "正文直出", "level": "超出校对级", "platform_ok": "⚠ 起点/番茄须人工改写>30%；晋江禁止叙事级/描写级直出"})
    return {
        "status": "ok",
        "version": VERSION,
        "title": "《AI辅助使用申报清单》",
        "text_scope": texts,
        "modules_declared": checks,
        "human_claim": "本人确认：以上 AI 辅助仅为校对/润色/创意方向参考，核心剧情、人物、爽点均为本人原创，成稿经本人人工主导完成。",
        "signature_line": "作者签名：__________  日期：__________",
        "note": "本清单供作者主动申报与申诉留档；平台最终以人工复核为准。",
    }


def load_platform_policies():
    """读取内置平台规范快照（含 O-2 溯源字段 verified_date/source_url）。"""
    base = Path(__file__).resolve().parent.parent
    path = base / "references" / "antiai_blacklist.json"
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        return d.get("platform_policies", {})
    except Exception:
        return {}


# ---------- CP-2 平台合规体检 ----------

def platform_check(text, platform, live=False):
    if platform not in PLATFORM_ALLOWED:
        return {"status": "skip", "reason": f"暂不支持平台: {platform}（支持: 起点/番茄/晋江）"}
    policy = PLATFORM_ALLOWED[platform]
    risks = []
    # 违规特征扫描（各平台红线词）
    red_pat = {
        "起点": r"AI占比|自动生成|代笔|托管|洗稿|抄袭",
        "番茄": r"AI粗制滥造|语句重复|逻辑断裂|对话僵硬|空洞水文|无有效剧情|格式混乱",
        "晋江": r"代写|AI直出|叙事级|描写级|细纲级",
    }[platform]
    hits = re.findall(red_pat, text)
    if hits:
        risks.append({"level": "红牌", "item": f"检测到平台红线特征词: {list(set(hits))[:5]}", "action": "删除相关表述，确保人工主导"})
    # 结构规整度（对标番茄"逻辑过于工整"）
    sents = [s.strip() for s in re.split(r"(?<=[。！？；.!?])", text) if s.strip()]
    if len(sents) >= 6:
        lens = [len(s) for s in sents]
        mid = sum(1 for l in lens if 8 <= l <= 30) / len(lens) * 100
        if mid > 85:
            risks.append({"level": "黄灯", "item": "句式过于规整（中句占比过高），平台可能判定结构工整度过高", "action": "建议长短句交错，增加句式变化"})
    allowed = policy["allowed"]
    summary = {
        "platform": platform,
        "allowed_levels": allowed,
        "risk_matrix": risks if risks else [{"level": "绿", "item": "未检出明显红线特征", "action": "可继续按平台规则创作"}],
        "declare_scope": f"建议主动声明: 使用了校对/润色/创意方向类 AI 辅助（属于{platform}允许范围）",
        "label_reminder": "发布时按《人工智能生成合成内容标识办法》在显著位置主动标识 AI 辅助，不缩小/隐藏/删除。",
        "note": "本体检为本地启发式自查，非权威检测；请以平台官方规则与人工复核为准（可运行 platform_policy_check.py 联网核实最新政策）。",
    }
    # O-2 数据溯源：内置快照的核实日期与来源 URL
    pp = load_platform_policies()
    pl = pp.get("platforms", {}).get(platform, {})
    if pl.get("verified_date"):
        summary["verified_date"] = pl["verified_date"]
    if pl.get("source_url"):
        summary["source_url"] = pl["source_url"]
    # O-4 实时联网核实：--live 时调用 platform_policy_check 强制刷新并并入结果
    if live:
        live_info = _live_policy(platform)
        if live_info:
            summary["live_verified"] = live_info
            summary["note"] += "（已启用 --live 联网核实，实时结果见 live_verified）"
    return {"status": "ok", "summary": summary}


def _live_policy(platform):
    """调用 platform_policy_check.py 联网核实指定平台，返回精简实时信息（失败返回 None）。"""
    src_id_map = {"起点": "qidian", "番茄": "fanqie", "晋江": "jinjiang"}
    src_id = src_id_map.get(platform)
    if not src_id:
        return None
    try:
        script = Path(__file__).resolve().parent / "platform_policy_check.py"
        import subprocess
        p = subprocess.run([sys.executable, str(script), "--platform", src_id, "--refresh", "--json"],
                           capture_output=True, encoding="utf-8", timeout=60)
        data = json.loads(p.stdout)
        if isinstance(data, list) and data:
            r = data[0]
            return {
                "platform": r.get("platform"),
                "status": r.get("status"),
                "url": r.get("url"),
                "fetched_at": r.get("fetched_at"),
                "points": r.get("points", []),
                "error": r.get("error", ""),
                "found_by_search": r.get("found_by_search", False),
            }
    except Exception:
        return None
    return None


# ---------- CP-3 人工改写比例 ----------

def rewrite_ratio(orig, new):
    """人工改写比例 / 人类主导度估算（只能算"改写比例"，不能算"是否真人改写"）。"""
    keep = _overlap_ratio(orig, new)
    rewrite = 1.0 - keep
    ratio_pct = round(rewrite * 100, 1)
    # 对标起点/番茄 "30% 人工改写" 门槛
    meet_30 = ratio_pct >= 30
    return {
        "status": "ok",
        "version": VERSION,
        "overlap_ratio": round(keep * 100, 1),
        "human_rewrite_ratio": ratio_pct,
        "meets_30pct_guideline": meet_30,
        "conclusion": ("改写比例达到平台常见的 30% 人工加工参考线"
                       if meet_30
                       else "改写比例未达 30% 参考线，建议进一步人工改写核心句后再提交"),
        "disclaimer": "该指标为作者自查参考（仅衡量文本差异度），不能证明'是否真人改写'，平台以人工复核为准。",
    }


# ---------- CP-4 创作留痕 ----------

def trail(orig, new, extra=None):
    """创作留痕：原稿 + 改稿 + 差异摘要 + 时间戳，供申诉/留档。"""
    keep = _overlap_ratio(orig, new)
    diff = round((1.0 - keep) * 100, 1)
    import datetime
    record = {
        "version": VERSION,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "original_char_count": len(re.sub(r"\s", "", orig)),
        "rewritten_char_count": len(re.sub(r"\s", "", new)),
        "rewrite_ratio": diff,
        "modules_used": extra or [],
        "note": "留痕供作者保存创作过程证据；被误判/被举报时可作为申诉材料（配合申报清单使用）。",
    }
    return {"status": "ok", "trail": record}


# ---------- CP-5 标识提醒 ----------

def label_reminder(platform=None):
    txt = [
        "【标识提醒 · 《人工智能生成合成内容标识办法》】",
        "1. 自 2025-09-01 起，AI 生成合成内容须同时带显式标识与隐式标识，未标识可依法处罚。",
        "2. 显式标识应置于内容起始等显著位置，禁止缩小、隐藏或发布后删除。",
        "3. 网文平台另有各自标识与申报要求（如起点主动申报、晋江申诉需原稿与AI对话记录）。",
        "4. 请勿使用任何去除标识/规避检测的工具或教程（中央网信办'清朗'专项行动重点打击）。",
    ]
    if platform and platform in PLATFORM_ALLOWED:
        txt.append(f"5. [{platform}] 允许范围: {'、'.join(PLATFORM_ALLOWED[platform]['allowed'])}；红线: {'；'.join(PLATFORM_ALLOWED[platform]['red_lines'])}")
    return {"status": "ok", "reminder": "\n".join(txt)}


# ---------- CLI ----------

def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd = argv[0]
    platform = None
    live = False
    out_path = None
    # 解析参数：--platform/--out/--live 与其取值从位置参数中剔除，避免取值被误当文件路径
    positional = []
    i = 1
    while i < len(argv):
        a = argv[i]
        if a == "--platform" and i + 1 < len(argv):
            platform = argv[i + 1]
            i += 2
            continue
        if a == "--out" and i + 1 < len(argv):
            out_path = argv[i + 1]
            i += 2
            continue
        if a == "--live":
            live = True
            i += 1
            continue
        if a.startswith("--"):
            i += 1
            continue
        positional.append(a)
        i += 1
    args = positional

    if cmd == "manifest":
        if not args:
            print("请提供处理记录 JSON 文件")
            return 1
        try:
            rec = json.loads(Path(args[0]).read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"❌ 处理记录读取失败: {args[0]}（{e}）")
            return 1
        print(json.dumps(manifest(rec), ensure_ascii=False, indent=2))
        return 0
    if cmd == "platform":
        if not args:
            print("请提供文本文件")
            return 1
        text = read_text(args[0])
        print(json.dumps(platform_check(text, platform or "起点", live=live), ensure_ascii=False, indent=2))
        return 0
    if cmd == "ratio":
        if len(args) < 2:
            print("用法: ratio <原稿.md> <改稿.md>")
            return 1
        print(json.dumps(rewrite_ratio(read_text(args[0]), read_text(args[1])), ensure_ascii=False, indent=2))
        return 0
    if cmd == "trail":
        if len(args) < 2:
            print("用法: trail <原稿.md> <改稿.md> [--out <json>]")
            return 1
        data = trail(read_text(args[0]), read_text(args[1]))
        if out_path:
            Path(out_path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            print("已保存留痕:", out_path)
        else:
            print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0
    if cmd == "label":
        print(json.dumps(label_reminder(platform), ensure_ascii=False, indent=2))
        return 0
    print(f"未知命令: {cmd}（可用: manifest/platform/ratio/trail/label）")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
