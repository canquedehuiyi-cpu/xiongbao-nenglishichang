#!/usr/bin/env python3
"""profit_calculator.py — 电商利润计算器 (v1.0.7)

功能:
  1. 全链路成本计算: 售价-产品成本-平台佣金-物流-关税-营销-退货损耗
  2. 多币种换算: 内置快照(标注快照日期) + --fx-live 实时抓取 + --fx-rates 手动注入
  3. 盈亏平衡分析(含初始投入), 52周财务预测(ramp经验假设)
  4. AI vs 传统团队成本对比(行业估算,非实测)
  5. --json 输出 + --version

用法:
    python3 profit_calculator.py --price 199 --cost 80 --commission 15 --logistics 30 --json
    python3 profit_calculator.py --price 199 --cost 80 --commission 15 --fx-live --json
    python3 profit_calculator.py --price 29.99 --cost 8.50 --commission 15 --currency USD --fx-rates fx.json --json
    python3 profit_calculator.py --price 199 --cost 80 --commission 15 --model compare

参数:
    --price          售价
    --cost           产品成本
    --commission     平台佣金比例(百分数)
    --logistics      物流费用
    --currency       货币(默认CNY)
    --fx-live        抓取实时汇率(调用 fetch-rates.mjs,失败降级快照)
    --fx-rates       注入实时汇率: JSON 字符串或文件路径(格式见 fetch-rates.mjs --json 输出)
    --tax            关税(可选)
    --marketing      营销费用(可选)
    --return-rate    退货率(百分数,可选)
    --monthly-sales  月销量(可选,用于52周预测+盈亏平衡)
    --initial-invest 初始投入(可选,首批库存+开店+杂费,用于盈亏平衡)
    --model          模式: basic/compare
    --json           输出JSON
    --version        输出版本
"""

import argparse
import datetime
import json
import os
import subprocess
import sys

VERSION = "1.0.7"

# 汇率快照(非实时) — 2026-09-02 由公开汇率 API 实测换算而来,仅作离线兜底
# 口径: 1 外币 = X 人民币。实时使用请以 fetch-rates.mjs --json 为准
FX_RATES = {
    "CNY": 1.0, "USD": 6.7369, "EUR": 7.8110, "GBP": 9.1112, "JPY": 0.04208,
    "KRW": 0.004904, "SGD": 5.2921, "THB": 0.20256, "MYR": 1.66821,
    "PHP": 0.10779, "VND": 0.0002590, "IDR": 0.0003792, "BRL": 1.30157,
    "MXN": 0.39652, "AUD": 4.8150, "CAD": 4.84997, "AED": 1.83442,
    "SAR": 1.79651, "INR": 0.070915, "TRY": 0.139527,
}
FX_UPDATED = "2026-09-02"
FX_SOURCE = "内置快照(非实时; 实时请用 --fx-live)"

# AI vs 传统团队成本对比 — 行业估算值,非实测
AI_COST_MONTHLY = {
    "选品分析": 200, "竞品监控": 0, "客服": 1200, "广告优化": 500,
    "合规检查": 0, "内容制作": 300, "数据分析": 0,
}
TRADITIONAL_COST_MONTHLY = {
    "选品分析": 8000, "竞品监控": 6000, "客服": 12000, "广告优化": 10000,
    "合规检查": 5000, "内容制作": 8000, "数据分析": 6000,
}


def meta_fields(tool):
    return {
        "ok": True,
        "tool": tool,
        "version": VERSION,
        "schema": "global-ecommerce-intelligence/" + tool,
        "generatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    }


def convert_to_cny(amount, currency):
    rate = FX_RATES.get(currency, None)
    if rate is None:
        raise KeyError('汇率表中无该币种: ' + currency + '（可用: ' + ','.join(sorted(FX_RATES.keys())) + '）')
    return amount * rate


def calculate_profit(price, cost, commission_pct, logistics, tax=0, marketing=0, return_rate=0):
    commission = price * commission_pct / 100
    # 退货损耗模型: 退货率 × (售价 + 10%翻新折旧 + 往返物流×2)。估算口径,输出含说明
    refund_loss_per_unit = price * 1.10 + 2 * logistics
    refund_cost = refund_loss_per_unit * return_rate / 100
    total_cost = cost + commission + logistics + tax + marketing + refund_cost
    profit = price - total_cost
    margin = (profit / price) * 100 if price > 0 else 0
    roi = (profit / total_cost) * 100 if total_cost > 0 else 0
    return {
        "售价": round(price, 2),
        "产品成本": round(cost, 2),
        "平台佣金": round(commission, 2),
        "物流费用": round(logistics, 2),
        "关税": round(tax, 2),
        "营销费用": round(marketing, 2),
        "退货损耗": round(refund_cost, 2),
        "总成本": round(total_cost, 2),
        "净利润": round(profit, 2),
        "利润率": round(margin, 1),
        "ROI": round(roi, 1),
        "退货损耗说明": "退货率 × (售价 + 10%翻新折旧 + 往返物流×2),估算口径",
    }


def breakeven_months(initial_invest, profit_per_unit, monthly_sales):
    """回本月数 = 初始投入 / 月净利润。月净利润 = 单件净利润 × 月销量。"""
    monthly_profit = profit_per_unit * monthly_sales
    if monthly_profit <= 0:
        return None
    if initial_invest <= 0:
        return None
    return round(initial_invest / monthly_profit, 1)


def weekly_projection(profit_per_unit, monthly_sales, weeks=52):
    """52周预测(每4周采样)。ramp模型: 前12周爬坡(0.3→1.0),之后稳定。经验假设,非真实曲线。

    直接以月销量乘以 ramp 系数: 先除以 4.33 再乘回 4.33 属无意义往返,
    且受二进制浮点影响会产生误差(实测约 13% 的取值不精确还原)。
    """
    results = []
    for w in range(1, weeks + 1, 4):
        ramp = min(1.0, 0.3 + 0.7 * (w / 12))
        adj_sales = monthly_sales * ramp
        results.append({
            "week": w,
            "monthly_sales": round(adj_sales),
            "monthly_profit": round(profit_per_unit * adj_sales, 2),
        })
    return results


def compare_mode(as_json=False):
    ai_total = sum(AI_COST_MONTHLY.values())
    trad_total = sum(TRADITIONAL_COST_MONTHLY.values())
    rows = []
    for key in TRADITIONAL_COST_MONTHLY:
        t = TRADITIONAL_COST_MONTHLY[key]
        a = AI_COST_MONTHLY[key]
        pct = round((1 - a / t) * 100) if t > 0 else 0
        rows.append({"item": key, "traditional": t, "ai": a, "saving_pct": pct})

    data = meta_fields("profit_calculator")
    data.update({
        "model": "compare",
        "method": "行业估算值(非实测)",
        "rows": rows,
        "ai_total_monthly": ai_total,
        "traditional_total_monthly": trad_total,
        "saving_pct": round((1 - ai_total / trad_total) * 100),
        "annual_saving": (trad_total - ai_total) * 12,
    })
    if as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    print("\nAI vs 传统团队 成本对比 (月) [行业估算,非实测]")
    print("=" * 50)
    print("  {:<10} {:>10} {:>10} {:>8}".format("项目", "传统团队", "AI赋能", "节省"))
    for r in rows:
        print("  {:<10} ¥{:>8,} ¥{:>8,} {:>6}%".format(r["item"], r["traditional"], r["ai"], r["saving_pct"]))
    print("  {:<10} ¥{:>8,} ¥{:>8,} {:>6}%".format("合计", trad_total, ai_total, data["saving_pct"]))
    print("  年节省: ¥{:,}".format(data["annual_saving"]))
    print("=" * 50)


def load_fx_live():
    """调用 fetch-rates.mjs 抓取实时汇率;失败诚实降级到内置快照。"""
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fetch-rates.mjs')
    if not os.path.exists(script):
        return None, None, 'fetch-rates.mjs 缺失,使用内置快照(非实时)'
    try:
        r = subprocess.run(['node', script, '--json'], capture_output=True, text=True, timeout=25)
        if r.returncode != 0:
            return None, None, 'fetch-rates.mjs 抓取失败(退出码 %d),使用内置快照: %s' % (
                r.returncode, (r.stdout or r.stderr or '').strip()[:120])
        data = json.loads(r.stdout)
        if not data.get('ok') or not data.get('rates'):
            return None, None, 'fetch-rates.mjs 返回异常,使用内置快照'
        return data['rates'], data.get('fetchedAt'), data.get('source') or '实时API'
    except Exception as e:
        return None, None, 'fetch-rates.mjs 调用异常,使用内置快照: %s' % e


def load_fx_rates_arg(raw):
    """--fx-rates: 接受 JSON 字符串或文件路径。"""
    if os.path.exists(raw):
        with open(raw, 'r', encoding='utf-8') as f:
            return json.load(f)
    return json.loads(raw)


def main():
    parser = argparse.ArgumentParser(description="电商利润计算器 v" + VERSION)
    parser.add_argument("--price", type=float, default=0, help="售价")
    parser.add_argument("--cost", type=float, default=0, help="产品成本")
    parser.add_argument("--commission", type=float, default=15, help="平台佣金比例(百分数)")
    parser.add_argument("--logistics", type=float, default=0, help="物流费用")
    parser.add_argument("--tax", type=float, default=0, help="关税")
    parser.add_argument("--marketing", type=float, default=0, help="营销费用")
    parser.add_argument("--currency", type=str, default="CNY", help="货币")
    parser.add_argument("--return-rate", type=float, default=0, help="退货率(百分数)")
    parser.add_argument("--monthly-sales", type=int, default=0, help="月销量")
    parser.add_argument("--initial-invest", type=float, default=0, help="初始投入(首批库存+开店+杂费)")
    parser.add_argument("--model", type=str, default="basic", choices=["basic", "compare"], help="模式")
    parser.add_argument("--fx-live", action="store_true", help="抓取实时汇率(调用 fetch-rates.mjs,失败降级快照)")
    parser.add_argument("--fx-rates", type=str, default=None,
                        help="注入实时汇率: JSON 字符串 或 文件路径(格式同 fetch-rates.mjs --json 输出)")
    parser.add_argument("--json", action="store_true", help="输出JSON")
    parser.add_argument("--version", action="version", version=VERSION, help="输出版本")
    args = parser.parse_args()

    if args.model == "compare":
        compare_mode(as_json=args.json)
        return

    if args.price <= 0 or args.cost <= 0:
        parser.error("--price 与 --cost 为必填参数（basic 模式）")
    if not (0 <= args.commission <= 100):
        parser.error("--commission 须在 0-100 之间(百分数)")
    if not (0 <= args.return_rate <= 100):
        parser.error("--return-rate 须在 0-100 之间(百分数)")
    if args.monthly_sales < 0:
        parser.error("--monthly-sales 不能为负")
    if args.initial_invest < 0:
        parser.error("--initial-invest 不能为负")
    if args.logistics < 0:
        parser.error("--logistics 不能为负")
    if args.tax < 0:
        parser.error("--tax 不能为负")
    if args.marketing < 0:
        parser.error("--marketing 不能为负")

    # 汇率来源决策: --fx-rates 注入 > --fx-live 实时抓取 > 内置快照
    global FX_RATES, FX_UPDATED, FX_SOURCE
    fx_note = None
    if args.fx_rates:
        try:
            injected = load_fx_rates_arg(args.fx_rates)
            rates = injected.get('rates') or injected
            base = injected.get('base', 'CNY')
            if not isinstance(rates, dict) or not rates:
                fx_note = '--fx-rates 内容无效,使用内置快照'
            else:
                if base == 'CNY':
                    # 注入口径与内置一致: 1 外币 = X 人民币
                    FX_RATES = {k: float(v) for k, v in rates.items() if k and float(v) > 0}
                    # 注入表可能不含 CNY 自身,补回基准币,否则默认币种换算会取不到汇率
                    FX_RATES.setdefault('CNY', 1.0)
                else:
                    # 注入为"1 基准币 = X 外币"(如 er-api 口径),换算为 1 外币 = X 人民币
                    base_cny = float(rates.get('CNY') or 0)
                    if base_cny <= 0:
                        fx_note = '--fx-rates 缺基准换算值,使用内置快照'
                    else:
                        FX_RATES = {k: base_cny / float(v) for k, v in rates.items()
                                    if k and k != 'CNY' and float(v) > 0}
                        FX_RATES['CNY'] = 1.0
                FX_UPDATED = (injected.get('fetchedAt') or '实时注入')[:10]
                FX_SOURCE = injected.get('source') or '用户注入(--fx-rates)'
        except Exception as e:
            fx_note = '--fx-rates 解析失败(%s),使用内置快照' % e
    elif args.fx_live:
        live_rates, live_at, live_src = load_fx_live()
        if live_rates:
            FX_RATES = live_rates
            FX_UPDATED = (live_at or '')[:10]
            FX_SOURCE = live_src
        else:
            fx_note = live_src

    try:
        price_cny = convert_to_cny(args.price, args.currency)
        cost_cny = convert_to_cny(args.cost, args.currency)
        logistics_cny = convert_to_cny(args.logistics, args.currency)
        tax_cny = convert_to_cny(args.tax, args.currency)
        marketing_cny = convert_to_cny(args.marketing, args.currency)
    except KeyError as e:
        if args.json:
            out = meta_fields("profit_calculator")
            out.update({"ok": False, "error": str(e)})
            print(json.dumps(out, ensure_ascii=False, indent=2))
        else:
            print('错误: ' + str(e))
        sys.exit(1)

    result = calculate_profit(
        price_cny, cost_cny, args.commission,
        logistics_cny, tax_cny, marketing_cny, args.return_rate
    )
    result["原币"] = args.currency
    result["汇率日期"] = FX_UPDATED
    result["汇率来源"] = FX_SOURCE
    result["汇率说明"] = fx_note or ('实时汇率(来源: %s)' % FX_SOURCE if args.fx_live or args.fx_rates else '内置快照(非实时,需实时核实)')
    result["计算方法"] = "全链路成本模型(售价-成本-佣金-物流-关税-营销-退货损耗)"

    # 初始投入按币种换算为 CNY 后参与回本计算(避免原币与 CNY 混算)
    initial_invest_cny = 0
    if args.initial_invest > 0:
        initial_invest_cny = convert_to_cny(args.initial_invest, args.currency)
        result["初始投入"] = round(initial_invest_cny, 2)
        result["初始投入原币"] = round(args.initial_invest, 2)
        result["初始投入币种"] = args.currency
    if args.initial_invest > 0 and args.monthly_sales > 0 and result["净利润"] > 0:
        breakeven = breakeven_months(initial_invest_cny, result["净利润"], args.monthly_sales)
        result["月净利润"] = round(result["净利润"] * args.monthly_sales, 2)
        result["盈亏平衡月数"] = breakeven
    elif args.monthly_sales > 0 and result["净利润"] > 0:
        result["月净利润"] = round(result["净利润"] * args.monthly_sales, 2)
        result["盈亏平衡月数"] = None
        result["盈亏平衡提示"] = "未提供--initial-invest,无法计算回本月数(需首批库存+开店等一次性投入)"
    elif args.monthly_sales > 0:
        result["月净亏损"] = round(abs(result["净利润"]) * args.monthly_sales, 2)
        if result["净利润"] < 0:
            result["盈亏平衡提示"] = "当前单件净利润为负,无法回本;需先调整售价/成本结构"
        else:
            result["盈亏平衡提示"] = "当前单件净利润为零(收支相抵),无利润可累积回本;需提高售价或压降成本"

    if args.monthly_sales > 0 and result["净利润"] > 0:
        result["52周预测"] = weekly_projection(result["净利润"], args.monthly_sales)

    if args.json:
        out = meta_fields("profit_calculator")
        out.update({"model": "basic", "result": result})
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return

    print("\n利润分析 (CNY, 原币: %s)" % args.currency)
    print("汇率: %s (%s) %s" % (result["汇率来源"], result["汇率日期"], result["汇率说明"]))
    print("=" * 35)
    for k, v in result.items():
        if k in ("52周预测", "原币", "汇率日期", "汇率来源", "汇率说明", "计算方法", "退货损耗说明"):
            continue
        print("  %s: %s" % (k, v))
    print("=" * 35)
    print("  %s" % ('盈利' if result["净利润"] > 0 else '亏损'))

    if "52周预测" in result:
        print("\n52周预测 (每4周, ramp模型为经验假设)")
        for p in result["52周预测"]:
            print("  周%s: 月销量%s 月利润¥%s" % (p["week"], p["monthly_sales"], p["monthly_profit"]))
    print()


if __name__ == "__main__":
    main()
