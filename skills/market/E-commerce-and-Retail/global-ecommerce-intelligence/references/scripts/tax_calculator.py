#!/usr/bin/env python3
"""tax_calculator.py — 跨境税费试算器 (v1.0.7)

按目的地税制做试算,覆盖三层成本:
  1) 流转税: 欧盟/英国/新澳日加的增值税或消费税,美国为州销售税
  2) 关税: 按目的地起征点与税率;美国按 MFN + Section 301 分层;欧盟低值包裹按 €3/税则条目
  3) 规费: 美国报关的商品处理费(MPF)与港口维护费(HMF)

事实底座(2026-09-03 联网核实,来源见各字段 source):
  - 美国: de minimis 免税已自 2025-08-29 起全球无限期暂停(EO 14324/EO 14388),
          法定 $800 条款(19 U.S.C. 1321)另由 OBBBA 定于 2027-07-01 永久废除;
          所有货值均须报关缴税,故 MPF 必计。
          FY2026 MPF: 0.3464%,下限 $33.58、上限 $651.50(90 FR 34665)。
          HMF 仅海运,0.125%,无上下限。
          Section 301 强迫劳动关税(2026-07-24 生效): 10% 档 / 12.5% 档 /
          净 MFN 上限档(欧盟与台湾 10% 上限,日本·韩国·瑞士 12.5% 上限)。
          该关税存在大范围豁免(Section 232 商品、USMCA 项下加墨免税货物、
          Annex II 豁免清单、在途货物等),命中即不适用,详见运行时提示。
  - 欧盟: Council Regulation (EU) 2026/382(2026-02-11 通过)第 1 条删除基于阈值的关税免征,
          第 2 条规定 2026-07-01 至 2028-07-01 期间,内在价值合计 ≤EUR 150 的货物按件征收 EUR 3
          过渡性关税;计量单位源间存在分歧(原文 per item in a consignment / 理事会解读 per
          category of goods),本工具按 --tariff-lines 计征并强制提示核实。
          增值税自 2021-07 起无起征点,首欧元即征。
  - 英国: £135 以下免关税、增值税由卖家或平台在销售点征收;
          HMRC 已确认该免税额最迟 2028-10 取消。关税低于 £9 不征。
  - 新加坡/澳大利亚/日本/加拿大: 起征点分别为 SGD 400 / AUD 1000 / JPY 10000 / CAD 20;
          澳、新两国的 GST 无起征点,由卖家在销售环节征收。

口径说明: 本工具为试算辅助,不构成税务或报关意见;实际申报以海关与税务机关审定为准。
金额按目的地国币种计;未提供税率参数时不做估算,按 0 计入并显式提示。

用法:
    python3 tax_calculator.py --country DE --price 100 --shipping 15 --json
    python3 tax_calculator.py --country US --state CA --price 100 --origin CN --json
    python3 tax_calculator.py --country US --state NY --price 700 --duty-rate 5 --origin VN --transport ocean --json
    python3 tax_calculator.py --version

参数:
    --country       目的地: US/UK/DE/FR/IT/ES/NL/SG/AU/JP/CA (默认 US)
    --state         仅美国: 州代码(如 CA/NY/TX)
    --price         商品售价(不含税,目的地国币种)
    --shipping      运费(默认 0)
    --duty-rate     最惠国(MFN/Column 1)从价税率 %(按 HS/HTS 编码确定;不传按 0 计入并提示)
    --origin        原产国 ISO 3166-1 alpha-2(美国计 Section 301 分层所需)
    --extra-duty    叠加的贸易救济从价税率 %(如 Section 301 品类清单、Section 232;可多次不适用时留空)
    --transport     运输方式: air/ocean/truck/rail(美国计 HMF 所需,默认 air)
    --tariff-lines  欧盟 ≤€150 包裹的税则条目数(默认 1,每个条目 €3)
    --json          输出 JSON
"""

import argparse
import datetime
import json
from decimal import Decimal, ROUND_HALF_UP

VERSION = "1.0.7"
FACT_VERIFIED = "2026-09-03"

# 标准档增值税 / 消费税 / GST (%)
VAT_RATES = {
    "UK": {"rate": 20, "name": "英国进口增值税(Import VAT)"},
    "DE": {"rate": 19, "name": "德国增值税(Mehrwertsteuer)"},
    "FR": {"rate": 20, "name": "法国增值税(TVA)"},
    "IT": {"rate": 22, "name": "意大利增值税(IVA)"},
    "ES": {"rate": 21, "name": "西班牙增值税(IVA)"},
    "NL": {"rate": 21, "name": "荷兰增值税(BTW)"},
    "SG": {"rate": 9, "name": "新加坡商品服务税(GST)"},
    "AU": {"rate": 10, "name": "澳大利亚商品服务税(GST)"},
    "JP": {"rate": 10, "name": "日本消费税"},
    "CA": {"rate": 5, "name": "加拿大联邦商品服务税(GST,省税另计)"},
}

# 美国州级销售税率基准 (%);地方税另加,需按收货地复核
US_STATE_RATES = {
    "CA": 7.25, "TX": 6.25, "NY": 4.0, "FL": 6.0, "IL": 6.25, "PA": 6.0,
    "OH": 5.75, "GA": 4.0, "NC": 4.75, "MI": 6.0, "WA": 6.5, "AZ": 5.6,
    "CO": 2.9, "MA": 6.25, "VA": 5.3, "TN": 7.0, "MD": 6.0, "WI": 5.0,
    "MN": 6.875, "IN": 7.0, "SC": 6.0, "KY": 6.0, "OR": 0.0, "MT": 0.0,
    "NH": 0.0, "DE": 0.0, "AK": 0.0,
}

# 目的地进口税制
IMPORT_RULES = {
    "US": {
        "currency": "USD",
        "duty_threshold": None,
        "duty_threshold_note": "美国 de minimis 免税已自 2025-08-29 起全球无限期暂停,所有货值均须报关缴税",
        "formal_entry_threshold": 2500.0,
        "default_duty_rate": None,
    },
    "UK": {
        "currency": "GBP",
        "duty_threshold": 135.0,
        "duty_threshold_note": "£135 以下免关税(增值税仍在销售点征收);HMRC 已确认该免税额最迟 2028-10 取消",
        "duty_min_amount": 9.0,
        "default_duty_rate": 4.0,
    },
    "DE": {"currency": "EUR", "duty_threshold": None, "eu_low_value": True, "default_duty_rate": 4.5},
    "FR": {"currency": "EUR", "duty_threshold": None, "eu_low_value": True, "default_duty_rate": 4.5},
    "IT": {"currency": "EUR", "duty_threshold": None, "eu_low_value": True, "default_duty_rate": 4.5},
    "ES": {"currency": "EUR", "duty_threshold": None, "eu_low_value": True, "default_duty_rate": 4.5},
    "NL": {"currency": "EUR", "duty_threshold": None, "eu_low_value": True, "default_duty_rate": 4.5},
    # tax_threshold_exempt=True: 起征点同时免除关税与流转税(日本、加拿大属此类)
    "SG": {"currency": "SGD", "duty_threshold": 400.0, "default_duty_rate": 0.0},
    "AU": {"currency": "AUD", "duty_threshold": 1000.0, "default_duty_rate": 5.0},
    "JP": {"currency": "JPY", "duty_threshold": 10000.0, "default_duty_rate": 3.0,
           "tax_threshold_exempt": True},
    "CA": {"currency": "CAD", "duty_threshold": 20.0, "default_duty_rate": 5.0,
           "tax_threshold_exempt": True},
}

# 欧盟低值包裹过渡性定额关税(Council Regulation (EU) 2026/382,2026-02-11 通过)
# 法规第 2 条原文: "From 1 July 2026 until 1 July 2028, a customs duty of EUR 3
# per item in a consignment the intrinsic value of which does not exceed a total
# of EUR 150 shall apply instead of the relief eliminated pursuant to Article 1".
# 计量单位存在源间分歧: 法规字面为 per item in a consignment(每件),
# 欧盟理事会官方解读页为 per category of goods(每商品类别)。
# 本工具默认采用理事会解读(每类别),并强制输出该分歧提示,由使用者按清关口岸口径确认。
EU_LOW_VALUE_DUTY = {
    "threshold": 150.0,
    "flat_per_tariff_line": 3.0,
    "currency": "EUR",
    "adopted_on": "2026-02-11",
    "valid_from": "2026-07-01",
    "valid_until": "2028-07-01",
    "note": "欧盟基于阈值的关税免征已由 Council Regulation (EU) 2026/382 第 1 条删除;第 2 条规定 2026-07-01 至 2028-07-01 期间,内在价值合计不超过 EUR 150 的货物按件征收 EUR 3 关税",
}

# 美国 Section 301 强迫劳动关税分档(2026-07-24 生效)
US_301_FL_RATE_10 = {"AR", "BD", "KH", "CA", "EC", "SV", "GT", "HN", "IN", "ID",
                     "JO", "MY", "MX", "PK", "LK", "TT", "GB"}
EU_MEMBER_CODES = {"AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE",
                   "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT",
                   "RO", "SK", "SI", "ES", "SE"}
US_301_FL_CAP_10 = EU_MEMBER_CODES | {"TW"}
US_301_FL_CAP_125 = {"JP", "KR", "CH"}

# FY2026 美国报关规费(2025-10-01 起,90 FR 34665)
US_MPF = {
    "rate": 0.3464,
    "min": 33.58,
    "max": 651.50,
    "informal": {"automated": 2.69, "manual": 8.06, "cbp_prepared": 12.09},
}
US_HMF_RATE = 0.125  # 仅海运

# 配置一致性自检: 美国无增值税(以州销售税替代),其余目的地必须在两表中齐备。
# 置于模块载入期执行,使两表一旦不同步立即失败,而非在运行中抛出 KeyError。
_MISSING_VAT = sorted(set(IMPORT_RULES) - {"US"} - set(VAT_RATES))
if _MISSING_VAT:
    raise RuntimeError(
        "税务配置不一致: 以下辖区缺少流转税税率,请同步 VAT_RATES 与 IMPORT_RULES: "
        + ", ".join(_MISSING_VAT)
    )

SOURCES = [
    "美国 de minimis 暂停: EO 14324 / EO 14388 / CBP 公告",
    "美国 MPF 与 HMF: CBP 用户费表 FY2026 (90 FR 34665);19 CFR 24.22 / 24.24",
    "美国 Section 301 强迫劳动关税: USTR 2026-07-23 公告(Federal Register 文号 2026-15181),2026-07-24 生效",
    "美国 Section 301 强迫劳动关税豁免范围: 同一公告 Annex II 的 15 份豁免清单与 U.S. Note 52(含 Section 232 商品、USMCA 项下加墨免税货物等)",
    "欧盟低值包裹: Council Regulation (EU) 2026/382,2026-07-01 生效",
    "英国低值进口免税额: HMRC 2026-07-13 政策文件,最迟 2028-10 取消",
    "标准增值税率: 各目的地税务机关公布的标准档税率",
]


def format_amount(value, currency):
    """按币种格式化金额

    整数不带小数(避免 10000.0 这类冗余输出);不使用 %g,以免大数值退化为
    科学计数法(如 1234567 显示成 1.23457e+06)。
    """
    text = ("%.2f" % value).rstrip("0").rstrip(".")
    return (text or "0") + " " + currency


def money(value):
    """金额取两位小数(四舍五入)

    不用 float 直接 round: 二进制浮点会把 7.975 舍成 7.97 而非 7.98。
    """
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def meta_fields(tool):
    return {
        "ok": True,
        "tool": tool,
        "version": VERSION,
        "schema": "global-ecommerce-intelligence/" + tool,
        "generatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    }


def us_section_301_fl(origin, mfn_rate):
    """返回 (档位说明, 税率%) ;无法判定时返回 (说明, None)"""
    if not origin:
        return ("未提供 --origin,未计入 Section 301 强迫劳动关税", None)
    code = origin.upper()
    if code in US_301_FL_RATE_10:
        return ("Section 301 强迫劳动关税 10% 档", 10.0)
    if code in US_301_FL_CAP_10:
        rate = max(0.0, 10.0 - mfn_rate)
        return ("Section 301 强迫劳动关税:净 MFN 上限 10% 档(上限 − MFN)", round(rate, 4))
    if code in US_301_FL_CAP_125:
        rate = max(0.0, 12.5 - mfn_rate)
        return ("Section 301 强迫劳动关税:净 MFN 上限 12.5% 档(上限 − MFN)", round(rate, 4))
    return ("Section 301 强迫劳动关税 12.5% 档(其余被调查经济体)", 12.5)


def us_fees(entered_value, transport):
    """美国报关规费: MPF 与 HMF"""
    formal = entered_value > IMPORT_RULES["US"]["formal_entry_threshold"]
    if formal:
        mpf = money(entered_value * US_MPF["rate"] / 100)
        mpf = max(US_MPF["min"], min(US_MPF["max"], mpf))
        mpf_note = (
            "正式报关: 0.3464% 从价,受 FY2026 下限 $33.58 / 上限 $651.50 约束"
        )
    else:
        mpf = US_MPF["informal"]["automated"]
        mpf_note = "非正式报关(货值 ≤ $2,500): 电子申报固定费 $2.69"
    if transport == "ocean":
        hmf = money(entered_value * US_HMF_RATE / 100)
        hmf_note = "海运港口维护费 0.125%,无上下限"
    else:
        hmf = 0.0
        hmf_note = "非海运,不计港口维护费(HMF 仅海运)"
    return {"mpf": mpf, "mpf_note": mpf_note, "hmf": hmf, "hmf_note": hmf_note, "formal": formal}


def main():
    parser = argparse.ArgumentParser(description="跨境税费试算器 v" + VERSION)
    parser.add_argument("--country", default="US", help="目的地代码")
    parser.add_argument("--state", default=None, help="美国州代码")
    parser.add_argument("--price", type=float, required=True, help="商品售价(目的地国币种)")
    parser.add_argument("--shipping", type=float, default=0, help="运费")
    parser.add_argument("--duty-rate", type=float, default=None, help="最惠国(MFN)从价税率%%")
    parser.add_argument("--origin", default=None, help="原产国 ISO 3166-1 alpha-2")
    parser.add_argument("--extra-duty", type=float, default=0, help="叠加的贸易救济从价税率%%")
    parser.add_argument("--transport", default="air", choices=["air", "ocean", "truck", "rail"],
                        help="运输方式(美国计 HMF 所需)")
    parser.add_argument("--tariff-lines", type=int, default=1, help="欧盟 ≤€150 包裹的税则条目数")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument("--version", action="version", version=VERSION, help="输出版本")
    args = parser.parse_args()

    if args.price < 0 or args.shipping < 0:
        parser.error("--price/--shipping 不能为负")
    if args.tariff_lines < 1:
        parser.error("--tariff-lines 至少为 1")
    if args.duty_rate is not None and args.duty_rate < 0:
        parser.error("--duty-rate 不能为负")
    if args.extra_duty < 0:
        parser.error("--extra-duty 不能为负")

    country = args.country.upper()
    rules = IMPORT_RULES.get(country)
    if rules is None:
        parser.error("未支持目的地: " + country + " (支持: " + ", ".join(sorted(IMPORT_RULES)) + ")")

    base = money(args.price + args.shipping)
    warnings = []

    # ── 1) 流转税 ─────────────────────────────────────────────
    if country == "US":
        if not args.state:
            parser.error("美国销售税需指定 --state (如 CA/NY/TX)")
        rate = US_STATE_RATES.get(args.state.upper())
        if rate is None:
            parser.error(
                "未收录的美国州代码: " + args.state +
                " (已收录: " + ", ".join(sorted(US_STATE_RATES)) + ")"
            )
        tax = {
            "类型": "美国州销售税",
            "税率": rate,
            "金额": money(base * rate / 100),
            "征收环节": "销售环节(州级基准,地方税另加)",
        }
        warnings.append("美国州税为州级基准,实际按收货地叠加地方税,需按邮编级税率复核")
    else:
        vat = VAT_RATES[country]
        threshold = rules.get("duty_threshold")
        # 日本与加拿大的起征点同时免除关税与流转税
        tax_exempt = bool(rules.get("tax_threshold_exempt")) and threshold is not None and base <= threshold
        if tax_exempt:
            stage = "免征(计税价值 ≤ " + format_amount(threshold, rules["currency"]) + ")"
        elif country == "UK" and threshold is not None and base <= threshold:
            stage = "销售环节(≤£135 由卖家或平台代收)"
        elif country == "SG":
            stage = "销售或进口环节(空运/邮政低值商品自 2023-01-01 起取消 GST 减免)"
        elif country == "AU":
            stage = "销售或进口环节(GST 无起征点,由卖家在销售环节征收)"
        else:
            stage = "进口环节"
        tax = {
            "类型": vat["name"],
            "税率": 0.0 if tax_exempt else vat["rate"],
            "金额": 0.0 if tax_exempt else money(base * vat["rate"] / 100),
            "征收环节": stage,
        }
        if country == "CA":
            warnings.append("加拿大 GST 为联邦 5%,多数省份另有省税(PST/HST),需按收货省叠加")
        if country == "SG":
            warnings.append("新加坡 SGD 400 门槛的适用取决于运输方式与卖家 GST 注册状态,需复核")

    # ── 2) 关税 ───────────────────────────────────────────────
    duty_breakdown = []
    tariff_lines_used = False
    if country == "US":
        mfn = args.duty_rate if args.duty_rate is not None else 0.0
        if args.duty_rate is None:
            warnings.append("未提供 --duty-rate,最惠国税率按 0 计入;实际须按 10 位 HTS 编码确定")
        fl_note, fl_rate = us_section_301_fl(args.origin, mfn)
        if fl_rate is None:
            warnings.append(fl_note)
        else:
            duty_breakdown.append({"项目": fl_note, "税率": fl_rate})
            warnings.append(
                "Section 301 强迫劳动关税存在大范围豁免,命中任一项即不适用本项关税,申报前须逐项核对: "
                "(1) 受 Section 232 约束的商品(钢铝铜及其制品、汽车与零部件、中重型车辆、木材与木制品、半导体等)已明确排除,"
                "且本次 301 关税与 232 关税互不叠加; "
                "(2) 加拿大与墨西哥在 USMCA 项下免税入境的货物; "
                "(3) 公告 Annex II 的豁免清单(通用税号清单及各经济体专属清单); "
                "(4) 2026-07-24 前已装船且在途、并于 2026-07-28 前完成报关的货物"
            )
        duty_breakdown.insert(0, {"项目": "最惠国税率(MFN/Column 1)", "税率": mfn})
        if args.extra_duty:
            duty_breakdown.append({"项目": "叠加的贸易救济税率(Section 301 品类 / Section 232 等)", "税率": args.extra_duty})
            warnings.append(
                "已按 --extra-duty=" + str(args.extra_duty) + "% 叠加计征: 须确认该税率与上述 Section 301 关税不重复。"
                "Section 232 关税与本次 301 关税互不叠加(232 商品已排除在 301 范围之外),若在此传入 232 税率会造成重复计征"
            )
        total_rate = sum(x["税率"] for x in duty_breakdown)
        duty_amount = money(base * total_rate / 100)
        duty_note = (
            "美国 de minimis 免税已暂停,全部货值须报关缴税;"
            "税率为各层叠加,实际以 HTS 归类与原产地为准"
        )
    elif rules.get("eu_low_value"):
        if base <= EU_LOW_VALUE_DUTY["threshold"]:
            duty_amount = money(EU_LOW_VALUE_DUTY["flat_per_tariff_line"] * args.tariff_lines)
            tariff_lines_used = True
            duty_breakdown = [{
                "项目": "欧盟低值包裹过渡性定额关税(€3 × 计征单位数)",
                "税率": None,
                "计征单位数": args.tariff_lines,
            }]
            duty_note = EU_LOW_VALUE_DUTY["note"]
            warnings.append(
                "计量单位口径分歧: 法规原文为 per item in a consignment(每件),"
                "欧盟理事会官方解读为 per category of goods(每商品类别);"
                "本结果按 --tariff-lines 指定的计征单位数计算,申报前须按清关口岸执行口径确认"
            )
        else:
            mfn = args.duty_rate if args.duty_rate is not None else rules["default_duty_rate"]
            total_rate = mfn + args.extra_duty
            duty_amount = money(base * total_rate / 100)
            duty_breakdown = [
                {"项目": "最惠国从价税率", "税率": mfn},
            ]
            if args.extra_duty:
                duty_breakdown.append({"项目": "叠加税率", "税率": args.extra_duty})
            duty_note = "> €150 按税则归类征收从价关税;增值税另计"
        if args.duty_rate is None and base > EU_LOW_VALUE_DUTY["threshold"]:
            warnings.append("未提供 --duty-rate,按该目的地默认参考税率计入,实际须按 HS 编码确定")
    else:
        threshold = rules["duty_threshold"]
        if threshold is not None and base <= threshold:
            duty_amount = 0.0
            duty_breakdown = [{"项目": "未达关税起征点", "税率": 0.0}]
            duty_note = rules.get("duty_threshold_note", "未达起征点")
        else:
            mfn = args.duty_rate if args.duty_rate is not None else rules["default_duty_rate"]
            total_rate = mfn + args.extra_duty
            duty_amount = money(base * total_rate / 100)
            duty_breakdown = [{"项目": "最惠国从价税率", "税率": mfn}]
            if args.extra_duty:
                duty_breakdown.append({"项目": "叠加税率", "税率": args.extra_duty})
            min_amount = rules.get("duty_min_amount")
            if min_amount is not None and 0 < duty_amount < min_amount:
                duty_note = (
                    "计算的关税低于 " + str(min_amount) + " " + rules["currency"] +
                    ",按当地规则不予征收,已置 0"
                )
                duty_amount = 0.0
            else:
                duty_note = "实际以 HS 归类与海关审定为准"
            if args.duty_rate is None:
                warnings.append("未提供 --duty-rate,按该目的地默认参考税率计入,实际须按 HS 编码确定")
        extra_note = rules.get("duty_threshold_note")
        if extra_note:
            duty_note += "；" + extra_note

    # ── 3) 规费 ───────────────────────────────────────────────
    if country == "US":
        fees = us_fees(base, args.transport)
        fee_block = {
            "商品处理费(MPF)": fees["mpf"],
            "MPF 说明": fees["mpf_note"],
            "港口维护费(HMF)": fees["hmf"],
            "HMF 说明": fees["hmf_note"],
            "报关类型": "正式报关" if fees["formal"] else "非正式报关",
        }
        fee_total = fees["mpf"] + fees["hmf"]
    else:
        fee_block = {"说明": "该目的地不计入美国报关规费"}
        fee_total = 0.0

    # ── 4) 参数适用性回执: 避免用户传入的参数被静默忽略却不自知 ──
    if args.tariff_lines != 1 and not tariff_lines_used:
        warnings.append(
            "已忽略 --tariff-lines=" + str(args.tariff_lines) +
            ": 该参数仅用于欧盟内在价值合计 ≤ EUR 150 的包裹定额关税计征,当前目的地或计税价值不适用"
        )

    total = money(args.price + args.shipping + tax["金额"] + duty_amount + fee_total)

    result = {
        "目的地": country,
        "币种": rules["currency"],
        "美国州": args.state.upper() if (country == "US" and args.state) else None,
        "原产国": args.origin.upper() if args.origin else None,
        "运输方式": args.transport,
        "商品售价": args.price,
        "运费": args.shipping,
        "计税基数": base,
        "流转税": tax,
        "关税金额": duty_amount,
        "关税明细": duty_breakdown,
        "关税说明": duty_note,
        "规费": fee_block,
        "规费合计": fee_total,
        "到岸总成本": total,
        "数据时效": {
            "核实日期": FACT_VERIFIED,
            "波动提示": "美国关税政策处于诉讼与调整高频期,申报前须以 CBP/USTR 最新公告为准",
        },
        "核实提示": warnings,
        "口径说明": "试算辅助:不构成税务或报关意见;增值税按标准档,美国州税为州级基准,关税按所传税率;实际以海关与税务机关审定为准",
    }

    if args.json:
        out = meta_fields("tax_calculator")
        out["sources"] = SOURCES
        out["result"] = result
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return

    print("\n跨境税费试算")
    print("=" * 52)
    for k, v in result.items():
        if k in ("关税明细", "数据时效", "核实提示"):
            continue
        print("  " + k + ": " + str(v))
    print("  关税明细:")
    for item in duty_breakdown:
        print("    - " + str(item))
    if warnings:
        print("  核实提示:")
        for w in warnings:
            print("    - " + w)
    print("  事实核实日期: " + FACT_VERIFIED)
    print("=" * 52)


if __name__ == "__main__":
    main()
