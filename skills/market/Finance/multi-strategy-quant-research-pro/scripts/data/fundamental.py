"""A股基本面数据层。

数据来源：东方财富公开财务API（datacenter-web.eastmoney.com 数据中心 + push2 行情接口）。
全部为公开数据接口，不涉及认证。

覆盖指标：
- 财务摘要：每股收益、净资产收益率(ROE)、毛利率、净利率
- 估值指标：市盈率(PE)、市净率(PB)、市销率(PS)
- 分红数据：股息率
- 成长性指标：营收增长率、净利润增长率

财务摘要统一使用 datacenter-web 数据中心 RPT_F10_FINANCE_MAINFINADATA 报表，
字段语义已用公开财报交叉验证（XSMLL=毛利率、XSJLL=净利率）。
"""

import urllib.error
from typing import Optional

from ._http import http_get, push2_get, safe_float  # 东财共享客户端（标准库实现，主/备节点故障切换+数值清洗）
from cache import KlineCacheManager  # 复用K线缓存管理器（内存+文件双层、次日15:30过期机制）

# 结果级缓存（财务摘要/估值）：与K线同策略——写入后至"下一个自然日 15:30"前有效。
# 合理性：财务摘要本身滞后1-4个月（当日刷新无意义）；估值走官方延迟节点（约3分钟延迟），
# 当日缓存对选股场景足够；重复提问（同参数同市场）直接命中缓存，显著减少网络往返与耗时。
# 真实约束：仅缓存**含真实数据**的结果（字段非全 None），网络失败的降级结果不缓存，下次重试。
_RESULT_CACHE = KlineCacheManager()


# 估值接口 secid 前缀（push2 stock/get 对三市场均返回 PE/PB/股息率等估值字段）
# - A股: 1.沪 / 0.深（按代码首位动态）
# - 港股: 116.主板 / 115.创业板（主板失败时 fallback）
# - 美股: 105.（NYSE/NASDAQ 统一）
_MARKET_SECID_PREFIX = {
    "A股": None,   # 按代码首位动态判断
    "港股": "116",
    "美股": "105",
}


def _secid_for_valuation(code: str, market: str = "A股") -> str:
    """生成指定市场标的在 push2 stock/get 接口的 secid。"""
    prefix = _MARKET_SECID_PREFIX.get(market)
    if prefix is None:
        return f"1.{code}" if code.startswith("6") else f"0.{code}"
    if market == "港股":
        return f"116.{code.strip().zfill(5)}"
    return f"{prefix}.{code}"


# 财务摘要接口：东方财富数据中心公开报表（公开报表，字段语义已交叉验证）
FINANCE_API_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"
FINANCE_REPORT_NAME = "RPT_F10_FINANCE_MAINFINADATA"
# 港股/美股财务摘要：东财数据中心 GMAININDICATOR 关键财务指标报表（公开数据）
# - 港股 RPT_HKF10_FN_GMAININDICATOR（75 字段，含 ROE_AVG/每股经营现金流等）
# - 美股 RPT_USF10_FN_GMAININDICATOR（49 字段，含 ROE_AVG/毛利率/资产负债率等）
HK_FINANCE_REPORT_NAME = "RPT_HKF10_FN_GMAININDICATOR"
US_FINANCE_REPORT_NAME = "RPT_USF10_FN_GMAININDICATOR"


def _to_secucode(code: str) -> str:
    """A股代码 → 东财 SECUCODE（600519 → 600519.SH，300750 → 300750.SZ，8开头北交所 → .BJ）。"""
    code = str(code).strip()
    if code.startswith(("6", "9")):
        return f"{code}.SH"
    if code.startswith(("4", "8")):
        return f"{code}.BJ"
    return f"{code}.SZ"


def _to_hk_us_secucode(code: str, market: str) -> str:
    """港股/美股代码 → 东财 SECUCODE。

    - 港股：5位补零 + .HK（00700 → 00700.HK）
    - 美股：优先 NASDAQ 后缀 .O（AAPL → AAPL.O）；NYSE 标的需 .N
      （BABA → BABA.N），调用方对 .O 空结果回退 .N。
    """
    code = str(code).strip()
    if market == "港股":
        return f"{code.zfill(5)}.HK"
    return f"{code}.O"


def _num(v):
    """数值清洗：缺失/占位符（None、''、'-'、'--'）如实返回 None，其余走 safe_float。

    与 safe_float 默认 0.0 的区别：坏字段不会被"伪造"成 0.0，
    下游策略以 `is not None` 判断数据缺失，避免把缺失数据当成真实 0 值。
    """
    if v is None:
        return None
    if isinstance(v, str) and v.strip() in ("", "-", "--"):
        return None
    return safe_float(v)


def fetch_financial_summary(code: str, use_cache: bool = True) -> dict:
    """获取个股财务摘要。

    来源：东方财富数据中心公开报表 RPT_F10_FINANCE_MAINFINADATA（最新报告期）。
    字段映射（交叉验证）：ROEJQ=ROE加权、EPSJB=每股收益、XSMLL=销售毛利率、
    XSJLL=销售净利率、ZCFZL=资产负债率、MGJYXJJE=每股经营现金流、
    TOTALOPERATEREVETZ=营收同比、PARENTNETPROFITTZ=归母净利润同比。

    Returns:
        dict: 含 roe/per_eps/profit_gross/net_profit_rate/debt_ratio 等字段；
        接口失败或字段缺失时如实置 None，不伪造数据。

    结果级缓存：同市场同代码当日有效（次日15:30过期，与K线缓存一致），
    仅缓存含真实数据的 result（全 None 的失败结果不缓存，下次重试）。
    """
    cached = _RESULT_CACHE.get(f"fin:A:{code}", 1) if use_cache else None
    if cached is not None:
        return cached

    result = {
        "code": code,
        "roe": None,               # 净资产收益率(%)
        "per_eps": None,            # 每股收益
        "profit_gross": None,       # 毛利率(%)
        "net_profit_rate": None,    # 净利率(%)
        "debt_ratio": None,         # 资产负债率(%)
        "revenue_growth": None,     # 营收同比(%)
        "net_profit_growth": None,  # 净利润同比(%)
        "operating_cfps": None,     # 每股经营现金流
        "report_date": None,        # 报告期日期（YYYY-MM-DD，用于如实标注财务数据滞后）
    }

    try:
        resp = http_get(
            FINANCE_API_URL,
            params={
                "reportName": FINANCE_REPORT_NAME,
                "columns": "ALL",
                "filter": f'(SECUCODE="{_to_secucode(code)}")',
                "pageNumber": "1",
                "pageSize": "1",
                "source": "HSF10",
                "client": "PC",
            },
            timeout=8,
        )
        resp.raise_for_status()
        payload = resp.json()
        rows = (payload.get("result") or {}).get("data") or []
        if not rows:
            return result
        latest = rows[0]
        result["roe"] = _num(latest.get("ROEJQ"))
        result["per_eps"] = _num(latest.get("EPSJB"))
        result["profit_gross"] = _num(latest.get("XSMLL"))
        result["net_profit_rate"] = _num(latest.get("XSJLL"))
        result["debt_ratio"] = _num(latest.get("ZCFZL"))
        result["revenue_growth"] = _num(latest.get("TOTALOPERATEREVETZ"))
        result["net_profit_growth"] = _num(latest.get("PARENTNETPROFITTZ"))
        result["operating_cfps"] = _num(latest.get("MGJYXJJE"))
        rd = latest.get("REPORT_DATE")
        if rd:
            result["report_date"] = str(rd)[:10]  # 报告期日期（如实标注数据滞后）
    except (urllib.error.URLError, OSError, ValueError, KeyError):
        pass  # 网络/解析失败时如实返回全 None 默认值，不伪造数据

    if use_cache and any(v is not None for k, v in result.items() if k != "code"):
        _RESULT_CACHE.set(f"fin:A:{code}", 1, result)
    return result


def fetch_financial_summary_batch(
    codes: list[str],
    use_cache: bool = True,
    batch_size: int = 50,
) -> dict[str, dict]:
    """批量获取 A股财务摘要（东财数据中心同报表，filter 多 secucode OR）。

    与 fetch_financial_summary 完全同构（同报表 RPT_F10_FINANCE_MAINFINADATA、
    同字段映射、每只取最新报告期），网络请求数由"每只 1 个"降为"每批 1 个"
    （batch_size 只/批），慢网络下显著提速；结果逐只写回结果级缓存
    （缓存 key 与逐只路径一致，热启动与逐只/批量互通）。

    真实约束：整批接口失败时该批回退逐只 fetch_financial_summary，
    单只批量缺失时该只回退逐只，不静默丢数据、不伪造。
    分批后并发拉取各批（网络好时秒级；网络慢时每批最多一个请求超时预算，
    不会逐批串行叠加超时）。
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    result_map: dict[str, dict] = {}
    if not codes:
        return result_map
    unique = list(dict.fromkeys(codes))
    chunks = [unique[i:i + batch_size] for i in range(0, len(unique), batch_size)]

    def _fetch_batch(chunk: list[str]) -> dict[str, dict]:
        """拉取单批并解析为 code->result（失败批/缺失只回退逐只）。"""
        chunk_map: dict[str, dict] = {}
        secucodes = [_to_secucode(c) for c in chunk]
        filters = "(SECUCODE in (" + ",".join(f'"{s}"' for s in secucodes) + "))"
        try:
            resp = http_get(
                FINANCE_API_URL,
                params={
                    "reportName": FINANCE_REPORT_NAME,
                    "columns": "ALL",
                    "filter": filters,
                    "pageNumber": "1",
                    "pageSize": str(len(chunk) * 8),  # 接口按报告期全局降序混合返回、不返回 total；每股预留 8 期（覆盖两年），保证每只最新期都落在本页内，避免最新期较早的标的被整只截出（缺失仍有逐只回退兜底）
                    "source": "HSF10",
                    "client": "PC",
                },
                timeout=8,
            )
            resp.raise_for_status()
            rows = (resp.json().get("result") or {}).get("data") or []
        except Exception:
            rows = []

        if not rows:
            # 整批接口失败 → 回退逐只（不静默丢数据）
            for code in chunk:
                chunk_map[code] = fetch_financial_summary(code, use_cache=use_cache)
            return chunk_map

        # 每只取最新报告期（与逐只路径 pageSize=1 语义一致）
        latest_by_code: dict[str, tuple] = {}
        for r in rows:
            sc = r.get("SECUCODE")
            code = sc.split(".")[0] if sc else None
            if not code:
                continue
            rd = str(r.get("REPORT_DATE") or "")
            if code not in latest_by_code or rd > latest_by_code[code][0]:
                latest_by_code[code] = (rd, r)

        for code in chunk:
            item = latest_by_code.get(code)
            if item is None:
                # 该只批量缺失 → 回退逐只
                chunk_map[code] = fetch_financial_summary(code, use_cache=use_cache)
                continue
            row = item[1]
            result = {
                "code": code,
                "roe": _num(row.get("ROEJQ")),
                "per_eps": _num(row.get("EPSJB")),
                "profit_gross": _num(row.get("XSMLL")),
                "net_profit_rate": _num(row.get("XSJLL")),
                "debt_ratio": _num(row.get("ZCFZL")),
                "revenue_growth": _num(row.get("TOTALOPERATEREVETZ")),
                "net_profit_growth": _num(row.get("PARENTNETPROFITTZ")),
                "operating_cfps": _num(row.get("MGJYXJJE")),
                "report_date": str(row.get("REPORT_DATE") or "")[:10],
            }
            if use_cache and any(v is not None for k, v in result.items() if k != "code"):
                _RESULT_CACHE.set(f"fin:A:{code}", 1, result)
            chunk_map[code] = result
        return chunk_map

    # 分批并发拉取（并发批数上限控制，避免对数据源瞬时压力过大）
    with ThreadPoolExecutor(max_workers=min(10, len(chunks))) as executor:
        futures = {executor.submit(_fetch_batch, c): c for c in chunks}
        for future in as_completed(futures):
            result_map.update(future.result())
    return result_map


def fetch_hk_us_financial_summary(code: str, market: str, use_cache: bool = True) -> dict:
    """获取港股/美股个股财务摘要。

    来源：东方财富数据中心公开报表 GMAININDICATOR 关键财务指标（最新报告期）。
    - 港股 RPT_HKF10_FN_GMAININDICATOR：75 字段，含 ROE_AVG/每股经营现金流等
    - 美股 RPT_USF10_FN_GMAININDICATOR：49 字段，含 ROE_AVG/毛利率/资产负债率等；
      美股无"每股经营现金流"字段（PER_NETCASH_OPERATE），operating_cfps 如实 None

    字段映射（真实字段名，与 A股 fetch_financial_summary 输出同构）：
    ROE_AVG→roe、BASIC_EPS→per_eps、GROSS_PROFIT_RATIO→profit_gross、
    NET_PROFIT_RATIO→net_profit_rate、DEBT_ASSET_RATIO→debt_ratio、
    OPERATE_INCOME_YOY→revenue_growth、
    港股 HOLDER_PROFIT_YOY / 美股 PARENT_HOLDER_NETPROFIT_YOY→net_profit_growth、
    港股 PER_NETCASH_OPERATE→operating_cfps（美股无此字段，如实 None）。

    Returns:
        dict: 与 fetch_financial_summary 同构；接口失败或字段缺失时如实置 None，不伪造。

    结果级缓存：同市场同代码当日有效（次日15:30过期，与K线缓存一致），
    仅缓存含真实数据的 result（全 None 的失败结果不缓存，下次重试）。
    """
    cached = _RESULT_CACHE.get(f"fin:{market}:{code}", 1) if use_cache else None
    if cached is not None:
        return cached

    result = {
        "code": code,
        "roe": None,
        "per_eps": None,
        "profit_gross": None,
        "net_profit_rate": None,
        "debt_ratio": None,
        "revenue_growth": None,
        "net_profit_growth": None,
        "operating_cfps": None,
        "report_date": None,  # 报告期日期（用于如实标注财务数据滞后）
    }

    report_name = HK_FINANCE_REPORT_NAME if market == "港股" else US_FINANCE_REPORT_NAME
    secucode = _to_hk_us_secucode(code, market)

    def _query(secu: str):
        try:
            resp = http_get(
                FINANCE_API_URL,
                params={
                    "reportName": report_name,
                    "columns": "ALL",
                    "filter": f'(SECUCODE="{secu}")',
                    "pageNumber": "1",
                    "pageSize": "1",
                    "sortColumns": "REPORT_DATE",
                    "sortTypes": "-1",
                    "source": "WEB",
                    "client": "WEB",
                },
                timeout=8,
            )
            resp.raise_for_status()
            payload = resp.json()
            return (payload.get("result") or {}).get("data") or []
        except (urllib.error.URLError, OSError, ValueError, KeyError):
            return []

    rows = _query(secucode)
    if not rows and market == "美股":
        # 美股 NASDAQ(.O) 无数据时回退 NYSE(.N)（BABA.N 等纽交所标的）
        rows = _query(f"{code.strip()}.N")
    if not rows:
        return result

    latest = rows[0]
    result["roe"] = _num(latest.get("ROE_AVG"))
    result["per_eps"] = _num(latest.get("BASIC_EPS"))
    result["profit_gross"] = _num(latest.get("GROSS_PROFIT_RATIO"))
    result["net_profit_rate"] = _num(latest.get("NET_PROFIT_RATIO"))
    result["debt_ratio"] = _num(latest.get("DEBT_ASSET_RATIO"))
    result["revenue_growth"] = _num(latest.get("OPERATE_INCOME_YOY"))
    if market == "港股":
        result["net_profit_growth"] = _num(latest.get("HOLDER_PROFIT_YOY"))
        result["operating_cfps"] = _num(latest.get("PER_NETCASH_OPERATE"))
    else:
        result["net_profit_growth"] = _num(latest.get("PARENT_HOLDER_NETPROFIT_YOY"))
        # 美股无每股经营现金流字段（GMAININDICATOR 49 字段），如实 None
        result["operating_cfps"] = None
    rd = latest.get("REPORT_DATE")
    if rd:
        result["report_date"] = str(rd)[:10]  # 报告期日期（如实标注数据滞后）

    if use_cache and any(v is not None for k, v in result.items() if k != "code"):
        _RESULT_CACHE.set(f"fin:{market}:{code}", 1, result)
    return result


def fetch_valuation(code: str, market: str = "A股", use_cache: bool = True) -> dict:
    """获取个股估值指标（支持 A股/港股/美股；单只/回退场景用）。

    注意：push2 stock/get 的 f171 字段**不是可靠股息率**（三市场均不可靠）。
    批量筛选请使用候选池列表字段（clist f133，三市场真实可用）；
    本函数股息率如实置 None，不返回错误数据。

    Returns:
        dict: 含 pe/pb/ps/total_mv 等字段；dividend_yield 恒为 None（无可靠单只来源）

    结果级缓存：同市场同代码当日有效（次日15:30过期，与K线缓存一致），
    仅缓存含真实数据的 result（全 None 的失败结果不缓存，下次重试）。
    """
    cached = _RESULT_CACHE.get(f"val:{market}:{code}", 1) if use_cache else None
    if cached is not None:
        return cached

    result = {
        "code": code,
        "pe_ttm": None,        # 市盈率(TTM)
        "pb": None,            # 市净率
        "ps_ttm": None,        # 市销率(TTM)
        "dividend_yield": None, # 股息率(%)：push2 无可靠字段，如实 None（见 docstring）
        "total_mv": None,      # 总市值(亿)
    }

    def _try_fetch(secid: str) -> dict:
        # fltt=2 返回格式化小数（未加 fltt 时 PE/PB 为放大100倍整数，已核实）
        data = push2_get("/api/qt/stock/get", params={
            "secid": secid,
            "fltt": "2",
            "fields": "f57,f58,f116,f162,f163,f167,f168,f171",
        })
        return data.get("data", {}) if data else {}

    try:
        data = _try_fetch(_secid_for_valuation(code, market))
        if not data and market == "港股":
            # 港股创业板 fallback
            data = _try_fetch(f"115.{code.strip().zfill(5)}")

        if data:
            # 市盈率(TTM)：港股/美股该字段为0，回退静态市盈率(f163)（三市场口径一致）
            pe_ttm = _num(data.get("f162"))
            if not pe_ttm:
                pe_ttm = _num(data.get("f163"))
            result["pe_ttm"] = pe_ttm
            result["pb"] = _num(data.get("f167"))
            result["ps_ttm"] = _num(data.get("f168"))
            # 注意：不再映射 f171 为股息率（该字段不可靠，见 docstring）
            # f116 = 总市值(元) → 亿元（港股/美股口径一致）
            mv = _num(data.get("f116"))
            if mv:
                result["total_mv"] = round(mv / 1e8, 2)
    except (urllib.error.URLError, OSError, ValueError, KeyError):
        pass  # 网络/解析失败时如实返回全 None 默认值，不伪造数据

    if use_cache and any(v is not None for k, v in result.items() if k != "code"):
        _RESULT_CACHE.set(f"val:{market}:{code}", 1, result)
    return result


def fetch_fundamental_batch(
    codes: list[str],
    market: str = "A股",
    max_workers: int = 10,
    need_financial: bool = True,
    need_valuation: bool = True,
    pool_valuation: Optional[dict] = None,
    use_cache: bool = True,
    need_roe_history: bool = False,
) -> dict[str, dict]:
    """批量获取多只股票基本面+估值数据（按策略依赖裁剪，减少无谓请求）。

    Args:
        codes: 股票代码列表
        market: 市场（A股/港股/美股），决定估值 secid 前缀；港股/美股财务摘要走
            东财数据中心 GMAININDICATOR 报表（港股75字段/美股49字段，字段语义同构，
            三市场财务字段真实返回）
        max_workers: 并发线程数
        need_financial: 是否获取财务摘要（S12/S13/S14 依赖）
        need_valuation: 是否获取估值指标（S06/S07 依赖；三市场可用）
        pool_valuation: 候选池估值字典 code -> {pe_ttm, pb, dividend_yield, ...}
            （主流程优先使用候选池 clist 字段 f9/f23/f133——三市场可靠，
            替代逐只 push2 stock/get 请求以提速；仅候选池缺失的标的回退逐只请求）
        use_cache: 是否使用结果级缓存（--no-cache 时 False）

    Returns:
        dict[str, dict]: code -> {**financial_summary, **valuation}
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    results = {}

    # A股财务摘要批量预取（同报表、同字段、同口径，网络请求 N → N/batch_size，
    # 慢网络下显著提速；批量缺失/失败时逐只回退，不静默丢数据）
    financial_batch: dict[str, dict] = {}
    if need_financial and market == "A股" and len(codes) > 1:
        financial_batch = fetch_financial_summary_batch(codes, use_cache=use_cache)

    def _fetch_one(code: str):
        merged = {"code": code}
        if need_financial:
            if market == "A股":
                if code in financial_batch:
                    merged.update(financial_batch[code])
                else:
                    # 批量缺失该只时回退逐只（真实兜底，不伪造）
                    merged.update(fetch_financial_summary(code, use_cache=use_cache))
            else:
                # 港股/美股财务摘要（GMAININDICATOR 报表，三市场字段同构，
                # 港股 75 字段含 ROE/现金流，美股 49 字段含 ROE/毛利率等）
                merged.update(fetch_hk_us_financial_summary(code, market, use_cache=use_cache))
        if need_valuation:
            if pool_valuation and code in pool_valuation:
                # 候选池 clist 估值（真实字段，优先）；财务摘要照常拉取
                merged.update(pool_valuation[code])
            else:
                val = fetch_valuation(code, market=market, use_cache=use_cache)
                merged.update(val)
        merged["code"] = code
        return code, merged

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_fetch_one, c): c for c in codes}
        for future in as_completed(futures):
            code, data = future.result()
            results[code] = data

    # S18 多年度ROE严格校验：合并年度 ROE 序列（缺失如实留空，不伪造）
    if need_roe_history:
        roe_seq = fetch_annual_roe_series_batch(
            list(results.keys()), market=market, use_cache=use_cache,
        )
        for code, seq in roe_seq.items():
            if code in results:
                results[code]["roe_history"] = seq

    return results


# ============================================================
# 多年度 ROE 序列（S18 多年度ROE严格校验数据源，进阶）
# ============================================================

def _extract_annual_field(rows: list, field: str, years: int, value_key: str = "value") -> list[dict]:
    """从多期财务行按自然年提取指定数值字段（每自然年取该年报告期最新值，仅已完结自然年，按年倒序）。"""
    by_year: dict[int, dict] = {}
    for r in rows:
        if not isinstance(r, dict):
            continue
        rd = str(r.get("REPORT_DATE") or "")[:10]
        if len(rd) < 10:
            continue
        try:
            year = int(rd[:4])
        except (TypeError, ValueError):
            continue
        val = _num(r.get(field))
        if val is None:
            continue
        cur = by_year.get(year)
        if cur is None or rd > cur["report_date"]:
            by_year[year] = {"year": year, value_key: val, "report_date": rd}
    import datetime as _dt
    _cur_year = _dt.date.today().year

    def _is_complete(year: int) -> bool:
        if year < _cur_year:
            return True
        return year == _cur_year and by_year[year]["report_date"].endswith("-12-31")

    return [by_year[y] for y in sorted(by_year.keys(), reverse=True) if _is_complete(y)][:years]


# 年度指标序列字段映射（与最新期财务摘要同源，columns=ALL 多期报表）
# 净利润增速：A股 PARENTNETPROFITTZ / 港股 HOLDER_PROFIT_YOY / 美股 PARENT_HOLDER_NETPROFIT_YOY
# 毛利率：A股 XSMLL / 港股美股 GROSS_PROFIT_RATIO
_ANNUAL_INDICATOR_FIELD = {
    "profit_growth": {"A股": "PARENTNETPROFITTZ", "港股": "HOLDER_PROFIT_YOY", "美股": "PARENT_HOLDER_NETPROFIT_YOY"},
    "gross_margin": {"A股": "XSMLL", "港股": "GROSS_PROFIT_RATIO", "美股": "GROSS_PROFIT_RATIO"},
}


def _extract_annual_roe(rows: list, roe_field: str, years: int) -> list[dict]:
    """从多期财务行按自然年提取年度 ROE（输出键 "roe"，供 S18 多年度严格校验）。"""
    return _extract_annual_field(rows, roe_field, years, value_key="roe")



def _annual_report_name(market: str) -> str:
    """按市场返回多期财务报表 reportName。"""
    if market == "港股":
        return HK_FINANCE_REPORT_NAME
    if market == "美股":
        return US_FINANCE_REPORT_NAME
    return FINANCE_REPORT_NAME


def _annual_secucode(code: str, market: str) -> str:
    """按市场构造多期报表查询 secucode（美股优先 .O，查询失败再回退 .N）。"""
    if market == "港股":
        return _to_hk_us_secucode(code, market)
    if market == "美股":
        return f"{code.strip()}.O"
    return _to_secucode(code)


def _query_annual_rows(code: str, market: str, years: int) -> list:
    """拉取个股多期财务报表行（columns=ALL）；美股 .O 无数据时回退 .N；任何失败返回 []。"""
    report_name = _annual_report_name(market)
    secucode = _annual_secucode(code, market)
    page_size = years * 6 + 4  # 每年约4期，预留6期/年覆盖停牌/缺失
    sort_kwargs = {"sortColumns": "REPORT_DATE", "sortTypes": "-1"} if market in ("港股", "美股") else {}

    def _query(secu: str) -> list:
        params = {
            "reportName": report_name,
            "columns": "ALL",
            "filter": f'(SECUCODE="{secu}")',
            "pageNumber": "1",
            "pageSize": str(page_size),
            "source": "HSF10" if market == "A股" else "WEB",
            "client": "PC" if market == "A股" else "WEB",
        }
        params.update(sort_kwargs)
        try:
            resp = http_get(FINANCE_API_URL, params=params, timeout=8)
            resp.raise_for_status()
            return (resp.json().get("result") or {}).get("data") or []
        except (urllib.error.URLError, OSError, ValueError, KeyError):
            return []

    rows = _query(secucode)
    if not rows and market == "美股":
        rows = _query(f"{code.strip()}.N")
    return rows


def fetch_annual_roe_series(
    code: str,
    market: str = "A股",
    years: int = 3,
    use_cache: bool = True,
) -> list[dict]:
    """获取个股最近 years 个完整自然年的年度 ROE 序列。

    来源：东方财富数据中心公开报表（与 fetch_financial_summary 同源）：
    - A股：RPT_F10_FINANCE_MAINFINADATA（字段 ROEJQ=ROE加权，与最新期口径一致）
    - 港股：RPT_HKF10_FN_GMAININDICATOR（字段 ROE_AVG）
    - 美股：RPT_USF10_FN_GMAININDICATOR（字段 ROE_AVG，无数据时 .N 回退）

    每自然年取该年报告期最新的 ROE（年报优先）；按年倒序返回最近 years 个。

    Returns:
        list[dict]: [{"year": int, "roe": float, "report_date": str}, ...]
            数据缺失/接口失败时返回 []（如实，不伪造）。

    结果级缓存：同市场同代码当日有效（次日15:30过期，与财务摘要缓存一致），
    仅缓存含真实数据的 result（空列表不缓存，下次重试）。
    """
    cached = _RESULT_CACHE.get(f"roe:{market}:{code}", 1) if use_cache else None
    if cached is not None:
        return cached

    rows = _query_annual_rows(code, market, years)
    roe_field = "ROE_AVG" if market in ("港股", "美股") else "ROEJQ"
    result = _extract_annual_roe(rows, roe_field, years)
    if use_cache and result:
        _RESULT_CACHE.set(f"roe:{market}:{code}", 1, result)
    return result

    if use_cache and result:
        _RESULT_CACHE.set(f"roe:{market}:{code}", 1, result)
    return result


def fetch_annual_indicator_series(
    code: str,
    market: str = "A股",
    indicator: str = "profit_growth",
    years: int = 3,
    use_cache: bool = True,
) -> list[dict]:
    """获取最近 years 个完整自然年的年度指标序列（成长/毛利率历史因子的真实数据源）。

    Args:
        indicator: "profit_growth"=净利润同比增速序列（growth_acceleration/growth_stability 数据源）；
                   "gross_margin"=毛利率序列（margin_expansion 数据源）。

    与 fetch_annual_roe_series 同源多期报表：按自然年取该年最新值、仅已完结自然年、按年倒序。

    Returns:
        list[dict]: [{"year": int, "value": float, "report_date": str}, ...]；无此指标/失败返回 []。
    """
    field_map = _ANNUAL_INDICATOR_FIELD.get(indicator)
    if not field_map:
        return []
    cache_key = f"annual:{indicator}:{market}:{code}"
    cached = _RESULT_CACHE.get(cache_key, 1) if use_cache else None
    if cached is not None:
        return cached
    field = field_map.get(market) or field_map["A股"]
    rows = _query_annual_rows(code, market, years)
    result = _extract_annual_field(rows, field, years, value_key="value")
    if use_cache and result:
        _RESULT_CACHE.set(cache_key, 1, result)
    return result


def fetch_annual_indicator_series_batch(
    codes: list[str],
    market: str = "A股",
    indicator: str = "profit_growth",
    years: int = 3,
    use_cache: bool = True,
    max_workers: int = 10,
) -> dict[str, list[dict]]:
    """批量获取年度指标序列（并发逐只，单只失败返回空，不伪造、不中断整体）。"""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    result_map: dict[str, list[dict]] = {}
    if not codes:
        return result_map
    unique = list(dict.fromkeys(codes))

    def _one(code: str):
        try:
            return code, fetch_annual_indicator_series(
                code, market=market, indicator=indicator, years=years, use_cache=use_cache)
        except Exception:
            return code, []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_one, c): c for c in unique}
        for future in as_completed(futures):
            code, seq = future.result()
            if seq:
                result_map[code] = seq
    return result_map


def fetch_annual_roe_series_batch(
    codes: list[str],
    market: str = "A股",
    years: int = 3,
    use_cache: bool = True,
    max_workers: int = 10,
    batch_size: int = 50,
) -> dict[str, list[dict]]:
    """批量获取多只股票的年度 ROE 序列。

    - A股：走东财数据中心同报表批量接口（filter 多 secucode OR，每只预留多期），
      与 fetch_financial_summary_batch 同构；批量缺失/失败逐只回退，不静默丢数据。
    - 港股/美股：并发逐只 fetch_annual_roe_series（无同构批量报表可用时如实逐只）。

    Returns:
        dict[str, list[dict]]: code -> 年度 ROE 序列（[{year, roe, report_date}, ...]）
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    result_map: dict[str, list[dict]] = {}
    if not codes:
        return result_map
    unique = list(dict.fromkeys(codes))

    if market != "A股":
        # 港股/美股：并发逐只（批量报表不可用，如实逐只拉取）
        def _fetch_one(code: str):
            try:
                return code, fetch_annual_roe_series(
                    code, market=market, years=years, use_cache=use_cache,
                )
            except Exception:
                return code, []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_fetch_one, c): c for c in unique}
            for future in as_completed(futures):
                code, seq = future.result()
                if seq:
                    result_map[code] = seq
        return result_map

    # A股：批量接口（同报表 RPT_F10_FINANCE_MAINFINADATA，filter 多 secucode OR）
    chunks = [unique[i:i + batch_size] for i in range(0, len(unique), batch_size)]

    def _fetch_batch(chunk: list[str]) -> dict[str, list[dict]]:
        chunk_map: dict[str, list[dict]] = {}
        secucodes = [_to_secucode(c) for c in chunk]
        filters = "(SECUCODE in (" + ",".join(f'"{s}"' for s in secucodes) + "))"
        # 每只预留 years*6+4 期（与 fetch_annual_roe_series 口径一致），保证各只年度序列完整
        page_size = len(chunk) * (years * 6 + 4)
        try:
            resp = http_get(
                FINANCE_API_URL,
                params={
                    "reportName": FINANCE_REPORT_NAME,
                    "columns": "ALL",
                    "filter": filters,
                    "pageNumber": "1",
                    "pageSize": str(page_size),
                    "source": "HSF10",
                    "client": "PC",
                },
                timeout=8,
            )
            resp.raise_for_status()
            rows = (resp.json().get("result") or {}).get("data") or []
        except Exception:
            rows = []

        if not rows:
            # 整批失败 → 逐只回退（不静默丢数据）
            for code in chunk:
                seq = fetch_annual_roe_series(
                    code, market=market, years=years, use_cache=use_cache,
                )
                if seq:
                    chunk_map[code] = seq
            return chunk_map

        # 按 code 分组后逐只提取年度 ROE（分组内按 REPORT_DATE 取每自然年最新）
        rows_by_code: dict[str, list] = {}
        for r in rows:
            if not isinstance(r, dict):
                continue
            sc = r.get("SECUCODE")
            code = sc.split(".")[0] if sc else None
            if not code:
                continue
            rows_by_code.setdefault(code, []).append(r)

        for code in chunk:
            seq = _extract_annual_roe(rows_by_code.get(code, []), "ROEJQ", years)
            if not seq:
                # 该只批量缺失 → 逐只回退
                seq = fetch_annual_roe_series(
                    code, market=market, years=years, use_cache=use_cache,
                )
            if seq:
                chunk_map[code] = seq
                if use_cache:
                    _RESULT_CACHE.set(f"roe:{market}:{code}", 1, seq)
        return chunk_map

    with ThreadPoolExecutor(max_workers=min(10, len(chunks))) as executor:
        futures = {executor.submit(_fetch_batch, c): c for c in chunks}
        for future in as_completed(futures):
            result_map.update(future.result())
    return result_map
