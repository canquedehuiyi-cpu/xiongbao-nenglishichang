"""个股资金流向数据获取层。

数据来源：东方财富公开资金流向API（多日历史走 push2his 历史节点；实时/延迟走 push2 节点）。
全部为公开数据接口，不涉及认证，合规合法。

资金流向定义：
- 主力净流入 = 超大单净流入 + 大单净流入
- 超大单：单笔 >= 100万元
- 大单：单笔 >= 20万元且 < 100万元
- 中单：单笔 >= 4万元且 < 20万元
- 小单：单笔 < 4万元

API说明（多通道，如实降级）：
- 多日历史：push2his.eastmoney.com/api/qt/stock/fflow/daykline/get（多编号节点，返回逐日资金流序列）
- 实时/延迟：push2.eastmoney.com / push2delay.eastmoney.com（延迟节点下通常仅返回最近1日）
- 拉取策略：优先 push2his 历史节点拿多日数据；全部历史节点不可达时回退 push2 实时/延迟节点。
  （部分网络环境 push2his 整体不可达，资金流退化为最近1日，S15 等依赖"连续≥3日"的
   判定按实际数据如实不通过，不伪造。实际数据来源经 flow_source_label() 如实暴露。）
- 连续流入：基于多日资金流数据累加计算
"""

from ._http import push2_get, push2his_get, safe_float, LAST_HOST  # 东财共享客户端（历史/实时多节点容灾+数值清洗）
from .fundamental import _RESULT_CACHE  # 共享结果级缓存（与财务/估值同实例，键带 flow: 前缀）

# 最近一次资金流请求实际使用的数据来源（供如实标注数据通道/深度）
LAST_FLOW_SOURCE = [None]


def flow_source_label() -> str:
    """返回最近一次资金流请求实际使用的数据来源说明。

    - 结果级缓存          → 当日结果级缓存命中（来源节点同缓存写入时，当日有效）
    - push2his.*.eastmoney.com  → 东财历史节点（逐日资金流多日可用）
    - push2.eastmoney.com       → 实时主节点
    - push2delay.eastmoney.com  → 官方延迟节点（约3分钟延迟，资金流通常仅最近1日）
    - None                      → 最近资金流请求全部失败
    """
    src = LAST_FLOW_SOURCE[0]
    if not src:
        return "资金流通道异常（最近请求全部失败）"
    if src == "结果级缓存":
        return "资金流结果级缓存（当日有效）"
    if "push2his" in src:
        return f"资金流历史节点（{src}，逐日多日数据）"
    if "delay" in src:
        return f"资金流延迟节点（{src}，通常仅最近1日）"
    return f"资金流实时节点（{src}）"


def _secid(code: str, market: str = "A股") -> str:
    """生成指定市场标的在 push2 fflow 接口的 secid。

    - A股：1.沪（6开头）/ 0.深
    - 港股：116.{5位代码}（主板/创业板统一走 116，真实返回）
    - 美股：105.{代码}（公开接口对美股不返回日级资金流数据，如实无）
    """
    code = str(code).strip()
    if market == "港股":
        return f"116.{code.zfill(5)}"
    if market == "美股":
        return f"105.{code}"
    return f"1.{code}" if code.startswith("6") else f"0.{code}"


def _parse_flow_klines(klines) -> list[dict]:
    """解析东财 fflow/daykline CSV 行为结构化资金流字典（三市场/多节点同构）。

    行格式（fields2=f51..f65，逗号分隔，至少10列）：
        0日期, 1主力净流入, 2小单, 3中单, 4大单, 5超大单 (单位:元), 6..占比/价格/涨跌幅...

    主力净流入 = 超大单 + 大单（东财口径），接口直接返回主力值，直接采用。
    """
    result = []
    for line in klines:
        parts = line.split(",")
        if len(parts) < 10:
            continue
        main_net = safe_float(parts[1])
        small = safe_float(parts[2])
        medium = safe_float(parts[3])
        large = safe_float(parts[4])
        super_large = safe_float(parts[5])
        result.append({
            "date": parts[0],
            "main_net_inflow": main_net,
            "super_large_net": super_large,
            "large_net": large,
            "medium_net": medium,
            "small_net": small,
        })
    return result


def fetch_stock_money_flow(code: str, days: int = 30, market: str = "A股", use_cache: bool = True) -> list[dict]:
    """获取个股逐日资金流向数据（多通道：push2his 历史节点优先，push2 实时/延迟兜底）。

    请求URL:
        https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get（多日历史）
        https://push2.eastmoney.com/api/qt/stock/fflow/daykline/get（实时/延迟兜底）
    参数:
        lmt: 获取天数
        klt: 101 日线
        secid: 市场.代码 (如 1.600519 / 116.00700)

    返回字段说明:
        - date: 日期
        - main_net_inflow: 主力净流入(元) = 超大单净流入 + 大单净流入
        - super_large_net: 超大单净流入(元)
        - large_net: 大单净流入(元)
        - medium_net: 中单净流入(元)
        - small_net: 小单净流入(元)

    数据可用性（如实）：
    - A股/港股：push2his 历史节点可达时返回逐日多日资金流；全部历史节点不可达时
      回退 push2 实时/延迟节点（延迟节点下通常仅最近1日，如实降级）
    - 美股：公开接口对美股不返回该口径数据（105.AAPL 无数据），如实返回 []

    Returns:
        list[dict]: 逐日资金流向列表

    结果级缓存：同市场同代码当日有效（次日15:30过期，与K线缓存一致），
    仅缓存含真实数据的结果（网络失败返回空不缓存，下次重试）。
    """
    cached = _RESULT_CACHE.get(f"flow:{market}:{code}:{days}", 1) if use_cache else None
    if cached is not None:
        # 结果级缓存命中：如实标注来源为缓存（当日有效），不误标通道异常
        LAST_FLOW_SOURCE[0] = "结果级缓存"
        return cached

    secid = _secid(code, market)
    params = {
        "lmt": days,
        "klt": "101",
        "secid": secid,
        "fields1": "f1,f2,f3,f7",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65",
    }

    # 多日历史优先走 push2his 历史节点；全部历史节点不可达时回退 push2 实时/延迟节点
    data = push2his_get("/api/qt/stock/fflow/daykline/get", params, timeout=5)
    if data:
        LAST_FLOW_SOURCE[0] = "push2his"
    else:
        data = push2_get("/api/qt/stock/fflow/daykline/get", params, timeout=8)
        if data:
            real_host = LAST_HOST[0] or ""
            LAST_FLOW_SOURCE[0] = "push2delay" if "delay" in real_host else "push2实时节点"
    if not data:
        LAST_FLOW_SOURCE[0] = None
        return []

    klines = data.get("data", {}).get("klines", [])
    result = _parse_flow_klines(klines)

    # 仅缓存含真实数据的列表（网络失败返回空不缓存，下次重试；美股无口径如实空亦不缓存）
    if use_cache and result:
        _RESULT_CACHE.set(f"flow:{market}:{code}:{days}", 1, result)
    return result
