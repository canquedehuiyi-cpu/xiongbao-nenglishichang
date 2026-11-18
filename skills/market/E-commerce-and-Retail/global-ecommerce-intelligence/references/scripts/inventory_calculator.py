#!/usr/bin/env python3
"""inventory_calculator.py — 库存补货计算器 (v1.0.7)

基于 SOP-09 库存管理公式：
  安全库存 = Z(服务水平) × 日均销量标准差 σ × √补货周期
  补货量   = (补货周期 + 安全天数) × 日均销量 − 现有库存 − 在途库存
  库存天数 DOS = 现有库存 / 日均销量
  冗余库存判定: DOS > 90 天
口径: 模型估算，实际需结合平台补货限制(亚马逊 FBA 容量等)与促销节奏复核。

用法:
    python3 inventory_calculator.py --daily-sales 10 --lead-time 15 --safety-days 7 --on-hand 100 --json
    python3 inventory_calculator.py --daily-sales 10 --lead-time 15 --safety-days 7 --on-hand 50 --on-order 30 --service-level 95 --json
    python3 inventory_calculator.py --version

参数:
    --daily-sales    日均销量(必填, 建议取近30/60/90天加权)
    --lead-time      补货周期天数(下单到入库)
    --safety-days    安全期天数(补货周期外的缓冲)
    --on-hand        现有可售库存
    --on-order       在途库存(可选, 默认0)
    --std-dev        日均销量标准差(可选; 提供后按服务水平算安全库存)
    --service-level  服务水平: 90/95/97.5 (默认90; z=1.28/1.645/1.96)
    --json           输出JSON
"""

import argparse
import datetime
import json
import math

VERSION = "1.0.7"

Z_SCORES = {"90": 1.28, "95": 1.645, "97.5": 1.96}


def meta_fields(tool):
    return {
        "ok": True,
        "tool": tool,
        "version": VERSION,
        "schema": "global-ecommerce-intelligence/" + tool,
        "generatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    }


def main():
    parser = argparse.ArgumentParser(description="库存补货计算器 v" + VERSION)
    parser.add_argument("--daily-sales", type=float, required=True, help="日均销量")
    parser.add_argument("--lead-time", type=int, default=15, help="补货周期天数")
    parser.add_argument("--safety-days", type=int, default=7, help="安全期天数")
    parser.add_argument("--on-hand", type=float, default=0, help="现有可售库存")
    parser.add_argument("--on-order", type=float, default=0, help="在途库存")
    parser.add_argument("--std-dev", type=float, default=None, help="日均销量标准差")
    parser.add_argument("--service-level", type=str, default="90", choices=["90", "95", "97.5"], help="服务水平")
    parser.add_argument("--json", action="store_true", help="输出JSON")
    parser.add_argument("--version", action="version", version=VERSION, help="输出版本")
    args = parser.parse_args()

    if args.daily_sales <= 0:
        parser.error("--daily-sales 必须为正数")
    # 逐项校验: 负值会让安全库存的 sqrt 抛 math domain error, 或让补货量与 DOS 静默算成错误结果
    if args.lead_time < 0:
        parser.error("--lead-time 不能为负")
    if args.safety_days < 0:
        parser.error("--safety-days 不能为负")
    if args.on_hand < 0:
        parser.error("--on-hand 不能为负")
    if args.on_order < 0:
        parser.error("--on-order 不能为负")
    if args.std_dev is not None and args.std_dev < 0:
        parser.error("--std-dev 不能为负")

    z = Z_SCORES[args.service_level]
    safety_stock = None
    if args.std_dev is not None:
        safety_stock = round(z * args.std_dev * math.sqrt(args.lead_time), 1)

    # 补货量: (LT + safety_days) × 日均销量 − 现有 − 在途
    reorder_qty = max(0, round((args.lead_time + args.safety_days) * args.daily_sales - args.on_hand - args.on_order, 1))
    # 库存天数(日均销量已校验为正, 不存在除零分支)
    dos = round(args.on_hand / args.daily_sales, 1)
    # 冗余判定
    redundant = dos > 90
    # 断货风险: 现有+在途 能否覆盖 补货周期
    cover_days = round((args.on_hand + args.on_order) / args.daily_sales, 1)
    stockout_risk = cover_days < args.lead_time

    result = {
        "日均销量": args.daily_sales,
        "补货周期天数": args.lead_time,
        "安全期天数": args.safety_days,
        "现有库存": args.on_hand,
        "在途库存": args.on_order,
        "服务水平": args.service_level + "%",
        "安全库存": safety_stock if safety_stock is not None else "未提供标准差,未计算",
        "建议补货量": reorder_qty,
        "库存可售天数DOS": dos,
        "现有+在途覆盖天数": cover_days,
        "冗余库存判定": "是(>90天)" if redundant else "否",
        "断货风险": "高(覆盖天数<补货周期)" if stockout_risk else "低",
        "建议": (
            "建议下单补货 " + str(reorder_qty) + " 件" if reorder_qty > 0 else "库存充足,暂无需补货"
        ),
        "口径说明": "模型估算: 安全库存=Z×σ×√LT; 补货量=(LT+安全期)×日均销量−现有−在途; 需结合平台容量与促销复核",
    }

    if args.json:
        out = meta_fields("inventory_calculator")
        out.update({"result": result})
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print("\n库存补货分析")
        print("=" * 44)
        for k, v in result.items():
            print("  " + k + ": " + str(v))
        print("=" * 44)


if __name__ == "__main__":
    main()
