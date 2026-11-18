"""交易系统并发安全审计模块（多线程 + asyncio）。

基于 Python AST 静态分析（不执行代码、不修改被测文件），检测：
- 多线程：共享全局状态无锁、竞态（check-then-act）、止损失效逻辑、锁内阻塞、死锁风险
- asyncio：async 函数内阻塞调用、取消异常被吞、共享状态无保护、回测与实盘一致性

定位：确定性静态规则，输出可追溯问题（文件:行号 + 证据 + 修复建议）。
"""

import ast
import os
from typing import Optional

from .security import Finding, AuditResult

# ── 需 AST 解析的辅助 ──


def _read_source(path: str) -> Optional[str]:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return None


def _module_level_names(tree: ast.AST) -> set:
    """收集模块级赋值的目标名（全局共享状态候选）。"""
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            for t in (node.targets if isinstance(node, ast.Assign) else [node.target]):
                if isinstance(t, ast.Name):
                    names.add(t.id)
    return names


def _lock_guarded_node_ids(scope: ast.AST) -> set:
    """收集 scope 内 with lock: 块覆盖的所有节点 id（用于识别锁保护区域）。"""
    guarded = set()
    for node in ast.walk(scope):
        if isinstance(node, ast.With):
            is_lock = False
            for item in node.items:
                ctx = item.context_expr
                if isinstance(ctx, (ast.Name, ast.Attribute)):
                    is_lock = True
                elif isinstance(ctx, ast.Call) and getattr(ctx.func, "attr", "") in ("acquire", "release"):
                    is_lock = True
            if is_lock:
                for sub in ast.walk(node):
                    guarded.add(id(sub))
    return guarded



def _in_thread_target(tree: ast.AST) -> bool:
    """文件是否创建 threading.Thread。"""
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
            if n.func.attr == "Thread" and "threading" in (
                getattr(n.func.value, "id", "") or ""
            ):
                return True
        if isinstance(n, ast.ImportFrom) and n.module == "threading":
            return True
    return False


# ── 多线程审计 ──


def _audit_threading(source: str, tree: ast.AST, fpath: str, result: AuditResult) -> None:
    has_thread = _in_thread_target(tree)
    module_globals = _module_level_names(tree)

    for node in ast.walk(tree):
        # 1) 共享全局状态无锁：函数体内修改模块级可变对象（dict/list 下标赋值）
        if isinstance(node, ast.FunctionDef) and has_thread:
            guarded = _lock_guarded_node_ids(node)
            for sub in ast.walk(node):
                if isinstance(sub, ast.Subscript) and isinstance(sub.value, ast.Name):
                    if sub.value.id in module_globals and isinstance(sub.ctx, ast.Store):
                        if id(sub) in guarded:
                            continue  # 锁内赋值已受保护
                        result.findings.append(Finding(
                            file=fpath, line=sub.lineno,
                            rule="共享全局状态无锁",
                            severity="高",
                            match=f"{sub.value.id}[...] = ...",
                            message=f"多线程并发修改全局对象 {sub.value.id} 无锁保护，存在数据竞争",
                            fix="对全局共享对象加 threading.Lock，写入前 acquire；或改用线程安全的并发容器/每线程副本。",
                        ))

        # 2) 竞态 check-then-act：if X not in DICT: 块内 DICT[X]=...
        if isinstance(node, ast.If):
            test = node.test
            inner = None
            # `x not in d` 在 AST 中为 Compare(ops=[NotIn])；`not x in d` 为 UnaryOp(Not, Compare(In))
            if isinstance(test, ast.Compare) and test.ops and isinstance(test.ops[0], ast.NotIn):
                inner = test
            elif isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not) \
                    and isinstance(test.operand, ast.Compare) and test.operand.ops \
                    and isinstance(test.operand.ops[0], ast.In):
                inner = test.operand
            if inner is not None and isinstance(inner.left, ast.Name) \
                    and isinstance(inner.comparators[0], ast.Name):
                dictname = inner.comparators[0].id
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Subscript) and isinstance(sub.value, ast.Name) \
                            and sub.value.id == dictname and isinstance(sub.ctx, ast.Store):
                        if has_thread:
                            guarded = _lock_guarded_node_ids(tree)
                            if id(node) in guarded:
                                continue  # 已在锁内，原子
                            result.findings.append(Finding(
                                file=fpath, line=node.lineno,
                                rule="竞态 check-then-act",
                                severity="高",
                                match=f"if {inner.left.id} not in {dictname}: {dictname}[...]=",
                                message=f"先检查再写入 {dictname} 的非原子操作，多线程下存在竞态窗口",
                                fix="将检查与写入置于同一锁内（with lock: if ... not in ...: ...=），或用 setdefault。",
                            ))

        # 3) 止损失效：止损判断中比较方向可疑（止损应为 价格<=止损价 触发）
        if isinstance(node, ast.Compare):
            src_seg = ast.get_source_segment(source, node) or ""
            lowered = src_seg.lower()
            if ("stop" in lowered or "止损" in lowered or "stop_loss" in lowered):
                # 正常止损：close <= stop_loss；若出现 > 且被赋值给状态，提示复核
                ops = [type(o).__name__ for o in node.ops]
                if "Gt" in ops or "GtE" in ops:
                    if any(k in lowered for k in ("price", "close", "last", "cur")):
                        result.findings.append(Finding(
                            file=fpath, line=node.lineno,
                            rule="止损失效风险",
                            severity="中",
                            match=src_seg[:70],
                            message=f"止损判断疑似方向反转（{src_seg}）：止损通常应在 价格<=止损价 时触发",
                            fix="核对止损比较方向：触发止损应为 close <= stop_loss；若此处是反向判断请确认语义。",
                        ))

        # 4) 锁内阻塞：with lock: 块内存在 time.sleep / 同步网络请求
        if isinstance(node, ast.With):
            for item in node.items:
                ctx = item.context_expr
                # 兼容 `with lock:` 与 `with lock.acquire():` 两种写法
                is_lock = isinstance(ctx, (ast.Name, ast.Attribute)) or (
                    isinstance(ctx, ast.Call) and getattr(ctx.func, "attr", "") in ("acquire", "release"))
                if is_lock:
                    for sub in ast.walk(node):
                        if isinstance(sub, ast.Call):
                            fname = getattr(sub.func, "attr", "") or getattr(sub.func, "id", "")
                            if fname in ("sleep", "get", "post", "request"):
                                result.findings.append(Finding(
                                    file=fpath, line=sub.lineno,
                                    rule="锁内阻塞",
                                    severity="中",
                                    match=f"{fname}(...) 位于锁内",
                                    message=f"持锁期间执行 {fname} 阻塞操作，会长时间占用锁，放大并发延迟",
                                    fix="将耗时/网络操作移出锁外；锁内只保留临界区读写。",
                                ))

        # 5) 嵌套锁顺序不一致（死锁风险）：两个 with lock 嵌套
        if isinstance(node, ast.With):
            outer_names = set()
            for item in node.items:
                ctx = item.context_expr
                if isinstance(ctx, ast.Name):
                    outer_names.add(ctx.id)
                elif isinstance(ctx, ast.Attribute):
                    outer_names.add(ast.unparse(ctx) if hasattr(ast, "unparse") else ctx.attr)
                elif isinstance(ctx, ast.Call) and isinstance(ctx.func, ast.Name):
                    outer_names.add(ctx.func.id)
            if outer_names:
                for sub in ast.walk(node):
                    if sub is not node and isinstance(sub, ast.With):
                        for it in sub.items:
                            inner = it.context_expr
                            inner_name = None
                            if isinstance(inner, ast.Name):
                                inner_name = inner.id
                            elif isinstance(inner, ast.Attribute):
                                inner_name = ast.unparse(inner) if hasattr(ast, "unparse") else inner.attr
                            elif isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name):
                                inner_name = inner.func.id
                            if inner_name and inner_name in outer_names:
                                result.findings.append(Finding(
                                    file=fpath, line=sub.lineno,
                                    rule="嵌套锁/死锁风险",
                                    severity="中",
                                    match=f"{inner_name} 在 {", ".join(outer_names)} 内再次加锁",
                                    message=f"同一把锁 {inner_name} 被嵌套重复加锁，存在死锁风险",
                                    fix="确保锁的获取顺序全局一致，避免同一线程重复加同一把锁；使用可重入锁 RLock 若确需嵌套。",
                                ))
                                break


# ── asyncio 审计 ──


def _audit_asyncio(source: str, tree: ast.AST, fpath: str, result: AuditResult) -> None:
    module_globals = _module_level_names(tree)
    # 仅当文件包含 async 定义或显式引用 asyncio 时，asyncio 规则才适用
    # （避免对纯多线程/同步文件误报 async 类问题）
    has_async = any(isinstance(n, ast.AsyncFunctionDef) for n in ast.walk(tree)) or "asyncio" in source

    for node in ast.walk(tree):
        # 6) async 函数内阻塞调用
        if isinstance(node, ast.AsyncFunctionDef):
            for sub in ast.walk(node):
                if isinstance(sub, ast.Call):
                    fname = getattr(sub.func, "attr", "") or getattr(sub.func, "id", "")
                    if fname in ("sleep",) and "time" in (getattr(sub.func.value, "id", "") or ""):
                        result.findings.append(Finding(
                            file=fpath, line=sub.lineno,
                            rule="async 中阻塞调用",
                            severity="高",
                            match="time.sleep(...)",
                            message="async 函数内使用 time.sleep 阻塞事件循环，应改用 await asyncio.sleep()",
                            fix="将 time.sleep 替换为 await asyncio.sleep()；同步网络/文件 IO 用 asyncio.to_thread 或异步客户端。",
                        ))
                    if fname in ("get", "post", "request") and "requests" in (
                            getattr(sub.func.value, "attr", "") or getattr(sub.func.value, "id", "")):
                        result.findings.append(Finding(
                            file=fpath, line=sub.lineno,
                            rule="async 中同步网络请求",
                            severity="高",
                            match=f"requests.{fname}(...)",
                            message="async 函数内使用同步 requests 阻塞事件循环",
                            fix="改用 httpx/aiohttp 异步客户端，或在 asyncio.to_thread 中运行同步请求。",
                        ))

        # 7) 取消处理：裸 except 吞 CancelledError
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            if isinstance(node, ast.ExceptHandler) and any(
                isinstance(n, ast.Pass) for n in node.body
            ):
                result.findings.append(Finding(
                    file=fpath, line=node.lineno,
                    rule="异步取消异常被吞",
                    severity="中",
                    match="except: pass",
                    message="裸 except 会吞掉 asyncio.CancelledError，导致任务无法被正确取消",
                    fix="用 except asyncio.CancelledError: raise 先重抛取消，再处理其他异常；避免裸 except。",
                ))

        # 8) async 任务共享全局状态无保护（仅 async 文件）
        if has_async and isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
            for sub in ast.walk(node):
                if isinstance(sub, ast.Subscript) and isinstance(sub.value, ast.Name) \
                        and sub.value.id in module_globals and isinstance(sub.ctx, ast.Store):
                    result.findings.append(Finding(
                        file=fpath, line=sub.lineno,
                        rule="并发共享状态无保护",
                        severity="中",
                        match=f"{sub.value.id}[...] = ...",
                        message=f"并发任务修改全局 {sub.value.id} 无同步保护，存在数据竞争",
                        fix="使用 asyncio.Lock 保护共享状态，或让任务返回结果由主协程汇总。",
                    ))

        # 9) 回测与实盘一致性：滑点/手续费参数不一致
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and any(
                    k in t.id.lower() for k in ("slippage", "commission", "fee", "cost")
                ):
                    val = ast.unparse(node.value) if hasattr(ast, "unparse") else ""
                    if val:
                        result.findings.append(Finding(
                            file=fpath, line=node.lineno,
                            rule="回测实盘成本参数待核对",
                            severity="低",
                            match=f"{t.id} = {val}",
                            message=f"成本/滑点参数 {t.id} = {val}：请核对回测与实盘取值是否一致，避免回测失真",
                            fix="确保回测 slippage/commission 与实盘经纪商口径一致，并在报告中声明参数。",
                        ))

        # 10) look-ahead bias：回测中用当日未来数据（如用 klines[i+1] 决策）
        if isinstance(node, ast.Subscript):
            idx = node.slice
            if isinstance(idx, ast.BinOp) and isinstance(idx.op, ast.Add):
                if isinstance(idx.left, ast.Name) and idx.left.id.lower() in ("i", "idx", "index"):
                    if isinstance(idx.right, ast.Constant) and isinstance(idx.right.value, int) and idx.right.value > 0:
                        result.findings.append(Finding(
                            file=fpath, line=node.lineno,
                            rule="前视偏差风险（look-ahead）",
                            severity="高",
                            match=f"xxx[i+{idx.right.value}]",
                            message=f"使用未来索引 i+{idx.right.value} 引用数据，回测中可能引入前视偏差（用未来数据决策）",
                            fix="回测决策只能使用截至当日的收盘/信号数据；若为信号移1日应显式 shift 并在文档说明。",
                        ))


# ── 入口 ──


def audit_file_for_concurrency(path: str, result: AuditResult) -> None:
    """对单个 Python 文件执行并发安全审计（多线程 + asyncio）。"""
    source = _read_source(path)
    if source is None:
        result.findings.append(Finding(
            file=path, line=0, rule="文件读取失败", severity="低",
            match="", message="无法读取文件",
        ))
        return
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        result.findings.append(Finding(
            file=path, line=getattr(e, "lineno", 0) or 0, rule="语法错误",
            severity="低", match="", message=f"被测文件存在语法错误（{e}）",
        ))
        return
    result.scanned_files += 1
    result.scanned_lines += source.count("\n") + 1
    _audit_threading(source, tree, path, result)
    _audit_asyncio(source, tree, path, result)


def audit_dir_for_concurrency(path: str, result: AuditResult) -> None:
    """递归审计目录下所有 .py 文件的并发安全。"""
    if os.path.isfile(path):
        if path.endswith(".py"):
            audit_file_for_concurrency(path, result)
        return
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__", ".venv", "venv", "node_modules")]
        for fn in files:
            if fn.endswith(".py"):
                audit_file_for_concurrency(os.path.join(root, fn), result)
