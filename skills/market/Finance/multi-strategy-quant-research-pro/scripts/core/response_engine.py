# -*- coding: utf-8 -*-
"""多模式回复引擎：新手/专业/极简三模式自动切换。

三种模式：
1. 新手模式：详细解释术语，步骤化引导，风险提示充分
2. 专业模式：简洁数据，专业术语，深度分析，指标完整
3. 极简模式：只给结果表格，最少文字，快速获取

自动检测：根据用户输入中的专业术语密度、提问方式判断用户水平。
"""



# 专业术语库（新手模式需要解释的术语）
TERM_GLOSSARY = {
    "ROE": "净资产收益率（Return on Equity），衡量公司用股东权益赚钱的能力，越高越好",
    "PE": "市盈率（Price-to-Earnings），股价除以每股收益，越低通常越便宜",
    "PB": "市净率（Price-to-Book），股价除以每股净资产，低于1可能被低估",
    "股息率": "年度分红除以股价，越高代表分红回报越高",
    "MACD": "指数平滑异同移动平均线，金叉（DIF上穿DEA）通常是买入信号",
    "RSI": "相对强弱指标，70以上超买可能回调，30以下超卖可能反弹",
    "布林带": "由中轨(MA20)和上下轨(±2倍标准差)组成的通道，突破上轨可能超买",
    "ATR": "平均真实波幅，衡量波动率，越高波动越大",
    "夏普比率": "每承担1单位风险获得的超额收益，>1较好，>2优秀",
    "最大回撤": "从最高点到最低点的最大跌幅，越小风险控制越好",
    "卡玛比率": "年化收益除以最大回撤，越高风险调整后收益越好",
    "金叉": "短期均线上穿长期均线，通常视为买入信号",
    "死叉": "短期均线下穿长期均线，通常视为卖出信号",
    "多头排列": "MA5>MA10>MA20>MA60，代表上升趋势",
    "量比": "当日成交量与过去5日均量的比值，>1.5代表放量",
    "筹码集中度": "持仓成本集中程度，越集中代表主力控盘度越高",
    "北向资金": "通过沪股通/深股通买入A股的境外资金，常被视为聪明钱",
    "前复权": "以最新价为基准，对历史价格进行除权除息调整，保持价格连续",
    "IC值": "信息系数，因子值与未来收益的相关系数，>0.05代表有效因子",
}

# 专业术语列表（用于检测用户专业度）
PROFESSIONAL_TERMS = [
    "ROE", "PE", "PB", "MACD", "RSI", "ATR", "夏普", "卡玛", "索提诺",
    "金叉", "死叉", "多头排列", "量比", "筹码", "北向", "前复权", "IC",
    "因子", "回测", "回撤", "波动率", "alpha", "beta", "夏普比率",
    "市净率", "市盈率", "净资产收益率", "股息率", "换手率", "振幅",
]


def detect_user_level(text: str) -> str:
    """自动检测用户专业水平。

    Args:
        text: 用户输入文本

    Returns:
        str: "beginner" / "professional" / "minimal"
    """
    text_lower = text.lower()

    # 极简模式信号
    minimal_signals = ["直接给", "只要结果", "别废话", "简单点", "快速", "列表", "表格就行"]
    if any(sig in text for sig in minimal_signals):
        return "minimal"

    # 新手模式信号
    beginner_signals = [
        "什么是", "怎么看", "不懂", "新手", "入门", "解释一下",
        "通俗", "简单说", "举个例子", "帮我理解", "小白",
    ]
    if any(sig in text for sig in beginner_signals):
        return "beginner"

    # 专业术语计数
    pro_count = sum(1 for term in PROFESSIONAL_TERMS if term.lower() in text_lower)

    # 专业模式信号
    professional_signals = [
        "回测", "因子", "alpha", "夏普", "卡玛", "IC值", "正交化",
        "最大回撤", "年化", "超额收益", "基准", "策略对比",
    ]
    pro_signal_count = sum(1 for sig in professional_signals if sig in text)

    if pro_count >= 3 or pro_signal_count >= 2:
        return "professional"

    # 默认新手模式（更友好）
    return "beginner"


class ResponseEngine:
    """多模式回复引擎。"""

    def __init__(self, mode: str = "auto"):
        self.mode = mode  # auto/beginner/professional/minimal

    def set_mode(self, mode: str):
        if mode in ["auto", "beginner", "professional", "minimal"]:
            self.mode = mode

    def render(self, data: dict, user_text: str = "") -> dict:
        """根据模式渲染回复。

        Args:
            data: 选股结果数据 {stocks, strategy, params, metrics}
            user_text: 用户原始输入（用于自动检测模式）

        Returns:
            dict: {mode, summary, table, explanations, risk_warning, next_steps}
        """
        mode = self.mode
        if mode == "auto":
            mode = detect_user_level(user_text)

        stocks = data.get("stocks", [])
        strategy = data.get("strategy", "")
        params = data.get("params", {})
        metrics = data.get("metrics", {})

        if mode == "minimal":
            return self._render_minimal(stocks, strategy, params)
        elif mode == "professional":
            return self._render_professional(stocks, strategy, params, metrics)
        else:
            return self._render_beginner(stocks, strategy, params, metrics)

    def _render_beginner(self, stocks, strategy, params, metrics) -> dict:
        """新手模式：详细解释+步骤化+充分风险提示。"""
        summary = (
            f"已为您完成「{strategy}」选股，共找到{len(stocks)}只符合条件的股票。\n\n"
            f"筛选条件：{self._format_params(params)}\n\n"
            f"以下是筛选结果，每只股票都标注了关键指标，方便您理解："
        )

        # 新手表格：包含解释性列
        table_headers = ["序号", "代码", "名称", "现价", "关键指标", "入选原因"]
        table_rows = []
        for i, s in enumerate(stocks[:20], 1):
            key_metrics = self._format_key_metrics(s, beginner=True)
            reason = s.get("reason", "符合筛选条件")
            table_rows.append([str(i), s.get("code", ""), s.get("name", ""),
                               f"{s.get('close', 0):.2f}", key_metrics, reason])

        # 术语解释
        explanations = self._generate_explanations(stocks, strategy)

        risk_warning = (
            "【重要风险提示】\n"
            "1. 以上结果仅基于公开数据和量化规则筛选，不构成投资建议\n"
            "2. 历史表现不代表未来收益，股市有风险，投资需谨慎\n"
            "3. 建议结合公司基本面、行业前景和自身风险承受能力综合判断\n"
            "4. 新手投资者建议先学习基础知识，小额尝试，不要一次性投入过多"
        )

        next_steps = (
            "【下一步建议】\n"
            "1. 点击股票代码查看详细分析\n"
            "2. 可以问我「解释一下ROE是什么」了解更多术语\n"
            "3. 可以说「用更严格的条件再筛一次」调整筛选标准"
        )

        return {
            "mode": "beginner",
            "summary": summary,
            "table_headers": table_headers,
            "table_rows": table_rows,
            "explanations": explanations,
            "risk_warning": risk_warning,
            "next_steps": next_steps,
        }

    def _render_professional(self, stocks, strategy, params, metrics) -> dict:
        """专业模式：简洁数据+完整指标+深度分析。"""
        summary = (
            f"策略「{strategy}」筛选完成，命中{len(stocks)}只。"
            f"条件：{self._format_params(params)}。"
            f"组合指标：{self._format_metrics(metrics)}"
        )

        # 专业表格：完整指标
        table_headers = ["代码", "名称", "现价", "涨跌幅", "ROE", "PE", "PB",
                         "股息率", "市值(亿)", "信号分", "入选条件"]
        table_rows = []
        for s in stocks[:30]:
            table_rows.append([
                s.get("code", ""), s.get("name", ""),
                f"{s.get('close', 0):.2f}",
                f"{s.get('change_pct', 0):.2f}%",
                f"{s.get('roe', 0):.1f}%" if s.get("roe") else "N/A",
                f"{s.get('pe', 0):.1f}" if s.get("pe") else "N/A",
                f"{s.get('pb', 0):.2f}" if s.get("pb") else "N/A",
                f"{s.get('dividend_yield', 0):.2f}%" if s.get("dividend_yield") else "N/A",
                f"{s.get('market_cap', 0):.0f}" if s.get("market_cap") else "N/A",
                f"{s.get('signal_score', 0):.0f}" if s.get("signal_score") else "N/A",
                s.get("conditions", ""),
            ])

        risk_warning = "数据基于公开来源，量化筛选不构成投资建议。注意因子失效和市场环境变化风险。"

        return {
            "mode": "professional",
            "summary": summary,
            "table_headers": table_headers,
            "table_rows": table_rows,
            "explanations": [],
            "risk_warning": risk_warning,
            "next_steps": "可请求回测验证、因子分析或组合优化。",
        }

    def _render_minimal(self, stocks, strategy, params) -> dict:
        """极简模式：只给结果表格。"""
        table_headers = ["代码", "名称", "现价"]
        table_rows = [[s.get("code", ""), s.get("name", ""), f"{s.get('close', 0):.2f}"]
                      for s in stocks[:50]]

        return {
            "mode": "minimal",
            "summary": f"{strategy}：{len(stocks)}只",
            "table_headers": table_headers,
            "table_rows": table_rows,
            "explanations": [],
            "risk_warning": "",
            "next_steps": "",
        }

    def _format_params(self, params: dict) -> str:
        if not params:
            return "默认条件"
        parts = []
        for k, v in params.items():
            if k == "top_n":
                parts.append(f"前{v}只")
            elif k == "market":
                parts.append(f"市场:{v}")
            elif k == "roe_min":
                parts.append(f"ROE≥{v}%")
            elif k == "dividend_min":
                parts.append(f"股息率≥{v}%")
            elif k == "pe_max":
                parts.append(f"PE≤{v}")
            elif k == "consecutive_years":
                parts.append(f"连续{v}年")
            else:
                parts.append(f"{k}={v}")
        return "，".join(parts)

    def _format_key_metrics(self, stock: dict, beginner: bool = False) -> str:
        parts = []
        if stock.get("roe"):
            parts.append(f"ROE {stock['roe']:.1f}%")
        if stock.get("pe"):
            parts.append(f"PE {stock['pe']:.1f}")
        if stock.get("dividend_yield"):
            parts.append(f"股息 {stock['dividend_yield']:.2f}%")
        if stock.get("signal_score"):
            parts.append(f"信号 {stock['signal_score']:.0f}分")
        return " / ".join(parts) if parts else "—"

    def _format_metrics(self, metrics: dict) -> str:
        if not metrics:
            return ""
        parts = []
        if metrics.get("sharpe"):
            parts.append(f"夏普{metrics['sharpe']:.2f}")
        if metrics.get("max_drawdown"):
            parts.append(f"回撤{metrics['max_drawdown']:.1f}%")
        if metrics.get("win_rate"):
            parts.append(f"胜率{metrics['win_rate']:.1f}%")
        return "，".join(parts)

    def _generate_explanations(self, stocks: list, strategy: str) -> list:
        """根据结果中出现的术语生成解释。"""
        terms_needed = set()
        if "ROE" in strategy or any(s.get("roe") for s in stocks):
            terms_needed.add("ROE")
        if any(s.get("pe") for s in stocks):
            terms_needed.add("PE")
        if any(s.get("dividend_yield") for s in stocks):
            terms_needed.add("股息率")
        if "MACD" in strategy:
            terms_needed.add("MACD")
        if "RSI" in strategy:
            terms_needed.add("RSI")

        return [{"term": t, "explanation": TERM_GLOSSARY.get(t, "")}
                for t in terms_needed if t in TERM_GLOSSARY]
