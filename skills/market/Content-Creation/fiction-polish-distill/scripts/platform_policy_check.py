#!/usr/bin/env python3
"""platform_policy_check.py — 平台 AI 创作规范联网核实工具

联网实时核实各大小说平台与监管机构对 AI 辅助创作的最新规范，
作为技能处理时的真实依据（不依赖任何第三方库，仅标准库）。

用法:
    python3 platform_policy_check.py                    # 核实全部来源
    python3 platform_policy_check.py --platform jinjiang # 仅核实指定来源
    python3 platform_policy_check.py --refresh           # 强制刷新缓存（默认 24 小时有效）
    python3 platform_policy_check.py --json              # JSON 格式输出

来源说明:
    全部来源均为官方或权威公开页面（监管机构官网/平台官方公告/权威媒体转载），
    抓取结果如实输出；任一来源不可达时如实标记"未获取到最新信息，请人工核实"，
    绝不编造政策内容。

零外部依赖声明: 本脚本仅使用 Python 标准库（urllib/json/re/tempfile/os）。
"""

import json
import os
import re
import sys
import tempfile
import urllib.request
from datetime import datetime, timedelta

CACHE_TTL_HOURS = 24

# 官方/权威来源清单（平台、标识、来源名称、URL、政策关键词提取规则、检索降级）
# fallback_domains: 官方域名列表，用于固定 URL 失效时的站内检索降级
# fallback_query:   检索关键词（含平台名，用于定位最新官方公告）
SOURCES = [
    {
        "id": "jinjiang",
        "platform": "晋江文学城",
        "builtin_name": "晋江",
        "name": "《关于AI辅助写作使用、判定的试行公告》（官方公告，权威媒体全文转载）",
        "url": "https://news.qq.com/rain/a/20250218A07F5700",
        "keywords": ["校对", "要素", "粗纲", "锁章", "禁榜", "举报", "原创性", "60%"],
        "title_pattern": r"AI辅助写作",
        "fallback_domains": ["jjwxc.net"],
        "fallback_query": "晋江文学城 AI辅助写作 使用 判定 公告",
    },
    {
        "id": "qidian",
        "platform": "起点中文网",
        "builtin_name": "起点",
        "name": "《关于进一步加强对非真人自动化创作管理力度的公告》及持续治理报道",
        "url": "https://m.jiemian.com/article/14946731.html",
        "keywords": ["非真人", "自动化", "暂停推荐", "撤下榜单", "屏蔽", "下架", "公示", "检测"],
        "title_pattern": r"AI",
        "fallback_domains": ["qidian.com", "yuewen.com"],
        "fallback_query": "起点中文网 非真人 自动化创作 管理 公告",
    },
    {
        "id": "fanqie",
        "platform": "番茄小说",
        "builtin_name": "番茄",
        "name": "AI 稿件收紧签约审查标准（2025-04 公告，权威媒体综述）",
        "url": "https://m.thepaper.cn/newsDetail_forward_31989458",
        "keywords": ["情节叙事不清", "结构混乱", "转折生硬", "逻辑割裂", "签约审查"],
        "title_pattern": r"AI",
        "fallback_domains": ["fanqienovel.com"],
        "fallback_query": "番茄小说 AI 稿件 签约审查 标准",
    },
    {
        "id": "cac",
        "platform": "国家网信办",
        "builtin_name": "网信办",
        "name": "《人工智能生成合成内容标识办法》（官方法规）",
        "url": "https://www.gov.cn/zhengce/202503/content_7014404.htm",
        "keywords": ["显式标识", "隐式标识", "元数据", "生成合成内容", "疑似"],
        "title_pattern": r"标识",
        "fallback_domains": ["cac.gov.cn", "gov.cn"],
        "fallback_query": "人工智能生成合成内容标识办法",
    },
    {
        "id": "industry",
        "platform": "网络文学行业",
        "builtin_name": "行业公约",
        "name": "16家平台《网络文学行业反洗稿自律公约》（2025-04-28，权威媒体）",
        "url": "https://www.guancha.cn/economy/2025_04_29_774125.shtml",
        "keywords": ["反洗稿", "自律公约", "AI辅助创作", "原创", "版权"],
        "title_pattern": r"反洗稿",
        "fallback_domains": ["guancha.cn"],
        "fallback_query": "网络文学 反洗稿 自律公约 16家平台",
    },
]

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"


def cache_dir():
    """缓存目录：系统临时目录下的技能专属子目录（不污染技能包）。"""
    d = os.path.join(tempfile.gettempdir(), "fiction-polish-distill-cache")
    os.makedirs(d, exist_ok=True)
    return d


def cache_path(src_id):
    return os.path.join(cache_dir(), f"policy_{src_id}.json")


def load_cache(src_id):
    """读取缓存（24 小时内有效）。"""
    p = cache_path(src_id)
    if not os.path.exists(p):
        return None
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        fetched = datetime.fromisoformat(data.get("fetched_at", ""))
        if datetime.now() - fetched > timedelta(hours=CACHE_TTL_HOURS):
            return None
        return data
    except Exception:
        return None


def save_cache(src_id, data):
    try:
        with open(cache_path(src_id), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        pass


def fetch_url(url, timeout=15):
    """抓取页面 HTML。失败抛异常，由调用方如实处理。"""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    for enc in ("utf-8", "gb18030"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def strip_html(html):
    """去除 HTML 标签与脚本样式，保留正文文本。"""
    html = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html)
    text = re.sub(r"(?is)<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    return text


def extract_points(text, source):
    """按关键词提取政策要点：命中关键词附近的句子，去重后输出。

    窗口内片段默认保留完整句；仅当片段超长（>160 字符）时才截断到
    最近的句子结束符（避免截掉句首字导致要点残缺）。
    """
    hits = set()
    for kw in source["keywords"]:
        for m in re.finditer(re.escape(kw), text):
            start = max(0, m.start() - 60)
            end = min(len(text), m.end() + 60)
            snippet = text[start:end].strip()
            # 超长片段截断到最近句子结束符（保留完整句）
            if len(snippet) > 160:
                for sep in ("。", "！", "？", "；", "\n"):
                    idx = snippet.rfind(sep, 0, 150)
                    if idx > 0:
                        snippet = snippet[idx + 1:].strip()
                        break
            snippet = re.sub(r"\s+", " ", snippet)
            if 12 <= len(snippet) <= 180:
                hits.add(snippet)
            if len(hits) >= 6:
                break
    return sorted(hits)


def search_fallback(source, timeout=15):
    """O-1 来源双通道：固定 URL 失效时，用通用检索 + 官方域名限定定位最新官方公告。

    返回 (实际公告URL, 提取要点列表)；检索也未果时返回 None。
    仅使用标准库（urllib/re）；检索页结构变化时如实返回 None，绝不编造要点。
    """
    import urllib.parse

    query = source.get("fallback_query") or f"{source['platform']} AI 公告"
    domains = source.get("fallback_domains") or []
    urls = []
    # 先做官方域名限定检索（site: 语法），优先定位官方公告
    for dom in domains:
        search_url = "https://www.bing.com/search?q=" + urllib.parse.quote(f"site:{dom} {query}")
        try:
            html = fetch_url(search_url, timeout)
            for m in re.finditer(r'href="(https?://[^"#&]+)"', html):
                href = m.group(1)
                if dom in href and href not in urls:
                    urls.append(href)
        except Exception:
            continue
        if len(urls) >= 3:
            break
    # 逐个候选抓取，用关键词提取要点；首个能提取到要点的即视为检索成功
    for url in urls[:3]:
        try:
            html = fetch_url(url, timeout)
            text = strip_html(html)
            points = extract_points(text, source)
            if points:
                return url, points
        except Exception:
            continue
    return None


def load_builtin_policies():
    """读取内置 platform_policies（antiai_blacklist.json），供 O-3 时效比对。"""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base, "references", "antiai_blacklist.json")
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        return d.get("platform_policies", {})
    except Exception:
        return {}


def diff_builtin(builtin, result):
    """O-3 过期告警：比对内置快照与本次联网要点，返回差异说明（无差异返回空串）。

    以 source.keywords 为桥：联网要点中命中的关键词，若内置平台快照
    （allowed/red_lines/rules）文本完全未覆盖，则提示"内置规范可能已过期"。
    仅为提示性判断，不替代人工核对。
    """
    platform = result.get("builtin_name") or result.get("platform", "")
    pl = builtin.get("platforms", {}).get(platform, {})
    builtin_text = " ".join([
        " ".join(pl.get("allowed", [])),
        " ".join(pl.get("red_lines", [])),
        " ".join(pl.get("rules", [])),
    ])
    src = next((s for s in SOURCES if s.get("builtin_name", s["platform"]) == platform), None)
    if not src:
        return ""
    point_text = " ".join(result.get("points", []))
    uncovered = [kw for kw in src["keywords"] if kw in point_text and kw not in builtin_text]
    if not uncovered:
        return ""
    verified = pl.get("verified_date", "未知")
    return (f"⚠ 内置快照（核实于 {verified}）未覆盖本次联网命中的关键词 {uncovered}；"
            "平台口径可能已更新，请以本次联网结果为准。")


def verify_source(source, refresh=False):
    """核实单个来源。返回结果字典（如实标记成功/失败）。"""
    src_id = source["id"]
    if not refresh:
        cached = load_cache(src_id)
        if cached:
            cached["from_cache"] = True
            # 兼容旧缓存：补 builtin_name（diff_builtin 平台匹配用）
            cached.setdefault("builtin_name", source.get("builtin_name", source["platform"]))
            return cached

    result = {
        "id": src_id,
        "platform": source["platform"],
        "builtin_name": source.get("builtin_name", source["platform"]),
        "name": source["name"],
        "url": source["url"],
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        "status": "ok",
        "points": [],
        "error": "",
        "from_cache": False,
    }
    try:
        html = fetch_url(source["url"])
        text = strip_html(html)
        points = extract_points(text, source)
        if not points:
            # 页面结构变化导致关键词未命中：如实标记，不编造要点
            result["status"] = "partial"
            result["error"] = "已获取页面但未能提取政策要点（页面结构可能已更新），请人工核实"
        else:
            result["points"] = points
        save_cache(src_id, result)
    except Exception as e:
        # O-1 来源双通道：固定 URL 失效 → 检索降级定位最新官方公告
        found = search_fallback(source)
        if found:
            result["url"] = found[0]
            result["points"] = found[1]
            result["found_by_search"] = True
            result["status"] = "ok"
            result["error"] = ""
            result["note"] = "固定来源 URL 已失效，本结果来自联网检索发现的官方公告"
            save_cache(src_id, result)
        else:
            result["status"] = "unreachable"
            result["error"] = f"未获取到最新信息（{type(e).__name__}: {str(e)[:60]}；检索降级也未果），请人工核实"
            # 不缓存失败结果：下次运行会重新尝试，避免临时网络故障被缓存成"陈旧不可达"
    return result


def report(results, as_json=False):
    """输出核实报告（含数据溯源与 O-3 过期告警）。"""
    if as_json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return
    builtin = load_builtin_policies()
    print("══ 平台 AI 创作规范联网核实报告 ══")
    print(f"核实时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    for r in results:
        tag = {"ok": "✅", "partial": "⚠", "unreachable": "❌"}.get(r["status"], "?")
        print(f"\n{tag} {r['platform']} — {r['name']}")
        print(f"   来源: {r['url']} | 抓取: {r['fetched_at']} {'(缓存)' if r.get('from_cache') else ''}")
        if r["status"] == "ok":
            if r.get("found_by_search"):
                print("   来源通道: 固定 URL 失效 → 联网检索发现（O-1 双通道降级）")
            for p in r["points"]:
                print(f"   · {p}")
            diff = diff_builtin(builtin, r)
            if diff:
                print(f"   {diff}")
        else:
            print(f"   {r['error']}")
    print("\n说明: 以上要点均来自官方/权威公开页面原文提取；请以各平台官方最新公告为准。")
    print("内置结构化规范见 references/antiai_blacklist.json（platform_policies，各平台含核实日期）；"
          "本次联网结果与内置快照有差异时会以上述告警提示。")


def main(argv):
    import argparse

    parser = argparse.ArgumentParser(description="平台 AI 创作规范联网核实工具")
    parser.add_argument(
        "--platform",
        choices=[s["id"] for s in SOURCES],
        help="仅核实指定来源（jinjiang/qidian/fanqie/cac/industry）",
    )
    parser.add_argument("--refresh", action="store_true", help="强制刷新缓存（默认 24 小时有效）")
    parser.add_argument("--json", action="store_true", dest="as_json", help="JSON 格式输出")
    args = parser.parse_args(argv)

    refresh = args.refresh
    as_json = args.as_json
    platform_only = args.platform

    targets = SOURCES
    if platform_only:
        targets = [s for s in SOURCES if s["id"] == platform_only]

    results = [verify_source(s, refresh) for s in targets]
    report(results, as_json)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
