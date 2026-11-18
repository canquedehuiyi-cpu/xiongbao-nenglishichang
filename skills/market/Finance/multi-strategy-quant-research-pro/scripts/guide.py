"""
multi-strategy-quant-research-pro v1.1.2 新用户交互式引导向导 (Interactive Guide)

设计理念：
- 不强制用户从某一步开始，允许从任意环节切入
- 每一步均可跳过或返回上一步
- 所有数据/建议来自东方财富公开API真实返回，绝不编造数值
- 每步提供实时真实数据作为决策依据

流程：
  1. 欢迎页    → 功能概览 + 策略清单
  2. 环境检测  → 真实调用东方财富API测试各接口连通性
  3. 市场选择  → 查询A股/港股/美股当前真实可获取的股票数量
  4. 策略适配  → 基于真实大盘MA均线判断多空，智能适配策略组合
  5. 参数配置  → 非强制引导式设置输出格式/TOP-N等
  6. 执行确认  → 预览配置后转入筛选执行
  7. 档案追踪  → 询问是否开启策略表现档案库（可选）
"""

import os
import sys
import json
from datetime import datetime
from typing import Optional

# 确保 scripts 目录在路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config

# 策略注册表（模块级导入，避免各步骤内重复 import）
from strategies import STRATEGY_REGISTRY

# 东财实时/历史接口共享客户端（多节点故障切换）
from data._http import push2_get, kline_get, http_get

# ============================================================
# 引导交互状态
# ============================================================

# ============================================================
# 配色辅助（终端ANSI码）
# ============================================================
C = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "cyan": "\033[36m",
    "red": "\033[91m",
    "magenta": "\033[95m",
}


def _c(text: str, color: str) -> str:
    """给文本包裹颜色码。"""
    return f"{C.get(color, '')}{text}{C['reset']}"


# ============================================================
# Session State: 引导过程中的配置状态
# ============================================================
_session_state = {
    "market": config.DEFAULT_MARKET,
    "mode": config.SCREEN_MODE,
    "strategy_ids": None,          # None = 全部启用
    "strategy_mode": config.DEFAULT_STRATEGY_MODE,
    "weights": None,
    "top_n": config.TOP_N_OUTPUT,
    "output_format": "all",
    "output_dir": config.OUTPUT_DIR,
    "multi_period": False,
    "no_cache": False,
    "track": False,
    "reply_level": config.REPLY_LEVEL_DEFAULT,
}

# 步骤定义
STEPS = [
    "welcome",          # 0
    "env_check",        # 1
    "market_select",    # 2
    "strategy_recommend",  # 3
    "param_config",     # 4
    "exec_confirm",     # 5
    "archive_setup",    # 6
]

# ============================================================
# 用户偏好记忆（越用越懂用户）
# 将上次引导确定的偏好保存到本地文件，下次引导自动预填，
# 仅影响默认值，不覆盖用户本次的新选择。
# ============================================================
PREFS_FILE = os.path.join(os.path.expanduser("~"), ".multi_strategy_quant_research_prefs.json")
# 环境检测完成标记（非首次跳过重复连通测试，避免慢网络下重复等待）
ENV_CHECK_FLAG = ".multi_strategy_quant_research_env_checked"
_PREF_KEYS = ("market", "mode", "strategy_mode", "top_n", "output_format",
              "output_dir", "multi_period", "reply_level")


def _load_prefs() -> dict:
    """读取本地用户偏好。文件不存在或损坏时返回空 dict。"""
    try:
        with open(PREFS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_prefs():
    """将本次引导确定的关键偏好写入本地文件。"""
    prefs = {}
    for key in _PREF_KEYS:
        val = _session_state.get(key)
        if val is not None:
            prefs[key] = val
    try:
        with open(PREFS_FILE, "w", encoding="utf-8") as f:
            json.dump(prefs, f, ensure_ascii=False, indent=2)
    except OSError:
        pass  # 偏好写入失败不影响引导主流程


# ============================================================
# 通用 API 调用工具
# ============================================================

def _api_get(url: str, params: dict = None, timeout: int = 15) -> Optional[dict]:
    """安全调用东方财富公开API，返回 parsed JSON 或 None。

    - push2 实时接口（列表/行情/估值）：经共享客户端做域名级故障切换
      （主节点不可达时切换官方备用延迟节点）
    - push2his 历史K线接口：经共享客户端做多编号节点故障切换，
      全部节点不可达时自动切换腾讯公开K线通道（三市场可用）
    - 其余接口直连
    """
    try:
        if "push2.eastmoney.com" in url:
            path = url.split("push2.eastmoney.com", 1)[1]
            data = push2_get(path, params=params, timeout=timeout)
            return data if data else None
        if "push2his.eastmoney.com" in url:
            from urllib.parse import urlsplit, parse_qs
            parts = urlsplit(url)
            qs = {k: v[0] for k, v in parse_qs(parts.query).items()}
            if params:
                qs.update(params)
            data = kline_get(parts.path, params=qs, timeout=timeout)
            return data if data else None
        resp = http_get(url, params=params, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


# ============================================================
# Step 1: 欢迎页
# ============================================================

def _step_welcome():
    """展示欢迎信息：Skill功能与策略概览。"""
    print()
    print("=" * 70)
    print(_c("  multi-strategy-quant-research-pro v" + config.VERSION + "  新用户引导向导", "bold"))
    print(f"  启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()
    print("  欢迎使用 multi-strategy-quant-research-pro 多市场量化研究引擎！")
    print()
    print("  【核心能力】")
    print("    - 数据与主流程执行覆盖 A股 / 港股 / 美股（技术面/估值/财务摘要三市场可用；资金流 A股/港股可用）")
    print("    - 内置 23 种选股策略（全部真实代码可审计）")
    print("    - 三种策略组合模式：并集 / 交集 / 加权评分")
    print("    - 多周期交叉验证（日/周）")
    print("    - 输出 Text / JSON / HTML / CSV 四格式报告（支持组合与仅控制台输出）")
    print()
    print("  【数据来源】")
    print("    东方财富公开行情API（push2.eastmoney.com）")
    print("    全部为公开接口，不涉及认证，合规合法")
    print("    数据延迟约 3-5 分钟，非Level-2实时数据")
    print()
    print("  【23种策略一览】")
    print("    " + "-" * 60)
    for k, v in sorted(config.STRATEGY_DEFAULT_WEIGHTS.items()):
        name = STRATEGY_REGISTRY.get(k, {}).get("name", k)
        weight = v
        print(f"    {k:5s}  {name:12s}  默认权重: {weight:.2f}")
    print("    " + "-" * 60)
    print()
    print("  【数据源声明】")
    print("    全部数据来自东方财富公开HTTP接口，数值均为真实返回。")
    print("    本引导中每一步的环境检测和建议都基于实时API数据。")
    print()
    print("  【风险提示】")
    print("    以上为技术形态与基本面筛选结果，不构成投资建议。")
    print("    股市有风险，投资需谨慎。请结合自身风险承受能力独立决策。")
    print()
    print("-" * 70)
    print("  接下来将依次引导：环境检测 → 市场选择 → 策略适配 → 参数配置 → 执行确认 → 档案追踪")
    print("  每步均可键入 's' 跳过、'b' 返回上一步、'q' 退出引导")
    print("-" * 70)
    print()


# ============================================================
# Step 2: 环境检测（真实调用API测试连通性）
# ============================================================

def _step_env_check():
    """真实调用东方财富公开API，测试各接口当前连通状态。

    非首次运行（已成功检测过，标记文件存在）时跳过重复检测——
    6 个接口的逐项连通测试在慢网络下会叠加等待，重复执行无信息增量；
    需重新检测时删除标记文件或显式 --guide 进入完整引导。
    """
    env_flag = os.path.join(os.path.dirname(PREFS_FILE), ENV_CHECK_FLAG)
    if os.path.exists(env_flag):
        print()
        print(_c("  [环境检测] 此前已检测通过，本次跳过重复检测（如需重测请删除偏好标记文件）。", "dim"))
        print()
        return None
    print()
    print(_c("─" * 60, "dim"))
    print(_c("  [环境检测] 正在测试东方财富公开API连通性...", "bold"))
    print(_c("─" * 60, "dim"))
    print()

    endpoints = {}

    # 1. A股列表接口
    print("  测试 A股列表接口 ...", end=" ")
    result = _api_get(
        "https://push2.eastmoney.com/api/qt/clist/get",
        params={
            "pn": "1", "pz": "5", "po": "1", "np": "1",
            "fltt": "2", "invt": "2",
            "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",
            "fields": "f12,f14",
        },
    )
    if result and result.get("data", {}).get("diff"):
        total = result["data"].get("total", "?")
        endpoints["A股列表"] = {"status": "OK", "info": f"沪深A股总计约 {total} 只"}
        print(_c("OK", "green") + f" (总计 {total} 只)")
    else:
        endpoints["A股列表"] = {"status": "FAIL", "info": "接口未返回数据"}
        print(_c("FAIL (接口未响应或返回空)", "red"))

    # 2. 实时行情接口
    print("  测试 实时行情接口 ...", end=" ")
    result = _api_get(
        "https://push2.eastmoney.com/api/qt/ulist.np",
        params={
            "fltt": "2",
            "secids": "1.600519,0.000001",
            "fields": "f2,f3,f12,f14",
        },
    )
    if result and result.get("data", {}).get("diff"):
        items = result["data"]["diff"]
        names = [it.get("f14", "?") for it in items]
        endpoints["实时行情"] = {"status": "OK", "info": f"可获取 {', '.join(names)} 等标的实时数据"}
        print(_c("OK", "green") + f" (获取 {len(items)} 只)")
    else:
        endpoints["实时行情"] = {"status": "FAIL", "info": "接口未返回数据"}
        print(_c("FAIL", "red"))

    # 3. K线接口（与主流程同款通道：push2his 多节点 → 腾讯/新浪兜底，
    #    如实反映端到端K线可用性，避免对单一死主机误报）
    print("  测试 日K线接口 ...", end=" ")
    result = kline_get(
        "/api/qt/stock/kline/get",
        params={
            "secid": "1.600519",
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
            "klt": "101", "fqt": "1",
            "end": "20500101",
            "lmt": "5",
        },
    )
    if result and result.get("data", {}).get("klines"):
        kline_count = len(result["data"]["klines"])
        endpoints["日K线"] = {"status": "OK", "info": f"成功获取贵州茅台K线，返回 {kline_count} 条"}
        print(_c("OK", "green") + f" (获取 {kline_count} 条)")
    else:
        endpoints["日K线"] = {"status": "FAIL", "info": "K线接口未返回数据"}
        print(_c("FAIL", "red"))

    # 4. 港股列表接口
    print("  测试 港股列表接口 ...", end=" ")
    result = _api_get(
        "https://push2.eastmoney.com/api/qt/clist/get",
        params={
            "pn": "1", "pz": "5", "po": "1", "np": "1",
            "fltt": "2", "invt": "2",
            "fs": "m:128+t:3,m:128+t:4",
            "fields": "f12,f14",
        },
    )
    if result and result.get("data", {}).get("diff"):
        total = result["data"].get("total", "?")
        endpoints["港股列表"] = {"status": "OK", "info": f"港股总计约 {total} 只"}
        print(_c("OK", "green") + f" (总计 {total} 只)")
    else:
        endpoints["港股列表"] = {"status": "FAIL", "info": "接口未返回数据"}
        print(_c("FAIL", "red"))

    # 5. 美股列表接口
    print("  测试 美股列表接口 ...", end=" ")
    result = _api_get(
        "https://push2.eastmoney.com/api/qt/clist/get",
        params={
            "pn": "1", "pz": "5", "po": "1", "np": "1",
            "fltt": "2", "invt": "2",
            "fs": "m:105+t:3,m:105+t:4",
            "fields": "f12,f14",
        },
    )
    if result and result.get("data", {}).get("diff"):
        total = result["data"].get("total", "?")
        endpoints["美股列表"] = {"status": "OK", "info": f"美股总计约 {total} 只"}
        print(_c("OK", "green") + f" (总计 {total} 只)")
    else:
        endpoints["美股列表"] = {"status": "FAIL", "info": "接口未返回数据"}
        print(_c("FAIL", "red"))

    # 6. 估值接口
    print("  测试 估值数据接口 ...", end=" ")
    result = _api_get(
        "https://push2.eastmoney.com/api/qt/stock/get",
        params={
            "secid": "1.600519",
            "fields": "f43,f44,f45,f46,f48,f50,f57,f58,f60,f116,f117,f162",
        },
    )
    if result and result.get("data"):
        data = result["data"]
        price = data.get("f43", "?")
        # push2 估值接口未带 fltt 参数时 f43 为整数分单位（如 144500 = 1445.00元），统一 /100
        price_val = round(price / 100, 2) if isinstance(price, (int, float)) and price else price
        endpoints["估值数据"] = {"status": "OK", "info": f"贵州茅台最新价: {price_val}"}
        print(_c("OK", "green"))
    else:
        endpoints["估值数据"] = {"status": "FAIL", "info": "接口未返回数据"}
        print(_c("FAIL", "red"))

    # 汇总报告
    print()
    print("  " + "=" * 55)
    print(f"  {'接口名称':20s} {'状态':10s} {'详情'}")
    print("  " + "-" * 55)
    ok_count = 0
    for name, info in endpoints.items():
        status_str = _c("✓ 可用", "green") if info["status"] == "OK" else _c("✗ 不可用", "red")
        if info["status"] == "OK":
            ok_count += 1
        print(f"  {name:20s} {status_str:14s} {info['info'][:40]}")
    print("  " + "-" * 55)
    print(f"  总计: {ok_count}/{len(endpoints)} 个接口可用")
    print()

    if ok_count == 0:
        print(_c("  [WARN] 所有接口均不可用，请检查网络连接或东方财富API状态。", "yellow"))
        print("  您可以继续后续步骤，但筛选执行可能失败。")
    elif ok_count < len(endpoints):
        missing = [n for n, i in endpoints.items() if i["status"] == "FAIL"]
        print(_c(f"  [NOTE] 以下接口暂不可用: {', '.join(missing)}", "yellow"))
        print("  相关功能将自动降级。")
    else:
        print(_c("  [OK] 所有接口连通正常，可以进行筛选。", "green"))

    print()
    # 检测完成写标记：仅当至少一个接口可用（检测有效完成）才写，后续运行跳过重复连通测试；
    # 全部接口失败（ok_count==0，网络全断）时不写标记，下次仍可重新检测
    if ok_count > 0:
        try:
            os.makedirs(os.path.dirname(PREFS_FILE), exist_ok=True)
            with open(env_flag, "w", encoding="utf-8") as f:
                f.write("ok")
        except OSError:
            pass  # 标记写入失败不影响检测结果
    return endpoints


# ============================================================
# Step 3: 市场选择（真实查询各市场股票数量）
# ============================================================

def _step_market_select():
    """真实查询A股/港股/美股当前可获取的股票数量。"""
    print()
    print(_c("─" * 60, "dim"))
    print(_c("  [市场选择] 查询各市场当前真实可获股票数量...", "bold"))
    print(_c("─" * 60, "dim"))
    print()

    markets_info = {}

    # A股
    print("  查询 A股 全市场列表 ...", end=" ")
    result = _api_get(
        "https://push2.eastmoney.com/api/qt/clist/get",
        params={
            "pn": "1", "pz": "1", "po": "1", "np": "1",
            "fltt": "2", "invt": "2",
            "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",
            "fields": "f12,f14",
        },
    )
    a_count = 0
    if result and result.get("data"):
        a_count = result["data"].get("total", 0)
        print(_c("OK", "green") + f" ({a_count} 只)")
    else:
        print(_c("查询失败", "red"))
    markets_info["A股"] = a_count

    # 港股
    print("  查询 港股 全市场列表 ...", end=" ")
    result = _api_get(
        "https://push2.eastmoney.com/api/qt/clist/get",
        params={
            "pn": "1", "pz": "1", "po": "1", "np": "1",
            "fltt": "2", "invt": "2",
            "fs": "m:128+t:3,m:128+t:4",
            "fields": "f12,f14",
        },
    )
    hk_count = 0
    if result and result.get("data"):
        hk_count = result["data"].get("total", 0)
        print(_c("OK", "green") + f" ({hk_count} 只)")
    else:
        print(_c("查询失败", "red"))
    markets_info["港股"] = hk_count

    # 美股
    print("  查询 美股 全市场列表 ...", end=" ")
    result = _api_get(
        "https://push2.eastmoney.com/api/qt/clist/get",
        params={
            "pn": "1", "pz": "1", "po": "1", "np": "1",
            "fltt": "2", "invt": "2",
            "fs": "m:105+t:3,m:105+t:4",
            "fields": "f12,f14",
        },
    )
    us_count = 0
    if result and result.get("data"):
        us_count = result["data"].get("total", 0)
        print(_c("OK", "green") + f" ({us_count} 只)")
    else:
        print(_c("查询失败", "red"))
    markets_info["美股"] = us_count

    print()
    print(f"  {'市场':12s} {'可获取股票数':>12s}  {'说明'}")
    print("  " + "-" * 50)
    for mkt, count in markets_info.items():
        note = ""
        if mkt == "A股":
            note = "沪深A股（主板/创业板/科创板，按总市值降序候选）"
        elif mkt == "港股":
            note = "港股主板 + 创业板"
        elif mkt == "美股":
            note = "NYSE + NASDAQ"
        print(f"  {mkt:12s} {count:>10,} 只  {note}")

    print()
    print("  当前选择: " + _c(_session_state["market"], "cyan"))
    print()
    print("  输入选择: [1] A股  [2] 港股  [3] 美股  [4] 全部  [Enter] 保持不变")
    print("           也可以直接输入市场名（如 港股 / 美股 / 全选 / all），s 跳过本步，b 返回上一步")
    print()
    print("  提示: 主流程支持 A股/港股/美股 三市场全功能执行；")
    print("        估值/财务/技术面策略三市场真实可用（港股/美股财务摘要走东财数据中心 GMAININDICATOR 报表）；")
    print("        S15 在美股的资金流辅助条件不可用（无对应公开口径），技术面核心条件仍如实判定。")
    print()

    return markets_info


# ============================================================
# Step 4: 策略适配（基于真实大盘MA均线判断多空）
# ============================================================

# ============================================================
# 策略适配三套方案（激进/稳健/保守）
# 策略归类基于各策略真实算法逻辑（趋势进攻 vs 防御价值），
# 仅描述风险特征与适用场景，不构成收益承诺与投资建议。
# 三套方案合计覆盖全部 23 种策略，无重复、无遗漏。
# ============================================================
RECOMMEND_PLANS = {
    "1": {
        "name": "激进·进取型",
        "desc": "进攻性较强、波动相对较大，适合风险承受能力较高者",
        "strategies": [
            ("S01", "红肥绿瘦", "阳线主导，顺势做多"),
            ("S02", "上涨波段", "温和放量上攻"),
            ("S08", "放量突破", "突破前高确认"),
            ("S09", "趋势分析", "均线多头排列"),
            ("S14", "费雪成长股", "成长驱动行情"),
            ("S16", "海龟交易", "唐奇安通道突破顺势"),
            ("S17", "动量策略", "趋势动量延续"),
            ("S19", "MACD金叉择时", "金叉趋势启动信号"),
            ("S20", "资金流策略", "主力净流入吸筹信号"),
            ("S21", "多周期共振", "日线周线趋势共振确认"),
            ("S22", "相对强度策略", "强势股动量加速信号"),
            ("S23", "均线趋势风控", "趋势线上站稳的顺势风控"),
        ],
    },
    "2": {
        "name": "稳健·均衡型",
        "desc": "技术面与基本面兼顾，攻守相对均衡",
        "strategies": [
            ("S03", "回调缩量", "回调企稳机会"),
            ("S05", "MACD底背离", "底部信号捕捉"),
            ("S11", "筹码集中", "主力吸筹迹象"),
            ("S12", "现金流质量", "财务质量把关"),
            ("S13", "ROE杜邦筛选", "盈利质量优选"),
            ("S18", "多年度ROE严格校验", "多年盈利质量严格把关"),
            ("S15", "长期蓄力", "底部放量启动"),
        ],
    },
    "3": {
        "name": "保守·防御型",
        "desc": "以防御为主、波动相对较小，追求安全边际",
        "strategies": [
            ("S04", "横盘调整", "蓄力突破前"),
            ("S06", "高股息策略", "防御性配置"),
            ("S07", "低估值策略", "价值洼地"),
            ("S10", "布林带下轨", "超跌反弹机会"),
        ],
    },
}


def _step_strategy_recommend():
    """基于真实上证/深证指数MA均线判断大盘环境，智能适配策略组合。"""
    print()
    print(_c("─" * 60, "dim"))
    print(_c("  [策略适配] 基于真实大盘环境智能适配...", "bold"))
    print(_c("─" * 60, "dim"))
    print()

    # 按当前所选市场获取对应真实指数K线（A股: 上证+深证 / 港股: 恒生+国企 / 美股: 道琼斯+纳指）
    market = _session_state.get("market") or config.DEFAULT_MARKET
    index_cfg = config.INDEX_SECIDS.get(market)
    if index_cfg is None:
        # "全部" 市场无单一指数代表，策略适配以A股大盘为参考
        print(_c("  [NOTE] 全部市场模式无单一指数代表，策略适配以A股大盘为参考。", "yellow"))
        index_cfg = config.INDEX_SECIDS.get(config.MARKET_A, {})
    groups = []
    for code, (name, mkt) in index_cfg.items():
        print(f"  获取 {name}({code}) 近{config.INDEX_KLINE_DAYS}日K线 ...", end=" ")
        result = _api_get(
            "https://79.push2his.eastmoney.com/api/qt/stock/kline/get",
            params={
                "secid": f"{mkt}.{code}",
                "fields1": "f1,f2,f3,f4,f5,f6",
                "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
                "klt": "101", "fqt": "1",
                "end": "20500101",
                "lmt": str(config.INDEX_KLINE_DAYS),
            },
        )
        klines = None
        if result and result.get("data", {}).get("klines"):
            klines = [line.split(",") for line in result["data"]["klines"]]
            print(_c("OK", "green") + f" ({len(klines)} 条)")
        else:
            print(_c("获取失败", "red"))
        groups.append((name, klines))

    # 分析大盘环境
    print()
    market_analysis = _analyze_market(*groups)
    env = market_analysis["environment"]
    detail = market_analysis["detail"]
    ma5 = market_analysis["ma5"]
    ma20 = market_analysis["ma20"]
    ma60 = market_analysis.get("ma60")
    idx_name = market_analysis.get("index_name") or "指数"

    print("  大盘环境判断: " + _c(env, "cyan"))
    print(f"  {detail}")
    if ma5 and ma20:
        print(f"  {idx_name}: MA5={ma5:.0f}  MA20={ma20:.0f}" + (f"  MA60={ma60:.0f}" if ma60 else ""))

    # 三套策略方案（基于真实策略逻辑分类，覆盖全部 23 种策略，无重复遗漏）
    print()
    print("  基于当前大盘环境（" + _c(env, "cyan") + "），提供三套策略组合方案供选择:")
    print("  " + "-" * 60)
    for key, plan in RECOMMEND_PLANS.items():
        print(f"  [{key}] {plan['name']}  — {plan['desc']}")
        for sid, name, reason in plan["strategies"]:
            print(f"      {sid:6s} {name:10s} {reason}")
    print("  " + "-" * 60)
    print("  说明: 方案仅按策略真实风险特征与适用场景归类（趋势进攻 vs 防御价值），")
    print("        不构成收益承诺与投资建议。可任选一套，或自定义策略ID。")
    print()

    # 市场能力边界（如实）：估值/财务/技术面策略三市场真实可用
    # （港股/美股财务摘要走 GMAININDICATOR 报表，真实返回）；
    # S15 在美股的资金流辅助条件不可用（美股无对应公开口径），技术面核心条件仍如实判定、可独立通过
    _cur_market = _session_state.get("market")
    if _cur_market == config.MARKET_HK:
        print(_c(
            "  提示: 港股技术面/估值/财务/资金流/周线策略均真实可用，23 种策略全部可用。",
            "yellow",
        ))
    elif _cur_market == config.MARKET_US:
        print(_c(
            "  提示: 美股技术面/估值/财务策略真实可用；S20 资金流、S21 多周期共振（需周线）"
            "无对应公开口径而如实不可用，其余 21 种策略可用。",
            "yellow",
        ))
    else:
        print("  A股 23 种策略全部可用（技术面/估值/财务/资金流/周线均有公开数据）。")
    print()
    print("  输入 [1]激进 [2]稳健 [3]保守 选方案，或策略ID（逗号分隔）自定义，或 Enter 保持全部启用:")

    return market_analysis, None


def _analyze_market(*groups):
    """基于真实指数K线数据判断大盘多空。

    Args:
        *groups: (指数名, K线列表) 可变参数组；K线为 CSV 行 split 后的列表，
                 优先使用第一组数据充足的指数作为判断基准。

    Returns:
        dict: {environment, ma5, ma20, ma60, detail, factor, index_name}
    """
    result = {
        "environment": "未知",
        "ma5": None,
        "ma20": None,
        "ma60": None,
        "detail": "",
        "factor": 1.0,
        "index_name": "",
    }

    # 优先使用第一组有足够数据的指数
    index_name = None
    klines = None
    for name, kls in groups:
        if kls and len(kls) >= 20:
            index_name = name
            klines = kls
            break

    if not klines:
        result["detail"] = "K线数据不足，无法判断大盘环境"
        return result

    # 格式: ["日期","开盘","收盘","最高","最低","成交量","成交额","振幅","涨跌幅","涨跌额","换手率"]
    # 逐行安全解析：东财偶发占位符"-"/缺字段时跳过，避免单条坏数据中断大盘判断
    closes = []
    for k in klines:
        try:
            closes.append(float(k[2]))
        except (ValueError, TypeError, IndexError):
            continue
    if len(closes) < 20:
        result["detail"] = "指数K线收盘价无效或不足，无法判断大盘环境"
        return result

    # 计算移动均线
    ma5 = sum(closes[-5:]) / 5
    ma20 = sum(closes[-20:]) / 20
    ma60 = sum(closes[-60:]) / 60 if len(closes) >= 60 else sum(closes) / len(closes)

    result["ma5"] = ma5
    result["ma20"] = ma20
    result["ma60"] = ma60
    result["index_name"] = index_name

    if ma5 > ma20 > ma60:
        result["environment"] = "多头"
        result["factor"] = config.MARKET_BULL_COEFFICIENT
        result["detail"] = (
            f"{index_name}: MA5({ma5:.0f}) > MA20({ma20:.0f}) > MA60({ma60:.0f})，"
            f"均线多头排列，市场处于上升趋势"
        )
    elif ma5 < ma20 < ma60:
        result["environment"] = "空头"
        result["factor"] = config.MARKET_BEAR_COEFFICIENT
        result["detail"] = (
            f"{index_name}: MA5({ma5:.0f}) < MA20({ma20:.0f}) < MA60({ma60:.0f})，"
            f"均线空头排列，市场处于下跌趋势"
        )
    else:
        result["environment"] = "震荡"
        result["factor"] = config.MARKET_OSCILLATE_COEFFICIENT
        result["detail"] = (
            f"{index_name}: MA5({ma5:.0f}), MA20({ma20:.0f}), MA60({ma60:.0f})"
            f" 交织缠绕，市场处于震荡格局"
        )

    return result


# ============================================================
# Step 5: 参数配置
# ============================================================

def _step_param_config():
    """引导式设置输出格式、TOP数量等非强制参数。"""
    print()
    print(_c("─" * 60, "dim"))
    print(_c("  [参数配置] 引导式配置筛选参数", "bold"))
    print(_c("─" * 60, "dim"))
    print()

    print("  以下参数均可跳过，直接使用默认值。")
    print()

    # 输出格式（支持动态组合）
    print("  [1] 输出形式")
    print("      可选: text | json | html | csv | all | print | 组合(逗号分隔)")
    print("      - text : 纯文本摘要报告（写文件）")
    print("      - json : 结构化JSON数据")
    print("      - html : 交互式可视化报告（含K线迷你图）")
    print("      - csv  : CSV表格（Excel/WPS直接打开）")
    print("      - all  : 同时输出四种格式")
    print("      - print: 仅控制台文字贴出（不写文件）")
    print("      - 组合 : 如 text,html 只输出所选格式")
    print("      当前: " + _c(_session_state["output_format"], "cyan"))

    # TOP-N
    print("  [2] 输出前N只")
    print("      默认显示评分最高的前50只标的")
    print("      当前: " + _c(str(_session_state["top_n"]), "cyan"))

    # 策略组合模式
    print("  [3] 策略组合模式")
    print("      可选: union | intersection | weighted")
    print("      - union       : 任一策略通过即入选（覆盖面最广）")
    print("      - intersection: 全部策略通过才入选（最严格）")
    print("      - weighted    : 加权评分排序（最灵活）")
    print("      当前: " + _c(_session_state["strategy_mode"], "cyan"))

    # 多周期验证
    status_m = "开" if _session_state["multi_period"] else "关"
    print("  [4] 多周期交叉验证")
    print("      启用后同时检查日/周线，减少假信号但耗时更长")
    print("      当前: " + _c(status_m, "cyan"))

    # 缓存
    status_c = "关" if _session_state["no_cache"] else "开"
    print("  [5] 缓存")
    print("      缓存K线数据写入后至次日 15:30 前有效，重复运行更快")
    print("      当前: " + _c(status_c, "cyan"))

    # 回复详细度
    rl = _session_state["reply_level"]
    print("  [6] 回复详细度")
    print("      可选: brief | standard | full")
    print("      - brief   : 简洁（只展示核心筛选结果 + 简短风险提示）")
    print("      - standard: 标准（大盘/策略/结果/行业/数据质量/风险声明）")
    print("      - full    : 全量（标准内容 + 每条标的完整判定理由）")
    print("      仅控制展示丰富度，不影响数据真实性")
    print("      当前: " + _c(f"{rl}（{config.REPLY_LEVEL_NAMES.get(rl, rl)}）", "cyan"))

    print()
    print("  输入配置编号修改（如 '2 30'），或 Enter 保持不变")


# ============================================================
# Step 6: 执行确认
# ============================================================

def _step_exec_confirm():
    """预览当前所有配置，确认后执行筛选。"""
    print()
    print(_c("─" * 60, "dim"))
    print(_c("  [执行确认] 预览配置并执行筛选", "bold"))
    print(_c("─" * 60, "dim"))
    print()

    print("  最终配置预览:")
    print("  " + "-" * 40)
    print(f"    市场:      {_session_state['market']}")
    print(f"    模式:      {_session_state['mode']}")
    print(f"    输出形式:  {_session_state['output_format']}")
    print(f"    回复详细度: {_session_state['reply_level']}（{config.REPLY_LEVEL_NAMES.get(_session_state['reply_level'], _session_state['reply_level'])}）")
    print(f"    输出TOP-N: {_session_state['top_n']}")
    total_strategies = len(STRATEGY_REGISTRY)
    strat_count = len(_session_state["strategy_ids"]) if _session_state["strategy_ids"] else total_strategies
    print(f"    策略数:    {strat_count} 种（{'全部' if _session_state['strategy_ids'] is None else ','.join(_session_state['strategy_ids'])}）")
    print(f"    组合模式:  {_session_state['strategy_mode']}")
    print(f"    多周期:    {'开' if _session_state['multi_period'] else '关'}")
    print(f"    缓存:      {'关' if _session_state['no_cache'] else '开'}")
    print("  " + "-" * 40)
    print()

    cmd_parts = ["python run_screening.py"]
    mkt = _session_state["market"]
    mode = _session_state["mode"]
    fmt = _session_state["output_format"]
    top_n = _session_state["top_n"]
    sm = _session_state["strategy_mode"]
    cmd_parts.append(f'--market "{mkt}"')
    cmd_parts.append(f"--mode {mode}")
    cmd_parts.append(f"--format {fmt}")
    cmd_parts.append(f"--top {top_n}")
    if _session_state["strategy_ids"]:
        sids = ','.join(s.upper() for s in _session_state['strategy_ids'])
        cmd_parts.append(f"--strategies {sids}")
    cmd_parts.append(f"--strategy-mode {sm}")
    if _session_state["multi_period"]:
        cmd_parts.append("--multi-period")
    if _session_state["no_cache"]:
        cmd_parts.append("--no-cache")
    if _session_state["output_dir"] != config.OUTPUT_DIR:
        cmd_parts.append(f'--output "{_session_state["output_dir"]}"')
    if _session_state.get("track"):
        cmd_parts.append("--track")

    full_cmd = " ".join(cmd_parts)

    print("  等效命令:")
    print("  " + _c(full_cmd, "cyan"))
    print()
    print("  确认执行？输入 [y] 执行  [n] 取消  [b] 返回修改")


# ============================================================
# 主交互循环
# ============================================================

def _get_user_input(prompt: str = "> ") -> str:
    """获取用户输入并小写化。"""
    try:
        return input(prompt).strip().lower()
    except (EOFError, KeyboardInterrupt):
        return "q"


def _handle_step_input(step_name: str, input_str: str) -> str:
    """处理步骤输入，返回下一个动作: 'next' / 'skip' / 'back' / 'quit' / 'stay'。

    同时根据 step_name 解析具体输入内容并更新 session state。
    - 'next': 已成功处理输入 → 推进到下一步
    - 'stay': 输入无效/未识别 → 停留在当前步骤重新提示
    """
    if input_str == "q":
        return "quit"
    if input_str == "s":
        return "skip"
    if input_str == "b":
        return "back"
    if input_str == "":
        return "next"

    # 步骤特定解析
    if step_name == "market_select":
        market_map = {"1": "A股", "2": "港股", "3": "美股", "4": "全部"}
        if input_str in market_map:
            _session_state["market"] = market_map[input_str]
            print(_c(f"  已选择: {_session_state['market']}", "green"))
            return "next"
        # 人性化自由输入：直接输入市场名/别名，不强制编号（用户明确需求时灵活应变）
        alias_map = {
            "a股": "A股", "a": "A股", "沪深": "A股", "沪深京": "A股", "国内": "A股",
            "港股": "港股", "hk": "港股", "港": "港股", "hongkong": "港股",
            "美股": "美股", "us": "美股", "美": "美股", "usa": "美股",
            "全部": "全部", "全选": "全部", "all": "全部", "都": "全部",
            "三个市场": "全部", "三市场": "全部", "所有市场": "全部",
        }
        norm = input_str.strip().lower().replace(" ", "")
        if norm in alias_map:
            _session_state["market"] = alias_map[norm]
            print(_c(f"  已选择: {_session_state['market']}", "green"))
            return "next"
        print(_c(f"  无法识别: {input_str}（可用: 1=A股 2=港股 3=美股 4=全部，或直接输入市场名）", "yellow"))
        return "stay"

    elif step_name == "strategy_recommend":
        # 三套方案快捷选择：1 激进 / 2 稳健 / 3 保守（覆盖全部策略的合理子集）
        if input_str in RECOMMEND_PLANS:
            plan = RECOMMEND_PLANS[input_str]
            plan_ids = [sid for sid, _, _ in plan["strategies"]]
            _session_state["strategy_ids"] = plan_ids
            print(_c(f"  已启用方案: {plan['name']}（{', '.join(plan_ids)}）", "green"))
            return "next"
        # 人性化快捷：all / 全部 恢复全部策略启用（覆盖此前选定的子集）
        if input_str in ("all", "全部", "全部策略", "恢复全部", "全选"):
            _session_state["strategy_ids"] = None
            print(_c("  已恢复全部策略启用。", "green"))
            return "next"
        if input_str:
            ids = [s.strip().upper() for s in input_str.split(",")]
            valid = [s for s in ids if s in STRATEGY_REGISTRY]
            invalid = [s for s in ids if s not in STRATEGY_REGISTRY]
            if invalid:
                print(_c(f"  无效策略: {invalid}", "red"))
            if valid:
                _session_state["strategy_ids"] = valid
                print(_c(f"  已启用策略: {', '.join(valid)}", "green"))
                return "next"
        # 全部无效 → 重新输入
        return "stay"

    elif step_name == "param_config":
        parts = input_str.split()
        if not parts:
            return "stay"
        # 支持一次修改多个参数：如 "1 text 2 30 3 weighted 4"（编号+取值成对，开关型无需取值）
        changed = False
        i = 0
        while i < len(parts):
            try:
                param_id = int(parts[i])
            except ValueError:
                print(_c(f"  输入格式错误: {parts[i]}", "red"))
                return "stay"
            i += 1
            # 开关型参数（4 多周期 / 5 缓存）：单个编号即可切换
            if param_id == 4:
                _session_state["multi_period"] = not _session_state["multi_period"]
                s = "开" if _session_state["multi_period"] else "关"
                print(_c(f"  多周期验证 → {s}", "green"))
                changed = True
                continue
            if param_id == 5:
                _session_state["no_cache"] = not _session_state["no_cache"]
                s = "关" if _session_state["no_cache"] else "开"
                print(_c(f"  缓存 → {s}", "green"))
                changed = True
                continue
            # 取值型参数（1 格式 / 2 TOP-N / 3 组合模式）需要 编号+值
            if i >= len(parts):
                print(_c(f"  参数 {param_id} 需要附带取值，如 '2 30'", "yellow"))
                return "stay"
            val = parts[i]
            i += 1
            if param_id == 1:
                fmt = val.lower()
                # 支持单格式 / 组合（逗号分隔）/ print（仅控制台文字）
                fmt_parts = [x.strip() for x in fmt.split(",") if x.strip()]
                valid_formats = {"text", "json", "html", "csv", "all", "print"}
                if fmt_parts and all(x in valid_formats for x in fmt_parts):
                    _session_state["output_format"] = ",".join(fmt_parts)
                    print(_c(f"  输出形式 → {','.join(fmt_parts)}", "green"))
                    changed = True
                else:
                    print(_c(f"  无效输出形式: {fmt}（可用 text/json/html/csv/all/print 或逗号组合如 text,html）", "red"))
                    return "stay"
            elif param_id == 2:
                try:
                    n = int(val)
                except ValueError:
                    print(_c(f"  TOP-N 须为数字: {val}", "red"))
                    return "stay"
                if not (1 <= n <= config.TOP_N_MAX):
                    print(_c(f"  TOP-N 超出范围（1~{config.TOP_N_MAX}）: {n}", "red"))
                    return "stay"
                _session_state["top_n"] = n
                print(_c(f"  TOP-N → {n}", "green"))
                changed = True
            elif param_id == 3:
                mode = val.lower()
                if mode in ("union", "intersection", "weighted"):
                    _session_state["strategy_mode"] = mode
                    print(_c(f"  组合模式 → {mode}", "green"))
                    changed = True
                else:
                    print(_c(f"  无效组合模式: {mode}", "red"))
                    return "stay"
            elif param_id == 6:
                lv = val.lower()
                if lv in config.REPLY_LEVELS:
                    _session_state["reply_level"] = lv
                    print(_c(f"  回复详细度 → {lv}（{config.REPLY_LEVEL_NAMES.get(lv, lv)}）", "green"))
                    changed = True
                else:
                    print(_c(f"  无效回复详细度: {lv}（可用 brief/standard/full）", "red"))
                    return "stay"
            else:
                print(_c(f"  无效配置编号: {param_id}", "red"))
                return "stay"
        return "next" if changed else "stay"

    elif step_name == "exec_confirm":
        if input_str == "y":
            return "execute"
        elif input_str == "n":
            return "cancel"
        elif input_str == "b":
            return "back"
        return "stay"

    elif step_name == "archive_setup":
        # 1/2 为明确选择；s/b/q/Enter 由外层统一处理（本步骤不再二次询问）
        if input_str == "1":
            _session_state["track"] = True
            print(_c("  已开启档案追踪。每次筛选结果将自动存档。", "green"))
            print(_c("  后续可使用 --analyze / --archive-report 查看策略表现。", "dim"))
            return "next"
        if input_str == "2":
            _session_state["track"] = False
            print(_c("  暂不开启。后续可通过 --track 参数手动启用。", "yellow"))
            return "next"
        return "stay"

    return "stay"


# ============================================================
# Step 7: 档案追踪设置
# ============================================================

def _step_archive_setup():
    """询问是否开启策略表现档案追踪。"""
    print()
    print("=" * 70)
    print(_c("  Step 7/7: 策略表现档案库", "bold"))
    print("=" * 70)
    print()
    print("  策略表现档案库可以追踪每次筛选结果的真实表现，")
    print("  帮你了解哪些策略在什么市场环境下更有效。")
    print()
    print("  【功能】")
    print("    - 筛选快照：每次筛选结果自动存档")
    print("    - 回测验证：7个自然日后自动回填真实收益")
    print("    - 聚合统计：策略胜率、平均收益等指标排名")
    print("    - 档案报告：生成 text/json 格式的策略表现报告")
    print()
    print("  【数据安全】")
    print("    - 数据全部存储在你电脑本地（SQLite），不上传")
    print("    - 可随时删除 archive/multi_strategy_quant_research.db 重置")
    print("    - 不影响 Skill 核心筛选功能")
    print()
    print(_c("  1=开启档案追踪  2=暂不开启  [s]跳过  [b]返回  [q]退出  [Enter]继续", "cyan"))


def _execute_screening():
    """基于 session state 执行真实筛选。

    复用 run_screening.run_pipeline 共享流水线（多市场、报告、档案一致），
    避免与主入口维护两份执行逻辑。
    """
    print()
    print("=" * 70)
    print(_c("  正在执行筛选 ...", "bold"))
    print("=" * 70)
    print()

    try:
        from run_screening import run_pipeline
    except ImportError as e:
        print(_c(f"  模块导入错误: {e}", "red"))
        print("  请确保在 scripts 目录内运行。")
        return None

    return run_pipeline(
        market=_session_state["market"],
        mode=_session_state["mode"],
        strategy_ids=_session_state["strategy_ids"],
        strategy_mode=_session_state["strategy_mode"],
        weights=_session_state["weights"],
        multi_period=_session_state["multi_period"],
        output_dir=_session_state["output_dir"],
        output_format=_session_state["output_format"],
        top_n=_session_state["top_n"],
        no_cache=_session_state["no_cache"],
        track=_session_state.get("track", False),
        reply_level=_session_state.get("reply_level", config.REPLY_LEVEL_DEFAULT),
    )


# ============================================================
# 交互式引导主入口
# ============================================================

def run_guide(skip_to_step: Optional[str] = None, **kwargs):
    """启动交互式引导向导。

    Args:
        skip_to_step: 直接跳转到指定步骤名（welcome/env_check/market_select/
                      strategy_recommend/param_config/exec_confirm/archive_setup）
        **kwargs: 可预填的初始配置覆盖
            - market
            - mode
            - strategy_ids
            - strategy_mode
            - weights
            - top_n
            - output_format
            - output_dir
            - multi_period
            - no_cache
    """
    # 应用预填配置（优先级：kwargs > 用户历史偏好 > config 默认）
    for key, value in kwargs.items():
        if key in _session_state and value is not None:
            _session_state[key] = value

    prefs = _load_prefs()
    for key, value in prefs.items():
        # 仅当 CLI/调用方未通过 kwargs 预填该键时，才用历史偏好覆盖默认值
        if key in _session_state and key not in kwargs and value is not None:
            _session_state[key] = value

    # 确定起始步骤
    start_idx = 0
    if skip_to_step and skip_to_step in STEPS:
        start_idx = STEPS.index(skip_to_step)

    step_funcs = {
        "welcome": _step_welcome,
        "env_check": _step_env_check,
        "market_select": _step_market_select,
        "strategy_recommend": _step_strategy_recommend,
        "param_config": _step_param_config,
        "exec_confirm": _step_exec_confirm,
        "archive_setup": _step_archive_setup,
    }

    step_idx = start_idx
    while step_idx < len(STEPS):
        step_name = STEPS[step_idx]

        # 执行当前步骤
        func = step_funcs[step_name]
        func()

        # 获取用户输入
        print(_c("  [s]跳过  [b]返回  [q]退出  [Enter]继续", "dim"))
        user_input = _get_user_input("> ")

        action = _handle_step_input(step_name, user_input)

        if action == "quit":
            _save_prefs()
            print()
            print(_c("  已退出引导。配置已保存，可随时通过 run_screening.py 执行筛选。", "yellow"))
            return None
        elif action == "cancel":
            _save_prefs()
            print()
            print(_c("  已取消执行。配置已保存，可随时通过 run_screening.py 重新筛选。", "yellow"))
            return None
        elif action == "back":
            step_idx = max(0, step_idx - 1)
            print(_c(f"  返回至: {STEPS[step_idx]}", "yellow"))
        elif action == "skip":
            step_idx += 1
            print(_c("  跳过当前步骤", "yellow"))
        elif action == "execute":
            _save_prefs()
            return _execute_screening()
        elif action == "next":
            step_idx += 1
        else:  # stay：输入无效/未识别，停留在当前步骤重新提示
            print(_c("  输入未识别，请重新输入。", "yellow"))

    # 所有步骤走完：若未在 exec_confirm 确认执行（跳过/回车跳过），
    # 用最终配置补齐执行，保证"引导完成"必然产出筛选结果，不空手而归。
    print()
    print(_c("  引导完成！", "green"))
    _save_prefs()
    return _execute_screening()


# ============================================================
# CLI 入口（用于独立启动）
# ============================================================

def main():
    """命令行独立启动引导。"""
    import argparse

    parser = argparse.ArgumentParser(
        description="multi-strategy-quant-research-pro 交互式引导向导",
    )
    parser.add_argument("--step", default=None,
                        choices=STEPS,
                        help="直接跳转到指定步骤")
    # 预填参数（支持 CLI 预填市场等配置）
    parser.add_argument("--market", default=None,
                        help="预填目标市场: A股/港股/美股/全部")
    parser.add_argument("--mode", default=None,
                        help="预填筛选范围: full")
    parser.add_argument("--strategies", default=None,
                        help="预填策略ID（逗号分隔），如 S01,S03,S05")
    parser.add_argument("--strategy-mode", default=None,
                        choices=["union", "intersection", "weighted"],
                        help="预填策略组合模式")
    parser.add_argument("--top", type=int, default=None,
                        help="预填输出前N只标的")

    args = parser.parse_args()

    kwargs = {
        "market": args.market,
        "mode": args.mode,
        # _session_state["strategy_ids"] 为列表（None = 全部启用）
        "strategy_ids": [s.strip().upper() for s in args.strategies.split(",")]
        if args.strategies else None,
        "strategy_mode": args.strategy_mode,
        "top_n": args.top,
    }
    run_guide(skip_to_step=args.step, **kwargs)


if __name__ == "__main__":
    main()
