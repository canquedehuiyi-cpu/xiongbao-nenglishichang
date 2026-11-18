#!/usr/bin/env python3
"""validate.py — 多策略量化研究 skill 自检脚本（仅标准库，零外部依赖）。

校验项：
1. SKILL.md frontmatter 合规（仅 name / description 两个必需字段；name 仅含小写字母/数字/连字符/下划线且以字母数字首尾）
2. 版本一致性（config.VERSION 与 SKILL.md 正文声明版本一致）
3. 引用完整性（SKILL.md 提及的 scripts 路径全部存在）
4. 策略注册表一致性（STRATEGY_REGISTRY 覆盖 S01-S23 共 23 种）
5. Python 语法（scripts/ 下全部 .py 通过编译检查）
6. 表述规范性检查（无开发日志 / 版本历史痕迹，如"实测/旧实现/修复 2026/旧版本号"）
7. 标准结构（顶层仅 SKILL.md 与 scripts/，无 README/安装指南等元文档）

用法：python scripts/validate.py
退出码：0=全部通过；1=存在未通过项。
"""
import os
import re
import sys
import py_compile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(ROOT, "SKILL.md")
SCRIPTS = os.path.join(ROOT, "scripts")
FAIL: list[str] = []


def check(ok: bool, label: str) -> None:
    print(("  ✓ " if ok else "  ✗ ") + label)
    if not ok:
        FAIL.append(label)


def _frontmatter() -> dict:
    text = open(SKILL, encoding="utf-8").read()
    m = re.match(r"^---\n([\s\S]*?)\n---", text)
    if not m:
        return {}
    fields = {}
    for line in m.group(1).splitlines():
        k, _, v = line.partition(":")
        fields[k.strip()] = v.strip()
    fields["_raw"] = m.group(1)  # frontmatter 原文（嵌套字段存在性检查用）
    return fields


def main() -> int:
    print("== 1. frontmatter 合规 ==")
    fm = _frontmatter()
    raw = fm.get("_raw", "")
    fm_keys = [ln.split(":", 1)[0].strip() for ln in raw.splitlines() if ln.strip()]
    check(fm.get("name") == "multi-strategy-quant-research-pro", "name 为 multi-strategy-quant-research-pro")
    check(bool(fm.get("description")), "frontmatter 含 description 字段")
    name = fm.get("name", "")
    name_ok = bool(re.fullmatch(r"[a-z0-9](?:[a-z0-9_-]*[a-z0-9])?", name))
    check(name_ok, "name 仅含小写字母/数字/连字符/下划线且以字母或数字首尾")
    check(set(fm_keys) == {"name", "description"}, f"frontmatter 仅 name/description 两字段（实际 {fm_keys}）")

    print("== 2. 版本一致性 ==")
    sys.path.insert(0, SCRIPTS)
    import config  # noqa: E402
    body = open(SKILL, encoding="utf-8").read().split("---", 2)[-1]
    mv = re.search(r"v(\d+\.\d+\.\d+)", body)
    body_ver = mv.group(1) if mv else None
    check(config.VERSION == body_ver, f"config.VERSION({config.VERSION}) 与 SKILL.md 正文版本({body_ver})一致")

    print("== 3. 引用完整性（SKILL.md 提及的 scripts 路径）==")
    skill = open(SKILL, encoding="utf-8").read()
    refs = sorted(set(re.findall(r"scripts/[\w/]+\.py", skill)))
    for r in refs:
        check(os.path.exists(os.path.join(ROOT, r)), f"{r} 存在")
    print(f"  引用 {len(refs)} 个 scripts 路径")

    print("== 4. 策略注册表一致性 ==")
    import strategies  # noqa: E402
    registry = strategies.STRATEGY_REGISTRY
    declared = {f"S{i:02d}" for i in range(1, 24)}
    actual = set(registry.keys())
    check(declared == actual, f"注册表覆盖 S01-S23（实际 {len(actual)} 种）")
    missing = declared - actual
    extra = actual - declared
    if missing:
        check(False, f"缺失策略: {sorted(missing)}")
    if extra:
        check(False, f"多余策略: {sorted(extra)}")

    print("== 5. Python 语法 ==")
    py_files = []
    for root, _, files in os.walk(SCRIPTS):
        if "__pycache__" in root:
            continue
        for f in files:
            if f.endswith(".py"):
                py_files.append(os.path.join(root, f))
    err = 0
    for p in py_files:
        try:
            py_compile.compile(p, doraise=True)
        except py_compile.PyCompileError as e:
            check(False, f"{os.path.relpath(p, ROOT)} 语法错误: {e}")
            err += 1
    if err == 0:
        check(True, f"全部 {len(py_files)} 个 .py 编译通过")

    print("== 6. 表述规范性检查 ==")
    pattern = re.compile(r"实测|旧实现|旧逻辑|修复 2026|2026-08|v1\.0\.[0-3]|dev\s+log")
    hits = []
    for root, _, files in os.walk(os.path.join(ROOT, "scripts")):
        if "__pycache__" in root:
            continue
        for f in files:
            if f.endswith(".py"):
                p = os.path.join(root, f)
                if os.path.basename(p) == "validate.py":
                    continue  # 自检脚本自身含检查词，跳过
                for i, line in enumerate(open(p, encoding="utf-8"), 1):
                    if pattern.search(line):
                        hits.append(f"{os.path.relpath(p, ROOT)}:{i}")
    check(not hits, f"表面无开发日志话术（残留 {len(hits)} 处）")
    for h in hits[:5]:
        print(f"    {h}")

    print("== 7. 标准结构 ==")
    top = sorted(os.listdir(ROOT))
    check(set(top) <= {"SKILL.md", "scripts"}, f"顶层仅 SKILL.md/scripts（实际 {top}）")
    banned = ["README.md", "INSTALLATION_GUIDE.md", "CHANGELOG.md", "QUICK_REFERENCE.md"]
    found_banned = []
    for root, _, files in os.walk(ROOT):
        if "__pycache__" in root:
            continue
        for f in files:
            if f in banned:
                found_banned.append(os.path.relpath(os.path.join(root, f), ROOT))
    check(not found_banned, f"无 README/安装指南/变更日志等元文档（发现 {found_banned}）")

    print("== 8. 回测引擎与扩展数据层 ==")
    # 回测引擎模块存在性
    bt_dir = os.path.join(SCRIPTS, "backtest")
    check(os.path.isdir(bt_dir), "backtest/ 回测引擎目录存在")
    for mod in ["__init__.py", "engine.py", "metrics.py", "optimizer.py"]:
        check(os.path.isfile(os.path.join(bt_dir, mod)), f"backtest/{mod} 存在")
    # run_backtest.py 入口
    check(os.path.isfile(os.path.join(SCRIPTS, "run_backtest.py")), "run_backtest.py 回测入口存在")
    # 扩展数据层
    ext_file = os.path.join(SCRIPTS, "data", "extended.py")
    check(os.path.isfile(ext_file), "data/extended.py 扩展数据层存在")
    # 回测引擎可导入
    try:
        from backtest import BacktestEngine, BacktestConfig, calculate_metrics, optimize_params
        check(True, "回测引擎模块可正常导入")
    except Exception as e:
        check(False, f"回测引擎导入失败: {e}")
    # 扩展数据层可导入
    try:
        from data import extended
        check(True, f"扩展数据层可导入（{len(extended.EXTENDED_DATA_SOURCES)} 个数据源）")
    except Exception as e:
        check(False, f"扩展数据层导入失败: {e}")
    # 扩展数据源函数齐全
    fetch_funcs = [
        "fetch_minute_kline", "fetch_balance_sheet", "fetch_income_statement",
        "fetch_cashflow_statement", "fetch_dragon_tiger", "fetch_margin_trading",
        "fetch_northbound_holding", "fetch_dividend_history", "fetch_shareholder_count",
    ]
    missing_fn = [f for f in fetch_funcs if not hasattr(extended, f)]
    check(not missing_fn, f"扩展数据源函数齐全（缺失 {missing_fn}）")

    print("== 9. 因子库完整性 ==")
    factors_dir = os.path.join(SCRIPTS, "factors")
    check(os.path.isdir(factors_dir), "factors/ 因子库目录存在")
    for mod in ["__init__.py", "technical.py", "value.py", "quality.py", "growth.py", "money_flow.py", "ic_test.py", "composite.py"]:
        check(os.path.isfile(os.path.join(factors_dir, mod)), f"factors/{mod} 存在")
    try:
        from factors import ALL_FACTORS, FACTOR_GROUPS, get_factor_count
        count = get_factor_count()
        check(count == 47, f"因子总数47个（实际 {count} 个）")
        expected_groups = {"技术": 18, "价值": 9, "质量": 9, "成长": 6, "资金": 5}
        for cat, expected in expected_groups.items():
            actual = len(FACTOR_GROUPS.get(cat, []))
            check(actual == expected, f"{cat}因子 {expected} 个（实际 {actual} 个）")
    except Exception as e:
        check(False, f"因子库导入失败: {e}")
    # 多因子合成与IC检验公共 API
    try:
        from factors import (composite_equal_weight, composite_ic_weight,
                             composite_custom_weight, select_effective_factors,
                             format_composite_result, rank_normalize,
                             calculate_ic_series, stratified_backtest, evaluate_factor)
        check(True, "多因子合成与IC检验公共 API 可正常导入")
    except Exception as e:
        check(False, f"多因子合成/IC检验导入失败: {e}")

    print("== 10. 自进化引擎与市场环境引擎 ==")
    # 自进化引擎
    evo_dir = os.path.join(SCRIPTS, "self_evolution")
    check(os.path.isdir(evo_dir), "self_evolution/ 自进化引擎目录存在")
    for mod in ["__init__.py", "knowledge_base.py", "param_adapter.py", "factor_weight.py", "strategy_selector.py"]:
        check(os.path.isfile(os.path.join(evo_dir, mod)), f"self_evolution/{mod} 存在")
    # 市场环境引擎
    regime_dir = os.path.join(SCRIPTS, "market_regime")
    check(os.path.isdir(regime_dir), "market_regime/ 市场环境引擎目录存在")
    for mod in ["__init__.py", "detector.py", "sector_rotation.py", "strategy_recommender.py"]:
        check(os.path.isfile(os.path.join(regime_dir, mod)), f"market_regime/{mod} 存在")
    # 可导入性
    try:
        from self_evolution import SelfEvolutionEngine, KnowledgeBase, ParamAdapter, FactorWeightAdapter, StrategySelector
        check(True, "自进化引擎模块可正常导入")
    except Exception as e:
        check(False, f"自进化引擎导入失败: {e}")
    try:
        from market_regime import MarketRegimeEngine, detect_market_regime, analyze_sector_rotation, recommend_strategies_by_regime
        check(True, "市场环境引擎模块可正常导入")
    except Exception as e:
        check(False, f"市场环境引擎导入失败: {e}")

    print("== 11. 组合优化/动态仓位/因子正交化/回测精度模块完整性 ==")
    # 组合优化器
    portfolio_dir = os.path.join(SCRIPTS, "portfolio")
    check(os.path.isdir(portfolio_dir), "portfolio/ 组合优化目录存在")
    for mod in ["__init__.py", "optimizer.py", "style_neutral.py"]:
        check(os.path.isfile(os.path.join(portfolio_dir, mod)), f"portfolio/{mod} 存在")
    # 动态仓位
    position_dir = os.path.join(SCRIPTS, "position")
    check(os.path.isdir(position_dir), "position/ 动态仓位目录存在")
    for mod in ["__init__.py", "sizing.py"]:
        check(os.path.isfile(os.path.join(position_dir, mod)), f"position/{mod} 存在")
    # 因子正交化
    check(os.path.isfile(os.path.join(SCRIPTS, "factors", "orthogonal.py")), "factors/orthogonal.py 存在")
    # 回测精度
    check(os.path.isfile(os.path.join(SCRIPTS, "backtest", "precision.py")), "backtest/precision.py 存在")
    # 可导入性
    try:
        from portfolio import optimize_portfolio
        check(True, "组合优化器可正常导入")
    except Exception as e:
        check(False, f"组合优化器导入失败: {e}")
    try:
        from position import kelly_position, atr_position, signal_strength_position
        check(True, "动态仓位模块可正常导入")
    except Exception as e:
        check(False, f"动态仓位导入失败: {e}")
    try:
        from factors.orthogonal import calc_correlation_matrix, gram_schmidt_orthogonalize, neutralize_factor
        check(True, "因子正交化可正常导入")
    except Exception as e:
        check(False, f"因子正交化导入失败: {e}")
    try:
        from backtest.precision import stratified_backtest, overfitting_detection, factor_decay_curve
        check(True, "回测精度模块可正常导入")
    except Exception as e:
        check(False, f"回测精度导入失败: {e}")

    print("== 12. 多时间框架/市场宽度/HTML图表模块完整性 ==")
    # 多时间框架
    check(os.path.isfile(os.path.join(SCRIPTS, "indicators", "multi_timeframe.py")),
          "indicators/multi_timeframe.py 存在")
    # 市场宽度
    check(os.path.isfile(os.path.join(SCRIPTS, "market_regime", "breadth.py")),
          "market_regime/breadth.py 存在")
    # HTML 可视化报告
    check(os.path.isdir(os.path.join(SCRIPTS, "reports")), "reports/ 报告目录存在")
    check(os.path.isfile(os.path.join(SCRIPTS, "reports", "html_report.py")),
          "reports/html_report.py 存在")
    # 可导入性
    try:
        from indicators.multi_timeframe import multi_timeframe_resonance
        check(True, "多时间框架共振可正常导入")
    except Exception as e:
        check(False, f"多时间框架导入失败: {e}")
    try:
        from market_regime.breadth import market_breadth_score
        check(True, "市场宽度指标可正常导入")
    except Exception as e:
        check(False, f"市场宽度导入失败: {e}")
    try:
        from reports.html_report import generate_html_report
        check(True, "HTML可视化报告模块可正常导入")
    except Exception as e:
        check(False, f"HTML可视化报告导入失败: {e}")

    print("== 13. 信号质量/数据质量/性能优化模块完整性 ==")
    # 信号质量过滤
    check(os.path.isfile(os.path.join(SCRIPTS, "indicators", "signal_quality.py")),
          "indicators/signal_quality.py 存在")
    # 数据质量保障
    check(os.path.isfile(os.path.join(SCRIPTS, "data", "quality.py")),
          "data/quality.py 存在")
    # 性能优化
    check(os.path.isdir(os.path.join(SCRIPTS, "utils")), "utils/ 工具目录存在")
    check(os.path.isfile(os.path.join(SCRIPTS, "utils", "performance.py")),
          "utils/performance.py 存在")
    # 可导入性
    try:
        from indicators.signal_quality import signal_quality_score
        check(True, "信号质量过滤可正常导入")
    except Exception as e:
        check(False, f"信号质量导入失败: {e}")
    try:
        from data.quality import data_quality_report
        check(True, "数据质量保障可正常导入")
    except Exception as e:
        check(False, f"数据质量导入失败: {e}")
    try:
        from utils.performance import SmartCache, precompute_indicators, PerformanceMonitor
        check(True, "性能优化模块可正常导入")
    except Exception as e:
        check(False, f"性能优化导入失败: {e}")

    print("== 14. 意图解析/多模式回复/错误自愈/可观测性模块完整性 ==")
    # 意图解析（scripts/intent.py 为主流程真实意图解析，23策略对齐）
    check(os.path.isfile(os.path.join(SCRIPTS, "intent.py")),
          "scripts/intent.py 存在")
    # 多模式回复
    check(os.path.isfile(os.path.join(SCRIPTS, "core", "response_engine.py")),
          "core/response_engine.py 存在")
    # 错误自愈
    check(os.path.isfile(os.path.join(SCRIPTS, "core", "resilience.py")),
          "core/resilience.py 存在")
    # 可观测性
    check(os.path.isfile(os.path.join(SCRIPTS, "core", "observability.py")),
          "core/observability.py 存在")
    # 可导入性
    try:
        from intent import resolve_intent
        check(True, "意图解析（scripts/intent.py）可正常导入")
    except Exception as e:
        check(False, f"意图解析导入失败: {e}")
    try:
        from core.response_engine import ResponseEngine, detect_user_level
        check(True, "多模式回复可正常导入")
    except Exception as e:
        check(False, f"多模式回复导入失败: {e}")
    try:
        from core.resilience import ResilienceManager, CircuitBreaker
        check(True, "错误自愈可正常导入")
    except Exception as e:
        check(False, f"错误自愈导入失败: {e}")
    try:
        from core.observability import ObservabilityHub, get_observability
        check(True, "可观测性可正常导入")
    except Exception as e:
        check(False, f"可观测性导入失败: {e}")

    print("== 15. 单股诊断 / 代码审计 / 定向筛选模块 ==")
    # 单股诊断入口
    check(os.path.isfile(os.path.join(SCRIPTS, "run_diagnose.py")), "run_diagnose.py 单股诊断入口存在")
    # 代码审计入口与包
    check(os.path.isfile(os.path.join(SCRIPTS, "run_audit.py")), "run_audit.py 代码审计入口存在")
    audit_dir = os.path.join(SCRIPTS, "audit")
    check(os.path.isdir(audit_dir), "audit/ 代码审计包目录存在")
    for mod in ["__init__.py", "security.py", "concurrency.py"]:
        check(os.path.isfile(os.path.join(audit_dir, mod)), f"audit/{mod} 存在")
    # 定向筛选数据函数导出
    try:
        from data import fetch_screened_a_share_codes
        check(True, "定向筛选数据函数可正常导入")
    except Exception as e:
        check(False, f"定向筛选数据函数导入失败: {e}")
    # 审计包可导入
    try:
        from audit import run_security_audit, audit_dir_for_concurrency, audit_file_for_concurrency
        check(True, "代码审计包可正常导入")
    except Exception as e:
        check(False, f"代码审计包导入失败: {e}")
    # S23 趋势风控策略
    try:
        from strategies.s20_trend_safeguard import check_s23_trend_safeguard
        check(True, "S23 均线趋势风控策略可正常导入")
    except Exception as e:
        check(False, f"S23 策略导入失败: {e}")

    print()
    if FAIL:
        print(f"结果: {len(FAIL)} 项未通过")
        return 1
    print("结果: 全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
