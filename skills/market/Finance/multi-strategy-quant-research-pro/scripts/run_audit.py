"""交易系统代码审计命令：静态安全扫描 + 多线程/异步并发安全审计。

用法：
    python run_audit.py --target 交易系统.py                 # 默认全量审计
    python run_audit.py --target ./src --mode security       # 仅安全扫描
    python run_audit.py --target ./src --mode concurrency    # 仅并发审计
    python run_audit.py --target ./src --mode all

定位：
- 确定性静态规则扫描（AST/正则），不执行被测代码、不修改被测文件
- 输出可追溯问题（文件:行号 + 证据 + 严重度 + 修复建议）
- 覆盖：API密钥/凭据泄露、危险函数、SQL注入、多线程止损失效/竞态/锁问题、
  asyncio 阻塞/取消/共享状态、回测实盘一致性
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from audit import run_security_audit, audit_dir_for_concurrency, AuditResult

_SEV_ORDER = {"高": 0, "中": 1, "低": 2}


def _merge(results: list) -> AuditResult:
    merged = AuditResult()
    for r in results:
        merged.findings.extend(r.findings)
        merged.scanned_files += r.scanned_files
        merged.scanned_lines += r.scanned_lines
    merged.findings.sort(key=lambda f: (_SEV_ORDER.get(f.severity, 3), f.file, f.line))
    return merged


def _render(result: AuditResult, mode: str) -> str:
    lines = []
    lines.append("=" * 66)
    lines.append(f"交易系统代码审计报告（{'安全扫描 + 并发审计' if mode == 'all' else mode}）")
    lines.append("=" * 66)
    lines.append(f"扫描文件: {result.scanned_files} 个 | 扫描行数: {result.scanned_lines}")
    lines.append(f"发现: 高 {result.high_count} / 中 {result.medium_count} / 低 {result.low_count} / 合计 {len(result.findings)}")
    lines.append("-" * 66)

    if not result.findings:
        lines.append("未发现安全问题（扫描范围内）。")
    else:
        for f in result.findings:
            loc = f"{f.file}:{f.line}" if f.line else f.file
            lines.append(f"[{f.severity}] {f.rule} @ {loc}")
            if f.match:
                lines.append(f"    证据: {f.match}")
            lines.append(f"    说明: {f.message}")
            if f.fix:
                lines.append(f"    修复: {f.fix}")
            lines.append("")

    lines.append("-" * 66)
    lines.append("说明：以上为静态规则扫描结果，供人工复核；未执行被测代码。")
    lines.append("修复建议：请结合上下文逐条确认后修改，修改完成后可重跑本审计确认问题消除。")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        prog="run_audit.py",
        description="multi-strategy-quant-research-pro 交易系统代码审计（静态扫描，不执行被测代码）")
    parser.add_argument("--target", required=True, help="待审计文件或目录路径")
    parser.add_argument("--mode", choices=["security", "concurrency", "all"], default="all",
                        help="审计模式: security=静态安全扫描 / concurrency=并发安全审计 / all=全部（默认）")
    args = parser.parse_args()

    target = args.target
    if not os.path.exists(target):
        print(f"错误: 路径不存在: {target}")
        return

    results = []
    if args.mode in ("security", "all"):
        r = run_security_audit(target)
        results.append(r)
    if args.mode in ("concurrency", "all"):
        r2 = AuditResult()
        audit_dir_for_concurrency(target, r2)
        results.append(r2)

    merged = _merge(results)
    print(_render(merged, args.mode))


if __name__ == "__main__":
    main()
