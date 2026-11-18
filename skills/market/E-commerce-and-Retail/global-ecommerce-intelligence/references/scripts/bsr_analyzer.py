#!/usr/bin/env python3
"""bsr_analyzer.py — BSR销量估算 (v1.0.7)

说明:
  - 所有系数为经验估算值,未经真实数据校准,输出仅供量级参考
  - 置信区间为经验区间,非统计置信区间
  - 模型来源: Amazon 用对数回归; 淘宝/Shopee/京东/Temu/SHEIN/TikTok 为参数化假设
  - 支持 --json 输出

用法:
    python3 bsr_analyzer.py --bsr 1500 --category home --json
    python3 bsr_analyzer.py --bsr 500 --category electronics --price 29.99 --market amazon --json
    python3 bsr_analyzer.py --bsr 3000 --category clothing --price 19.99 --market taobao --season summer --json
    python3 bsr_analyzer.py --bsr 2000 --category clothing --market temu --json   # Temu 无公开BSR体系: 置信度极低

参数:
    --bsr       排名
    --category  品类
    --price     售价(可选)
    --market    市场: amazon/taobao/shopee/jd/temu/shein/tiktok（后三者无公开BSR体系,置信度极低）
    --season    季节(可选)
    --json      输出JSON
"""

import argparse
import datetime
import json
import math

VERSION = "1.0.7"


def meta_fields(tool):
    return {
        "ok": True,
        "tool": tool,
        "version": VERSION,
        "schema": "global-ecommerce-intelligence/" + tool,
        "generatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    }


# ─────────────────────────────────────────────────────────────
# 品类系数 — 经验估算值,无真实数据标定
# 来源: 行业经验+公开BSR-销量关系讨论整理
# 用途: 不同品类BSR-销量曲线斜率差异的近似
# ─────────────────────────────────────────────────────────────
CATEGORY_COEFF = {
    "electronics": 1.5, "home": 1.2, "kitchen": 1.2, "toys": 1.0,
    "sports": 1.1, "beauty": 0.9, "clothing": 0.8, "books": 0.7,
    "tools": 1.3, "pet": 1.4, "default": 1.0,
    "automotive": 1.1, "grocery": 1.6, "health": 1.3, "garden": 1.0,
    "office": 0.9, "music": 0.6, "outdoor": 1.2, "baby": 1.1,
}

# 季节因子 — 经验估算
SEASON_FACTOR = {
    "spring": 1.0,
    "summer": {"clothing": 1.3, "sports": 1.4, "outdoor": 1.5, "beauty": 1.2, "toys": 0.8, "default": 1.0},
    "fall": {"clothing": 1.1, "home": 1.2, "kitchen": 1.3, "default": 1.0},
    "winter": {"clothing": 1.4, "toys": 1.8, "electronics": 1.3, "health": 1.2, "home": 1.1, "default": 1.0},
}

# 各市场模型 — 参数化假设,非真实数据拟合
# Amazon: 对数回归(base=50000, decay=0.55)为业界常用经验公式
# 淘宝/Shopee/京东: 无公开BSR-销量数据,系数为推测值,置信度极低
# Temu/SHEIN/TikTok: 平台无公开BSR体系,以下为量级参考的参数化假设,置信度极低
TAOBAO_MODEL = {"coeff": 0.85, "base_sales": 15000, "decay": 0.65}
SHOPEE_MODEL = {"coeff": 0.6, "base_sales": 8000, "decay": 0.55}
JD_MODEL = {"coeff": 0.9, "base_sales": 12000, "decay": 0.62}
TEMU_MODEL = {"coeff": 0.5, "base_sales": 6000, "decay": 0.5}
SHEIN_MODEL = {"coeff": 0.45, "base_sales": 5000, "decay": 0.5}
TIKTOK_MODEL = {"coeff": 0.4, "base_sales": 4000, "decay": 0.5}

MODEL_DISCLAIMER = {
    "amazon": "对数回归经验公式,业界常用,置信度:中",
    "taobao": "参数化假设,无真实数据标定,置信度:低",
    "shopee": "参数化假设,无真实数据标定,置信度:低",
    "jd": "参数化假设,无真实数据标定,置信度:低",
    "temu": "参数化假设,平台无公开BSR体系,仅供量级参考,置信度:极低",
    "shein": "参数化假设,平台无公开BSR体系,仅供量级参考,置信度:极低",
    "tiktok": "参数化假设,平台无公开BSR体系,仅供量级参考,置信度:极低",
}


def log_regression_sales(bsr, base, decay, coeff):
    if bsr <= 0:
        bsr = 1
    return max(round(base * math.pow(bsr, -decay) * coeff), 1)


def estimate_sales_amazon(bsr, category="default", season=None):
    coeff = CATEGORY_COEFF.get(category, 1.0)
    base_sales = log_regression_sales(bsr, 50000, 0.55, coeff)
    if season and season in SEASON_FACTOR:
        sf = SEASON_FACTOR[season]
        if isinstance(sf, dict):
            factor = sf.get(category, sf.get("default", 1.0))
        else:
            factor = sf
        base_sales = max(round(base_sales * factor), 1)
    return base_sales


# 非 Amazon 市场模型映射 — 数据驱动, 各市场仅参数不同
NON_AMAZON_MODELS = {
    "taobao": TAOBAO_MODEL,
    "shopee": SHOPEE_MODEL,
    "jd": JD_MODEL,
    "temu": TEMU_MODEL,
    "shein": SHEIN_MODEL,
    "tiktok": TIKTOK_MODEL,
}


def estimate_sales_model(bsr, model, category="default"):
    coeff = CATEGORY_COEFF.get(category, 1.0)
    return log_regression_sales(bsr, model["base_sales"], model["decay"], coeff * model["coeff"])


def confidence_interval(sales, bsr):
    """经验区间 — 非统计置信区间,无数据支撑,仅供量级参考"""
    if bsr <= 100:
        low, high = 0.6, 1.4
    elif bsr <= 1000:
        low, high = 0.65, 1.35
    elif bsr <= 5000:
        low, high = 0.7, 1.3
    elif bsr <= 20000:
        low, high = 0.75, 1.25
    else:
        low, high = 0.8, 1.2
    return {
        "low": max(round(sales * low), 1),
        "mid": sales,
        "high": max(round(sales * high), 1),
        "interval_type": "经验区间(非统计置信区间)",
    }


def build_report(bsr, category, price, market, season):
    if market == "amazon":
        sales = estimate_sales_amazon(bsr, category, season)
    else:
        sales = estimate_sales_model(bsr, NON_AMAZON_MODELS[market], category)
    market_name = {
        "amazon": "Amazon", "taobao": "淘宝", "shopee": "Shopee", "jd": "京东",
        "temu": "Temu", "shein": "SHEIN", "tiktok": "TikTok Shop",
    }.get(market, market)

    ci = confidence_interval(sales, bsr)
    coeff = CATEGORY_COEFF.get(category, 1.0)
    disclaimer = MODEL_DISCLAIMER.get(market, "")

    report = {
        "市场": market_name,
        "排名": bsr,
        "品类": category,
        "品类系数": coeff,
        "提示": (
            ["未知品类 '%s', 已回退通用系数 1.0, 估算置信度进一步降低" % category]
            if category not in CATEGORY_COEFF else []
        ),
        "模型": "对数回归(经验估算)",
        "模型置信度": disclaimer,
        "月销量估算": {
            "保守": ci["low"],
            "中性": ci["mid"],
            "乐观": ci["high"],
        },
        "日销量估算": {
            "保守": round(ci["low"] / 30, 1),
            "中性": round(ci["mid"] / 30, 1),
            "乐观": round(ci["high"] / 30, 1),
        },
        "区间类型": ci["interval_type"],
        "季节": season,
    }

    if price:
        report["售价"] = price
        report["月收入估算"] = {
            "保守": round(ci["low"] * price, 2),
            "中性": round(ci["mid"] * price, 2),
            "乐观": round(ci["high"] * price, 2),
        }

    # 竞争区位判断
    if bsr < 500:
        report["竞争区位"] = "[头部] 竞争激烈区(头部卖家)"
    elif bsr < 5000:
        report["竞争区位"] = "[增长] 增长潜力区"
    elif bsr < 50000:
        report["竞争区位"] = "[长尾] 长尾市场区"
    else:
        report["竞争区位"] = "[需评估] 低销量区(需评估)"

    return report


def print_report(report):
    print(f"\nBSR 销量分析 — {report['市场']}")
    print("=" * 40)
    print(f"  排名: {report['排名']}")
    print(f"  品类: {report['品类']} (系数: {report['品类系数']})")
    print(f"  模型: {report['模型']}")
    print(f"  模型置信度: {report['模型置信度']}")
    print("  ─────────────────────────")
    print("  月销量估算:")
    print(f"    保守: {report['月销量估算']['保守']} 单")
    print(f"    中性: {report['月销量估算']['中性']} 单")
    print(f"    乐观: {report['月销量估算']['乐观']} 单")
    print("  日销量估算:")
    print(f"    保守: {report['日销量估算']['保守']} 单")
    print(f"    中性: {report['日销量估算']['中性']} 单")
    print(f"    乐观: {report['日销量估算']['乐观']} 单")
    if "售价" in report:
        print("  ─────────────────────────")
        print(f"  售价: {report['售价']}")
        print("  月收入估算:")
        print(f"    保守: {report['月收入估算']['保守']}")
        print(f"    中性: {report['月收入估算']['中性']}")
        print(f"    乐观: {report['月收入估算']['乐观']}")
    print("  ─────────────────────────")
    print(f"  {report['竞争区位']}")
    print("  ─────────────────────────")
    print(f"  区间类型: {report['区间类型']}")
    print("=" * 40)


def main():
    parser = argparse.ArgumentParser(description="BSR销量估算 v" + VERSION)
    parser.add_argument("--bsr", type=int, default=None, help="排名")
    parser.add_argument("--category", type=str, default="default", help="品类")
    parser.add_argument("--price", type=float, default=0, help="售价")
    parser.add_argument("--market", type=str, default="amazon",
                        choices=["amazon", "taobao", "shopee", "jd", "temu", "shein", "tiktok"],
                        help="市场（season 仅对 amazon 生效）")
    parser.add_argument("--season", type=str, default=None,
                        choices=["spring", "summer", "fall", "winter"], help="季节（仅 amazon）")
    parser.add_argument("--json", action="store_true", help="输出JSON")
    parser.add_argument("--version", action="version", version=VERSION, help="输出版本")
    args = parser.parse_args()

    if args.bsr is None:
        parser.error("--bsr 必填（排名1为最佳）")
    if args.bsr <= 0:
        parser.error("--bsr 必须为正整数（排名1为最佳）")
    if args.price < 0:
        parser.error("--price 不能为负")
    if args.market != 'amazon' and args.season:
        print('提示: --season 季节因子仅对 amazon 生效, 已忽略')

    report = build_report(args.bsr, args.category, args.price, args.market, args.season)
    if args.json:
        out = meta_fields("bsr_analyzer")
        out.update({"result": report})
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print_report(report)


if __name__ == "__main__":
    main()
