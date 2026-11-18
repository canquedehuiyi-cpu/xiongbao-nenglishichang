# -*- coding: utf-8 -*-
"""行业轮动分析：基于行业板块涨幅和资金流判断轮动方向。

输入：行业板块排行数据（来自 data.sector.fetch_industry_ranking）
输出：强势行业/弱势行业/轮动方向/配置建议
"""


def analyze_sector_rotation(industry_ranking: list[dict], top_n: int = 5) -> dict:
    """分析行业轮动。

    Args:
        industry_ranking: 行业板块排行列表，每项含 {name, change_pct, ...}
        top_n: 取前N个强势/弱势行业

    Returns:
        dict: {strong_sectors, weak_sectors, rotation_direction, suggestion}
    """
    if not industry_ranking:
        return {
            "strong_sectors": [],
            "weak_sectors": [],
            "rotation_direction": "未知",
            "suggestion": "无行业数据",
        }

    # 按涨幅排序
    sorted_sectors = sorted(industry_ranking, key=lambda x: x.get("pct_chg", x.get("change_pct", 0)), reverse=True)

    strong = sorted_sectors[:top_n]
    weak = sorted_sectors[-top_n:]

    # 计算强弱分化度
    strong_avg = sum(s.get("pct_chg", s.get("change_pct", 0)) for s in strong) / len(strong) if strong else 0
    weak_avg = sum(w.get("pct_chg", w.get("change_pct", 0)) for w in weak) / len(weak) if weak else 0
    divergence = strong_avg - weak_avg

    # 轮动方向判断
    if divergence > 3:
        rotation = "行业分化明显，资金向强势行业集中"
    elif divergence > 1:
        rotation = "温和轮动，强势行业略占优"
    elif divergence > -1:
        rotation = "行业普涨/普跌，轮动不明显"
    else:
        rotation = "资金从高位行业流出，可能切换到低位行业"

    # 配置建议
    if strong_avg > 2:
        suggestion = f"关注强势行业（平均涨幅{strong_avg:.1f}%），但需警惕追高风险"
    elif weak_avg < -2:
        suggestion = f"弱势行业平均跌幅{weak_avg:.1f}%，可关注超跌反弹机会"
    else:
        suggestion = "行业分化不大，建议均衡配置或等待明确方向"

    return {
        "strong_sectors": [{"name": s.get("name"), "change_pct": s.get("pct_chg", s.get("change_pct"))} for s in strong],
        "weak_sectors": [{"name": w.get("name"), "change_pct": w.get("pct_chg", w.get("change_pct"))} for w in weak],
        "rotation_direction": rotation,
        "divergence": round(divergence, 2),
        "strong_avg_change": round(strong_avg, 2),
        "weak_avg_change": round(weak_avg, 2),
        "suggestion": suggestion,
    }


def get_concept_hotspots(concept_ranking: list[dict], top_n: int = 5) -> list:
    """获取概念板块热点。"""
    if not concept_ranking:
        return []
    sorted_concepts = sorted(concept_ranking, key=lambda x: x.get("pct_chg", x.get("change_pct", 0)), reverse=True)
    return [{"name": c.get("name"), "change_pct": c.get("pct_chg", c.get("change_pct"))} for c in sorted_concepts[:top_n]]
