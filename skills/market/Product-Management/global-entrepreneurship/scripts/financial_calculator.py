"""
财务模型计算器 - 全球一人公司创业全链路指导系统
支持一次性购买、订阅制/SaaS、AI成本对比三种模型。
用于精确计算收入预测、成本分析、盈亏平衡点和三档场景模拟。

零第三方依赖，仅使用 Python 标准库；Python >= 3.8 可运行。
"""
import argparse
import json
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


# 月利润目标档位（货币单位随 --currency，跨币种通用）
PROFIT_TARGET_TIERS = [
    ("tier_1", 3000),
    ("tier_2", 10000),
    ("tier_3", 30000),
    ("tier_4", 100000),
]


def _emit(payload):
    """输出 JSON；error 字段存在时以退出码 1 结束。"""
    is_error = isinstance(payload, dict) and "error" in payload
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.exit(1 if is_error else 0)


def _normalize_churn(value):
    """
    归一化月流失率：
    - 输入 0 或缺省语义由调用方处理；
    - 0 < value <= 1 视为小数（如 0.05 = 5%）；
    - 1 < value <= 100 视为百分数（如 5 = 5%）；
    - 其余为非法输入。
    """
    if value is None or value < 0 or value > 100:
        return None, "月流失率必须在 0~100 之间（百分数，如 5 表示 5%；或 0~1 小数）"
    if value == 0:
        return 0.05, None  # 未提供时默认 5%
    if value > 1:
        return value / 100.0, None
    return float(value), None


def _validate_scenarios(conservative, moderate, optimistic):
    """三档预测必须非负且按 保守<=中性<=乐观 排列。"""
    for label, value in (("保守预测", conservative), ("中性预测", moderate), ("乐观预测", optimistic)):
        if value < 0:
            return f"{label}不能为负数"
    if not (conservative <= moderate <= optimistic):
        return "三档预测需满足 保守 <= 中性 <= 乐观"
    return None


def _safety_desc(rate, base_volume):
    """安全边际描述；base_volume 为中性销量/用户数，为 0 时说明缺少数据而非亏损。"""
    if base_volume == 0:
        return "缺少中性预测数据，无法计算安全边际，请先补充中性预测"
    if rate > 0.5:
        return "较高安全边际，经营风险较低"
    if rate > 0.2:
        return "中等安全边际，需关注波动"
    if rate > 0:
        return "较低安全边际，建议降低成本或提高销量"
    return "负安全边际，中性预测下仍亏损，需调整定价或成本结构"


def calculate_compare_model(traditional_low=30000, traditional_high=50000,
                            ai_low=250, ai_high=1000, currency="USD"):
    """AI 单人 vs 传统团队成本对比模型（行业典型估算，以实际工具定价为准）。"""
    err = _validate_compare_inputs(traditional_low, traditional_high, ai_low, ai_high)
    if err:
        return {"error": err}

    trad_mid = (traditional_low + traditional_high) / 2
    ai_mid = (ai_low + ai_high) / 2

    # AI 成本占传统团队比例：最乐观 = ai_low/traditional_high；最保守 = ai_high/traditional_low
    share_min = ai_low / traditional_high
    share_max = ai_high / traditional_low
    compression_min = 1 - share_max  # 压缩率下限
    compression_max = 1 - share_min  # 压缩率上限

    roles_traditional = [
        "产品经理", "全栈工程师", "UI/UX设计师", "营销专员",
        "客服", "财务/行政"
    ]
    roles_ai_replacement = [
        "AI产品规划(大模型对话工具)", "AI辅助编码(AI编程工具)",
        "AI设计(AI设计工具)", "AI营销(AI文案/投放工具)",
        "AI客服(自动化)", "AI财务(自动化工具)"
    ]
    annual_saving_low = (traditional_low - ai_high) * 12
    annual_saving_high = (traditional_high - ai_low) * 12

    return {
        "model_type": "compare",
        "currency": currency,
        "note": "行业典型估算区间，非官方统计；实际成本以所选工具与人力定价为准",
        "traditional_team": {
            "monthly_cost_low": traditional_low,
            "monthly_cost_high": traditional_high,
            "monthly_cost_mid": round(trad_mid, 2),
            "annual_cost_mid": round(trad_mid * 12, 2),
            "headcount": len(roles_traditional),
            "roles": roles_traditional
        },
        "ai_driven_solo": {
            "monthly_cost_low": ai_low,
            "monthly_cost_high": ai_high,
            "monthly_cost_mid": round(ai_mid, 2),
            "annual_cost_mid": round(ai_mid * 12, 2),
            "headcount": 1,
            "tools": roles_ai_replacement
        },
        "cost_compression": {
            "rate_low": f"{compression_min:.1%}",
            "rate_high": f"{compression_max:.1%}",
            "description": (
                f"AI驱动单人月成本为传统团队的{share_min:.1%}-{share_max:.1%}，"
                f"成本压缩约{compression_min:.1%}-{compression_max:.1%}"
            )
        },
        "annual_savings": {
            "low": round(annual_saving_low, 2),
            "high": round(annual_saving_high, 2),
            "description": f"年节省约{round(annual_saving_low, 2)}-{round(annual_saving_high, 2)}{currency}"
        },
        "recommendations": [
            f"AI工具月成本约{ai_low}-{ai_high}{currency}，可替代月成本约"
            f"{traditional_low}-{traditional_high}{currency}的传统基础团队，适合一人公司轻量化启动",
            "初期用AI替代非核心职能（客服/财务/营销），核心产品决策保留人工",
            "随营收增长逐步引入兼职/外包填补AI短板，保持成本结构优势",
            "定期评估AI工具投入产出，淘汰低效工具，把预算集中到高产工具"
        ]
    }


def _validate_compare_inputs(traditional_low, traditional_high, ai_low, ai_high):
    """对比模型入参校验。"""
    if traditional_low <= 0 or traditional_high <= 0 or ai_low < 0 or ai_high < 0:
        return "成本参数不能为负数，且传统团队成本必须大于0"
    if traditional_low > traditional_high:
        return "传统团队成本下限不能高于上限"
    if ai_low > ai_high:
        return "AI成本下限不能高于上限"
    if ai_high >= traditional_low:
        return "AI成本上限已不低于传统团队成本下限，无法构成有效对比，请检查参数"
    return None


def calculate_one_time_model(
    fixed_costs, variable_costs, price,
    conservative, moderate, optimistic, currency
):
    """一次性购买模型计算。"""
    if price <= 0:
        return {"error": "单价必须大于0"}
    if variable_costs < 0 or fixed_costs < 0:
        return {"error": "成本不能为负数"}
    if price <= variable_costs:
        return {"error": f"单价({price})必须大于单位变动成本({variable_costs})，否则每卖一件都亏损"}
    err = _validate_scenarios(conservative, moderate, optimistic)
    if err:
        return {"error": err}

    margin_per_unit = price - variable_costs
    margin_rate = margin_per_unit / price
    breakeven_units = fixed_costs / margin_per_unit
    breakeven_revenue = breakeven_units * price

    scenarios = {}
    for name, units in (("conservative", conservative), ("moderate", moderate), ("optimistic", optimistic)):
        revenue = price * units
        total_cost = fixed_costs + variable_costs * units
        gross_profit = revenue - total_cost
        net_margin = gross_profit / revenue if revenue > 0 else 0
        scenarios[name] = {
            "monthly": {
                "units": units,
                "revenue": round(revenue, 2),
                "total_cost": round(total_cost, 2),
                "gross_profit": round(gross_profit, 2),
                "net_margin": f"{net_margin:.1%}"
            },
            "annual": {
                "units": units * 12,
                "revenue": round(revenue * 12, 2),
                "total_cost": round(total_cost * 12, 2),
                "gross_profit": round(gross_profit * 12, 2),
                "net_margin": f"{net_margin:.1%}"
            }
        }

    moderate_revenue = price * moderate
    safety_margin = (moderate_revenue - breakeven_revenue) / moderate_revenue if moderate_revenue > 0 else 0

    targets = {}
    for tier_id, t_income in PROFIT_TARGET_TIERS:
        req_units = (fixed_costs + t_income) / margin_per_unit
        targets[tier_id] = {
            "target_monthly_profit": t_income,
            "currency": currency,
            "required_units": round(req_units, 1),
            "required_revenue": round(req_units * price, 2)
        }

    return {
        "model_type": "one_time",
        "currency": currency,
        "inputs": {
            "fixed_costs_monthly": fixed_costs,
            "variable_costs_per_unit": variable_costs,
            "price_per_unit": price,
            "margin_per_unit": round(margin_per_unit, 2),
            "margin_rate": f"{margin_rate:.1%}"
        },
        "breakeven": {
            "units": round(breakeven_units, 1),
            "revenue": round(breakeven_revenue, 2),
            "description": f"每月需卖出{round(breakeven_units, 1)}件，月收入达到{round(breakeven_revenue, 2)}{currency}即可盈亏平衡"
        },
        "scenarios": scenarios,
        "safety_margin": {
            "rate": f"{safety_margin:.1%}",
            "description": _safety_desc(safety_margin, moderate)
        },
        "profit_targets": targets,
        "recommendations": _generate_recommendations(margin_rate, safety_margin, breakeven_units, moderate)
    }


def calculate_subscription_model(
    fixed_costs, variable_costs_per_user, monthly_price,
    conservative, moderate, optimistic,
    monthly_churn_rate, currency, cac=0
):
    """订阅制/SaaS模型计算。"""
    if monthly_price <= 0:
        return {"error": "月费必须大于0"}
    if variable_costs_per_user < 0 or fixed_costs < 0 or cac < 0:
        return {"error": "成本/获客成本不能为负数"}
    if monthly_price <= variable_costs_per_user:
        return {"error": f"月费({monthly_price})必须大于每用户变动成本({variable_costs_per_user})"}
    err = _validate_scenarios(conservative, moderate, optimistic)
    if err:
        return {"error": err}
    churn, churn_err = _normalize_churn(monthly_churn_rate)
    if churn_err:
        return {"error": churn_err}

    margin_per_user = monthly_price - variable_costs_per_user
    margin_rate = margin_per_user / monthly_price
    # LTV = 单用户边际贡献 / 月流失率
    ltv = margin_per_user / churn
    # 盈亏平衡: 固定成本 / 单用户边际贡献 = 需要的付费用户数
    breakeven_users = fixed_costs / margin_per_user

    scenarios = {}
    for name, total_users in (("conservative", conservative), ("moderate", moderate), ("optimistic", optimistic)):
        monthly_revenue = monthly_price * total_users
        monthly_cost = fixed_costs + variable_costs_per_user * total_users
        monthly_profit = monthly_revenue - monthly_cost
        net_margin = monthly_profit / monthly_revenue if monthly_revenue > 0 else 0
        monthly_new_needed = total_users * churn
        annual_revenue = monthly_revenue * 12
        annual_profit = monthly_profit * 12
        # 首年累计获取量近似：期末净增 total_users + 线性增长期累计流失补充
        # 线性增长下第 t 月规模约为 total_users*t/12，全年流失合计 churn*total_users*Σ(t/12,t=1..12)=churn*total_users*6.5
        first_year_acquisitions = round(total_users + total_users * churn * 6.5)

        scenarios[name] = {
            "monthly": {
                "active_users": total_users,
                "mrr": round(monthly_revenue, 2),
                "total_cost": round(monthly_cost, 2),
                "monthly_profit": round(monthly_profit, 2),
                "net_margin": f"{net_margin:.1%}",
                "new_users_needed": round(monthly_new_needed, 1)
            },
            "annual": {
                "revenue": round(annual_revenue, 2),
                "profit": round(annual_profit, 2),
                "net_margin": f"{net_margin:.1%}",
                "total_acquisitions_needed": first_year_acquisitions,
                "note": "首年累计获取量为线性增长近似估算，非精确金融指标，以实际运营数据为准"
            }
        }

    moderate_mrr = monthly_price * moderate
    breakeven_mrr = breakeven_users * monthly_price
    safety_margin = (moderate_mrr - breakeven_mrr) / moderate_mrr if moderate_mrr > 0 else 0

    targets = {}
    for tier_id, t_mrr in PROFIT_TARGET_TIERS:
        req_users = (fixed_costs + t_mrr) / margin_per_user
        targets[tier_id] = {
            "target_monthly_mrr": t_mrr,
            "currency": currency,
            "required_users": round(req_users, 1),
            "required_arr": round(t_mrr * 12, 2)
        }

    return {
        "model_type": "subscription",
        "currency": currency,
        "inputs": {
            "fixed_costs_monthly": fixed_costs,
            "variable_costs_per_user_monthly": variable_costs_per_user,
            "monthly_price": monthly_price,
            "monthly_churn_rate": f"{churn:.1%}",
            "margin_per_user": round(margin_per_user, 2),
            "margin_rate": f"{margin_rate:.1%}",
            "ltv_per_user": round(ltv, 2),
            "cac_per_user": cac,
            "cac_payback_months": round(cac / margin_per_user, 1) if cac > 0 and margin_per_user > 0 else None,
            "ltv_cac_ratio": round(ltv / cac, 1) if cac > 0 else None
        },
        "breakeven": {
            "users": round(breakeven_users, 1),
            "mrr": round(breakeven_users * monthly_price, 2),
            "description": f"需要{round(breakeven_users, 1)}个付费用户，MRR达到{round(breakeven_users * monthly_price, 2)}{currency}即可盈亏平衡"
        },
        "scenarios": scenarios,
        "safety_margin": {
            "rate": f"{safety_margin:.1%}",
            "description": _safety_desc(safety_margin, moderate)
        },
        "profit_targets": targets,
        "recommendations": _generate_subscription_recommendations(margin_rate, safety_margin, breakeven_users, moderate, churn, ltv, currency)
    }


def _generate_recommendations(margin_rate, safety_margin, breakeven, moderate):
    recs = []
    if margin_rate < 0.3:
        recs.append("毛利率偏低(<30%)，建议提高定价或降低变动成本")
    elif margin_rate > 0.7:
        recs.append("毛利率优秀(>70%)，有空间进行促销获客")
    if breakeven > moderate * 0.8:
        recs.append("盈亏平衡点接近中性预测，经营风险较高，建议优先降低固定成本")
    if safety_margin < 0.2:
        recs.append("安全边际不足，建议: 1)降低固定成本 2)提高客单价 3)增加销售渠道")
    if 0 < moderate < 10:
        recs.append("中性月销量较低，建议先验证市场需求，从小规模测试开始")
    if not recs:
        recs.append("财务模型健康，建议按中性预测执行，持续监控实际数据与预测的偏差")
    return recs


def _generate_subscription_recommendations(margin_rate, safety_margin, breakeven, moderate, churn, ltv, currency):
    recs = []
    if margin_rate < 0.5:
        recs.append("订阅毛利率偏低(<50%)，SaaS建议毛利率>70%，需优化成本结构或提高定价")
    elif margin_rate > 0.8:
        recs.append("订阅毛利率优秀(>80%)，可加大获客投入")
    if churn > 0.1:
        recs.append(f"月流失率{churn:.0%}偏高(>10%)，需重点提升留存: 优化产品价值、增加切换成本、建立社群")
    elif churn > 0.05:
        recs.append(f"月流失率{churn:.0%}中等(5-10%)，建议持续优化留存机制")
    else:
        recs.append(f"月流失率{churn:.0%}优秀(<5%)，产品粘性强")
    if ltv < 500:
        recs.append(f"LTV较低(约{round(ltv)}{currency})，建议: 1)降低流失率 2)提高客单价 3)增加增值服务")
    if breakeven > moderate * 0.8:
        recs.append("盈亏平衡用户数接近中性预测，建议降低固定成本或加速获客")
    if not recs:
        recs.append("订阅模型健康，建议聚焦获客和留存双轮驱动")
    return recs


def main():
    parser = argparse.ArgumentParser(
        description="全球一人公司创业全链路指导系统 - 财务模型计算器(支持一次性购买/订阅制/AI成本对比)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例(一次性购买):
  python scripts/financial_calculator.py --model one-time --fixed-costs 500 --variable-costs 20 --price 99 --conservative 30 --moderate 80 --optimistic 200

示例(订阅制/SaaS):
  python scripts/financial_calculator.py --model subscription --fixed-costs 2000 --variable-costs 10 --price 49 --conservative 50 --moderate 200 --optimistic 500 --churn 5

示例(AI成本对比):
  python scripts/financial_calculator.py --model compare
  python scripts/financial_calculator.py --model compare --traditional-low 30000 --traditional-high 50000 --ai-low 250 --ai-high 1000 --currency USD
        """
    )
    parser.add_argument("--model", type=str, default="one-time", choices=["one-time", "subscription", "compare"],
                        help="商业模型: one-time(一次性购买) / subscription(订阅制) / compare(AI成本对比)")
    parser.add_argument("--fixed-costs", type=float, default=0, help="月固定成本")
    parser.add_argument("--variable-costs", type=float, default=0, help="单位变动成本/每用户月成本")
    parser.add_argument("--price", type=float, default=0, help="单价/月费")
    parser.add_argument("--conservative", type=int, default=0, help="保守预测(月销量或用户数)")
    parser.add_argument("--moderate", type=int, default=0, help="中性预测(月销量或用户数)")
    parser.add_argument("--optimistic", type=int, default=0, help="乐观预测(月销量或用户数)")
    parser.add_argument("--churn", type=float, default=5,
                        help="月流失率(仅订阅制): 百分数输入如5表示5%%; 若输入0~1小数则按小数解释; 0取默认5%%")
    parser.add_argument("--cac", type=float, default=0, help="单用户获客成本(仅订阅制,用于计算CAC回本周期)")
    parser.add_argument("--traditional-low", type=float, default=30000, help="传统团队月成本下限(仅compare,默认30000)")
    parser.add_argument("--traditional-high", type=float, default=50000, help="传统团队月成本上限(仅compare,默认50000)")
    parser.add_argument("--ai-low", type=float, default=250, help="AI驱动月成本下限(仅compare,默认250)")
    parser.add_argument("--ai-high", type=float, default=1000, help="AI驱动月成本上限(仅compare,默认1000)")
    parser.add_argument("--currency", type=str, default=None,
                        help="货币单位(默认: one-time/subscription为CNY, compare为USD)")

    args = parser.parse_args()

    if args.model == "compare":
        currency = args.currency or "USD"
        result = calculate_compare_model(
            traditional_low=args.traditional_low,
            traditional_high=args.traditional_high,
            ai_low=args.ai_low,
            ai_high=args.ai_high,
            currency=currency
        )
        _emit(result)

    # 一次性 / 订阅模型的通用入参校验
    if args.fixed_costs < 0:
        _emit({"error": "固定成本不能为负数"})
    if args.variable_costs < 0:
        _emit({"error": "变动成本不能为负数"})
    if args.cac < 0:
        _emit({"error": "获客成本不能为负数"})
    if args.price <= 0:
        _emit({"error": "单价/月费必须大于0"})

    currency = args.currency or "CNY"

    if args.model == "subscription":
        result = calculate_subscription_model(
            fixed_costs=args.fixed_costs,
            variable_costs_per_user=args.variable_costs,
            monthly_price=args.price,
            conservative=args.conservative,
            moderate=args.moderate,
            optimistic=args.optimistic,
            monthly_churn_rate=args.churn,
            currency=currency,
            cac=args.cac
        )
    else:
        result = calculate_one_time_model(
            fixed_costs=args.fixed_costs,
            variable_costs=args.variable_costs,
            price=args.price,
            conservative=args.conservative,
            moderate=args.moderate,
            optimistic=args.optimistic,
            currency=currency
        )

    _emit(result)


if __name__ == "__main__":
    main()
