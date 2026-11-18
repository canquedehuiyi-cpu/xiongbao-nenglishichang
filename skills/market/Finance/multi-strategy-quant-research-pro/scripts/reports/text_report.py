"""纯文本报告生成器。

生成包含大盘环境、策略统计、筛选结果、行业分布、风险声明的文本报告。
所有数据基于真实计算结果，不编造。

支持回复详细度（reply_level）：brief（简洁）/ standard（标准）/ full（全量）。
回复详细度仅控制"展示哪些真实数据段/展示多少细节"，不改变任何数据本身：
- brief   : 只展示核心筛选结果与简短风险提示
- standard: 标准报告（大盘环境/策略通过率/筛选结果/行业分布/数据质量/风险声明）
- full    : 全量报告（标准内容 + 每条标的完整判定理由/多因子画像/技术位明细）

支持 return_text=True 直接返回文本内容（不写文件），用于"仅控制台文字输出"模式。
"""

from datetime import datetime
import os

import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import config  # noqa: E402

_VALID_LEVELS = ("brief", "standard", "full")


def generate_text_report(
    results: list[dict],
    output_dir: str,
    market_env: dict = None,
    strategy_stats: dict = None,
    total_passed: int = None,
    reply_level: str = "full",
    return_text: bool = False,
) -> str:
    """生成纯文本选股报告。

    Args:
        results: 筛选结果列表（已按 --top 截断，仅含展示名单），每项含 code/name/score/strategy_hits/reasons/details 等。
        output_dir: 输出目录。
        market_env: 大盘环境数据 {indices: {...}, environment: "多头"/"震荡"/"空头"}。
        strategy_stats: 策略统计 {strategy_code: {passed: int, total: int}, ...}。
        total_passed: 实际通过总标的数（未截断），如实标注，避免与展示名单数量混淆。
        reply_level: 回复详细度 brief/standard/full（仅控制展示丰富度，不影响数据真实性）。
        return_text: True 时返回报告文本内容（不写文件），供"仅控制台文字输出"模式使用。

    Returns:
        str: 报告文件路径；return_text=True 时返回报告文本内容。
    """
    if reply_level not in _VALID_LEVELS:
        reply_level = "full"

    os.makedirs(output_dir, exist_ok=True)
    now = datetime.now()
    filename = f"选股报告_{now.strftime('%Y%m%d_%H%M%S')}.txt"
    report_path = os.path.join(output_dir, filename)

    brief = reply_level == "brief"
    full = reply_level == "full"

    lines = []
    a = lines.append
    a("=" * 70)
    a(f"   multi-strategy-quant-research-pro {config.VERSION} 选股报告")
    a(f"   生成时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    a("   数据源: 东方财富公开行情API（K线备选: 腾讯/新浪公开通道）")
    if market_env and market_env.get("data_channel"):
        a(f"   数据通道: {market_env['data_channel']}")
    a("=" * 70)
    a("")

    # 大盘环境（简洁模式省略详细信号，聚焦结果）
    if market_env and not brief:
        a("【大盘环境】")
        env = market_env.get("environment", "未知")
        factor = market_env.get("factor", 1.0)
        a(f"  市场状态: {env}（环境系数 {factor:.2f}）")
        indices = market_env.get("indices", {})
        for code, info in indices.items():
            direction = "上涨" if info.get("pct_change", 0) > 0 else ("下跌" if info.get("pct_change", 0) < 0 else "平盘")
            a(f"  {info.get('name', code)}: {info.get('price', 0):.2f}  "
              f"{info.get('pct_change', 0):+.2f}% {direction}")

        # 指数信号（均线结构/短期动量/量能）
        signals = market_env.get("signals", {})
        if signals:
            a("  指数信号（真实数据）:")
            for code, sig in signals.items():
                name = sig.get("name", code)
                direction = sig.get("direction", "-")
                mom = sig.get("momentum_5d")
                mom_str = f"{mom:+.2f}%" if mom is not None else "-"
                vol = sig.get("volume_note", "-")
                vr = sig.get("volume_ratio")
                vol_str = f"{vol}" + (f"({vr:.2f}x)" if vr is not None else "")
                a(f"    {name}: MA{direction} | 近5日 {mom_str} | 量能 {vol_str}")

        # 市场宽度（A股）
        breadth = market_env.get("breadth")
        if breadth:
            a(f"  市场宽度: 上涨 {breadth['up']} / 下跌 {breadth['down']} / 平 {breadth['flat']} "
              f"(上涨占比 {breadth['ratio'] * 100:.1f}%)")
        a("")

    # 数据质量（真实偏差显式量化：候选池覆盖率 / 财务滞后 / 估值口径）
    dq = (market_env or {}).get("data_quality")
    if dq and not brief:
        a("【数据质量】")
        cov = dq.get("candidate_coverage", {})
        for m, c in cov.items():
            if c.get("total"):
                ratio = c["sampled"] / c["total"] * 100
                a(f"  {m}候选池: {c['sampled']}/{c['total']} 只（覆盖 {ratio:.1f}%），"
                  "按总市值降序取前N近似，非指数成分精确匹配")
            else:
                a(f"  {m}候选池: {c['sampled']} 只（全市场总数未知，如实标注）")
        lag = dq.get("financial_lag_days")
        lr = dq.get("financial_latest_report")
        if lr:
            lag_txt = f"（滞后约 {lag} 天）" if lag is not None else ""
            a(f"  财务数据: 基于最近披露报告（{lr}{lag_txt}；财报滞后1-4个月为正常）")
        vnote = dq.get("valuation_note")
        if vnote:
            a(f"  估值口径: {vnote}")
        a("")

    # 趋势推演（条件式，非预测承诺）
    outlook = market_env.get("outlook", []) if market_env else []
    if outlook and not brief:
        a("【市场趋势推演】（基于实时真实信号 · 条件式表述 · 非预测承诺）")
        for it in outlook:
            a(f"  [{it.get('kind', '')}] {it.get('name', '')}（{it.get('signal', '')}）")
            a(f"    → {it.get('outlook', '')}")
        a("  推演仅为数据结构的条件式描述（若…则…），不构成涨跌承诺与投资建议。")
        a("")

    # 策略统计
    if strategy_stats and not brief:
        a("【策略通过率】")
        for s_code, stat in sorted(strategy_stats.items()):
            passed = stat.get("passed", 0)
            total = stat.get("total", 0)
            rate = f"{passed}/{total}" if total > 0 else "0/0"
            a(f"  {s_code}: {rate}")
        a("")

    # 筛选结果
    if not results:
        a("【筛选结果】")
        a("  当日未筛选出符合条件的标的。")
        a("")
    else:
        shown = len(results)
        if total_passed is not None and total_passed > shown:
            a(f"【筛选结果】（共 {total_passed} 只通过，以下展示前 {shown} 只）")
            a("")
        else:
            a(f"【筛选结果】（共 {shown} 只通过）")
            a("")

        # results 已在主流程按 --top 截断，此处不再二次截断（避免与实际名单数量不一致）
        for i, s in enumerate(results):
            code = s.get("code", "")
            name = s.get("name", "")
            score = s.get("score", 0)
            hits = s.get("strategy_hits", [])
            consensus = s.get("consensus_level", "")
            mkt = s.get("market", "")
            mkt_str = f"[{mkt}] " if mkt else ""
            a(f"#{i+1}  {mkt_str}{code}  {name}  评分: {score:.2f}")
            if consensus:
                a(f"    共识度: {consensus}")
            if hits:
                a(f"    命中策略: {', '.join(hits)}")
            if not brief:
                # 多因子画像：各策略维度得分概览（真实来源于策略判定结果，可解释"为什么入选"）
                profile = s.get("factor_profile") or {}
                if profile:
                    prof_str = "  ".join(f"{k}={v}" for k, v in profile.items())
                    a(f"    策略画像: {prof_str}")
                # 支撑/压力位：近N日真实K线高低点（简单技术位，非预测承诺）
                sr = s.get("support_resistance")
                if sr:
                    a(f"    技术位(近{sr['window']}日真实高低点): "
                      f"支撑 {sr['support']} / 压力 {sr['resistance']}（非预测承诺）")
                reasons = s.get("reasons", [])
                # 简洁/标准模式展示前5条，全量模式展示全部判定理由
                reason_limit = None if full else 5
                for reason in reasons[:reason_limit]:
                    a(f"    · {reason}")
            a("")

    # 行业分布（简洁模式省略）
    industry_map = {}
    for s in results:
        ind = s.get("industry", "未知")
        industry_map[ind] = industry_map.get(ind, 0) + 1
    if industry_map and not brief:
        a("【行业分布】")
        for ind, cnt in sorted(industry_map.items(), key=lambda x: x[1], reverse=True):
            a(f"  {ind}: {cnt}只")
        a("")

    # 关注方向说明
    a("【关注方向说明】")
    a("  本报告基于多种技术形态与基本面量化筛选，提供的选股列表仅作技术形态参考，")
    a("  不构成任何投资建议。投资者应结合基本面、消息面、市场情绪等多维因素综合")
    a("  判断，自主决策并承担风险。")
    a("")

    # 风险声明
    a("=" * 70)
    a("【风险声明】")
    a("1. 本报告基于东方财富公开行情接口生成（K线备选腾讯/新浪公开通道），数据可能存在3-5分钟延迟。")
    a("2. 技术形态筛选仅反映历史量价关系，不代表未来走势。")
    a("3. 本报告不构成任何投资建议，也不构成收益承诺。")
    a("4. 所有判定逻辑公开透明、可审计复现。")
    a(f"5. 数据时效: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    a("6. 股市有风险，投资需谨慎。")
    a("=" * 70)

    text = "\n".join(lines)
    if return_text:
        return text
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(text)
        if not text.endswith("\n"):
            f.write("\n")
    return report_path
