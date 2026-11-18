"""multi-strategy-quant-research-pro v1.1.2 扩展数据层。

提供东方财富公开API的扩展数据接口：
- 分钟K线（1/5/15/30/60分钟）
- 财务三表（资产负债表/利润表/现金流量表）
- 龙虎榜数据
- 融资融券数据
- 北向资金持股
- 分红历史
- 股东人数变化

所有数据来自东方财富公开HTTP接口，无需认证，零外部依赖。
缺失字段如实返回None，不伪造数据。
"""

from typing import Optional

from ._http import http_get, kline_get, safe_float

DATACENTER_BASE = "https://datacenter-web.eastmoney.com/api/data/v1/get"

def _safe_get(url: str, params: dict):
    """请求并解析JSON；网络/解析失败如实返回 None（不伪造、不抛出中断调用方）。"""
    try:
        return http_get(url, params).json()
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════
# 分钟K线
# ══════════════════════════════════════════════════════════════

def fetch_minute_kline(code: str, period: int = 5, count: int = 240,
                       market_code: Optional[str] = None) -> list:
    """获取分钟K线数据。

    Args:
        code: 股票代码，如 '600519'
        period: 分钟周期，可选 1/5/15/30/60
        count: 获取条数
        market_code: 市场代码 '1'=沪 '0'=深/北，自动推断

    Returns:
        list[dict]: 分钟K线列表，每根含 date/time/open/high/low/close/volume/amount
    """
    if market_code is None:
        market_code = "1" if code.startswith(("6", "9")) else "0"

    secid = f"{market_code}.{code}"
    params = {
        "secid": secid,
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58",
        "klt": str(period),
        "fqt": "1",  # 前复权
        "end": "20500101",
        "lmt": str(count),
    }

    data = kline_get("/api/qt/stock/kline/get", params)
    if not data or not data.get("data"):
        return []

    klines = data["data"].get("klines", [])
    result = []
    for line in klines:
        parts = line.split(",")
        if len(parts) < 7:
            continue
        try:
            result.append({
                "datetime": parts[0],
                "open": safe_float(parts[1]),
                "close": safe_float(parts[2]),
                "high": safe_float(parts[3]),
                "low": safe_float(parts[4]),
                "volume": safe_float(parts[5]),
                "amount": safe_float(parts[6]),
                "amplitude": safe_float(parts[7]) if len(parts) > 7 else 0.0,
            })
        except (ValueError, TypeError, IndexError):
            # 单行异常（占位符/缺列）跳过，不中断整段解析
            continue
    return result


# ══════════════════════════════════════════════════════════════
# 财务三表
# ══════════════════════════════════════════════════════════════

def _fetch_financial_report(code: str, report_name: str, page_size: int = 5) -> list:
    """通用财务报表获取。"""
    params = {
        "reportName": report_name,
        "columns": "ALL",
        "filter": f'(SECURITY_CODE="{code}")',
        "pageNumber": "1",
        "pageSize": str(page_size),
        "sortTypes": "-1",
        "sortColumns": "REPORT_DATE",
        "source": "WEB",
        "client": "WEB",
    }
    data = _safe_get(DATACENTER_BASE, params)
    if not data or not data.get("result"):
        return []
    return data["result"].get("data", [])


def fetch_balance_sheet(code: str, page_size: int = 5) -> list:
    """获取资产负债表（最近N期）。"""
    return _fetch_financial_report(code, "RPT_DMSK_FN_BALANCE", page_size)


def fetch_income_statement(code: str, page_size: int = 5) -> list:
    """获取利润表（最近N期）。"""
    return _fetch_financial_report(code, "RPT_DMSK_FN_INCOME", page_size)


def fetch_cashflow_statement(code: str, page_size: int = 5) -> list:
    """获取现金流量表（最近N期）。"""
    return _fetch_financial_report(code, "RPT_DMSK_FN_CASHFLOW", page_size)


# ══════════════════════════════════════════════════════════════
# 龙虎榜
# ══════════════════════════════════════════════════════════════

def fetch_dragon_tiger(code: Optional[str] = None, days: int = 30) -> list:
    """获取龙虎榜数据。

    Args:
        code: 股票代码，None则返回最近全部龙虎榜
        days: 最近天数

    Returns:
        list[dict]: 龙虎榜记录
    """
    params = {
        "reportName": "RPT_DAILYBILLBOARD_DETAILSNEW",
        "columns": "ALL",
        "pageNumber": "1",
        "pageSize": "100",
        "sortTypes": "-1",
        "sortColumns": "TRADE_DATE",
        "source": "WEB",
        "client": "WEB",
    }
    if code:
        params["filter"] = f'(SECURITY_CODE="{code}")'

    data = _safe_get(DATACENTER_BASE, params)
    if not data or not data.get("result"):
        return []
    return data["result"].get("data", [])


# ══════════════════════════════════════════════════════════════
# 融资融券
# ══════════════════════════════════════════════════════════════

def fetch_margin_trading(code: str, days: int = 30) -> list:
    """获取个股融资融券数据。

    Args:
        code: 股票代码
        days: 最近天数

    Returns:
        list[dict]: 融资融券记录，含融资余额/融券余额/融资买入额等
    """
    params = {
        "reportName": "RPTA_WEB_RZRQ_GGMX",
        "columns": "ALL",
        "filter": f'(scode="{code}")',
        "pageNumber": "1",
        "pageSize": str(days),
        "sortTypes": "-1",
        "sortColumns": "date",
        "source": "WEB",
        "client": "WEB",
    }
    data = _safe_get(DATACENTER_BASE, params)
    if not data or not data.get("result"):
        return []
    return data["result"].get("data", [])


# ══════════════════════════════════════════════════════════════
# 北向资金持股
# ══════════════════════════════════════════════════════════════

def fetch_northbound_holding(code: str, days: int = 30) -> list:
    """获取北向资金（陆股通）持股数据。

    Args:
        code: 股票代码
        days: 最近天数

    Returns:
        list[dict]: 北向持股记录，含持股数量/持股市值/占总股本比例等
    """
    params = {
        "reportName": "RPT_MUTUAL_HOLDSTOCKNORTH_STA",
        "columns": "ALL",
        "filter": f'(SECURITY_CODE="{code}")',
        "pageNumber": "1",
        "pageSize": str(days),
        "sortTypes": "-1",
        "sortColumns": "TRADE_DATE",
        "source": "WEB",
        "client": "WEB",
    }
    data = _safe_get(DATACENTER_BASE, params)
    if not data or not data.get("result"):
        return []
    return data["result"].get("data", [])


# ══════════════════════════════════════════════════════════════
# 分红历史
# ══════════════════════════════════════════════════════════════

def fetch_dividend_history(code: str) -> list:
    """获取分红送配历史。

    Args:
        code: 股票代码

    Returns:
        list[dict]: 分红记录，含公告日/股权登记日/除权除息日/每股分红/分红率等
    """
    params = {
        "reportName": "RPT_SHAREBONUS_DET",
        "columns": "ALL",
        "filter": f'(SECURITY_CODE="{code}")',
        "pageNumber": "1",
        "pageSize": "50",
        "sortTypes": "-1",
        "sortColumns": "NOTICE_DATE",
        "source": "WEB",
        "client": "WEB",
    }
    data = _safe_get(DATACENTER_BASE, params)
    if not data or not data.get("result"):
        return []
    return data["result"].get("data", [])


# ══════════════════════════════════════════════════════════════
# 股东人数变化
# ══════════════════════════════════════════════════════════════

def fetch_shareholder_count(code: str, periods: int = 8) -> list:
    """获取股东人数变化（每期披露）。

    Args:
        code: 股票代码
        periods: 获取期数

    Returns:
        list[dict]: 股东人数记录，含股东总户数/人均持股/较上期变化等
    """
    params = {
        "reportName": "RPT_HOLDERNUMLATEST",
        "columns": "ALL",
        "filter": f'(SECURITY_CODE="{code}")',
        "pageNumber": "1",
        "pageSize": str(periods),
        "sortTypes": "-1",
        "sortColumns": "END_DATE",
        "source": "WEB",
        "client": "WEB",
    }
    data = _safe_get(DATACENTER_BASE, params)
    if not data or not data.get("result"):
        return []
    return data["result"].get("data", [])


# ══════════════════════════════════════════════════════════════
# 数据可用性汇总
# ══════════════════════════════════════════════════════════════

EXTENDED_DATA_SOURCES = {
    "minute_kline": {"name": "分钟K线", "markets": ["A股", "港股"], "status": "可用"},
    "balance_sheet": {"name": "资产负债表", "markets": ["A股", "港股", "美股"], "status": "可用"},
    "income_statement": {"name": "利润表", "markets": ["A股", "港股", "美股"], "status": "可用"},
    "cashflow_statement": {"name": "现金流量表", "markets": ["A股", "港股", "美股"], "status": "可用"},
    "dragon_tiger": {"name": "龙虎榜", "markets": ["A股"], "status": "可用"},
    "margin_trading": {"name": "融资融券", "markets": ["A股"], "status": "可用"},
    "northbound_holding": {"name": "北向资金持股", "markets": ["A股"], "status": "可用"},
    "dividend_history": {"name": "分红历史", "markets": ["A股", "港股"], "status": "可用"},
    "shareholder_count": {"name": "股东人数", "markets": ["A股"], "status": "可用"},
}
