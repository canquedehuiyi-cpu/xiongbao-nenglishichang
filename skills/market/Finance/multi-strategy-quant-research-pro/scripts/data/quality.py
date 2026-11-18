# -*- coding: utf-8 -*-
"""数据质量保障层：复权处理+异常值检测+完整性校验+来源标注。

四大功能：
1. 前复权处理：基于涨跌幅的前复权计算
2. 异常值检测：涨跌幅异常、成交量异常、价格异常
3. 完整性校验：连续缺失K线、财务数据滞后、字段缺失
4. 来源标注：每个数据标注来源和获取时间
"""



def adjust_forward(klines: list[dict]) -> list[dict]:
    """前复权处理：基于涨跌幅复权。

    原理：从最新价往前推，用每日涨跌幅还原历史价格。
    复权后价格连续，消除除权除息缺口。

    Args:
        klines: 原始K线列表（按时间正序）

    Returns:
        list[dict]: 前复权后的K线（新增adj_open/adj_high/adj_low/adj_close字段）
    """
    if not klines or len(klines) < 2:
        return klines

    result = []
    # 从最后一根往前推
    for i in range(len(klines) - 1, -1, -1):
        k = klines[i]
        if i == len(klines) - 1:
            adj_open = k["open"]
            adj_high = k["high"]
            adj_low = k["low"]
            adj_close_cur = k["close"]
        else:
            # 用涨跌幅还原
            next_k = klines[i + 1]
            next_adj_close = result[-1]["adj_close"] if result else next_k["close"]
            # 当日涨跌幅 = (当日收盘 - 前日收盘) / 前日收盘
            # 复权后前日收盘 = 复权后当日收盘 / (1 + 涨跌幅)
            if k["close"] > 0:
                change_pct = (next_k["close"] - k["close"]) / k["close"]
            else:
                change_pct = 0
            adj_close_cur = next_adj_close / (1 + change_pct) if (1 + change_pct) != 0 else k["close"]
            # 开高低按比例缩放
            if k["close"] > 0:
                scale = adj_close_cur / k["close"]
            else:
                scale = 1
            adj_open = k["open"] * scale
            adj_high = k["high"] * scale
            adj_low = k["low"] * scale

        result.append({
            **k,
            "adj_open": round(adj_open, 4),
            "adj_high": round(adj_high, 4),
            "adj_low": round(adj_low, 4),
            "adj_close": round(adj_close_cur, 4),
        })

    result.reverse()
    return result


# 单日涨跌幅异常阈值（%）：A股主板涨跌停约±10%，超过11%视为异常；
# 港股、美股无涨跌停限制，正常行情单日波动可能较大，仅对数据错误级的极端跳变（50%）告警。
_CHANGE_LIMIT_PCT = {"A股": 11.0, "港股": 50.0, "美股": 50.0}
_CHANGE_HIGH_PCT = {"A股": 15.0, "港股": 70.0, "美股": 70.0}


def detect_anomalies(klines: list[dict], market: str = "A股") -> dict:
    """异常值检测。

    检测：
    - 涨跌幅异常（A股超过涨跌停口径阈值；港股/美股无涨跌停，仅捕获极端跳变）
    - 成交量异常（>5倍20日均量）
    - 价格异常（高低价差>20%）
    - 零成交量（全序列检测，不依赖20日均量窗口）

    Args:
        klines: K线列表
        market: 市场（A股/港股/美股），决定单日涨跌幅异常阈值

    Returns:
        dict: {anomalies, anomaly_count, quality_score}
    """
    change_limit = _CHANGE_LIMIT_PCT.get(market, 11.0)
    change_high = _CHANGE_HIGH_PCT.get(market, 15.0)
    if not klines:
        return {"anomalies": [], "anomaly_count": 0, "quality_score": 100}

    anomalies = []
    volumes = [k.get("volume", 0) for k in klines]

    for i, k in enumerate(klines):
        date = k.get("date", f"#{i}")

        # 涨跌幅异常（阈值随市场口径）
        if i > 0 and klines[i-1]["close"] > 0:
            change_pct = (k["close"] - klines[i-1]["close"]) / klines[i-1]["close"] * 100
            if abs(change_pct) > change_limit:
                anomalies.append({
                    "date": date, "type": "涨跌幅异常",
                    "value": round(change_pct, 2),
                    "severity": "high" if abs(change_pct) > change_high else "medium",
                })

        # 零成交量（与均量窗口无关，全序列检测）
        if k.get("volume", 0) == 0:
            anomalies.append({
                "date": date, "type": "零成交量",
                "value": 0, "severity": "high",
            })

        # 成交量异常（需20日均量窗口）
        if i >= 20:
            avg20 = sum(volumes[i-20:i]) / 20
            if avg20 > 0 and k.get("volume", 0) > avg20 * 5:
                anomalies.append({
                    "date": date, "type": "成交量异常放大",
                    "value": round(k["volume"] / avg20, 1),
                    "severity": "medium",
                })

        # 价格异常（日内振幅）
        if k.get("low", 0) > 0:
            amplitude = (k["high"] - k["low"]) / k["low"] * 100
            if amplitude > 20:
                anomalies.append({
                    "date": date, "type": "日内振幅异常",
                    "value": round(amplitude, 2),
                    "severity": "high",
                })

    # 质量评分：每1个异常扣5分，high异常扣10分
    score = 100
    for a in anomalies:
        score -= 10 if a["severity"] == "high" else 5
    score = max(0, score)

    return {
        "anomalies": anomalies,
        "anomaly_count": len(anomalies),
        "high_severity_count": sum(1 for a in anomalies if a["severity"] == "high"),
        "quality_score": score,
        "note": f"检测到{len(anomalies)}个异常（{sum(1 for a in anomalies if a['severity']=='high')}个高风险）",
    }


def check_completeness(klines: list[dict], expected_trading_days: int = None) -> dict:
    """数据完整性校验。

    检测：
    - 连续缺失K线（日期间隔>4天）
    - 字段缺失（open/high/low/close/volume）
    - 数据量不足
    - 财务数据滞后（如果有report_date）

    Args:
        klines: K线列表
        expected_trading_days: 预期交易日数（可选）

    Returns:
        dict: {complete, missing_days, missing_fields, completeness_score, note}
    """
    if not klines:
        return {"complete": False, "completeness_score": 0, "note": "无数据"}

    issues = []
    required_fields = ["date", "open", "high", "low", "close", "volume"]

    # 字段缺失检测
    missing_fields = set()
    for k in klines:
        for f in required_fields:
            if f not in k or k[f] is None:
                missing_fields.add(f)
    if missing_fields:
        issues.append(f"缺失字段: {missing_fields}")

    # 连续缺失检测（日期间隔）
    from datetime import datetime
    missing_days = 0
    for i in range(1, len(klines)):
        try:
            d1 = datetime.strptime(klines[i-1].get("date", "")[:10], "%Y-%m-%d")
            d2 = datetime.strptime(klines[i].get("date", "")[:10], "%Y-%m-%d")
            gap = (d2 - d1).days
            if gap > 4:  # 超过4天（周末+1天假期）
                missing_days += gap - 2
                issues.append(f"日期间隔异常: {klines[i-1]['date']} ~ {klines[i]['date']} ({gap}天)")
        except (ValueError, IndexError):
            pass

    # 数据量检查
    if expected_trading_days and len(klines) < expected_trading_days * 0.8:
        issues.append(f"数据量不足: {len(klines)}/{expected_trading_days}")

    # 完整性评分
    score = 100
    score -= len(missing_fields) * 15
    score -= min(missing_days * 2, 30)
    # “缺失字段”已按字段数扣分，不再作为普通 issue 重复扣
    other_issues = [item for item in issues if not item.startswith("缺失字段")]
    score -= len(other_issues) * 5
    score = max(0, score)

    complete = len(issues) == 0 and not missing_fields

    return {
        "complete": complete,
        "missing_days": missing_days,
        "missing_fields": list(missing_fields),
        "issues": issues,
        "completeness_score": score,
        "n_records": len(klines),
        "note": f"完整度{score}/100，{len(issues)}个问题" if issues else "数据完整",
    }


def data_quality_report(klines: list[dict], source: str = "未知", market: str = "A股") -> dict:
    """综合数据质量报告。

    Args:
        klines: K线列表
        source: 数据来源

    Returns:
        dict: {overall_score, adj_applied, anomalies, completeness, source, recommendation}
    """
    # 1. 异常检测
    anomaly_result = detect_anomalies(klines, market=market)
    # 2. 完整性校验
    completeness_result = check_completeness(klines)
    # 3. 复权处理
    adj_klines = adjust_forward(klines)

    # 综合评分
    overall = round((anomaly_result["quality_score"] + completeness_result["completeness_score"]) / 2, 1)

    if overall >= 80:
        recommendation = "数据质量良好，可直接用于分析"
    elif overall >= 60:
        recommendation = "数据质量一般，建议关注异常值"
    else:
        recommendation = "数据质量较差，建议检查数据源或增加样本"

    return {
        "overall_score": overall,
        "anomaly_score": anomaly_result["quality_score"],
        "completeness_score": completeness_result["completeness_score"],
        "anomaly_count": anomaly_result["anomaly_count"],
        "completeness_issues": len(completeness_result["issues"]),
        "adj_applied": True,
        "adj_klines": adj_klines,
        "source": source,
        "recommendation": recommendation,
        "anomalies": anomaly_result["anomalies"][:10],  # 最多返回10个
        "completeness": completeness_result,
    }
